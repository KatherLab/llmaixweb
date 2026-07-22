"""Unit tests for the pure helpers in ``utils/info_extraction.py``.

The extraction pipeline was only exercised end-to-end (via the trial API with a
mocked LLM), which left the module's rich helper layer — provider detection,
prompt building, the tolerant JSON repair path, truncation analysis, tuning
advice, and result-status classification — almost entirely uncovered (~31%).
These are pure, branchy, security-relevant functions, so they get direct
unit coverage here. DB-touching helpers (``update_trial_progress``,
``_store_result``) are exercised at the bottom against real ORM rows.
"""

import uuid

import pytest

from backend.tests.fake_llm import make_fake_openai

# Imported lazily (below) so test *collection* doesn't trigger the app's
# settings init — ``info_extraction`` pulls in ``db.session``, which builds the
# engine from ``settings`` and ``sys.exit``s without the env vars the
# session-scoped conftest fixture installs at setup time.
ie = None


@pytest.fixture(scope="session", autouse=True)
def _load_info_extraction(configure_test_environment):
    global ie
    from backend.src.utils import info_extraction

    ie = info_extraction
    yield


# ---------------------------------------------------------------------------
# _detect_provider
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("", "generic"),
        (None, "generic"),
        ("https://api.openai.com/v1", "openai"),
        ("https://openai.com/v1", "openai"),
        # Look-alike hosts must NOT be classified as OpenAI (substring trap).
        ("https://openai.com.evil.example/v1", "generic"),
        ("https://myopenai.com/v1", "generic"),
        ("http://my-vllm-host:8000/v1", "vllm"),
        ("http://localhost:5000/v1", "vllm"),
        ("http://localhost:11434/v1", "ollama"),
        ("http://ollama:11434/v1", "ollama"),
        ("http://llama-cpp-server/v1", "llama_cpp"),
        ("http://host/cpp/v1", "llama_cpp"),
        ("http://some-random-host/v1", "generic"),
    ],
)
def test_detect_provider(url, expected):
    assert ie._detect_provider(url) == expected


# ---------------------------------------------------------------------------
# sanitize_for_prompt
# ---------------------------------------------------------------------------


def test_sanitize_none_and_bytes():
    assert ie.sanitize_for_prompt(None) == ""
    assert ie.sanitize_for_prompt(b"hello \xff world") == "hello � world"


def test_sanitize_strips_c0_controls_but_keeps_newline():
    raw = "a\x00b\x07c\nd"
    out = ie.sanitize_for_prompt(raw)
    assert "\x00" not in out and "\x07" not in out
    assert "\n" in out
    assert out == "abc\nd"


def test_sanitize_tabs_become_spaces_and_cr_becomes_newline():
    assert ie.sanitize_for_prompt("a\tb") == "a    b"
    # CR is normalized to LF; note a CRLF therefore becomes a doubled newline.
    assert ie.sanitize_for_prompt("a\rb") == "a\nb"
    assert ie.sanitize_for_prompt("a\r\nb") == "a\n\nb"


def test_sanitize_collapse_space():
    raw = "a" + "\n" * 6 + "b" + " " * 5 + "c"
    out = ie.sanitize_for_prompt(raw, collapse_space=True)
    assert "\n\n\n\n" not in out
    assert "     " not in out


# ---------------------------------------------------------------------------
# _build_messages
# ---------------------------------------------------------------------------


def _prompt(system=None, user=None):
    from types import SimpleNamespace

    return SimpleNamespace(system_prompt=system, user_prompt=user)


def test_build_messages_user_placeholder_replaced():
    msgs = ie._build_messages(
        _prompt(system="You extract.", user="Doc: {document_content}"),
        "SECRET_TEXT",
    )
    user = [m for m in msgs if m["role"] == "user"][0]
    assert "SECRET_TEXT" in user["content"]
    assert "{document_content}" not in user["content"]


def test_build_messages_injection_guidance_added_once():
    msgs = ie._build_messages(_prompt(system="Extract data", user="go"), "doc")
    system = [m for m in msgs if m["role"] == "system"][0]["content"]
    assert "untrusted" in system.lower()
    # Not added again when the prompt already talks about untrusted content.
    msgs2 = ie._build_messages(
        _prompt(system="The document is untrusted data.", user="go"), "doc"
    )
    system2 = [m for m in msgs2 if m["role"] == "system"][0]["content"]
    assert system2.lower().count("untrusted") == 1


def test_build_messages_no_placeholder_appends_document_markers():
    msgs = ie._build_messages(_prompt(system="sys", user="Extract"), "BODY")
    user = [m for m in msgs if m["role"] == "user"][0]["content"]
    assert "--- DOCUMENT CONTENT ---" in user
    assert "BODY" in user


def test_build_messages_schema_appended_unless_present():
    schema = {"type": "object"}
    msgs = ie._build_messages(_prompt(user="Extract"), "doc", schema)
    user = [m for m in msgs if m["role"] == "user"][0]["content"]
    assert "JSON schema" in user
    # If the prompt already references a schema placeholder, don't append again.
    msgs2 = ie._build_messages(_prompt(user="Use {schema} here"), "doc", schema)
    user2 = [m for m in msgs2 if m["role"] == "user"][0]["content"]
    assert "Extract the data according to this JSON schema" not in user2


def test_build_messages_fallback_minimal_user_when_no_prompts():
    msgs = ie._build_messages(_prompt(), "DOCBODY", {"type": "object"})
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    assert "DOCBODY" in msgs[0]["content"]


def test_build_messages_system_only_without_placeholder_includes_document():
    """Regression: a prompt with only a system prompt (no placeholder) and no
    user prompt must still send the document to the model. Previously the
    document text was silently dropped, so extraction ran against nothing."""
    msgs = ie._build_messages(_prompt(system="Extract data"), "DOCBODY")
    user = [m for m in msgs if m["role"] == "user"]
    assert len(user) == 1
    assert "DOCBODY" in user[0]["content"]


def test_build_messages_system_placeholder_no_user_does_not_duplicate_document():
    """When the document IS injected via a system-prompt placeholder and there is
    no user prompt, we must NOT also append a duplicate document user message."""
    msgs = ie._build_messages(_prompt(system="Doc: {document_content}"), "DOCBODY")
    assert not any(m["role"] == "user" for m in msgs)
    system = [m for m in msgs if m["role"] == "system"][0]["content"]
    assert "DOCBODY" in system


# ---------------------------------------------------------------------------
# _completion_kwargs
# ---------------------------------------------------------------------------


def test_completion_kwargs_generic_uses_response_format_and_max_tokens():
    kw = ie._completion_kwargs(
        "m",
        {"type": "object"},
        [{"role": "user", "content": "x"}],
        {"max_completion_tokens": 512},
        base_url="http://generic-host/v1",
    )
    assert kw["response_format"]["type"] == "json_schema"
    # generic maps the cap to `max_tokens`
    assert kw["max_tokens"] == 512
    assert "max_completion_tokens" not in kw


def test_completion_kwargs_openai_uses_completion_tokens_param():
    kw = ie._completion_kwargs(
        "m",
        {"type": "object"},
        [],
        {"max_completion_tokens": 512},
        base_url="https://api.openai.com/v1",
    )
    assert kw["max_completion_tokens"] == 512
    assert "max_tokens" not in kw


def test_completion_kwargs_vllm_sets_guided_json():
    kw = ie._completion_kwargs(
        "m", {"type": "object"}, [], None, base_url="http://vllm-host/v1"
    )
    assert kw["extra_body"]["guided_json"] == {"type": "object"}
    assert kw["extra_body"]["guided_decode"] is True


def test_completion_kwargs_reasoning_effort_only_when_supported():
    # openai supports it
    kw = ie._completion_kwargs(
        "m",
        {"type": "object"},
        [],
        {"reasoning_effort": "high"},
        base_url="https://api.openai.com/v1",
    )
    assert kw["reasoning_effort"] == "high"
    # ollama does not -> silently dropped
    kw2 = ie._completion_kwargs(
        "m",
        {"type": "object"},
        [],
        {"reasoning_effort": "high"},
        base_url="http://localhost:11434/v1",
    )
    assert "reasoning_effort" not in kw2


def test_completion_kwargs_empty_adv_returns_base():
    kw = ie._completion_kwargs("m", {"type": "object"}, [], None)
    assert kw["model"] == "m"
    assert "temperature" not in kw


# ---------------------------------------------------------------------------
# _extract_json_snippet / _escape_ctrls_in_json_strings / safe_json_loads
# ---------------------------------------------------------------------------


def test_extract_json_snippet_strips_code_fence():
    s = '```json\n{"a": 1}\n```'
    assert ie._extract_json_snippet(s) == '{"a": 1}'


def test_extract_json_snippet_ignores_braces_inside_strings():
    s = 'noise {"a": "}"} trailing'
    assert ie._extract_json_snippet(s) == '{"a": "}"}'


def test_extract_json_snippet_array_top_level():
    s = "prefix [1, 2, 3] suffix"
    assert ie._extract_json_snippet(s) == "[1, 2, 3]"


def test_extract_json_snippet_unbalanced_returns_from_start():
    s = 'x {"a": 1'
    assert ie._extract_json_snippet(s) == '{"a": 1'


def test_extract_json_snippet_non_string():
    assert ie._extract_json_snippet(None) == ""


def test_escape_ctrls_in_json_strings_escapes_only_inside_strings():
    s = '{"a": "line1\nline2"}'
    out = ie._escape_ctrls_in_json_strings(s)
    assert "\\u000a" in out
    # The structural newline handling shouldn't corrupt the keys/values
    import json

    assert json.loads(out) == {"a": "line1\nline2"}


def test_safe_json_loads_valid():
    assert ie.safe_json_loads('{"a": 1}') == {"a": 1}


def test_safe_json_loads_repairs_fenced_and_smart_quotes():
    # Regression: curly/typographic quotes must be normalized to straight quotes
    # during repair. This normalization was previously dead code (the curly-quote
    # literals had been mangled into a triple-quoted string), so LLM output using
    # typographic quotes was wrongly rejected as invalid JSON.
    raw = "```json\n{“key”: “val”}\n```"
    assert ie.safe_json_loads(raw) == {"key": "val"}
    # A curly apostrophe inside a value is normalized to a straight apostrophe.
    assert ie.safe_json_loads("{“k”: “it’s ok”}") == {"k": "it's ok"}


def test_safe_json_loads_repairs_control_chars():
    raw = '{"a": "b\nc"}'  # literal newline inside string
    assert ie.safe_json_loads(raw) == {"a": "b\nc"}


def test_safe_json_loads_none_and_unparseable():
    with pytest.raises(Exception):
        ie.safe_json_loads(None)
    with pytest.raises(Exception):
        ie.safe_json_loads("this is definitely not json")


# ---------------------------------------------------------------------------
# validate_against_schema
# ---------------------------------------------------------------------------


def test_validate_against_schema_ok():
    ok, err = ie.validate_against_schema(
        {"x": "hi"}, {"type": "object", "properties": {"x": {"type": "string"}}}
    )
    assert ok and err is None


def test_validate_against_schema_invalid_instance():
    ok, err = ie.validate_against_schema(
        {"x": 5}, {"type": "object", "properties": {"x": {"type": "string"}}}
    )
    assert not ok and "validation failed" in err.lower()


def test_validate_against_schema_bad_schema():
    ok, err = ie.validate_against_schema({"x": 1}, {"type": "not-a-real-type"})
    assert not ok and err


# ---------------------------------------------------------------------------
# _analyze_truncation
# ---------------------------------------------------------------------------


def test_analyze_truncation_empty():
    r = ie._analyze_truncation("")
    assert r["empty_output"] and r["likely_truncated"]


def test_analyze_truncation_balanced_clean():
    r = ie._analyze_truncation('{"a": 1}')
    assert not r["likely_truncated"]
    assert r["unclosed_braces"] == 0


def test_analyze_truncation_unclosed_brace():
    r = ie._analyze_truncation('{"a": {"b": 1}')
    assert r["likely_truncated"] and r["unclosed_braces"] == 1


def test_analyze_truncation_unclosed_string():
    r = ie._analyze_truncation('{"a": "unterminated')
    assert r["likely_truncated"] and r["unclosed_string"]


# ---------------------------------------------------------------------------
# _determine_result_status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            dict(
                finish_reason="stop",
                parse_error=None,
                schema_error=None,
                has_refusal=True,
                has_content=True,
            ),
            "refused",
        ),
        (
            dict(
                finish_reason="stop",
                parse_error="boom",
                schema_error=None,
                has_refusal=False,
                has_content=False,
            ),
            "invalid_json",
        ),
        (
            dict(
                finish_reason="stop",
                parse_error=None,
                schema_error="bad",
                has_refusal=False,
                has_content=True,
            ),
            "schema_invalid",
        ),
        (
            dict(
                finish_reason="stop",
                parse_error=None,
                schema_error=None,
                has_refusal=False,
                has_content=False,
            ),
            "failed",
        ),
        (
            dict(
                finish_reason="length",
                parse_error=None,
                schema_error=None,
                has_refusal=False,
                has_content=True,
            ),
            "incomplete",
        ),
        (
            dict(
                finish_reason="stop",
                parse_error=None,
                schema_error=None,
                has_refusal=False,
                has_content=True,
            ),
            "success",
        ),
    ],
)
def test_determine_result_status(kwargs, expected):
    assert ie._determine_result_status(**kwargs) == expected


# ---------------------------------------------------------------------------
# _bump_for_length
# ---------------------------------------------------------------------------


def test_bump_for_length_defaults_and_temperature():
    out = ie._bump_for_length(None, None, has_reasoning=False)
    assert out["max_completion_tokens"] >= 2048
    assert out["temperature"] == 0


def test_bump_for_length_uses_usage_completion_tokens():
    usage = type("U", (), {"completion_tokens": 1000})()
    out = ie._bump_for_length({"max_completion_tokens": 1500}, usage, False)
    # min(1000*2, 1000+4096)=2000, but never below current cap 1500
    assert out["max_completion_tokens"] == 2000


def test_bump_for_length_never_lowers_below_current_cap():
    usage = type("U", (), {"completion_tokens": 10})()
    out = ie._bump_for_length({"max_completion_tokens": 8000}, usage, False)
    assert out["max_completion_tokens"] == 8000


def test_bump_for_length_preserves_reasoning_effort():
    out = ie._bump_for_length({"reasoning_effort": "high"}, None, True)
    assert out["reasoning_effort"] == "high"


# ---------------------------------------------------------------------------
# advice + guidance formatting
# ---------------------------------------------------------------------------


def test_advice_for_finish_reason_length_recommends_more_tokens():
    usage = type(
        "U", (), {"completion_tokens": 500, "prompt_tokens": 100, "total_tokens": 600}
    )()
    advice = ie._advice_for_finish_reason(
        finish_reason="length",
        usage=usage,
        advanced_options={"max_completion_tokens": 500, "reasoning_effort": "high"},
        has_reasoning=True,
    )
    actions = {r["action"] for r in advice["recommendations"]}
    assert "increase_max_completion_tokens" in actions
    assert "lower_reasoning_effort" in actions


def test_advice_for_finish_reason_string_max_tokens_no_string_multiplication():
    """A numeric-*string* max_completion_tokens (advanced_options is unvalidated)
    with no usage completion_tokens must double to 2*N, not concatenate the
    string ("500" -> 1000, never 500500)."""
    advice = ie._advice_for_finish_reason(
        finish_reason="length",
        usage=None,
        advanced_options={"max_completion_tokens": "500"},
        has_reasoning=False,
    )
    reco = next(
        r
        for r in advice["recommendations"]
        if r["action"] == "increase_max_completion_tokens"
    )
    assert reco["suggested_value"] == 1000


def test_advice_for_finish_reason_garbage_max_tokens_falls_back():
    advice = ie._advice_for_finish_reason(
        finish_reason="length",
        usage=None,
        advanced_options={"max_completion_tokens": "not-a-number"},
        has_reasoning=False,
    )
    reco = next(
        r
        for r in advice["recommendations"]
        if r["action"] == "increase_max_completion_tokens"
    )
    assert reco["suggested_value"] == 2048


def test_advice_for_finish_reason_content_filter():
    advice = ie._advice_for_finish_reason(
        finish_reason="content_filter",
        usage=None,
        advanced_options=None,
        has_reasoning=False,
    )
    assert advice["recommendations"][0]["action"] == "adjust_prompt_or_redact"


def test_summarize_recommendations_dedupes():
    recos = [
        {"action": "increase_max_completion_tokens", "suggested_value": 2048},
        {"action": "increase_max_completion_tokens", "suggested_value": 2048},
        {"action": "lower_temperature"},
    ]
    out = ie._summarize_recommendations_for_message(recos)
    assert out.count("increase max_completion_tokens") == 1
    assert "lower temperature" in out


def test_build_user_guidance_length_has_title_and_message():
    trunc = ie._analyze_truncation("")
    advice = ie._advice_for_finish_reason(
        finish_reason="length",
        usage=None,
        advanced_options={"max_completion_tokens": 100},
        has_reasoning=False,
    )
    g = ie._build_user_guidance(finish_reason="length", truncation=trunc, advice=advice)
    assert "cut off" in g["title"].lower()
    assert g["user_message"].startswith(g["title"])


def test_format_reco_with_and_without_value():
    assert ie._format_reco("lower_temperature", None).endswith(".")
    assert "2048" in ie._format_reco("increase_max_completion_tokens", 2048)


# ---------------------------------------------------------------------------
# time helpers
# ---------------------------------------------------------------------------


def test_to_utc_naive_and_aware():
    import datetime as dt

    naive = dt.datetime(2020, 1, 1, 12, 0, 0)
    assert ie._to_utc(naive).tzinfo is not None
    aware = dt.datetime(2020, 1, 1, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
    assert ie._to_utc(aware).utcoffset() == dt.timedelta(0)


# ---------------------------------------------------------------------------
# DB-backed helpers: update_trial_progress + _store_result
# ---------------------------------------------------------------------------


@pytest.fixture
def extraction_fixture(client):
    """Create a minimal project/file/document/schema/prompt/trial graph and
    return the ids plus a live session for the DB-backed helpers."""
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import FileCreator, FileStorageType, FileType

    db = SessionLocal()

    def _add(obj):
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    proj = _add(
        models.Project(name=f"ie-{uuid.uuid4().hex[:8]}", description="x", owner_id=1)
    )
    cfg = _add(models.PreprocessingConfiguration(project_id=proj.id, name="c"))
    f = _add(
        models.File(
            project_id=proj.id,
            file_storage_type=FileStorageType.LOCAL,
            file_uuid=str(uuid.uuid4()),
            file_name="a.txt",
            file_type=list(FileType)[-1],
            file_creator=FileCreator.user,
        )
    )
    doc = _add(
        models.Document(
            project_id=proj.id,
            original_file_id=f.id,
            preprocessing_config_id=cfg.id,
            text="hello",
            document_name="d",
        )
    )
    schema = _add(
        models.Schema(
            project_id=proj.id,
            schema_name="s",
            schema_definition={
                "type": "object",
                "required": ["x"],
                "properties": {"x": {"type": "string"}},
            },
        )
    )
    prompt = _add(
        models.Prompt(
            project_id=proj.id, name="p", system_prompt="sys", user_prompt="u"
        )
    )
    trial = _add(
        models.Trial(
            project_id=proj.id,
            project_trial_number=1,
            schema_id=schema.id,
            prompt_id=prompt.id,
            llm_model="m",
            document_ids=[doc.id],
            api_key_encrypted="x",
            base_url="http://x",
        )
    )
    yield {"db": db, "trial": trial, "doc": doc, "schema": schema}
    db.close()


def _resp(**kw):
    return make_fake_openai(**kw)().chat.completions.create(model="m", messages=[])


def test_store_result_success(extraction_fixture):
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    ie._store_result(
        db, trial.id, doc.id, _resp(content='{"x": "ok"}'), {}, schema.schema_definition
    )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.SUCCESS
    assert row.result == {"x": "ok"}


def test_store_result_empty_raises_and_marks_status(extraction_fixture):
    from backend.src import models

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    with pytest.raises(ie.IncompleteLLMResponseError):
        ie._store_result(
            db,
            trial.id,
            doc.id,
            _resp(content="", finish_reason="length"),
            {},
            schema.schema_definition,
        )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.result is None
    assert (row.additional_content or {}).get("error_type") == "empty_content"


def test_store_result_invalid_json_raises(extraction_fixture):
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    with pytest.raises(ie.IncompleteLLMResponseError):
        ie._store_result(
            db,
            trial.id,
            doc.id,
            _resp(content="not json"),
            {},
            schema.schema_definition,
        )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.INVALID_JSON


def test_store_result_schema_invalid_raises(extraction_fixture):
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    # valid JSON but violates schema (x must be string, missing required)
    with pytest.raises(ie.IncompleteLLMResponseError):
        ie._store_result(
            db,
            trial.id,
            doc.id,
            _resp(content='{"y": 1}'),
            {},
            schema.schema_definition,
        )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.SCHEMA_INVALID


def test_store_result_refusal_raises(extraction_fixture):
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    with pytest.raises(ie.IncompleteLLMResponseError):
        ie._store_result(
            db,
            trial.id,
            doc.id,
            _resp(content="", refusal="I cannot help"),
            {},
            schema.schema_definition,
        )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.REFUSED


def test_store_result_truncated_but_valid_json_stored_as_incomplete(extraction_fixture):
    """A `finish_reason="length"` response whose content still parses to
    schema-valid JSON must be STORED (status=incomplete, with a warning +
    truncation/tuning metadata) and must NOT raise — the model was cut off but
    produced usable output."""
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    ie._store_result(
        db,
        trial.id,
        doc.id,
        _resp(content='{"x": "ok"}', finish_reason="length"),
        {"max_completion_tokens": 100},
        schema.schema_definition,
    )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.INCOMPLETE
    assert row.result == {"x": "ok"}
    additional = row.additional_content or {}
    assert "warning" in additional
    assert "truncation_analysis" in additional
    assert "tuning_advice" in additional


def test_store_result_skips_existing_success(extraction_fixture):
    from backend.src import models

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    ie._store_result(
        db,
        trial.id,
        doc.id,
        _resp(content='{"x": "first"}'),
        {},
        schema.schema_definition,
    )
    # A second call must NOT overwrite an already-successful result.
    ie._store_result(
        db,
        trial.id,
        doc.id,
        _resp(content='{"x": "second"}'),
        {},
        schema.schema_definition,
    )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.result == {"x": "first"}


def test_store_result_updates_prior_failure(extraction_fixture):
    from backend.src import models
    from backend.src.utils.enums import TrialResultStatus

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    with pytest.raises(ie.IncompleteLLMResponseError):
        ie._store_result(
            db, trial.id, doc.id, _resp(content="broken"), {}, schema.schema_definition
        )
    # Retrying a previously-failed doc should replace it with the success.
    ie._store_result(
        db,
        trial.id,
        doc.id,
        _resp(content='{"x": "recovered"}'),
        {},
        schema.schema_definition,
    )
    row = (
        db.query(models.TrialResult)
        .filter_by(trial_id=trial.id, document_id=doc.id)
        .one()
    )
    assert row.status == TrialResultStatus.SUCCESS
    assert row.result == {"x": "recovered"}


def test_update_trial_progress_dedupes_document_ids(extraction_fixture):

    fx = extraction_fixture
    db, trial, doc, schema = fx["db"], fx["trial"], fx["doc"], fx["schema"]
    # Duplicate doc ids must not inflate the denominator (progress would never
    # reach 1.0). One doc, one result -> progress 1.0.
    trial.document_ids = [doc.id, doc.id]
    db.commit()
    ie._store_result(
        db, trial.id, doc.id, _resp(content='{"x": "ok"}'), {}, schema.schema_definition
    )
    ie.update_trial_progress(db, trial.id)
    db.refresh(trial)
    assert trial.docs_done == 1
    assert trial.progress == 1.0


def test_update_trial_progress_missing_trial_is_noop():
    from backend.src.db.session import SessionLocal

    db = SessionLocal()
    try:
        # Should not raise for a non-existent trial id.
        ie.update_trial_progress(db, 10_000_000)
    finally:
        db.close()
