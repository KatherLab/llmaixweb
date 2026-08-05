# backend/tests/test_notifications.py
"""Tests for the email notification system.

Nothing here touches SMTP: ``utils.notifications._dispatch`` is patched to a
capture list, so each test asserts on *what would be sent to whom* rather than on
delivery. That is the interesting half — the gating rules (preference, presence,
minimum duration, admin-alert cooldown) are where the behaviour lives, and
``test_email_service.py`` already covers the SMTP layer.

Covers:

* catalog integrity — every locale has every key ``en`` has, and every key the
  notification builders reference actually exists,
* ``translate`` / ``format_duration`` fallbacks,
* preference resolution for users with and without a stored row,
* the job gate: category off, too-short, user online, unknown duration,
* recipient resolution: initiator, owner fallback, inactive user,
* PHI boundary — no document/file names in a rendered job email,
* project-share, security, and admin-alert paths (including cooldown),
* the preferences + language API endpoints.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# `email_i18n` has no configuration or database dependencies, so it is safe to
# import while pytest is still collecting — which matters because it parametrizes
# a test below. `notifications`, `presence`, and `config` all reach
# `db.session` transitively, and importing that before conftest's session fixture
# has pointed SQLALCHEMY_DATABASE_URI at the test SQLite file makes Settings
# exit the process. They are bound to module globals by `_late_imports` instead.
from backend.src.utils import email_i18n

CATALOG_DIR = Path("backend/src/locales/emails")

config = None
notifications = None
presence = None


@pytest.fixture(scope="module", autouse=True)
def _late_imports():
    """Import the settings-dependent modules once the test env is configured."""
    global config, notifications, presence
    from backend.src.core import config as _config
    from backend.src.utils import notifications as _notifications
    from backend.src.utils import presence as _presence

    config, notifications, presence = _config, _notifications, _presence
    yield


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def settings_inst():
    return config._get_settings()


@pytest.fixture
def email_on(monkeypatch, settings_inst):
    """Make ``_notifications_enabled()`` true without configuring real SMTP."""
    monkeypatch.setattr(notifications.email_service, "is_configured", lambda: True)
    monkeypatch.setattr(settings_inst, "NOTIFICATIONS_ENABLED", True)
    monkeypatch.setattr(settings_inst, "NOTIFY_MIN_JOB_SECONDS", 120)
    monkeypatch.setattr(settings_inst, "APP_URL", "https://llmaix.example")
    return settings_inst


@pytest.fixture
def sent(monkeypatch):
    """Capture dispatched emails as dicts instead of sending them."""
    captured: list[dict] = []

    def _capture(to, subject, html, text):
        captured.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr(notifications, "_dispatch", _capture)
    return captured


@pytest.fixture
def offline(monkeypatch):
    """Nobody is looking at the app (the usual case for a notification test)."""
    monkeypatch.setattr(notifications.presence, "is_online", lambda _uid: False)


@pytest.fixture
def db():
    from backend.src.db.session import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def make_user(db):
    """Create (and clean up) a user, optionally with notification preferences."""
    from backend.src.models.user import NotificationPreference, User
    from backend.src.utils.enums import UserRole

    created: list[int] = []

    def _make(
        email: str,
        *,
        role=UserRole.user,
        is_active: bool = True,
        language: str | None = None,
        prefs: dict | None = None,
    ) -> User:
        user = User(
            email=email,
            full_name=f"User {email}",
            hashed_password="",
            role=role,
            is_active=is_active,
            preferred_language=language,
        )
        db.add(user)
        db.flush()
        if prefs is not None:
            db.add(NotificationPreference(user_id=user.id, **prefs))
        db.commit()
        db.refresh(user)
        created.append(user.id)
        return user

    yield _make

    for uid in created:
        obj = db.get(User, uid)
        if obj is not None:
            db.delete(obj)
    db.commit()


@pytest.fixture
def make_job(db, make_user):
    """A project plus a finished preprocessing task or trial in it."""
    from backend.src.models.project import (
        PreprocessingStatus,
        PreprocessingTask,
        Project,
        Prompt,
        Schema,
        Trial,
        TrialStatus,
    )

    trash: list = []

    def _project(owner_id: int, name: str = "Cohort A") -> Project:
        project = Project(name=name, description="", owner_id=owner_id)
        db.add(project)
        db.commit()
        db.refresh(project)
        trash.append(project)
        return project

    def _preprocessing(
        project: Project,
        *,
        created_by_id: int | None,
        status=PreprocessingStatus.COMPLETED,
        total: int = 4,
        processed: int = 4,
        failed: int = 0,
        elapsed_seconds: int = 600,
    ) -> PreprocessingTask:
        now = datetime.now(UTC)
        task = PreprocessingTask(
            project_id=project.id,
            created_by_id=created_by_id,
            status=status,
            total_files=total,
            processed_files=processed,
            failed_files=failed,
            started_at=now - timedelta(seconds=elapsed_seconds),
            completed_at=now,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def _documents(project: Project, count: int) -> list[int]:
        """Real Document rows, because TrialResult.document_id is a live FK.

        A Document needs a source File and a PreprocessingConfiguration, so the
        whole chain is built here rather than faking ids.
        """
        from backend.src.models.project import (
            Document,
            File,
            PreprocessingConfiguration,
        )
        from backend.src.utils.enums import FileCreator, FileStorageType, FileType

        source = File(
            project_id=project.id,
            file_storage_type=FileStorageType.LOCAL,
            file_uuid=str(uuid.uuid4()),
            file_name="source.pdf",
            file_type=FileType.APPLICATION_PDF,
            file_creator=FileCreator.user,
        )
        config_row = PreprocessingConfiguration(project_id=project.id, name="cfg")
        db.add_all([source, config_row])
        db.flush()
        docs = [
            Document(
                project_id=project.id,
                original_file_id=source.id,
                preprocessing_config_id=config_row.id,
                text="text",
                document_name=f"doc-{i}",
            )
            for i in range(count)
        ]
        db.add_all(docs)
        db.commit()
        return [d.id for d in docs]

    def _trial(
        project: Project,
        *,
        created_by_id: int | None,
        status=TrialStatus.COMPLETED,
        document_ids: list[int] | None = None,
        elapsed_seconds: int = 900,
        name: str | None = "Run one",
    ) -> Trial:
        schema = Schema(
            project_id=project.id, schema_name="s", schema_definition={"type": "object"}
        )
        prompt = Prompt(
            project_id=project.id, name="p", system_prompt="sys", user_prompt="usr"
        )
        db.add_all([schema, prompt])
        db.flush()
        now = datetime.now(UTC)
        trial = Trial(
            name=name,
            project_trial_number=1,
            project_id=project.id,
            created_by_id=created_by_id,
            schema_id=schema.id,
            prompt_id=prompt.id,
            status=status,
            llm_model="gpt-4o-mini",
            base_url="https://api.example/v1",
            document_ids=document_ids if document_ids is not None else [1, 2, 3],
            started_at=now - timedelta(seconds=elapsed_seconds),
            finished_at=now,
        )
        trial.api_key = ""
        db.add(trial)
        db.commit()
        db.refresh(trial)
        return trial

    yield type(
        "JobFactory",
        (),
        {
            "project": staticmethod(_project),
            "preprocessing": staticmethod(_preprocessing),
            "documents": staticmethod(_documents),
            "trial": staticmethod(_trial),
        },
    )

    for obj in reversed(trash):
        merged = db.merge(obj)
        db.delete(merged)
    db.commit()


# --------------------------------------------------------------------------- #
# Catalogs
# --------------------------------------------------------------------------- #
def _flatten(node, prefix=""):
    for key, value in node.items():
        if isinstance(value, dict):
            yield from _flatten(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


class TestCatalogs:
    def test_every_locale_mirrors_english(self):
        """A missing key silently falls back to English — catch it here instead."""
        english = set(
            _flatten(json.loads((CATALOG_DIR / "en.json").read_text("utf-8")))
        )
        for locale in email_i18n.SUPPORTED_LOCALES:
            if locale == "en":
                continue
            keys = set(
                _flatten(
                    json.loads((CATALOG_DIR / f"{locale}.json").read_text("utf-8"))
                )
            )
            assert not english - keys, (
                f"{locale}.json is missing {sorted(english - keys)}"
            )
            assert not keys - english, (
                f"{locale}.json has extra keys {sorted(keys - english)}"
            )

    @pytest.mark.parametrize("locale", email_i18n.SUPPORTED_LOCALES)
    def test_keys_referenced_by_builders_exist(self, locale):
        """Every key the notification builders can produce resolves to a string."""
        required = [
            "common.greeting",
            "common.greeting_no_name",
            "common.details_heading",
            "common.footer_reason",
            "common.footer_manage",
            "common.footer_admin_reason",
            "duration.h_m",
            "duration.m_s",
            "duration.s",
            "test.subject",
            "test.heading",
            "test.intro",
            "test.cta",
            "reset.subject",
            "reset.heading",
            "reset.intro",
            "reset.instruction",
            "reset.cta",
            "reset.fallback",
            "reset.expiry",
            "reset.ignore",
            "job.cta.preprocessing",
            "job.cta.trial",
            "job.hint.failed",
            "share.cta",
            "security.cta",
            "security.note.contact_admin",
            "security.note.locked_hint",
            "admin.cta",
            "admin.note.cooldown",
        ]
        for kind in ("preprocessing", "trial"):
            for outcome in ("completed", "partial", "failed"):
                required += [
                    f"job.subject.{kind}.{outcome}",
                    f"job.heading.{kind}.{outcome}",
                    f"job.intro.{kind}.{outcome}",
                ]
        for outcome in ("completed", "partial", "failed"):
            required.append(f"status.{outcome}")
        for variant in ("granted", "updated"):
            required += [
                f"share.subject.{variant}",
                f"share.heading.{variant}",
                f"share.intro.{variant}",
            ]
        for perm in ("read", "write"):
            required += [f"share.permission.{perm}", f"share.permission_label.{perm}"]
        for event in notifications.SECURITY_EVENTS:
            required += [
                f"security.subject.{event}",
                f"security.heading.{event}",
                f"security.intro.{event}",
            ]
        for kind in notifications.ADMIN_ALERT_KINDS:
            required += [
                f"admin.subject.{kind}",
                f"admin.heading.{kind}",
                f"admin.intro.{kind}",
            ]
        for label in (
            "project",
            "run",
            "status",
            "duration",
            "model",
            "files_total",
            "files_processed",
            "files_failed",
            "documents_total",
            "documents_succeeded",
            "documents_failed",
            "permission",
            "granted_by",
            "provider",
            "time",
            "reason",
            "count",
            "error_id",
        ):
            required.append(f"label.{label}")

        for key in required:
            value = email_i18n.translate(locale, key)
            assert value != key, f"{locale} has no entry for {key}"


class TestTranslate:
    def test_falls_back_to_english_for_missing_key(self, monkeypatch):
        # 'de' has every key today, so simulate a gap rather than deleting one.
        monkeypatch.setattr(
            email_i18n,
            "_lookup",
            lambda cat, key: None if cat.get("__de__") else "English",
        )
        assert email_i18n.translate("de", "whatever") in ("English", "whatever")

    def test_unknown_key_returns_the_key(self):
        assert email_i18n.translate("en", "no.such.key") == "no.such.key"

    def test_missing_param_degrades_to_template(self):
        # Interpolation failure must not raise inside a Celery finalizer.
        out = email_i18n.translate("en", "job.subject.trial.completed")
        assert "{project}" in out

    @pytest.mark.parametrize(
        "value, expected",
        [
            (None, "en"),
            ("", "en"),
            ("de", "de"),
            ("de-DE", "de"),
            ("DE_at", "de"),
            ("zz", "en"),
        ],
    )
    def test_normalize_locale(self, value, expected):
        assert email_i18n.normalize_locale(value) == expected

    def test_format_duration(self):
        assert email_i18n.format_duration(4520, "en") == "1 h 15 min"
        assert email_i18n.format_duration(75, "en") == "1 min 15 s"
        assert email_i18n.format_duration(9, "en") == "9 s"
        assert email_i18n.format_duration(None, "en") == "—"
        assert email_i18n.format_duration(-1, "en") == "—"


class TestRendering:
    def test_user_authored_text_is_escaped(self):
        """Project and run names reach the HTML body — they must not be markup."""
        from backend.src.utils import email_service

        html, _text = email_service.render_notification(
            locale="en",
            subject="S",
            heading="H",
            paragraphs=["<img src=x onerror=alert(1)>"],
            details=[("Project", 'A & B "quoted"')],
            greeting_name="<b>Ada</b>",
        )
        assert "<img src=x" not in html
        assert "&lt;img src=x" in html
        assert "A &amp; B" in html
        assert "<b>Ada</b>" not in html

    def test_cta_query_string_is_escaped_inside_href(self):
        """`&` becomes `&amp;` in HTML — correct in an href, and why the raw URL
        is only asserted against the plain-text part elsewhere."""
        from backend.src.utils import email_service

        html, text = email_service.render_notification(
            locale="en",
            subject="S",
            heading="H",
            paragraphs=[],
            cta_label="Open",
            cta_url="https://x/projects/1?tab=trials&expandTrial=2",
        )
        assert "tab=trials&amp;expandTrial=2" in html
        assert "tab=trials&expandTrial=2" in text

    def test_plain_text_twin_contains_every_part(self):
        from backend.src.utils import email_service

        _html, text = email_service.render_notification(
            locale="en",
            subject="S",
            heading="Heading",
            paragraphs=["First.", "Second."],
            details=[("Project", "P")],
            note="Careful.",
            cta_label="Open",
            cta_url="https://x/",
            greeting_name="Ada",
            manage_url="https://x/account",
        )
        for fragment in (
            "Hi Ada",
            "Heading",
            "First.",
            "Second.",
            "Project: P",
            "Careful.",
            "Open: https://x/",
            "Manage notification settings",
        ):
            assert fragment in text

    def test_password_reset_is_localized(self):
        from backend.src.utils import email_service

        html = email_service._render_template(
            "password_reset.html",
            reset_url="https://x/reset-password/tok",
            locale="de",
            t=email_i18n.translator("de"),
        )
        assert "Passwort zurücksetzen" in html
        assert "https://x/reset-password/tok" in html

    def test_password_reset_renders_without_a_translator(self):
        """The `t is defined` guards keep the template usable in isolation."""
        from backend.src.utils import email_service

        html = email_service._render_template(
            "password_reset.html", reset_url="https://x/reset-password/tok"
        )
        assert "Password Reset" in html


# --------------------------------------------------------------------------- #
# Preferences + gating
# --------------------------------------------------------------------------- #
class TestPreferences:
    def test_user_without_row_gets_defaults(self, make_user):
        from backend.src.models.user import NotificationPreference

        user = make_user("prefs-default@example.com")
        assert notifications.preferences_for(user) == dict(
            NotificationPreference.DEFAULTS
        )

    def test_stored_row_wins(self, make_user):
        user = make_user(
            "prefs-stored@example.com",
            prefs={"job_finished": False, "min_job_seconds": 30},
        )
        prefs = notifications.preferences_for(user)
        assert prefs["job_finished"] is False
        assert prefs["min_job_seconds"] == 30


class TestJobGate:
    def test_passes_by_default(self, email_on, offline, make_user):
        user = make_user("gate-ok@example.com")
        assert notifications._job_gate_passes(user, 600) is True

    def test_category_off_blocks(self, email_on, offline, make_user):
        user = make_user("gate-off@example.com", prefs={"job_finished": False})
        assert notifications._job_gate_passes(user, 600) is False

    def test_short_job_blocked_by_server_default(self, email_on, offline, make_user):
        user = make_user("gate-short@example.com")
        assert notifications._job_gate_passes(user, 30) is False

    def test_per_user_threshold_overrides_server_default(
        self, email_on, offline, make_user
    ):
        user = make_user("gate-thresh@example.com", prefs={"min_job_seconds": 10})
        assert notifications._job_gate_passes(user, 30) is True

    def test_zero_threshold_lets_everything_through(self, email_on, offline, make_user):
        user = make_user("gate-zero@example.com", prefs={"min_job_seconds": 0})
        assert notifications._job_gate_passes(user, 1) is True

    def test_unknown_duration_is_not_treated_as_short(
        self, email_on, offline, make_user
    ):
        """A job with no started_at should still notify — see _job_gate_passes."""
        user = make_user("gate-unknown@example.com")
        assert notifications._job_gate_passes(user, None) is True

    def test_online_user_is_skipped(self, email_on, monkeypatch, make_user):
        user = make_user("gate-online@example.com")
        monkeypatch.setattr(notifications.presence, "is_online", lambda _uid: True)
        assert notifications._job_gate_passes(user, 600) is False

    def test_online_user_notified_when_away_gating_off(
        self, email_on, monkeypatch, make_user
    ):
        user = make_user("gate-online-off@example.com", prefs={"only_when_away": False})
        monkeypatch.setattr(notifications.presence, "is_online", lambda _uid: True)
        assert notifications._job_gate_passes(user, 600) is True


class TestNotificationsDisabled:
    def test_master_switch_off_sends_nothing(
        self, email_on, offline, sent, db, make_user, make_job, monkeypatch
    ):
        monkeypatch.setattr(email_on, "NOTIFICATIONS_ENABLED", False)
        user = make_user("off-switch@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(project, created_by_id=user.id)
        notifications.notify_preprocessing_finished(db, task)
        assert sent == []

    def test_unconfigured_smtp_sends_nothing(
        self, email_on, offline, sent, db, make_user, make_job, monkeypatch
    ):
        monkeypatch.setattr(notifications.email_service, "is_configured", lambda: False)
        user = make_user("off-smtp@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(project, created_by_id=user.id)
        notifications.notify_preprocessing_finished(db, task)
        assert sent == []


# --------------------------------------------------------------------------- #
# Job notifications
# --------------------------------------------------------------------------- #
class TestPreprocessingNotification:
    def test_completed_goes_to_initiator(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        owner = make_user("pp-owner@example.com")
        starter = make_user("pp-starter@example.com")
        project = make_job.project(owner.id, name="Cohort A")
        task = make_job.preprocessing(project, created_by_id=starter.id)

        notifications.notify_preprocessing_finished(db, task)

        assert len(sent) == 1
        assert sent[0]["to"] == "pp-starter@example.com"
        assert "Preprocessing finished" in sent[0]["subject"]
        assert "Cohort A" in sent[0]["subject"]
        # Deep link lands on the run, not just the project. Asserted on the
        # plain-text part: in the HTML the `&` is escaped to `&amp;` (correct
        # inside href, and covered by its own test below).
        assert f"tab=files&expandTask={task.id}" in sent[0]["text"]

    def test_falls_back_to_owner_without_initiator(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        """Rows created before created_by_id existed still reach someone."""
        owner = make_user("pp-fallback@example.com")
        project = make_job.project(owner.id)
        task = make_job.preprocessing(project, created_by_id=None)

        notifications.notify_preprocessing_finished(db, task)

        assert [m["to"] for m in sent] == ["pp-fallback@example.com"]

    def test_partial_failure_reports_counts_and_hint(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        from backend.src.models.project import PreprocessingStatus

        user = make_user("pp-partial@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(
            project,
            created_by_id=user.id,
            status=PreprocessingStatus.FAILED,
            total=5,
            processed=3,
            failed=2,
        )

        notifications.notify_preprocessing_finished(db, task)

        body = sent[0]["text"]
        assert "with errors" in sent[0]["subject"]
        assert "3 of 5" in body
        assert "retry the failed items" in body

    def test_total_failure_uses_failed_wording(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        from backend.src.models.project import PreprocessingStatus

        user = make_user("pp-failed@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(
            project,
            created_by_id=user.id,
            status=PreprocessingStatus.FAILED,
            total=2,
            processed=0,
            failed=2,
        )

        notifications.notify_preprocessing_finished(db, task)
        assert "Preprocessing failed" in sent[0]["subject"]

    def test_cancelled_is_silent(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        """The user cancelled it; they don't need to be told it stopped."""
        from backend.src.models.project import PreprocessingStatus

        user = make_user("pp-cancelled@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(
            project, created_by_id=user.id, status=PreprocessingStatus.CANCELLED
        )
        notifications.notify_preprocessing_finished(db, task)
        assert sent == []

    def test_inactive_initiator_falls_back_to_owner(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        owner = make_user("pp-active-owner@example.com")
        starter = make_user("pp-inactive@example.com", is_active=False)
        project = make_job.project(owner.id)
        task = make_job.preprocessing(project, created_by_id=starter.id)

        notifications.notify_preprocessing_finished(db, task)
        assert [m["to"] for m in sent] == ["pp-active-owner@example.com"]

    def test_localized_for_recipient(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        user = make_user("pp-de@example.com", language="de")
        project = make_job.project(user.id)
        task = make_job.preprocessing(project, created_by_id=user.id)

        notifications.notify_preprocessing_finished(db, task)
        assert "Vorverarbeitung abgeschlossen" in sent[0]["subject"]

    def test_carries_no_document_or_file_names(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        """The PHI boundary: labels and counts only, never per-item identifiers."""
        user = make_user("pp-phi@example.com")
        project = make_job.project(user.id, name="Cohort A")
        task = make_job.preprocessing(project, created_by_id=user.id)
        task.message = "patient_smith_scan.pdf failed: unreadable"
        db.commit()

        notifications.notify_preprocessing_finished(db, task)

        assert "patient_smith_scan.pdf" not in sent[0]["html"]
        assert "patient_smith_scan.pdf" not in sent[0]["text"]

    def test_a_broken_recipient_never_raises(
        self, email_on, offline, sent, db, make_user, make_job, monkeypatch
    ):
        """A notification failure must not fail the job that triggered it."""
        user = make_user("pp-boom@example.com")
        project = make_job.project(user.id)
        task = make_job.preprocessing(project, created_by_id=user.id)

        def _explode(*_a, **_kw):
            raise RuntimeError("render failed")

        monkeypatch.setattr(
            notifications.email_service, "render_notification", _explode
        )
        notifications.notify_preprocessing_finished(db, task)  # must not raise
        assert sent == []


class TestTrialNotification:
    def test_completed_counts_successful_results(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        from backend.src.models.project import TrialResult
        from backend.src.utils.enums import TrialResultStatus

        user = make_user("tr-ok@example.com")
        project = make_job.project(user.id, name="Cohort B")
        doc_ids = make_job.documents(project, 2)
        trial = make_job.trial(project, created_by_id=user.id, document_ids=doc_ids)
        db.add_all(
            [
                TrialResult(
                    trial_id=trial.id,
                    document_id=doc_id,
                    result={},
                    status=TrialResultStatus.SUCCESS,
                )
                for doc_id in doc_ids
            ]
        )
        db.commit()

        notifications.notify_trial_finished(db, trial)

        assert sent[0]["to"] == "tr-ok@example.com"
        assert "Extraction run finished" in sent[0]["subject"]
        assert "2 of 2" in sent[0]["text"]
        assert "gpt-4o-mini" in sent[0]["text"]
        assert f"tab=trials&expandTrial={trial.id}" in sent[0]["text"]

    def test_missing_results_are_reported_as_failures(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        user = make_user("tr-partial@example.com")
        project = make_job.project(user.id)
        # Three documents, no results at all → nothing succeeded.
        trial = make_job.trial(project, created_by_id=user.id, document_ids=[1, 2, 3])

        notifications.notify_trial_finished(db, trial)
        assert "failed" in sent[0]["subject"].lower()

    def test_unnamed_run_uses_its_number(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        user = make_user("tr-unnamed@example.com")
        project = make_job.project(user.id)
        trial = make_job.trial(project, created_by_id=user.id, name=None)

        notifications.notify_trial_finished(db, trial)
        assert "#1" in sent[0]["text"]

    def test_cancelled_is_silent(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        from backend.src.models.project import TrialStatus

        user = make_user("tr-cancelled@example.com")
        project = make_job.project(user.id)
        trial = make_job.trial(
            project, created_by_id=user.id, status=TrialStatus.CANCELLED
        )
        notifications.notify_trial_finished(db, trial)
        assert sent == []

    def test_naive_timestamps_do_not_crash_the_duration(
        self, email_on, offline, sent, db, make_user, make_job
    ):
        """SQLite hands back naive datetimes; subtracting them must still work."""
        user = make_user("tr-naive@example.com")
        project = make_job.project(user.id)
        trial = make_job.trial(project, created_by_id=user.id)
        trial.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=20
        )
        trial.finished_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

        notifications.notify_trial_finished(db, trial)
        assert len(sent) == 1


# --------------------------------------------------------------------------- #
# Project sharing
# --------------------------------------------------------------------------- #
class TestShareNotification:
    @pytest.fixture
    def share(self, db, make_user, make_job):
        from backend.src.models.project import ProjectShare
        from backend.src.utils.enums import ProjectPermission

        def _make(owner, collaborator, permission=ProjectPermission.READ):
            project = make_job.project(owner.id, name="Shared cohort")
            row = ProjectShare(
                project_id=project.id,
                user_id=collaborator.id,
                permission=permission,
                created_by_id=owner.id,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row

        return _make

    def test_grant_notifies_the_collaborator(
        self, email_on, sent, db, make_user, share
    ):
        owner = make_user("sh-owner@example.com")
        collaborator = make_user("sh-collab@example.com")
        row = share(owner, collaborator)

        notifications.notify_project_shared(db, row, actor=owner)

        assert sent[0]["to"] == "sh-collab@example.com"
        assert "Shared cohort" in sent[0]["subject"]
        assert "view-only" in sent[0]["text"]
        assert owner.full_name in sent[0]["text"]

    def test_update_uses_changed_wording(self, email_on, sent, db, make_user, share):
        from backend.src.utils.enums import ProjectPermission

        owner = make_user("sh-owner2@example.com")
        collaborator = make_user("sh-collab2@example.com")
        row = share(owner, collaborator, ProjectPermission.WRITE)

        notifications.notify_project_shared(db, row, actor=owner, updated=True)

        assert "has changed" in sent[0]["subject"]
        assert "full" in sent[0]["text"]

    def test_opted_out_collaborator_gets_nothing(
        self, email_on, sent, db, make_user, share
    ):
        owner = make_user("sh-owner3@example.com")
        collaborator = make_user(
            "sh-collab3@example.com", prefs={"project_shared": False}
        )
        notifications.notify_project_shared(db, share(owner, collaborator), actor=owner)
        assert sent == []

    def test_self_share_is_silent(self, email_on, sent, db, make_user, share):
        """An admin granting themselves access shouldn't email themselves."""
        actor = make_user("sh-self@example.com")
        other = make_user("sh-self-owner@example.com")
        row = share(other, actor)
        notifications.notify_project_shared(db, row, actor=actor)
        assert sent == []

    def test_presence_does_not_suppress_a_share(
        self, email_on, monkeypatch, sent, db, make_user, share
    ):
        """only_when_away is a job-email rule; a grant is worth mail regardless."""
        owner = make_user("sh-owner4@example.com")
        collaborator = make_user("sh-collab4@example.com")
        monkeypatch.setattr(notifications.presence, "is_online", lambda _uid: True)
        notifications.notify_project_shared(db, share(owner, collaborator), actor=owner)
        assert len(sent) == 1


# --------------------------------------------------------------------------- #
# Security notices
# --------------------------------------------------------------------------- #
class TestSecurityNotification:
    def test_password_changed(self, email_on, sent, db, make_user):
        user = make_user("sec-pw@example.com")
        notifications.notify_security_event(db, user, "password_changed")
        assert "password was changed" in sent[0]["subject"]
        assert "contact your administrator" in sent[0]["text"]

    def test_account_locked_interpolates_and_uses_its_own_note(
        self, email_on, sent, db, make_user
    ):
        user = make_user("sec-lock@example.com")
        notifications.notify_security_event(
            db, user, "account_locked", minutes=15, attempts=5
        )
        assert "15 minute" in sent[0]["text"]
        assert "5 failed sign-in attempts" in sent[0]["text"]
        assert "restored automatically" in sent[0]["text"]

    def test_identity_linked_names_the_provider(self, email_on, sent, db, make_user):
        user = make_user("sec-sso@example.com")
        notifications.notify_security_event(
            db, user, "identity_linked", provider="Keycloak"
        )
        assert "Keycloak" in sent[0]["text"]

    def test_unknown_event_sends_nothing(self, email_on, sent, db, make_user):
        user = make_user("sec-bogus@example.com")
        notifications.notify_security_event(db, user, "not_an_event")
        assert sent == []

    def test_opted_out_user_gets_nothing(self, email_on, sent, db, make_user):
        user = make_user("sec-off@example.com", prefs={"security": False})
        notifications.notify_security_event(db, user, "password_changed")
        assert sent == []

    def test_presence_does_not_suppress_a_security_notice(
        self, email_on, monkeypatch, sent, db, make_user
    ):
        user = make_user("sec-online@example.com")
        monkeypatch.setattr(notifications.presence, "is_online", lambda _uid: True)
        notifications.notify_security_event(db, user, "password_changed")
        assert len(sent) == 1


# --------------------------------------------------------------------------- #
# Admin alerts
# --------------------------------------------------------------------------- #
@pytest.fixture
def no_cooldown(monkeypatch):
    """Bypass the per-kind cooldown so each test starts from a clean slate."""
    monkeypatch.setattr(notifications, "_alert_cooldown_passed", lambda _kind: True)


class TestAdminAlerts:
    def test_goes_to_every_active_admin(
        self, email_on, sent, no_cooldown, db, make_user
    ):
        from backend.src.utils.enums import UserRole

        admin = make_user("al-admin@example.com", role=UserRole.admin)
        make_user("al-user@example.com")
        notifications.notify_admin_alert(db, "stuck_tasks", count=3)

        recipients = {m["to"] for m in sent}
        assert admin.email in recipients
        assert "al-user@example.com" not in recipients
        assert "3 task" in sent[0]["text"]

    def test_opted_out_admin_is_skipped(
        self, email_on, sent, no_cooldown, db, make_user
    ):
        from backend.src.utils.enums import UserRole

        make_user(
            "al-optout@example.com", role=UserRole.admin, prefs={"admin_alerts": False}
        )
        notifications.notify_admin_alert(db, "worker_crash", reason="WorkerLostError")
        assert "al-optout@example.com" not in {m["to"] for m in sent}

    def test_error_alert_carries_only_the_error_id(
        self, email_on, sent, no_cooldown, db, make_user
    ):
        from backend.src.utils.enums import UserRole

        make_user("al-err@example.com", role=UserRole.admin)
        notifications.notify_admin_alert(db, "error_spike", error_id="abc-123")
        body = sent[-1]["text"]
        assert "abc-123" in body

    def test_unknown_kind_sends_nothing(self, email_on, sent, no_cooldown, db):
        notifications.notify_admin_alert(db, "made_up_kind")
        assert sent == []

    def test_cooldown_suppresses_the_second_alert(
        self, email_on, sent, db, make_user, monkeypatch, settings_inst
    ):
        from backend.src.utils.enums import UserRole

        make_user("al-cool@example.com", role=UserRole.admin)
        monkeypatch.setattr(settings_inst, "NOTIFY_ADMIN_ALERT_COOLDOWN_MINUTES", 60)
        # Force the in-process fallback path (no Redis in tests anyway).
        monkeypatch.setattr(notifications, "get_settings", notifications.get_settings)
        notifications._local_alert_cooldown.clear()
        monkeypatch.setattr(
            "backend.src.utils.redis_broadcast.get_redis_client", lambda: None
        )

        notifications.notify_admin_alert(db, "worker_crash", reason="A")
        first = len(sent)
        notifications.notify_admin_alert(db, "worker_crash", reason="B")

        assert first >= 1
        assert len(sent) == first, "second alert of the same kind should be suppressed"


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
class TestDispatch:
    def test_falls_back_to_a_thread_when_celery_cannot_take_it(self, monkeypatch):
        """With DISABLE_CELERY (and on a dead broker) the send still happens."""
        import threading

        done = threading.Event()
        captured = {}

        def _send_email(*, to, subject, html, text):
            captured.update(to=to, subject=subject)
            done.set()
            return True

        monkeypatch.setattr(notifications.email_service, "send_email", _send_email)
        notifications._dispatch("a@b.c", "Subj", "<p>h</p>", "h")

        assert done.wait(timeout=5), "inline fallback never ran"
        assert captured == {"to": "a@b.c", "subject": "Subj"}

    def test_celery_task_is_none_when_celery_is_disabled(self):
        """The contract _dispatch checks before calling apply_async."""
        from backend.src.celery import notifications as celery_notifications

        assert celery_notifications.send_notification_email_task is None

    def test_prefers_celery_when_available(self, monkeypatch):
        """When a task exists, nothing is sent inline — it goes on the queue."""
        queued = {}

        class FakeTask:
            def apply_async(self, kwargs=None, **_options):
                queued.update(kwargs or {})

        module = type("M", (), {"send_notification_email_task": FakeTask()})
        monkeypatch.setitem(
            __import__("sys").modules, "backend.src.celery.notifications", module
        )

        def _must_not_send(**_kw):
            raise AssertionError("should have been queued, not sent inline")

        monkeypatch.setattr(notifications.email_service, "send_email", _must_not_send)
        notifications._dispatch("a@b.c", "Subj", "<p>h</p>", "h")
        assert queued["to"] == "a@b.c"


# --------------------------------------------------------------------------- #
# Presence
# --------------------------------------------------------------------------- #
class TestPresence:
    def test_reports_away_without_redis(self, monkeypatch):
        """No Redis means no presence data — we must err towards sending."""
        monkeypatch.setattr(presence, "get_redis_client", lambda: None)
        assert presence.is_online(1) is False

    def test_no_ops_without_redis(self, monkeypatch):
        monkeypatch.setattr(presence, "get_redis_client", lambda: None)
        presence.mark_online(1)
        presence.mark_offline(1)  # must not raise

    def test_marks_and_reads_through_the_client(self, monkeypatch):
        calls = []

        class FakeRedis:
            def setex(self, key, ttl, value):
                calls.append(("setex", key, ttl))

            def delete(self, key):
                calls.append(("delete", key))

            def exists(self, key):
                calls.append(("exists", key))
                return 1

        monkeypatch.setattr(presence, "get_redis_client", lambda: FakeRedis())
        presence.mark_online(7)
        assert presence.is_online(7) is True
        presence.mark_offline(7)
        assert [c[0] for c in calls] == ["setex", "exists", "delete"]
        assert all(c[1] == "presence:user:7" for c in calls)

    def test_redis_errors_are_swallowed(self, monkeypatch):
        class BrokenRedis:
            def setex(self, *_a):
                raise RuntimeError("down")

            def delete(self, *_a):
                raise RuntimeError("down")

            def exists(self, *_a):
                raise RuntimeError("down")

        monkeypatch.setattr(presence, "get_redis_client", lambda: BrokenRedis())
        presence.mark_online(1)
        presence.mark_offline(1)
        assert presence.is_online(1) is False


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
class TestPreferencesApi:
    def test_get_returns_defaults_without_a_stored_row(
        self, client, api_url, user_headers
    ):
        resp = client.get(
            f"{api_url}/user/me/notification-preferences", headers=user_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["job_finished"] is True
        assert body["only_when_away"] is True
        assert body["min_job_seconds"] is None
        assert "email_configured" in body

    def test_patch_persists_and_round_trips(self, client, api_url, user_headers):
        resp = client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"job_finished": False, "min_job_seconds": 300},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job_finished"] is False
        assert resp.json()["min_job_seconds"] == 300

        again = client.get(
            f"{api_url}/user/me/notification-preferences", headers=user_headers
        )
        assert again.json()["job_finished"] is False
        assert again.json()["min_job_seconds"] == 300

        # A partial patch must not reset the fields it omits.
        resp = client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"security": False},
        )
        assert resp.json()["job_finished"] is False
        assert resp.json()["security"] is False

        # Restore so later tests see a clean user.
        client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"job_finished": True, "security": True, "min_job_seconds": None},
        )

    def test_null_clears_the_duration_override(self, client, api_url, user_headers):
        client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"min_job_seconds": 600},
        )
        resp = client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"min_job_seconds": None},
        )
        assert resp.json()["min_job_seconds"] is None

    def test_out_of_range_duration_is_rejected(self, client, api_url, user_headers):
        resp = client.patch(
            f"{api_url}/user/me/notification-preferences",
            headers=user_headers,
            json={"min_job_seconds": 999999},
        )
        assert resp.status_code == 422

    def test_requires_authentication(self, client, api_url):
        assert (
            client.get(f"{api_url}/user/me/notification-preferences").status_code == 401
        )


class TestLanguageApi:
    def test_patch_stores_the_locale(self, client, api_url, user_headers):
        resp = client.patch(
            f"{api_url}/user/me/language",
            headers=user_headers,
            json={"preferred_language": "de"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["preferred_language"] == "de"
        assert (
            client.get(f"{api_url}/user/me", headers=user_headers).json()[
                "preferred_language"
            ]
            == "de"
        )
        client.patch(
            f"{api_url}/user/me/language",
            headers=user_headers,
            json={"preferred_language": "en"},
        )

    def test_unsupported_locale_is_rejected(self, client, api_url, user_headers):
        resp = client.patch(
            f"{api_url}/user/me/language",
            headers=user_headers,
            json={"preferred_language": "kl"},
        )
        assert resp.status_code == 422

    def test_requires_authentication(self, client, api_url):
        resp = client.patch(
            f"{api_url}/user/me/language", json={"preferred_language": "de"}
        )
        assert resp.status_code == 401


class TestTestEmailApi:
    def test_rejected_when_email_not_configured(self, client, api_url, admin_headers):
        resp = client.post(
            f"{api_url}/admin/settings/test-email", headers=admin_headers
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "admin.email_not_configured"

    def test_non_admin_is_forbidden(self, client, api_url, user_headers):
        resp = client.post(f"{api_url}/admin/settings/test-email", headers=user_headers)
        assert resp.status_code in (401, 403)

    def test_sends_to_the_caller(self, client, api_url, admin_headers, monkeypatch):
        from backend.src.routers.v1.endpoints import admin as admin_router

        monkeypatch.setattr(admin_router, "is_email_configured", lambda: True)
        recorded = {}

        def _send(user):
            recorded["to"] = user.email
            return True

        monkeypatch.setattr(admin_router, "send_test_email", _send)
        resp = client.post(
            f"{api_url}/admin/settings/test-email", headers=admin_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"sent": True, "recipient": "admin@example.com"}
        assert recorded["to"] == "admin@example.com"

    def test_smtp_rejection_surfaces_as_502(
        self, client, api_url, admin_headers, monkeypatch
    ):
        from backend.src.routers.v1.endpoints import admin as admin_router

        monkeypatch.setattr(admin_router, "is_email_configured", lambda: True)
        monkeypatch.setattr(admin_router, "send_test_email", lambda _u: False)
        resp = client.post(
            f"{api_url}/admin/settings/test-email", headers=admin_headers
        )
        assert resp.status_code == 502
