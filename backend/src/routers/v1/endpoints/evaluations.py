"""Evaluation endpoints for projects."""

import csv
import io
import zipfile

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db
from ....utils.helpers import (
    build_evaluation_zipfiles,
    collect_evaluation_field_level_details,
    collect_trial_document_metadata,
)

router = APIRouter()


@router.get("/evaluation", response_model=list[schemas.Evaluation])
def get_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.Evaluation]:
    """Get evaluation results for all trials using a specific ground truth."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    # Get all evaluations for this ground truth
    evaluations = list(
        db.execute(
            select(models.Evaluation).where(
                models.Evaluation.groundtruth_id == groundtruth_id
            )
        )
        .scalars()
        .all()
    )

    return [schemas.Evaluation.model_validate(eval) for eval in evaluations]


@router.get(
    "/evaluation/{evaluation_id}", response_model=schemas.EvaluationDetail
)
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

    if current_user.role != "admin" and project.owner_id != current_user.id:
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
        documents=evaluation.document_metrics,
        created_at=evaluation.created_at,
    )

    return evaluation_detail


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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
    evaluation_ids: str = Query(...),
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
    from ....utils.helpers import (
        build_evaluation_zipfiles,
        collect_evaluation_field_level_details,
    )

    # Parse IDs
    try:
        evaluation_ids_list = [int(i) for i in evaluation_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evaluation_ids")

    # Fetch project and permission check
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arcname, data in files:
                zf.writestr(arcname, data)
        out.seek(0)
        content = out.getvalue()
        media_type = "application/zip"
        filename = f"evaluation_export_{project_id}.zip"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # --- CSV Export ---
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        # Summary
        writer.writerow(
            [
                "Evaluation ID",
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
            gt = db.query(models.GroundTruth).get(eval_obj.groundtruth_id)
            writer.writerow(
                [
                    eval_obj.id,
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
                    "Total Count",
                    "Correct Count",
                ]
            )
            for eval_obj, _ in evaluations:
                for field, metrics in (eval_obj.field_metrics or {}).items():
                    writer.writerow(
                        [
                            eval_obj.id,
                            field,
                            metrics.get("accuracy", 0),
                            metrics.get("total_count", 0),
                            metrics.get("correct_count", 0),
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
                gt = db.query(models.GroundTruth).get(eval_obj.groundtruth_id)
                summary_data.append(
                    {
                        "Evaluation ID": eval_obj.id,
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
                                "Total Count": metrics.get("total_count", 0),
                                "Correct Count": metrics.get("correct_count", 0),
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
                for eval_obj, trial in evaluations:
                    docs = collect_trial_document_metadata(
                        db,
                        trial,
                        include_content=include_document_content,
                        include_ground_truth=include_ground_truth_content,
                    )
                    if docs:
                        pd.DataFrame(docs).to_excel(
                            writer, sheet_name=f"Trial {trial.id} Docs", index=False
                        )
        output.seek(0)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"evaluation_report_{project_id}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/evaluation/batch", response_model=list[schemas.EvaluationSummary]
)
def batch_evaluate_trials(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_ids: list[int] = Body(...),
    groundtruth_id: int = Body(...),
    force_recalculate: bool = Body(False),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.EvaluationSummary]:
    """Evaluate multiple trials against ground truth."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
            errors.append(f"Error evaluating trial {trial_id}: {str(e)}")
    if errors and not results:
        raise HTTPException(
            status_code=400, detail=f"All evaluations failed: {'; '.join(errors)}"
        )
    return results


@router.get("/evaluation/compare", response_model=dict)
def compare_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_ids: list[int] = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Compare multiple evaluations side by side."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Get evaluations
    evaluations = []
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
                evaluations.append({"evaluation": eval_obj, "trial": trial})

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
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        all_fields.update(eval.field_metrics.keys())

    # Build evaluation summaries
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        trial = eval_data["trial"]

        comparison["evaluations"].append(
            {
                "id": eval.id,
                "trial_id": eval.trial_id,
                "model": trial.llm_model,
                "groundtruth_id": eval.groundtruth_id,
                "metrics": eval.metrics,
                "created_at": eval.created_at.isoformat(),
            }
        )

    # Compare overall metrics
    metrics_to_compare = ["accuracy", "precision", "recall", "f1_score"]
    for metric in metrics_to_compare:
        comparison["overall_comparison"][metric] = []
        for eval_data in evaluations:
            eval = eval_data["evaluation"]
            trial = eval_data["trial"]
            comparison["overall_comparison"][metric].append(
                {
                    "evaluation_id": eval.id,
                    "model": trial.llm_model,
                    "value": eval.metrics.get(metric, 0),
                }
            )

    # Compare field metrics
    for field in sorted(all_fields):
        comparison["field_comparison"][field] = []
        for eval_data in evaluations:
            eval = eval_data["evaluation"]
            trial = eval_data["trial"]
            field_metric = eval.field_metrics.get(field, {})
            comparison["field_comparison"][field].append(
                {
                    "evaluation_id": eval.id,
                    "model": trial.llm_model,
                    "accuracy": field_metric.get("accuracy", 0),
                    "total_count": field_metric.get("total_count", 0),
                    "correct_count": field_metric.get("correct_count", 0),
                }
            )

    # Group by model
    model_groups = {}
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        trial = eval_data["trial"]
        model = trial.llm_model

        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(eval.metrics.get("accuracy", 0))

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


@router.get(
    "/evaluation/{evaluation_id}/errors", response_model=list[dict]
)
def get_evaluation_errors(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    field_name: str | None = Query(None),
    error_type: str | None = Query(None),
    limit: int = Query(100),
    current_user: models.User = Depends(get_current_user),
) -> list[dict]:
    """Get detailed error analysis for an evaluation."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    # Build error details
    error_details = []
    for error in errors:
        # Get document info
        document = db.query(models.Document).get(error.document_id)

        error_detail = {
            "document_id": error.document_id,
            "document_name": document.original_file.file_name
            if document and document.original_file
            else "Unknown",
            "field_name": error.field_name,
            "ground_truth_value": error.ground_truth_value,
            "predicted_value": error.predicted_value,
            "error_type": error.error_type,
            "confidence_score": error.confidence_score,
        }

        # Add context if available
        if document:
            # Extract surrounding text for context
            text_snippet = document.text[:500] if document.text else ""
            error_detail["context"] = text_snippet

        error_details.append(error_detail)

    return error_details
