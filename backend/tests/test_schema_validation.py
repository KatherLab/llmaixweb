"""Save-time validation of extraction schemas.

Regression origin: a production schema listed ``Biopsien_mit_IHC`` in
``required`` while ``properties`` defined a differently-named key. Grammar-
constrained decoding (vLLM/xgrammar, OpenAI structured outputs) builds its
automaton from ``properties`` and ignores the orphan, so the provider returned
output it considered conformant; ``validate_against_schema`` then rejected every
single document with "'Biopsien_mit_IHC' is a required property". The schema was
saved, and every trial using it was doomed before it started.

These tests pin the unit behaviour of ``find_schema_problems`` and the two gates
that use it: schema create/update, and trial creation (which also catches rows
saved before the check existed).
"""

import uuid

import pytest

from backend.src.utils.schema_validation import find_schema_problems

# --------------------------------------------------------------------------- #
# find_schema_problems
# --------------------------------------------------------------------------- #

_GOOD = {
    "type": "object",
    "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
    "required": ["a"],
}


def test_clean_schema_has_no_problems():
    assert find_schema_problems(_GOOD) == []


def test_schema_without_required_is_fine():
    assert find_schema_problems({"type": "object", "properties": {"a": {}}}) == []


def test_orphan_required_at_root_is_reported():
    problems = find_schema_problems(
        {
            "type": "object",
            "properties": {"Biopsien_mit_IHC_Anzahl": {"type": "integer"}},
            "required": ["Biopsien_mit_IHC"],
        }
    )
    assert len(problems) == 1
    assert problems[0]["code"] == "required_without_property"
    assert problems[0]["field"] == "Biopsien_mit_IHC"
    assert problems[0]["path"] == "#"
    # A near-miss name is the usual cause (a rename that missed `required`),
    # so the message points at it.
    assert problems[0]["suggestion"] == "Biopsien_mit_IHC_Anzahl"


def test_required_with_no_properties_at_all_is_reported():
    problems = find_schema_problems({"type": "object", "required": ["x"]})
    assert [p["code"] for p in problems] == ["required_without_property"]
    assert problems[0]["suggestion"] is None


@pytest.mark.parametrize(
    "schema,expected_path",
    [
        (
            {
                "type": "object",
                "properties": {
                    "Befund": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}},
                        "required": ["missing"],
                    }
                },
            },
            "#/properties/Befund",
        ),
        (
            {
                "type": "object",
                "properties": {
                    "Liste": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"a": {"type": "string"}},
                            "required": ["missing"],
                        },
                    }
                },
            },
            "#/properties/Liste/items",
        ),
        (
            {
                "type": "object",
                "$defs": {
                    "Node": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}},
                        "required": ["missing"],
                    }
                },
            },
            "#/$defs/Node",
        ),
    ],
)
def test_orphan_required_is_found_at_every_nesting_level(schema, expected_path):
    problems = find_schema_problems(schema)
    assert [p["path"] for p in problems] == [expected_path]


@pytest.mark.parametrize(
    "node",
    [
        # Composition can supply the property from another branch — we can't
        # decide locally, so we stay quiet rather than reject a valid schema.
        {"allOf": [{"properties": {"x": {"type": "string"}}}], "required": ["x"]},
        {"anyOf": [{"properties": {"x": {}}}], "required": ["x"]},
        {"$ref": "#/$defs/Other", "required": ["x"]},
        {"if": {"properties": {"x": {}}}, "then": {}, "required": ["x"]},
        {"patternProperties": {"^x": {"type": "string"}}, "required": ["x"]},
        # A *schema* for additional properties means free-form keys are modelled
        # deliberately.
        {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "required": ["x"],
        },
    ],
)
def test_composition_keywords_suppress_the_check(node):
    assert find_schema_problems(node) == []


def test_closed_object_with_orphan_required_is_still_reported():
    # additionalProperties: false makes the required name outright unsatisfiable.
    problems = find_schema_problems(
        {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["x"],
            "additionalProperties": False,
        }
    )
    assert [p["code"] for p in problems] == ["required_without_property"]


def test_invalid_json_schema_is_reported():
    problems = find_schema_problems({"type": "object", "properties": "not-a-map"})
    assert [p["code"] for p in problems] == ["invalid_json_schema"]


def test_non_dict_definition_is_reported():
    assert find_schema_problems(["nope"])[0]["code"] == "not_an_object"


def test_problem_list_is_capped():
    from backend.src.utils.schema_validation import MAX_PROBLEMS

    schema = {"type": "object", "required": [f"missing_{i}" for i in range(50)]}
    assert len(find_schema_problems(schema)) == MAX_PROBLEMS


# --------------------------------------------------------------------------- #
# API gates
# --------------------------------------------------------------------------- #

_BROKEN = {
    "type": "object",
    "properties": {"Biopsien_mit_IHC_Anzahl": {"type": "integer"}},
    "required": ["Biopsien_mit_IHC"],
}


def test_create_schema_rejects_orphan_required(
    client, api_url, user_headers, make_project
):
    project_id = make_project(user_headers, name=f"sv-{uuid.uuid4().hex[:6]}")["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=user_headers,
        json={"schema_name": "broken", "schema_definition": _BROKEN},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "schemas.required_without_property"
    assert "Biopsien_mit_IHC" in detail["params"]["details"]


def test_create_schema_rejects_invalid_json_schema(
    client, api_url, user_headers, make_project
):
    project_id = make_project(user_headers, name=f"sv-{uuid.uuid4().hex[:6]}")["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=user_headers,
        json={
            "schema_name": "bad",
            "schema_definition": {"type": "object", "required": "not-a-list"},
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "schemas.schema_definition_invalid"


def test_update_schema_rejects_orphan_required(
    client, api_url, user_headers, make_project, make_schema
):
    project_id = make_project(user_headers, name=f"sv-{uuid.uuid4().hex[:6]}")["id"]
    schema_id = make_schema(user_headers, project_id)["id"]
    resp = client.put(
        f"{api_url}/project/{project_id}/schema/{schema_id}",
        headers=user_headers,
        json={"schema_name": "renamed", "schema_definition": _BROKEN},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "schemas.required_without_property"


def test_valid_schema_still_saves(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers, name=f"sv-{uuid.uuid4().hex[:6]}")["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=user_headers,
        json={"schema_name": "good", "schema_definition": _GOOD},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["schema_definition"] == _GOOD


def test_trial_creation_rejects_a_schema_saved_before_the_check(
    client, api_url, admin_headers, make_project, make_schema, make_prompt
):
    """Rows predating the save-time gate must not silently burn a whole trial."""
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import FileCreator, FileStorageType, FileType

    project_id = make_project(admin_headers, name=f"sv-{uuid.uuid4().hex[:6]}")["id"]
    schema_id = make_schema(admin_headers, project_id)["id"]
    prompt_id = make_prompt(admin_headers, project_id)["id"]

    db = SessionLocal()
    try:
        # Bypass the API gate the way a legacy row would have: write it directly.
        db.get(models.Schema, schema_id).schema_definition = _BROKEN

        cfg = models.PreprocessingConfiguration(project_id=project_id, name="cfg")
        file = models.File(
            project_id=project_id,
            file_storage_type=FileStorageType.LOCAL,
            file_uuid=str(uuid.uuid4()),
            file_name="a.txt",
            file_type=FileType.TEXT_PLAIN,
            file_creator=FileCreator.user,
        )
        db.add_all([cfg, file])
        db.commit()
        doc = models.Document(
            project_id=project_id,
            original_file_id=file.id,
            preprocessing_config_id=cfg.id,
            text="hello",
            document_name="d",
        )
        db.add(doc)
        db.commit()
        document_ids = [doc.id]
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=admin_headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": document_ids,
            "llm_model": "mock-model",
            "api_key": "test-key",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "trials.required_without_property"
