# backend/src/utils/notifications.py
"""Notification email: who gets told what, and when.

Four categories, each independently opt-out-able per user (see
``models.user.NotificationPreference``):

* **job_finished** — a preprocessing task or extraction run reached a terminal
  state. Sent to whoever *started* it (``created_by_id``), falling back to the
  project owner for rows that predate that column. Deliberately not sent to every
  project member: a collaborator running their own batch shouldn't fill the
  owner's inbox.
* **project_shared** — someone was granted access, or their permission changed.
* **security** — password changed, account locked, SSO identity linked/unlinked.
* **admin_alerts** — operational problems, to admins only, rate-limited per kind.

Two rules the whole module is built around:

1. **No PHI.** Emails carry counts, timestamps, durations, model names, and the
   *labels* a user typed themselves (project name, run name) — never document
   names, file names, extracted values, or error text from a document. Anything
   more specific stays behind the deep link, which requires a login.
2. **Notification failure is never job failure.** Every public function swallows
   its own exceptions: these are called from Celery finalizers and request
   handlers where raising would turn "your email didn't arrive" into "your
   extraction run is marked failed".

Delivery itself is deferred to a Celery task because ``smtplib`` blocks for up to
15 seconds — far too long to hold an OCR worker or an HTTP response. When Celery
is unavailable the send happens on a throwaway thread instead.
"""

import logging
import threading
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.dynamic_settings import get_settings
from ..models.project import (
    PreprocessingStatus,
    PreprocessingTask,
    Project,
    ProjectShare,
    Trial,
    TrialResult,
    TrialStatus,
)
from ..models.user import NotificationPreference, User
from ..utils.enums import (
    NotificationCategory,
    ProjectPermission,
    TrialResultStatus,
    UserRole,
)
from . import email_service, presence
from .email_i18n import format_duration, translate

logger = logging.getLogger(__name__)

JobKind = Literal["preprocessing", "trial"]
JobOutcome = Literal["completed", "partial", "failed"]

SECURITY_EVENTS = frozenset(
    {
        "password_changed",
        "password_reset_by_admin",
        "account_locked",
        "identity_linked",
        "identity_unlinked",
    }
)

ADMIN_ALERT_KINDS = frozenset({"worker_crash", "stuck_tasks", "error_spike"})

# Fallback dedupe for admin alerts when Redis is unavailable. Per-process only,
# so with several workers an alert can slip through once per process — still far
# better than one email per occurrence, and the Redis path (the normal one) is
# properly global.
_local_alert_cooldown: dict[str, float] = {}
_local_alert_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Preferences
# --------------------------------------------------------------------------- #
def preferences_for(user: User) -> dict[str, Any]:
    """Effective notification preferences for a user.

    Users without a preferences row (i.e. everyone who never opened the settings)
    get ``NotificationPreference.DEFAULTS``, so this never returns None and no
    backfill migration is needed.
    """
    row = getattr(user, "notification_preference", None)
    if row is None:
        return dict(NotificationPreference.DEFAULTS)
    return {
        "job_finished": row.job_finished,
        "project_shared": row.project_shared,
        "security": row.security,
        "admin_alerts": row.admin_alerts,
        "only_when_away": row.only_when_away,
        "min_job_seconds": row.min_job_seconds,
    }


def _wants(user: User, category: NotificationCategory) -> bool:
    return bool(preferences_for(user).get(category.value, True))


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #
def _notifications_enabled() -> bool:
    """Whether notification email may be sent at all right now."""
    settings = get_settings()
    return bool(settings.NOTIFICATIONS_ENABLED) and email_service.is_configured()


def _deliverable(user: User | None) -> bool:
    """Whether we can and should email this user at all."""
    return bool(user and user.is_active and user.email)


def _app_url() -> str:
    return str(get_settings().APP_URL or "").rstrip("/")


def _account_url() -> str:
    return f"{_app_url()}/account"


def _project_url(project_id: int, tab: str, **params: Any) -> str:
    """Deep link into a project tab.

    Mirrors the query parameters ``ProjectDetail.vue`` consumes (``tab`` plus
    ``expandTask`` / ``expandTrial``), so the recipient lands on the run itself
    rather than on the project's first tab.
    """
    query = f"tab={quote(tab)}"
    for key, value in params.items():
        if value is not None:
            query += f"&{key}={quote(str(value))}"
    return f"{_app_url()}/projects/{project_id}?{query}"


def _dispatch(to: str, subject: str, html: str, text: str) -> None:
    """Hand one email to Celery, or send it on a thread if Celery can't take it.

    Never raises and never blocks the caller on SMTP.
    """
    try:
        from ..celery.notifications import send_notification_email_task

        if send_notification_email_task is not None:
            send_notification_email_task.apply_async(
                kwargs={"to": to, "subject": subject, "html": html, "text": text},
                # Fail fast instead of blocking the caller while kombu retries a
                # dead broker — the thread fallback below is the better answer.
                retry=False,
            )
            return
    except Exception as e:
        logger.info(
            "Could not queue notification email to %s (%s); sending inline", to, e
        )

    def _send() -> None:
        try:
            email_service.send_email(to=to, subject=subject, html=html, text=text)
        except Exception:
            logger.exception("Inline notification email to %s failed", to)

    threading.Thread(target=_send, name="notify-email", daemon=True).start()


def _send_notification(
    *,
    user: User,
    subject: str,
    heading: str,
    paragraphs: list[str],
    details: list[tuple[str, str]] | None = None,
    note: str | None = None,
    cta_label: str | None = None,
    cta_url: str | None = None,
    footer_key: str = "common.footer_reason",
    manage_url: str | None = None,
) -> None:
    """Render for one recipient's locale and queue it."""
    locale = user.preferred_language
    html, text = email_service.render_notification(
        locale=locale,
        subject=subject,
        heading=heading,
        paragraphs=paragraphs,
        details=details or [],
        note=note,
        cta_label=cta_label,
        cta_url=cta_url,
        greeting_name=user.full_name,
        footer_key=footer_key,
        manage_url=manage_url if manage_url is not None else _account_url(),
    )
    _dispatch(user.email, subject, html, text)


def _elapsed_seconds(start: datetime | None, end: datetime | None) -> float | None:
    """Seconds between two timestamps, tolerating naive values.

    Task timestamps are declared ``DateTime(timezone=True)`` but come back naive
    on SQLite, so both operands are normalized to UTC before subtracting rather
    than risking a "can't subtract offset-naive and offset-aware" TypeError
    inside a finalizer.
    """
    if start is None or end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return max(0.0, (end - start).total_seconds())


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


# --------------------------------------------------------------------------- #
# Job finished
# --------------------------------------------------------------------------- #
def _job_recipient(
    db: Session, project: Project | None, created_by_id: int | None
) -> User | None:
    """The initiator, or the project owner for rows without one."""
    if created_by_id is not None:
        user = db.get(User, created_by_id)
        if _deliverable(user):
            return user
    if project is not None:
        owner = db.get(User, project.owner_id)
        if _deliverable(owner):
            return owner
    return None


def _job_gate_passes(user: User, elapsed: float | None) -> bool:
    """Apply the per-user job gating: category, presence, minimum duration."""
    prefs = preferences_for(user)
    if not prefs.get("job_finished", True):
        return False

    min_seconds = prefs.get("min_job_seconds")
    if min_seconds is None:
        min_seconds = get_settings().NOTIFY_MIN_JOB_SECONDS
    # Unknown duration (a job that never recorded started_at) is treated as long
    # enough: better a stray email than silence about a run that misbehaved.
    if elapsed is not None and elapsed < float(min_seconds):
        logger.debug(
            "Skipping job notification for user %s: %.0fs < %ss threshold",
            user.id,
            elapsed,
            min_seconds,
        )
        return False

    if prefs.get("only_when_away", True) and presence.is_online(user.id):
        logger.debug("Skipping job notification for user %s: currently online", user.id)
        return False
    return True


def notify_preprocessing_finished(db: Session, task: PreprocessingTask) -> None:
    """Email the initiator that a preprocessing task reached a terminal state.

    Cancelled tasks are silent — the user cancelled them, they know.
    """
    try:
        if not _notifications_enabled():
            return
        if task.status == PreprocessingStatus.CANCELLED:
            return

        processed = task.processed_files or 0
        failed = task.failed_files or 0
        total = task.total_files or (processed + failed)
        if task.status == PreprocessingStatus.COMPLETED:
            outcome: JobOutcome = "completed"
        elif processed > 0:
            outcome = "partial"
        else:
            outcome = "failed"

        project = db.get(Project, task.project_id)
        recipient = _job_recipient(db, project, task.created_by_id)
        if recipient is None:
            return

        elapsed = _elapsed_seconds(
            task.started_at, task.completed_at or datetime.now(UTC)
        )
        if not _job_gate_passes(recipient, elapsed):
            return

        locale = recipient.preferred_language
        project_name = (project.name if project else None) or f"#{task.project_id}"
        details: list[tuple[str, str]] = [
            (translate(locale, "label.project"), project_name),
            (translate(locale, "label.status"), translate(locale, f"status.{outcome}")),
            (translate(locale, "label.files_total"), str(total)),
            (translate(locale, "label.files_processed"), str(processed)),
        ]
        if failed:
            details.append((translate(locale, "label.files_failed"), str(failed)))
        details.append(
            (translate(locale, "label.duration"), format_duration(elapsed, locale))
        )

        paragraphs = [
            translate(
                locale,
                f"job.intro.preprocessing.{outcome}",
                project=project_name,
                total=total,
                processed=processed,
                failed=failed,
            )
        ]
        if outcome != "completed":
            paragraphs.append(translate(locale, "job.hint.failed"))

        _send_notification(
            user=recipient,
            subject=translate(
                locale, f"job.subject.preprocessing.{outcome}", project=project_name
            ),
            heading=translate(locale, f"job.heading.preprocessing.{outcome}"),
            paragraphs=paragraphs,
            details=details,
            cta_label=translate(locale, "job.cta.preprocessing"),
            cta_url=_project_url(task.project_id, "files", expandTask=task.id),
        )
    except Exception:
        logger.exception(
            "Could not send preprocessing notification for task %s",
            getattr(task, "id", "?"),
        )


def notify_trial_finished(db: Session, trial: Trial) -> None:
    """Email the initiator that an extraction run reached a terminal state."""
    try:
        if not _notifications_enabled():
            return
        if trial.status == TrialStatus.CANCELLED:
            return

        total = len(set(trial.document_ids or []))
        succeeded = (
            db.scalar(
                select(func.count())
                .select_from(TrialResult)
                .where(
                    TrialResult.trial_id == trial.id,
                    TrialResult.status == TrialResultStatus.SUCCESS,
                )
            )
            or 0
        )
        failed = max(0, total - succeeded)
        if trial.status == TrialStatus.COMPLETED and not failed:
            outcome: JobOutcome = "completed"
        elif succeeded > 0:
            outcome = "partial"
        else:
            outcome = "failed"

        project = db.get(Project, trial.project_id)
        recipient = _job_recipient(db, project, trial.created_by_id)
        if recipient is None:
            return

        elapsed = _elapsed_seconds(
            trial.started_at, trial.finished_at or datetime.now(UTC)
        )
        if not _job_gate_passes(recipient, elapsed):
            return

        locale = recipient.preferred_language
        project_name = (project.name if project else None) or f"#{trial.project_id}"
        # Mirrors the frontend's display fallback for unnamed runs.
        run_name = trial.name or f"#{trial.project_trial_number}"
        details: list[tuple[str, str]] = [
            (translate(locale, "label.project"), project_name),
            (translate(locale, "label.run"), run_name),
            (translate(locale, "label.status"), translate(locale, f"status.{outcome}")),
            (translate(locale, "label.documents_total"), str(total)),
            (translate(locale, "label.documents_succeeded"), str(succeeded)),
        ]
        if failed:
            details.append((translate(locale, "label.documents_failed"), str(failed)))
        details.append((translate(locale, "label.model"), trial.llm_model or "—"))
        details.append(
            (translate(locale, "label.duration"), format_duration(elapsed, locale))
        )

        paragraphs = [
            translate(
                locale,
                f"job.intro.trial.{outcome}",
                project=project_name,
                run=run_name,
                total=total,
                succeeded=succeeded,
                failed=failed,
            )
        ]
        if outcome != "completed":
            paragraphs.append(translate(locale, "job.hint.failed"))

        _send_notification(
            user=recipient,
            subject=translate(
                locale, f"job.subject.trial.{outcome}", project=project_name
            ),
            heading=translate(locale, f"job.heading.trial.{outcome}"),
            paragraphs=paragraphs,
            details=details,
            cta_label=translate(locale, "job.cta.trial"),
            cta_url=_project_url(trial.project_id, "trials", expandTrial=trial.id),
        )
    except Exception:
        logger.exception(
            "Could not send trial notification for trial %s", getattr(trial, "id", "?")
        )


def notify_job_failed_by_crash(db: Session, *, kind: JobKind, job_id: int) -> None:
    """Notify after a worker crash marked a job failed outside its own finalizer.

    The normal finalizers never ran, so this re-enters the standard path with
    whatever state the crash handler persisted.
    """
    try:
        if kind == "preprocessing":
            task = db.get(PreprocessingTask, job_id)
            if task is not None:
                notify_preprocessing_finished(db, task)
        else:
            trial = db.get(Trial, job_id)
            if trial is not None:
                notify_trial_finished(db, trial)
    except Exception:
        logger.exception("Could not send crash notification for %s %s", kind, job_id)


# --------------------------------------------------------------------------- #
# Project shared
# --------------------------------------------------------------------------- #
def notify_project_shared(
    db: Session,
    share: ProjectShare,
    *,
    actor: User | None = None,
    updated: bool = False,
) -> None:
    """Tell a collaborator they were granted (or re-granted) project access.

    ``updated=True`` is the permission-change wording; without it the email reads
    as a first-time grant. Not sent on revocation — telling someone what they no
    longer have is noise, and the audit log records it.
    """
    try:
        if not _notifications_enabled():
            return

        recipient = share.user or db.get(User, share.user_id)
        if not _deliverable(recipient) or not _wants(
            recipient, NotificationCategory.PROJECT_SHARED
        ):
            return
        # Granting yourself access (admin acting on their own project) shouldn't
        # generate mail.
        if actor is not None and actor.id == recipient.id:
            return

        project = share.project or db.get(Project, share.project_id)
        locale = recipient.preferred_language
        project_name = (project.name if project else None) or f"#{share.project_id}"
        permission = (
            share.permission.value
            if isinstance(share.permission, ProjectPermission)
            else str(share.permission)
        )
        actor_name = (
            (actor.full_name or actor.email)
            if actor is not None
            else (
                (share.created_by.full_name or share.created_by.email)
                if share.created_by
                else translate(locale, "label.granted_by")
            )
        )
        variant = "updated" if updated else "granted"

        _send_notification(
            user=recipient,
            subject=translate(locale, f"share.subject.{variant}", project=project_name),
            heading=translate(locale, f"share.heading.{variant}"),
            paragraphs=[
                translate(
                    locale,
                    f"share.intro.{variant}",
                    actor=actor_name,
                    permission=translate(locale, f"share.permission.{permission}"),
                    project=project_name,
                )
            ],
            details=[
                (translate(locale, "label.project"), project_name),
                (
                    translate(locale, "label.permission"),
                    translate(locale, f"share.permission_label.{permission}"),
                ),
                (translate(locale, "label.granted_by"), actor_name),
            ],
            cta_label=translate(locale, "share.cta"),
            cta_url=f"{_app_url()}/projects/{share.project_id}",
        )
    except Exception:
        logger.exception(
            "Could not send share notification for share %s", getattr(share, "id", "?")
        )


# --------------------------------------------------------------------------- #
# Security notices
# --------------------------------------------------------------------------- #
def notify_security_event(db: Session, user: User, event: str, **params: Any) -> None:
    """Tell a user about a change to their own account's access.

    ``event`` must be one of :data:`SECURITY_EVENTS`; anything else is a
    programming error and is logged rather than mailed, so a typo can't send an
    email whose body is a raw catalog key.
    """
    try:
        if event not in SECURITY_EVENTS:
            logger.error("Unknown security notification event %r", event)
            return
        if not _notifications_enabled():
            return
        # Note the deliberate asymmetry with jobs: no presence gating. A security
        # notice is evidence the user may need later, so it goes out even if they
        # are looking at the app right now.
        if not _deliverable(user) or not _wants(user, NotificationCategory.SECURITY):
            return

        locale = user.preferred_language
        details: list[tuple[str, str]] = [
            (translate(locale, "label.time"), _utc_stamp())
        ]
        if params.get("provider"):
            details.insert(
                0, (translate(locale, "label.provider"), str(params["provider"]))
            )

        note_key = (
            "security.note.locked_hint"
            if event == "account_locked"
            else "security.note.contact_admin"
        )

        _send_notification(
            user=user,
            subject=translate(locale, f"security.subject.{event}"),
            heading=translate(locale, f"security.heading.{event}"),
            paragraphs=[translate(locale, f"security.intro.{event}", **params)],
            details=details,
            note=translate(locale, note_key),
            cta_label=translate(locale, "security.cta"),
            cta_url=_account_url(),
        )
    except Exception:
        logger.exception("Could not send security notification %r", event)


# --------------------------------------------------------------------------- #
# Admin alerts
# --------------------------------------------------------------------------- #
def _alert_cooldown_passed(kind: str) -> bool:
    """True at most once per cooldown window per alert kind.

    Uses Redis ``SET NX EX`` so all web/worker processes share one window;
    without Redis it falls back to a per-process timestamp map.
    """
    minutes = max(1, int(get_settings().NOTIFY_ADMIN_ALERT_COOLDOWN_MINUTES))
    window = minutes * 60
    key = f"notify:alert_cooldown:{kind}"

    from .redis_broadcast import get_redis_client

    client = get_redis_client()
    if client is not None:
        try:
            # nx=True means "only if absent" — the first caller in the window
            # gets True and everyone after it gets None until the key expires.
            return bool(client.set(key, b"1", ex=window, nx=True))
        except Exception as e:
            logger.debug("Redis alert cooldown unavailable (%s); using local map", e)

    import time

    now = time.monotonic()
    with _local_alert_lock:
        last = _local_alert_cooldown.get(kind)
        if last is not None and now - last < window:
            return False
        _local_alert_cooldown[kind] = now
        return True


def notify_admin_alert(db: Session, kind: str, **params: Any) -> None:
    """Email every opted-in admin about an operational problem.

    Rate-limited per ``kind`` (see :func:`_alert_cooldown_passed`) because the
    situations that trigger these — a crash-looping worker, a sweeper reaping a
    backlog — repeat.
    """
    try:
        if kind not in ADMIN_ALERT_KINDS:
            logger.error("Unknown admin alert kind %r", kind)
            return
        if not _notifications_enabled():
            return
        if not _alert_cooldown_passed(kind):
            logger.debug("Admin alert %r suppressed by cooldown", kind)
            return

        admins = (
            db.execute(
                select(User).where(
                    User.role == UserRole.admin, User.is_active.is_(True)
                )
            )
            .scalars()
            .all()
        )
        cooldown_minutes = int(get_settings().NOTIFY_ADMIN_ALERT_COOLDOWN_MINUTES)

        for admin in admins:
            if not _deliverable(admin) or not _wants(
                admin, NotificationCategory.ADMIN_ALERTS
            ):
                continue
            locale = admin.preferred_language
            details: list[tuple[str, str]] = [
                (translate(locale, "label.time"), _utc_stamp())
            ]
            if params.get("count") is not None:
                details.append((translate(locale, "label.count"), str(params["count"])))
            if params.get("error_id"):
                details.append(
                    (translate(locale, "label.error_id"), str(params["error_id"]))
                )
            if params.get("reason"):
                details.append(
                    (translate(locale, "label.reason"), str(params["reason"]))
                )

            _send_notification(
                user=admin,
                subject=translate(locale, f"admin.subject.{kind}"),
                heading=translate(locale, f"admin.heading.{kind}"),
                paragraphs=[
                    translate(locale, f"admin.intro.{kind}", **params),
                    translate(locale, "admin.note.cooldown", minutes=cooldown_minutes),
                ],
                details=details,
                cta_label=translate(locale, "admin.cta"),
                cta_url=f"{_app_url()}/admin",
                footer_key="common.footer_admin_reason",
            )
    except Exception:
        logger.exception("Could not send admin alert %r", kind)


# --------------------------------------------------------------------------- #
# Test email (admin settings)
# --------------------------------------------------------------------------- #
def send_test_email(user: User) -> bool:
    """Send the admin a test email synchronously and report whether SMTP took it.

    Synchronous on purpose: the admin pressed a button and needs the real answer,
    not "queued". Ignores NOTIFICATIONS_ENABLED — the point is to verify SMTP,
    which is governed by EMAIL_ENABLED.
    """
    if not email_service.is_configured():
        return False
    locale = user.preferred_language
    html, text = email_service.render_notification(
        locale=locale,
        subject=translate(locale, "test.subject"),
        heading=translate(locale, "test.heading"),
        paragraphs=[translate(locale, "test.intro")],
        cta_label=translate(locale, "test.cta"),
        cta_url=_app_url(),
        greeting_name=user.full_name,
        manage_url=_account_url(),
    )
    return email_service.send_email(
        to=user.email, subject=translate(locale, "test.subject"), html=html, text=text
    )
