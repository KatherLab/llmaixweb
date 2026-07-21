# backend/tests/test_email_service.py
"""Unit tests for ``utils/email_service.py`` (SMTP send + Jinja2 templates).

External I/O (``smtplib.SMTP``) and configuration (the ``settings`` proxy) are
mocked/monkeypatched so nothing touches the network. Covers:

* ``is_configured()`` truth table (each required setting toggled off),
* ``send_email`` TLS/auth branches (``starttls``/``login``/``sendmail``),
* every caught SMTP/OS/unexpected exception branch returning ``False``,
* the "not configured" early-return (no SMTP object constructed),
* ``send_invitation_email`` / ``send_password_reset_email`` delegation with a
  sensible subject + rendered body, and
* the ``_render_template`` ``TemplateNotFound`` plain-text fallback.
"""

import smtplib
from unittest.mock import MagicMock

import pytest

from backend.src.core import config
from backend.src.utils import email_service


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def settings_inst():
    """The real Settings instance behind the module-level proxy."""
    return config._get_settings()


@pytest.fixture
def configured(monkeypatch, settings_inst):
    """Set all required SMTP settings so ``is_configured()`` is True."""
    monkeypatch.setattr(settings_inst, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings_inst, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings_inst, "SMTP_PORT", 587)
    monkeypatch.setattr(settings_inst, "SMTP_FROM_ADDRESS", "noreply@example.com")
    monkeypatch.setattr(settings_inst, "SMTP_FROM_NAME", "LLMAIx Web")
    monkeypatch.setattr(settings_inst, "SMTP_USERNAME", "")
    monkeypatch.setattr(settings_inst, "SMTP_PASSWORD", "")
    monkeypatch.setattr(settings_inst, "SMTP_USE_TLS", False)
    return settings_inst


@pytest.fixture
def mock_smtp(monkeypatch):
    """Patch ``smtplib.SMTP`` and return (SMTP class mock, server mock).

    The server mock is what the ``with smtplib.SMTP(...) as server`` block
    yields (i.e. the ``__enter__`` return value).
    """
    smtp_cls = MagicMock(name="SMTP")
    server = smtp_cls.return_value.__enter__.return_value
    monkeypatch.setattr(email_service.smtplib, "SMTP", smtp_cls)
    return smtp_cls, server


# --------------------------------------------------------------------------- #
# is_configured
# --------------------------------------------------------------------------- #
class TestIsConfigured:
    def test_true_when_all_required_present(self, configured):
        assert email_service.is_configured() is True

    @pytest.mark.parametrize(
        "attr, falsy",
        [
            ("EMAIL_ENABLED", False),
            ("SMTP_HOST", ""),
            ("SMTP_PORT", 0),
            ("SMTP_FROM_ADDRESS", ""),
        ],
    )
    def test_false_when_any_required_missing(
        self, configured, monkeypatch, attr, falsy
    ):
        monkeypatch.setattr(configured, attr, falsy)
        assert email_service.is_configured() is False

    def test_returns_bool_not_truthy_object(self, configured):
        # Guard the ``bool(...)`` wrapper — must be an actual bool.
        assert isinstance(email_service.is_configured(), bool)


# --------------------------------------------------------------------------- #
# send_email — happy paths / branches
# --------------------------------------------------------------------------- #
class TestSendEmail:
    def test_not_configured_returns_false_without_smtp(self, monkeypatch, mock_smtp):
        smtp_cls, _ = mock_smtp
        monkeypatch.setattr(email_service, "is_configured", lambda: False)
        result = email_service.send_email("to@x.com", "Subj", "<p>hi</p>")
        assert result is False
        smtp_cls.assert_not_called()

    def test_plain_send_no_tls_no_auth(self, configured, mock_smtp):
        smtp_cls, server = mock_smtp
        result = email_service.send_email(
            "to@x.com", "Subject", "<p>html</p>", text="plain"
        )
        assert result is True
        smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=15)
        server.starttls.assert_not_called()
        server.login.assert_not_called()
        server.sendmail.assert_called_once()
        # sendmail(from, to, body)
        args = server.sendmail.call_args.args
        assert args[0] == "noreply@example.com"
        assert args[1] == "to@x.com"
        assert "Subject" in args[2]

    def test_starttls_when_tls_enabled(self, configured, monkeypatch, mock_smtp):
        _, server = mock_smtp
        monkeypatch.setattr(configured, "SMTP_USE_TLS", True)
        assert email_service.send_email("to@x.com", "S", "<p>h</p>") is True
        server.starttls.assert_called_once()

    def test_login_when_credentials_present(self, configured, monkeypatch, mock_smtp):
        _, server = mock_smtp
        monkeypatch.setattr(configured, "SMTP_USERNAME", "user")
        monkeypatch.setattr(configured, "SMTP_PASSWORD", "pass")
        assert email_service.send_email("to@x.com", "S", "<p>h</p>") is True
        server.login.assert_called_once_with("user", "pass")

    def test_no_login_when_only_username(self, configured, monkeypatch, mock_smtp):
        _, server = mock_smtp
        monkeypatch.setattr(configured, "SMTP_USERNAME", "user")
        monkeypatch.setattr(configured, "SMTP_PASSWORD", "")
        assert email_service.send_email("to@x.com", "S", "<p>h</p>") is True
        server.login.assert_not_called()

    def test_html_only_when_no_text(self, configured, mock_smtp):
        _, server = mock_smtp
        assert email_service.send_email("to@x.com", "S", "<p>h</p>") is True
        body = server.sendmail.call_args.args[2]
        assert "text/html" in body


# --------------------------------------------------------------------------- #
# send_email — exception branches (all caught, return False)
# --------------------------------------------------------------------------- #
class TestSendEmailExceptions:
    @pytest.mark.parametrize(
        "exc",
        [
            smtplib.SMTPAuthenticationError(535, b"bad creds"),
            smtplib.SMTPConnectError(421, b"cannot connect"),
            smtplib.SMTPException("generic smtp failure"),
            OSError("network down"),
            RuntimeError("unexpected boom"),
        ],
    )
    def test_exceptions_are_caught_and_return_false(self, configured, mock_smtp, exc):
        smtp_cls, _ = mock_smtp
        # Raise when the context manager is entered.
        smtp_cls.return_value.__enter__.side_effect = exc
        result = email_service.send_email("to@x.com", "S", "<p>h</p>")
        assert result is False

    def test_sendmail_failure_returns_false(self, configured, mock_smtp):
        _, server = mock_smtp
        server.sendmail.side_effect = smtplib.SMTPException("rejected")
        assert email_service.send_email("to@x.com", "S", "<p>h</p>") is False


# --------------------------------------------------------------------------- #
# _render_template
# --------------------------------------------------------------------------- #
class TestRenderTemplate:
    def test_renders_known_template(self):
        html = email_service._render_template(
            "invitation.html", invite_url="https://x/inv"
        )
        assert "https://x/inv" in html

    def test_template_not_found_falls_back_to_plaintext(self):
        out = email_service._render_template(
            "does_not_exist.html", foo="bar", answer=42
        )
        # Fallback renders "key: value" lines, not an exception.
        assert "foo: bar" in out
        assert "answer: 42" in out


# --------------------------------------------------------------------------- #
# send_invitation_email / send_password_reset_email delegation
# --------------------------------------------------------------------------- #
class TestHigherLevelSenders:
    def test_invitation_delegates_to_send_email(self, monkeypatch, configured):
        captured = {}

        def fake_send_email(to, subject, html, text=""):
            captured.update(to=to, subject=subject, html=html, text=text)
            return True

        monkeypatch.setattr(email_service, "send_email", fake_send_email)
        ok = email_service.send_invitation_email(
            "u@x.com", "tok", "https://app/invite?token=tok"
        )
        assert ok is True
        assert captured["to"] == "u@x.com"
        assert "Invit" in captured["subject"]
        assert "https://app/invite?token=tok" in captured["html"]
        assert "https://app/invite?token=tok" in captured["text"]

    def test_password_reset_delegates_to_send_email(self, monkeypatch, configured):
        captured = {}

        def fake_send_email(to, subject, html, text=""):
            captured.update(to=to, subject=subject, html=html, text=text)
            return True

        monkeypatch.setattr(email_service, "send_email", fake_send_email)
        ok = email_service.send_password_reset_email(
            "u@x.com", "tok", "https://app/reset?token=tok"
        )
        assert ok is True
        assert captured["to"] == "u@x.com"
        assert "Password Reset" in captured["subject"]
        assert "https://app/reset?token=tok" in captured["html"]
        assert "https://app/reset?token=tok" in captured["text"]

    def test_invitation_short_circuits_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(email_service, "is_configured", lambda: False)
        called = MagicMock()
        monkeypatch.setattr(email_service, "send_email", called)
        assert email_service.send_invitation_email("u@x.com", "t", "url") is False
        called.assert_not_called()

    def test_password_reset_short_circuits_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(email_service, "is_configured", lambda: False)
        called = MagicMock()
        monkeypatch.setattr(email_service, "send_email", called)
        assert email_service.send_password_reset_email("u@x.com", "t", "url") is False
        called.assert_not_called()
