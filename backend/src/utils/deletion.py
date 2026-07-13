# backend/src/utils/deletion.py
"""Shared cascade-deletion helpers.

These functions bulk-delete related rows in the correct order and return counts,
but never commit — the caller owns the transaction (so a document cascade can
delete trials, sets, and the document itself in a single commit). They exist to
be reused by both the trial/document endpoints, keeping the fragile delete
ordering (evaluation metrics have no DB-level ``ON DELETE``; trial-result /
metric ``document_id`` FKs are ``RESTRICT``) in one place.
"""

from __future__ import annotations

import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import models
from ..models.project import document_set_association


def trials_referencing_docs(
    db: Session, project_id: int, doc_ids: list[int]
) -> list[tuple[int, str | None, datetime.datetime | None]]:
    """Return ``(id, name, created_at)`` for trials in ``project_id`` whose
    ``document_ids`` JSON list contains any of ``doc_ids``.

    Loads only lightweight columns instead of full Trial rows (which include
    ``meta``, ``advanced_options``, schema/prompt snapshots, etc.). Membership
    is checked in Python to stay compatible with both SQLite (tests) and
    PostgreSQL (prod), since JSON array containment operators differ between
    the two.
    """
    if not doc_ids:
        return []
    doc_id_set = set(doc_ids)
    rows = db.execute(
        select(
            models.Trial.id,
            models.Trial.name,
            models.Trial.document_ids,
            models.Trial.created_at,
        ).where(models.Trial.project_id == project_id)
    ).all()
    return [
        (row[0], row[1], row[3])
        for row in rows
        if row[2] and doc_id_set.intersection(row[2])
    ]


def cascade_delete_trials(db: Session, trial_ids: list[int]) -> dict[str, int]:
    """Bulk-delete trials and their children (evaluation metrics → evaluations →
    trial results → trials), in the order required by the FK constraints.

    Does not commit. Returns counts of deleted rows.
    """
    if not trial_ids:
        return {"trials": 0, "results": 0, "evaluations": 0}

    eval_count = (
        db.scalar(
            select(func.count())
            .select_from(models.Evaluation)
            .where(models.Evaluation.trial_id.in_(trial_ids))
        )
        or 0
    )
    result_count = (
        db.scalar(
            select(func.count())
            .select_from(models.TrialResult)
            .where(models.TrialResult.trial_id.in_(trial_ids))
        )
        or 0
    )

    # Evaluation-metric children are removed before their evaluations (the FK has
    # no DB-level ON DELETE), then evaluations and trial results, then the trials.
    eval_ids = select(models.Evaluation.id).where(
        models.Evaluation.trial_id.in_(trial_ids)
    )
    db.execute(
        delete(models.EvaluationMetric).where(
            models.EvaluationMetric.evaluation_id.in_(eval_ids)
        )
    )
    db.execute(
        delete(models.Evaluation).where(models.Evaluation.trial_id.in_(trial_ids))
    )
    db.execute(
        delete(models.TrialResult).where(models.TrialResult.trial_id.in_(trial_ids))
    )
    # Core-delete the trial rows (rather than ORM db.delete) so the ORM doesn't
    # re-run a delete-orphan cascade over the children we just bulk-deleted.
    db.execute(delete(models.Trial).where(models.Trial.id.in_(trial_ids)))

    return {
        "trials": len(trial_ids),
        "results": result_count,
        "evaluations": eval_count,
    }


def cascade_delete_document_sets(db: Session, set_ids: list[int]) -> dict[str, int]:
    """Delete document sets (groups) and their membership rows.

    ``Trial.document_set_id`` is ``ON DELETE SET NULL``, so trials that reference
    a deleted set are simply detached, not removed. Does not commit.
    """
    if not set_ids:
        return {"document_sets": 0}

    db.execute(
        delete(document_set_association).where(
            document_set_association.c.document_set_id.in_(set_ids)
        )
    )
    db.execute(delete(models.DocumentSet).where(models.DocumentSet.id.in_(set_ids)))
    return {"document_sets": len(set_ids)}


def cascade_clear_document_references(
    db: Session, project_id: int, doc_ids: list[int]
) -> dict[str, int]:
    """Delete everything that would otherwise block deleting ``doc_ids``: whole
    trials (with their evaluations/results), whole groups, and any residual
    result/metric rows tied directly to those docs.

    Does **not** delete the documents themselves and does **not** commit — the
    caller deletes the documents (or their parent file) and owns the transaction.
    Returns merged counts. Shared by the document- and file-level cascade deletes.
    """
    counts: dict[str, int] = {
        "trials": 0,
        "results": 0,
        "evaluations": 0,
        "document_sets": 0,
    }
    if not doc_ids:
        return counts

    trial_ids = [tid for tid, _, _ in trials_referencing_docs(db, project_id, doc_ids)]
    counts.update(cascade_delete_trials(db, trial_ids))

    set_ids = [
        row[0]
        for row in db.execute(
            select(document_set_association.c.document_set_id)
            .where(document_set_association.c.document_id.in_(doc_ids))
            .distinct()
        ).all()
    ]
    counts.update(cascade_delete_document_sets(db, set_ids))

    db.execute(
        delete(models.EvaluationMetric).where(
            models.EvaluationMetric.document_id.in_(doc_ids)
        )
    )
    db.execute(
        delete(models.TrialResult).where(models.TrialResult.document_id.in_(doc_ids))
    )
    return counts


def compute_document_dependencies(
    db: Session, project_id: int, doc_ids: list[int]
) -> dict:
    """Summarize what a cascade delete of ``doc_ids`` would remove.

    Returns distinct counts (and a few display names) for the trials, document
    sets, trial results, evaluation metrics, and evaluations affected — computed
    over the whole selection so the frontend can show one aggregate preview.
    """
    empty = {
        "trials": {"count": 0, "names": []},
        "document_sets": {"count": 0, "names": []},
        "trial_results": 0,
        "evaluation_metrics": 0,
        "evaluations": 0,
    }
    if not doc_ids:
        return empty

    # Trials referencing any of the docs (JSON membership, in Python).
    trials = trials_referencing_docs(db, project_id, doc_ids)
    trial_names = [str(name or f"#{tid}") for tid, name, _ in trials]

    # Document sets containing any of the docs.
    set_rows = db.execute(
        select(models.DocumentSet.id, models.DocumentSet.name)
        .join(
            document_set_association,
            document_set_association.c.document_set_id == models.DocumentSet.id,
        )
        .where(document_set_association.c.document_id.in_(doc_ids))
        .distinct()
    ).all()
    set_names = [str(name or f"#{sid}") for sid, name in set_rows]

    trial_result_count = (
        db.scalar(
            select(func.count())
            .select_from(models.TrialResult)
            .where(models.TrialResult.document_id.in_(doc_ids))
        )
        or 0
    )
    metric_count = (
        db.scalar(
            select(func.count())
            .select_from(models.EvaluationMetric)
            .where(models.EvaluationMetric.document_id.in_(doc_ids))
        )
        or 0
    )
    # Distinct evaluations touched, either directly (via their metrics for these
    # docs) or through the affected trials.
    trial_ids = [tid for tid, _, _ in trials]
    eval_count = (
        db.scalar(
            select(func.count(func.distinct(models.Evaluation.id)))
            .select_from(models.Evaluation)
            .where(models.Evaluation.trial_id.in_(trial_ids))
        )
        or 0
        if trial_ids
        else 0
    )

    return {
        "trials": {"count": len(trials), "names": trial_names},
        "document_sets": {"count": len(set_rows), "names": set_names},
        "trial_results": trial_result_count,
        "evaluation_metrics": metric_count,
        "evaluations": eval_count,
    }
