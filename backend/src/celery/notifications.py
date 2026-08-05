# backend/src/celery/notifications.py
"""Celery task that performs the actual SMTP send for notification email.

Why this exists at all: ``smtplib`` blocks for up to 15 seconds per message, and
every notification is produced somewhere that must not stall — a preprocessing
worker finalizing an OCR batch, or an HTTP handler answering a password change.
Queuing on ``default`` keeps the send off the critical path and off the
single-slot ``preprocess`` queue.

The rendered HTML/text is passed as task arguments rather than being rebuilt
here. That keeps the worker stateless (no DB access, no locale lookup, no
template environment) and means a message already accepted for delivery cannot
change its content if the underlying rows are edited before it is sent. The cost
is a larger broker payload, which for a few kilobytes of HTML is a fine trade.
"""

import logging

from ..utils import email_service
from .celery_config import celery_app

logger = logging.getLogger(__name__)

# Retry a failed send twice with a growing gap: SMTP failures are usually
# transient (greylisting, a relay restart). ``send_email`` reports failure by
# returning False rather than raising, so the task inspects the result.
_RETRY_DELAYS = (60, 300)

send_notification_email_task = None

if celery_app is not None:

    @celery_app.task(
        bind=True,
        name="backend.src.celery.notifications.send_notification_email_task",
        max_retries=len(_RETRY_DELAYS),
        # An email is not worth blocking a worker slot for minutes.
        soft_time_limit=60,
        time_limit=90,
    )
    def send_notification_email_task(
        self, to: str, subject: str, html: str, text: str = ""
    ):
        """Send one already-rendered email, retrying transient SMTP failures."""
        if not email_service.is_configured():
            # Email was switched off (or misconfigured) between queueing and
            # running. Retrying can't fix that, so drop it.
            logger.info("Dropping queued email to %s: SMTP not configured", to)
            return False

        try:
            sent = email_service.send_email(
                to=to, subject=subject, html=html, text=text
            )
        except Exception as exc:  # pragma: no cover - send_email catches its own
            logger.warning("Notification email to %s raised: %s", to, exc)
            sent = False

        if sent:
            return True

        attempt = self.request.retries
        if attempt < len(_RETRY_DELAYS):
            raise self.retry(countdown=_RETRY_DELAYS[attempt])
        logger.error("Giving up on notification email to %s after retries", to)
        return False
