"""Email sending service using smtplib.

Uses Jinja2 for HTML template rendering with inline CSS.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from ..core.config import settings

logger = logging.getLogger(__name__)

# Path to email templates
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

# Jinja2 environment for email templates
_env: Optional[Environment] = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
    return _env


def _render_template(template_name: str, **kwargs) -> str:
    """Render an email template with the given context."""
    try:
        template = _get_env().get_template(template_name)
        return template.render(**kwargs)
    except TemplateNotFound:
        logger.error("Email template '%s' not found in %s", template_name, _TEMPLATES_DIR)
        # Fallback to plain text rendering
        lines = [f"{k}: {v}" for k, v in kwargs.items()]
        return "\n".join(lines)


def is_configured() -> bool:
    """Check if SMTP settings are properly configured."""
    return bool(
        settings.EMAIL_ENABLED
        and settings.SMTP_HOST
        and settings.SMTP_PORT
        and settings.SMTP_FROM_ADDRESS
    )


def send_email(
    to: str,
    subject: str,
    html: str,
    text: str = "",
) -> bool:
    """Send an email via SMTP.

    Returns True if sent successfully, False otherwise (logs errors).
    """
    if not is_configured():
        logger.warning("Email not sent to %s: SMTP not configured", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_ADDRESS}>"
    msg["To"] = to
    msg["Subject"] = subject

    # Attach plain text and HTML parts
    if text:
        msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls(context=context)
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_ADDRESS, to, msg.as_string())
        logger.info("Email sent successfully to %s", to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", settings.SMTP_USERNAME)
    except smtplib.SMTPConnectError:
        logger.error("Could not connect to SMTP server %s:%s", settings.SMTP_HOST, settings.SMTP_PORT)
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending email to %s: %s", to, e)
    except OSError as e:
        logger.error("Network error sending email to %s: %s", to, e)
    except Exception as e:
        logger.error("Unexpected error sending email to %s: %s", to, e)
    return False


def send_invitation_email(email: str, token: str, invite_url: str) -> bool:
    """Send an invitation email with a registration link."""
    if not is_configured():
        return False

    html = _render_template(
        "invitation.html",
        invite_url=invite_url,
    )
    text = (
        f"You have been invited to join LLMAIx Web.\n\n"
        f"Click the link below to create your account:\n{invite_url}\n\n"
        f"If you were not expecting this invitation, you can safely ignore this email."
    )
    return send_email(
        to=email,
        subject="You're Invited to LLMAIx Web",
        html=html,
        text=text,
    )


def send_password_reset_email(email: str, token: str, reset_url: str) -> bool:
    """Send a password reset email with a reset link."""
    if not is_configured():
        return False

    html = _render_template(
        "password_reset.html",
        reset_url=reset_url,
    )
    text = (
        f"We received a request to reset your LLMAIx Web password.\n\n"
        f"Click the link below to set a new password:\n{reset_url}\n\n"
        f"This link will expire in 24 hours.\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    return send_email(
        to=email,
        subject="Password Reset — LLMAIx Web",
        html=html,
        text=text,
    )
