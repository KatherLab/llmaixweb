# backend/src/routers/v1/endpoints/evaluations.py
"""Evaluation endpoints for projects."""

import csv
import io
import logging

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only, selectinload

from .... import models, schemas
from ....core.security import can_access_project, get_current_user
from ....dependencies import get_db
from ....utils.audit import record_audit
from ....utils.csv_safety import SafeCsvWriter
from ....utils.enums import AuditAction
from ....utils.helpers import (
    build_evaluation_zipfiles,
    collect_evaluation_field_level_details,
    collect_trial_document_metadata,
    excel_sheet_name,
    trial_display_label,
)
from ....utils.streaming_zip import iter_zip, sanitize_arcname

logger = logging.getLogger(__name__)

router = APIRouter()


def _enrich_document_metrics(db: Session, evaluation: models.Evaluation) -> list[dict]:
    """Return ``evaluation.document_metrics`` enriched for display.

    Each document entry gains:
      - ``document_name`` — the Document's name (falling back to the original
        file name), so the evaluation table can show real names instead of
        ``Document #<id>`` (consistent with the Documents tab).
      - ``field_details`` — per-field GT/predicted values, needed by the
        frontend confusion-matrix filter (otherwise it matches zero docs).

    Documents and EvaluationMetric rows are batch-loaded (one query each) to
    avoid N+1 per document.
    """
    doc_metrics = evaluation.document_metrics or []
    if not doc_metrics:
        return []

    doc_ids = []
    for doc in doc_metrics:
        try:
            doc_ids.append(int(doc.get("document_id")))
        except (TypeError, ValueError):
            continue
    if not doc_ids:
        return [dict(d) if not isinstance(d, dict) else dict(d) for d in doc_metrics]

    # Batch-load documents + their original_file (one query).
    documents_by_id: dict[int, models.Document] = {
        doc.id: doc
        for doc in db.execute(
            select(models.Document)
            .where(models.Document.id.in_(doc_ids))
            .options(selectinload(models.Document.original_file))
        )
        .scalars()
        .all()
    }

    # Batch-load per-field metric details (one query).
    field_details_by_doc: dict[int, dict] = {}
    details = (
        db.query(models.EvaluationMetric)
        .filter(models.EvaluationMetric.evaluation_id == evaluation.id)
        .all()
    )
    for detail in details:
        field_details_by_doc.setdefault(detail.document_id, {})[detail.field_name] = (
            schemas.EvaluationMetricDetail(
                document_id=detail.document_id,
                field_name=detail.field_name,
                ground_truth_value=detail.ground_truth_value,
                predicted_value=detail.predicted_value,
                is_correct=detail.is_correct,
                error_type=detail.error_type,
                confidence_score=detail.confidence_score,
            )
        )

    enriched = []
    for doc in doc_metrics:
        doc_dict = dict(doc) if not isinstance(doc, dict) else dict(doc)
        doc_id = doc_dict.get("document_id")
        document = documents_by_id.get(int(doc_id)) if doc_id is not None else None
        # Mirror the Documents-tab resolution order: document_name, then the
        # original file name. Leave the frontend's `Document #<id>` fallback
        # intact when neither is available.
        if document:
            doc_dict["document_name"] = (
                document.document_name
                or (
                    document.original_file.file_name if document.original_file else None
                )
                or doc_dict.get("document_name")
            )
        doc_dict["field_details"] = field_details_by_doc.get(
            int(doc_id) if doc_id is not None else -1, {}
        )
        enriched.append(doc_dict)
    return enriched


@router.get("/evaluation", response_model=list[schemas.EvaluationListItem])
def get_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int = Query(...),
    current_user: models.User = Depends(get_current_user),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[schemas.EvaluationListItem]:
    """List evaluation summaries for all trials using a specific ground truth.

    Returns the lightweight ``EvaluationListItem`` (overall metrics only). The
    heavy per-field / per-document metric columns are deferred via ``load_only``
    so they are never fetched for the list — clients read those from the
    per-evaluation detail endpoint.
    """
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Verify ground truth exists for this project
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Get all evaluations for this ground truth. Load only the columns the
    # summary needs; field_metrics / document_metrics / confusion_matrices
    # (potentially multi-MB JSON each) stay deferred and are never fetched here.
    # Join the trial to surface its project-wise number ("Trial #N" in the UI)
    # alongside the global trial_id, so the list/export match what users see.
    rows = list(
        db.execute(
            select(
                models.Evaluation,
                models.Trial.name,
                models.Trial.project_trial_number,
            )
            .join(models.Trial, models.Trial.id == models.Evaluation.trial_id)
            .options(
                load_only(
                    models.Evaluation.id,
                    models.Evaluation.trial_id,
                    models.Evaluation.groundtruth_id,
                    models.Evaluation.metrics,
                    models.Evaluation.created_at,
                )
            )
            .where(models.Evaluation.groundtruth_id == groundtruth_id)
            .order_by(models.Evaluation.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items: list[schemas.EvaluationListItem] = []
    for eval_obj, trial_name, project_trial_number in rows:
        item = schemas.EvaluationListItem.model_validate(eval_obj)
        item.trial_name = trial_name
        item.project_trial_number = project_trial_number
        items.append(item)
    return items


# NOTE: this static route must stay declared before the dynamic
# /evaluation/{evaluation_id} route below, or "compare" is captured as an id.
@router.get("/evaluation/compare", response_model=dict)
def compare_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_ids: list[int] = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Compare multiple evaluations side by side."""
    # Cap the number of evaluations in a single comparison to bound the
    # side-by-side matrix and per-eval queries.
    max_evaluations = 10
    if len(evaluation_ids) > max_evaluations:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot compare more than {max_evaluations} evaluations at once "
            f"(requested {len(evaluation_ids)}).",
        )

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Get evaluations
    evaluations: list[tuple[models.Evaluation, models.Trial]] = []
    for eval_id in evaluation_ids:
        eval_obj = db.execute(
            select(models.Evaluation).where(models.Evaluation.id == eval_id)
        ).scalar_one_or_none()

        if eval_obj:
            # Verify it belongs to project
            trial = db.execute(
                select(models.Trial).where(
                    models.Trial.id == eval_obj.trial_id,
                    models.Trial.project_id == project_id,
                )
            ).scalar_one_or_none()

            if trial:
                evaluations.append((eval_obj, trial))

    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found")

    # Build comparison
    comparison = {
        "evaluations": [],
        "overall_comparison": {},
        "field_comparison": {},
        "model_comparison": {},
    }

    # Collect all fields
    all_fields = set()
    for eval_obj, _trial in evaluations:
        all_fields.update(eval_obj.field_metrics.keys())

    # Build evaluation summaries
    for eval_obj, trial in evaluations:
        comparison["evaluations"].append(
            {
                "id": eval_obj.id,
                "trial_id": eval_obj.trial_id,
                "model": trial.llm_model,
                "groundtruth_id": eval_obj.groundtruth_id,
                "metrics": eval_obj.metrics,
                "created_at": eval_obj.created_at.isoformat(),
            }
        )

    # Compare overall metrics
    metrics_to_compare = ["accuracy", "precision", "recall", "f1_score"]
    for metric in metrics_to_compare:
        comparison["overall_comparison"][metric] = []
        for eval_obj, trial in evaluations:
            comparison["overall_comparison"][metric].append(
                {
                    "evaluation_id": eval_obj.id,
                    "model": trial.llm_model,
                    "value": eval_obj.metrics.get(metric, 0),
                }
            )

    # Compare field metrics
    for field in sorted(all_fields):
        comparison["field_comparison"][field] = []
        for eval_obj, trial in evaluations:
            field_metric = eval_obj.field_metrics.get(field, {})
            comparison["field_comparison"][field].append(
                {
                    "evaluation_id": eval_obj.id,
                    "model": trial.llm_model,
                    "accuracy": field_metric.get("accuracy", 0),
                    "total_count": field_metric.get("total_count", 0),
                    "correct_count": field_metric.get("correct_count", 0),
                }
            )

    # Group by model
    model_groups = {}
    for eval_obj, trial in evaluations:
        model = trial.llm_model

        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(eval_obj.metrics.get("accuracy", 0))

    comparison["model_comparison"] = {
        model: {
            "average_accuracy": sum(accuracies) / len(accuracies),
            "evaluation_count": len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
        }
        for model, accuracies in model_groups.items()
    }

    return comparison


@router.get("/evaluation/{evaluation_id}", response_model=schemas.EvaluationDetail)
def get_evaluation_detail(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.EvaluationDetail:
    """Get detailed evaluation for a specific trial/ground truth pair."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Ensure the evaluation belongs to a trial in this project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )

    # Get detailed evaluation data
    evaluation_detail = schemas.EvaluationDetail(
        id=evaluation.id,
        trial_id=evaluation.trial_id,
        groundtruth_id=evaluation.groundtruth_id,
        model=trial.llm_model,
        metrics=evaluation.metrics,
        document_count=len(evaluation.document_metrics),
        fields=evaluation.field_metrics,
        documents=_enrich_document_metrics(db, evaluation),
        confusion_matrices=evaluation.confusion_matrices,
        created_at=evaluation.created_at,
    )

    return evaluation_detail


@router.delete("/evaluation/{evaluation_id}", status_code=204)
def delete_evaluation(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    current_user: models.User = Depends(get_current_user),
) -> None:
    """Delete an evaluation and its detailed metrics.

    The trial and ground-truth data are preserved; only the computed
    evaluation record (and its child ``EvaluationMetric`` rows, via cascade)
    is removed. Re-evaluating the trial will recreate it.
    """
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this project's evaluations",
        )

    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Ensure the evaluation belongs to a trial in this project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )

    db.delete(evaluation)
    db.commit()

    record_audit(
        AuditAction.DELETE,
        actor=current_user,
        resource_type="evaluation",
        resource_id=evaluation_id,
        project_id=project_id,
    )


@router.get(
    "/evaluation/{evaluation_id}/document/{document_id}",
    response_model=schemas.DocumentEvaluationDetail,
)
def get_document_evaluation(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.DocumentEvaluationDetail:
    """Get detailed evaluation for a single document."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )
    # Get evaluation
    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    # Verify evaluation belongs to project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )
    # Find document metrics
    doc_metrics = None
    for metrics in evaluation.document_metrics:
        if metrics["document_id"] == document_id:
            doc_metrics = metrics
            break
    if not doc_metrics:
        raise HTTPException(status_code=404, detail="Document not found in evaluation")
    # Get detailed metrics
    field_details = {}
    details = (
        db.query(models.EvaluationMetric)
        .filter(
            models.EvaluationMetric.evaluation_id == evaluation_id,
            models.EvaluationMetric.document_id == document_id,
        )
        .all()
    )
    for detail in details:
        field_details[detail.field_name] = schemas.EvaluationMetricDetail(
            document_id=document_id,
            field_name=detail.field_name,
            ground_truth_value=detail.ground_truth_value,
            predicted_value=detail.predicted_value,
            is_correct=detail.is_correct,
            error_type=detail.error_type,
            confidence_score=detail.confidence_score,
        )
    return schemas.DocumentEvaluationDetail(
        document_id=document_id,
        accuracy=doc_metrics["accuracy"],
        correct_fields=doc_metrics["correct_fields"],
        total_fields=doc_metrics["total_fields"],
        missing_fields=doc_metrics.get("missing_fields", []),
        incorrect_fields=doc_metrics.get("incorrect_fields", []),
        field_details=field_details,
        error=doc_metrics.get("error"),
        has_error=doc_metrics.get("has_error"),
    )


@router.get("/evaluations/download", response_class=Response)
def download_evaluations_report(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_ids: list[str] = Query(...),
    format: str = Query("csv", enum=["csv", "xlsx", "zip"]),
    include_details: bool = Query(True),
    include_field_details: bool = Query(False),
    include_errors: bool = Query(False),
    include_document_content: bool = Query(False),
    include_ground_truth_content: bool = Query(False),
    current_user: "models.User" = Depends(get_current_user),
) -> Response:
    """
    Download evaluation report in CSV, XLSX, or ZIP format.
    ZIP: includes summary, per-field, per-doc content as separate files.
    """

    # Parse IDs. Accept both the repeated-param form
    # (?evaluation_ids=1&evaluation_ids=2, what the frontend sends) and the
    # legacy single comma-separated string (?evaluation_ids=1,2). Previously the
    # param was a scalar `str`, so repeated params collapsed to the last value
    # and a multi-evaluation export silently returned only one evaluation.
    try:
        evaluation_ids_list = [
            int(part)
            for value in evaluation_ids
            for part in str(value).split(",")
            if part.strip()
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evaluation_ids")
    if not evaluation_ids_list:
        raise HTTPException(status_code=400, detail="No evaluation_ids provided")

    # Cap the batch: the gather loop issues two DB queries per evaluation (N+1).
    # Compare with compare_evaluations (cap = 10).
    max_evaluations = 50
    if len(evaluation_ids_list) > max_evaluations:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot download more than {max_evaluations} evaluations at once "
            f"(requested {len(evaluation_ids_list)}).",
        )

    # Fetch project and permission check
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Gather evaluations (and their trials)
    evaluations = []
    for eval_id in evaluation_ids_list:
        eval_obj = db.execute(
            select(models.Evaluation).where(models.Evaluation.id == eval_id)
        ).scalar_one_or_none()
        if eval_obj:
            trial = db.execute(
                select(models.Trial).where(
                    models.Trial.id == eval_obj.trial_id,
                    models.Trial.project_id == project_id,
                )
            ).scalar_one_or_none()
            if trial:
                evaluations.append((eval_obj, trial))
    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found")

    # Audit the export before streaming. This endpoint can bundle raw document
    # text and ground-truth values (PHI) into the file via the *_content flags,
    # so it is a PHI-egress event that must leave a trail. detail records the
    # scope (which evaluations, format, and whether PHI content was included) —
    # never the content itself.
    record_audit(
        AuditAction.EXPORT,
        actor=current_user,
        resource_type="evaluation",
        project_id=project_id,
        detail={
            "evaluation_ids": [e.id for e, _ in evaluations],
            "format": format,
            "include_document_content": include_document_content,
            "include_ground_truth_content": include_ground_truth_content,
        },
    )

    # --- ZIP Export ---
    if format == "zip":
        files = build_evaluation_zipfiles(
            db,
            evaluations,
            include_details=include_details,
            include_field_details=include_field_details,
            include_errors=include_errors,
            include_document_content=include_document_content,
            include_ground_truth_content=include_ground_truth_content,
            zip_format="csv",
        )
        filename = f"evaluation_export_{project_id}.zip"
        # Stream: entries (incl. per-document texts) are produced lazily by the
        # generator, so the archive is never assembled in memory.
        return StreamingResponse(
            iter_zip((sanitize_arcname(arcname), data) for arcname, data in files),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # --- CSV Export ---
    if format == "csv":
        output = io.StringIO()
        writer = SafeCsvWriter(csv.writer(output))
        # Summary
        writer.writerow(
            [
                "Evaluation ID",
                "Trial",
                "Trial Number",
                "Trial ID",
                "Model",
                "Ground Truth",
                "Accuracy",
                "Precision",
                "Recall",
                "F1 Score",
                "Total Documents",
                "Total Fields",
                "Created At",
            ]
        )
        for eval_obj, trial in evaluations:
            gt = db.get(models.GroundTruth, eval_obj.groundtruth_id)
            writer.writerow(
                [
                    eval_obj.id,
                    trial_display_label(trial),
                    trial.project_trial_number,
                    eval_obj.trial_id,
                    trial.llm_model,
                    gt.name if gt else "Unknown",
                    eval_obj.metrics.get("accuracy", 0),
                    eval_obj.metrics.get("precision", 0),
                    eval_obj.metrics.get("recall", 0),
                    eval_obj.metrics.get("f1_score", 0),
                    eval_obj.metrics.get("total_documents", 0),
                    eval_obj.metrics.get("total_fields", 0),
                    eval_obj.created_at.isoformat(),
                ]
            )
        # Field metrics
        if include_details:
            writer.writerow([])
            writer.writerow(["Field-Level Metrics"])
            writer.writerow(
                [
                    "Evaluation ID",
                    "Field Name",
                    "Accuracy",
                    "Precision",
                    "Recall",
                    "F1 Score",
                    "Total Count",
                    "Correct Count",
                    "Error Count",
                ]
            )
            for eval_obj, _ in evaluations:
                for field, metrics in (eval_obj.field_metrics or {}).items():
                    writer.writerow(
                        [
                            eval_obj.id,
                            field,
                            metrics.get("accuracy", 0),
                            metrics.get("precision", 0),
                            metrics.get("recall", 0),
                            metrics.get("f1_score", 0),
                            metrics.get("total_count", 0),
                            metrics.get("correct_count", 0),
                            metrics.get("error_count", 0),
                        ]
                    )
        # Field-by-field details
        if include_field_details:
            writer.writerow([])
            writer.writerow(["Field-by-Field Details"])
            headers = [
                "Evaluation ID",
                "Document ID",
                "Field Name",
                "Ground Truth",
                "Prediction",
                "Is Correct",
            ]
            if include_errors:
                headers += ["Error Type", "Confidence"]
            writer.writerow(headers)
            for eval_obj, _ in evaluations:
                details = collect_evaluation_field_level_details(
                    db, eval_obj, include_errors
                )
                for detail in details:
                    row = [
                        detail.get("Evaluation ID", ""),
                        detail.get("Document ID", ""),
                        detail.get("Field Name", ""),
                        detail.get("Ground Truth", ""),
                        detail.get("Prediction", ""),
                        detail.get("Is Correct", ""),
                    ]
                    if include_errors:
                        row += [
                            detail.get("Error Type", ""),
                            detail.get("Confidence", ""),
                        ]
                    writer.writerow(row)
        # Document metrics
        if include_details:
            writer.writerow([])
            writer.writerow(["Document-Level Metrics"])
            writer.writerow(
                [
                    "Evaluation ID",
                    "Document ID",
                    "Accuracy",
                    "Correct Fields",
                    "Total Fields",
                    "Missing Fields",
                    "Incorrect Fields",
                    "Error",
                ]
            )
            for eval_obj, _ in evaluations:
                for doc_metrics in eval_obj.document_metrics:
                    writer.writerow(
                        [
                            eval_obj.id,
                            doc_metrics.get("document_id"),
                            doc_metrics.get("accuracy"),
                            doc_metrics.get("correct_fields"),
                            doc_metrics.get("total_fields"),
                            ";".join(doc_metrics.get("missing_fields", [])),
                            ";".join(doc_metrics.get("incorrect_fields", [])),
                            doc_metrics.get("error", ""),
                        ]
                    )
        # Document metadata/content/GT per doc
        if include_document_content or include_ground_truth_content:
            writer.writerow([])
            writer.writerow(["Document Metadata and Content"])
            doc_header_written = False
            for eval_obj, trial in evaluations:
                docs = collect_trial_document_metadata(
                    db,
                    trial,
                    include_content=include_document_content,
                    include_ground_truth=include_ground_truth_content,
                )
                if docs and not doc_header_written:
                    writer.writerow(docs[0].keys())
                    doc_header_written = True
                for doc in docs:
                    writer.writerow([doc.get(col, "") for col in docs[0].keys()])

        content = output.getvalue()
        media_type = "text/csv"
        filename = f"evaluation_report_{project_id}.csv"

    # --- XLSX Export ---
    else:  # format == "xlsx"
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Summary
            summary_data = []
            for eval_obj, trial in evaluations:
                gt = db.get(models.GroundTruth, eval_obj.groundtruth_id)
                summary_data.append(
                    {
                        "Evaluation ID": eval_obj.id,
                        "Trial": trial_display_label(trial),
                        "Trial Number": trial.project_trial_number,
                        "Trial ID": eval_obj.trial_id,
                        "Model": trial.llm_model,
                        "Ground Truth": gt.name if gt else "Unknown",
                        "Accuracy": eval_obj.metrics.get("accuracy", 0),
                        "Precision": eval_obj.metrics.get("precision", 0),
                        "Recall": eval_obj.metrics.get("recall", 0),
                        "F1 Score": eval_obj.metrics.get("f1_score", 0),
                        "Total Documents": eval_obj.metrics.get("total_documents", 0),
                        "Total Fields": eval_obj.metrics.get("total_fields", 0),
                        "Created At": eval_obj.created_at.isoformat(),
                    }
                )
            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary", index=False
            )
            # Field metrics
            if include_details:
                field_data = []
                for eval_obj, _ in evaluations:
                    for field, metrics in (eval_obj.field_metrics or {}).items():
                        field_data.append(
                            {
                                "Evaluation ID": eval_obj.id,
                                "Field Name": field,
                                "Accuracy": metrics.get("accuracy", 0),
                                "Precision": metrics.get("precision", 0),
                                "Recall": metrics.get("recall", 0),
                                "F1 Score": metrics.get("f1_score", 0),
                                "Total Count": metrics.get("total_count", 0),
                                "Correct Count": metrics.get("correct_count", 0),
                                "Error Count": metrics.get("error_count", 0),
                            }
                        )
                if field_data:
                    pd.DataFrame(field_data).to_excel(
                        writer, sheet_name="Field Metrics", index=False
                    )
            # Field-by-field details
            if include_field_details:
                all_details = []
                for eval_obj, _ in evaluations:
                    all_details.extend(
                        collect_evaluation_field_level_details(
                            db, eval_obj, include_errors
                        )
                    )
                if all_details:
                    pd.DataFrame(all_details).to_excel(
                        writer, sheet_name="Field Details", index=False
                    )
            # Document metrics
            if include_details:
                doc_data = []
                for eval_obj, _ in evaluations:
                    for doc_metrics in eval_obj.document_metrics:
                        doc_data.append(
                            {
                                "Evaluation ID": eval_obj.id,
                                "Document ID": doc_metrics.get("document_id"),
                                "Accuracy": doc_metrics.get("accuracy"),
                                "Correct Fields": doc_metrics.get("correct_fields"),
                                "Total Fields": doc_metrics.get("total_fields"),
                                "Missing Fields": ";".join(
                                    doc_metrics.get("missing_fields", [])
                                ),
                                "Incorrect Fields": ";".join(
                                    doc_metrics.get("incorrect_fields", [])
                                ),
                                "Error": doc_metrics.get("error", ""),
                            }
                        )
                if doc_data:
                    pd.DataFrame(doc_data).to_excel(
                        writer, sheet_name="Document Metrics", index=False
                    )
            # Document metadata/content/GT per doc
            if include_document_content or include_ground_truth_content:
                used_sheet_names: set[str] = {
                    "Summary",
                    "Field Metrics",
                    "Field Details",
                    "Document Metrics",
                }
                for eval_obj, trial in evaluations:
                    docs = collect_trial_document_metadata(
                        db,
                        trial,
                        include_content=include_document_content,
                        include_ground_truth=include_ground_truth_content,
                    )
                    if docs:
                        pd.DataFrame(docs).to_excel(
                            writer,
                            sheet_name=excel_sheet_name(
                                f"{trial_display_label(trial)} Docs",
                                fallback=f"Trial {trial.project_trial_number} Docs",
                                used=used_sheet_names,
                            ),
                            index=False,
                        )
        output.seek(0)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"evaluation_report_{project_id}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/evaluation/batch", response_model=list[schemas.Evaluation])
def batch_evaluate_trials(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_ids: list[int] = Body(...),
    groundtruth_id: int = Body(...),
    force_recalculate: bool = Body(False),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.Evaluation]:
    """Evaluate multiple trials against ground truth."""
    # Cap the batch to bound work (each trial evaluation recomputes metrics
    # across all its documents).
    max_trials = 200
    if len(trial_ids) > max_trials:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot evaluate more than {max_trials} trials at once "
            f"(requested {len(trial_ids)}).",
        )
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to evaluate trials for this project"
        )
    # Verify ground truth
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")
    # Evaluate trials
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    results = []
    errors = []
    for trial_id in trial_ids:
        try:
            # Verify trial exists
            trial: models.Trial | None = db.execute(
                select(models.Trial).where(
                    models.Trial.project_id == project_id, models.Trial.id == trial_id
                )
            ).scalar_one_or_none()
            if not trial:
                errors.append(f"Trial {trial_id} not found")
                continue
            evaluation = engine.evaluate_trial(
                trial_id=trial_id,
                groundtruth_id=groundtruth_id,
                force_recalculate=force_recalculate,
            )
            results.append(evaluation)
        except Exception as e:
            # Log the full error server-side; only a category-only message
            # reaches the client (str(e) can contain DB internals / paths).
            logger.warning("Error evaluating trial %s: %s", trial_id, e, exc_info=True)
            errors.append(f"Error evaluating trial {trial_id}")
    if errors and not results:
        raise HTTPException(
            status_code=400, detail=f"All evaluations failed: {'; '.join(errors)}"
        )
    record_audit(
        AuditAction.CREATE,
        actor=current_user,
        resource_type="evaluation",
        project_id=project_id,
        detail={
            "groundtruth_id": groundtruth_id,
            "evaluated": len(results),
            "errors": len(errors),
        },
    )
    return results


@router.get("/evaluation/{evaluation_id}/errors", response_model=list[dict])
def get_evaluation_errors(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    field_name: str | None = Query(None),
    error_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: models.User = Depends(get_current_user),
) -> list[dict]:
    """Get detailed error analysis for an evaluation."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Get evaluation
    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Verify evaluation belongs to project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )

    # Get errors from detailed metrics
    query = db.query(models.EvaluationMetric).filter(
        models.EvaluationMetric.evaluation_id == evaluation_id,
        ~models.EvaluationMetric.is_correct,
    )

    if field_name:
        query = query.filter(models.EvaluationMetric.field_name == field_name)

    if error_type:
        query = query.filter(models.EvaluationMetric.error_type == error_type)

    errors = query.limit(limit).all()

    # Batch-load the referenced documents' display name and a 500-char snippet
    # in one query. substr() runs in the database, so the full text column
    # (potentially hundreds of KB per document) is never hydrated just to show
    # a context preview.
    doc_ids = {error.document_id for error in errors if error.document_id}
    doc_info_by_id: dict[int, tuple[str | None, str]] = {}
    if doc_ids:
        rows = db.execute(
            select(
                models.Document.id,
                models.File.file_name,
                func.substr(models.Document.text, 1, 500),
            )
            .outerjoin(models.File, models.File.id == models.Document.original_file_id)
            .where(models.Document.id.in_(doc_ids))
        ).all()
        doc_info_by_id = {row[0]: (row[1], row[2] or "") for row in rows}

    # Build error details
    error_details = []
    for error in errors:
        doc_info = doc_info_by_id.get(error.document_id) if error.document_id else None

        error_detail = {
            "document_id": error.document_id,
            "document_name": doc_info[0] if doc_info and doc_info[0] else "Unknown",
            "field_name": error.field_name,
            "ground_truth_value": error.ground_truth_value,
            "predicted_value": error.predicted_value,
            "error_type": error.error_type,
            "confidence_score": error.confidence_score,
        }

        # Add context if available
        if doc_info:
            error_detail["context"] = doc_info[1]

        error_details.append(error_detail)

    return error_details
