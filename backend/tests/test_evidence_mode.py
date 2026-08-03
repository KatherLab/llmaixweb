"""Unit tests for evidence mode (``utils/evidence.py``).

Evidence mode augments the extraction schema with ``<field>__evidence``
companions and splits them back out of the reply. Both halves have to be exact:
a bad augmentation changes what the model is asked for, and a bad split leaks
provenance keys into the stored result, which would break schema validation,
ground-truth mapping and exports downstream.
"""

import pytest

from backend.src.utils.evidence import (
    EVIDENCE_SUFFIX,
    NOTE_MAX_LENGTH,
    NOTE_SUFFIX,
    augment_schema_with_evidence,
    evidence_requested,
    split_evidence,
)

# ---------------------------------------------------------------------------
# evidence_requested
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "options,expected",
    [
        (None, False),
        ({}, False),
        ({"temperature": 0.2}, False),
        ({"evidence_mode": False}, False),
        ({"evidence_mode": True}, True),
    ],
)
def test_evidence_requested(options, expected):
    assert evidence_requested(options) is expected


# ---------------------------------------------------------------------------
# augment_schema_with_evidence
# ---------------------------------------------------------------------------


def test_augment_adds_sibling_for_each_scalar():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "smoker": {"type": "boolean"},
        },
    }
    out = augment_schema_with_evidence(schema)
    props = out["properties"]

    assert set(props) == {
        "name",
        "age",
        "smoker",
        f"name{EVIDENCE_SUFFIX}",
        f"age{EVIDENCE_SUFFIX}",
        f"smoker{EVIDENCE_SUFFIX}",
        f"name{NOTE_SUFFIX}",
        f"age{NOTE_SUFFIX}",
        f"smoker{NOTE_SUFFIX}",
    }
    assert props[f"name{EVIDENCE_SUFFIX}"]["type"] == "string"


def test_augment_does_not_mutate_the_input_schema():
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    augment_schema_with_evidence(schema)
    assert set(schema["properties"]) == {"name"}


def test_augment_recurses_into_nested_objects_and_object_arrays():
    schema = {
        "type": "object",
        "properties": {
            "patient": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
            "medications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"dose": {"type": "string"}},
                },
            },
        },
    }
    out = augment_schema_with_evidence(schema)

    # Containers get no companion of their own — their leaves do.
    assert f"patient{EVIDENCE_SUFFIX}" not in out["properties"]
    assert f"medications{EVIDENCE_SUFFIX}" not in out["properties"]
    assert f"name{EVIDENCE_SUFFIX}" in out["properties"]["patient"]["properties"]
    assert (
        f"dose{EVIDENCE_SUFFIX}"
        in out["properties"]["medications"]["items"]["properties"]
    )


def test_augment_gives_primitive_arrays_a_parallel_quote_array():
    schema = {
        "type": "object",
        "properties": {"symptoms": {"type": "array", "items": {"type": "string"}}},
    }
    companion = augment_schema_with_evidence(schema)["properties"][
        f"symptoms{EVIDENCE_SUFFIX}"
    ]
    assert companion["type"] == "array"
    assert companion["items"] == {"type": "string"}


def test_augment_handles_nullable_unions_and_untyped_enums():
    schema = {
        "type": "object",
        "properties": {
            "mrn": {"type": ["string", "null"]},
            "stage": {"enum": ["I", "II"]},
        },
    }
    props = augment_schema_with_evidence(schema)["properties"]
    assert f"mrn{EVIDENCE_SUFFIX}" in props
    assert f"stage{EVIDENCE_SUFFIX}" in props


def test_augment_extends_required_only_when_it_is_already_exhaustive():
    strict = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
        "required": ["a", "b"],
    }
    assert augment_schema_with_evidence(strict)["required"] == [
        "a",
        "b",
        f"a{EVIDENCE_SUFFIX}",
        f"a{NOTE_SUFFIX}",
        f"b{EVIDENCE_SUFFIX}",
        f"b{NOTE_SUFFIX}",
    ]

    partial = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
        "required": ["a"],
    }
    # `b` is deliberately optional — don't make its quote mandatory either.
    assert augment_schema_with_evidence(partial)["required"] == ["a"]


def test_augment_leaves_a_user_field_that_already_owns_the_companion_name():
    schema = {
        "type": "object",
        "properties": {
            "note": {"type": "string"},
            f"note{EVIDENCE_SUFFIX}": {"type": "number"},
        },
    }
    props = augment_schema_with_evidence(schema)["properties"]
    assert props[f"note{EVIDENCE_SUFFIX}"] == {"type": "number"}


def test_augment_passes_through_non_dict_schemas():
    assert augment_schema_with_evidence(None) is None


# ---------------------------------------------------------------------------
# split_evidence
# ---------------------------------------------------------------------------


def test_split_returns_clean_result_and_path_keyed_quotes():
    raw = {
        "name": "Sarah Lee",
        f"name{EVIDENCE_SUFFIX}": "Patient: Sarah Lee, DOB",
        "age": 64,
        f"age{EVIDENCE_SUFFIX}": "64-year-old woman",
    }
    clean, quotes, _notes = split_evidence(raw)

    assert clean == {"name": "Sarah Lee", "age": 64}
    assert quotes == {
        "name": "Patient: Sarah Lee, DOB",
        "age": "64-year-old woman",
    }


def test_split_uses_frontend_path_syntax_for_nested_values():
    raw = {
        "patient": {
            "name": "Sarah Lee",
            f"name{EVIDENCE_SUFFIX}": "Patient: Sarah Lee",
        },
        "medications": [
            {"dose": "5 mg", f"dose{EVIDENCE_SUFFIX}": "5 mg once daily"},
            {"dose": "10 mg", f"dose{EVIDENCE_SUFFIX}": "10 mg at night"},
        ],
    }
    clean, quotes, _notes = split_evidence(raw)

    assert clean == {
        "patient": {"name": "Sarah Lee"},
        "medications": [{"dose": "5 mg"}, {"dose": "10 mg"}],
    }
    assert quotes == {
        "patient.name": "Patient: Sarah Lee",
        "medications[0].dose": "5 mg once daily",
        "medications[1].dose": "10 mg at night",
    }


def test_split_indexes_parallel_quote_arrays_per_item():
    raw = {
        "symptoms": ["dyspnea", "chest pain"],
        f"symptoms{EVIDENCE_SUFFIX}": ["Shortness of breath", "Chest pain"],
    }
    clean, quotes, _notes = split_evidence(raw)

    assert clean == {"symptoms": ["dyspnea", "chest pain"]}
    assert quotes == {
        "symptoms[0]": "Shortness of breath",
        "symptoms[1]": "Chest pain",
    }


def test_split_drops_blank_quotes():
    # An empty quote is the model saying "inferred / not stated" — that is an
    # absence of provenance, not a provenance of "".
    raw = {"stage": "II", f"stage{EVIDENCE_SUFFIX}": "   "}
    clean, quotes, _notes = split_evidence(raw)
    assert clean == {"stage": "II"}
    assert quotes == {}


def test_split_keeps_an_orphan_evidence_named_field_as_real_data():
    raw = {"note__evidence": "this is a real user field"}
    clean, quotes, _notes = split_evidence(raw)
    assert clean == raw
    assert quotes == {}


def test_split_is_a_no_op_on_a_result_without_companions():
    raw = {"a": 1, "b": {"c": [1, 2, 3]}}
    clean, quotes, _notes = split_evidence(raw)
    assert clean == raw
    assert quotes == {}


# ---------------------------------------------------------------------------
# Notes — the short "why is there nothing to quote" companion
# ---------------------------------------------------------------------------


def test_note_companion_is_length_capped_in_the_schema():
    """The cap is the safeguard: a note has room to label, not to argue."""
    schema = {"type": "object", "properties": {"chest_pain": {"type": "boolean"}}}
    note = augment_schema_with_evidence(schema)["properties"][
        f"chest_pain{NOTE_SUFFIX}"
    ]
    assert note["type"] == "string"
    assert note["maxLength"] == NOTE_MAX_LENGTH


def test_primitive_arrays_get_a_parallel_note_array():
    schema = {
        "type": "object",
        "properties": {"symptoms": {"type": "array", "items": {"type": "string"}}},
    }
    note = augment_schema_with_evidence(schema)["properties"][f"symptoms{NOTE_SUFFIX}"]
    assert note["type"] == "array"
    assert note["items"]["maxLength"] == NOTE_MAX_LENGTH


def test_containers_get_no_note_of_their_own():
    schema = {
        "type": "object",
        "properties": {
            "patient": {"type": "object", "properties": {"name": {"type": "string"}}}
        },
    }
    props = augment_schema_with_evidence(schema)["properties"]
    assert f"patient{NOTE_SUFFIX}" not in props
    assert f"name{NOTE_SUFFIX}" in props["patient"]["properties"]


def test_split_separates_notes_from_quotes():
    raw = {
        "chest_pain": False,
        f"chest_pain{EVIDENCE_SUFFIX}": "",
        f"chest_pain{NOTE_SUFFIX}": "explicitly denied",
        "name": "Sarah Lee",
        f"name{EVIDENCE_SUFFIX}": "Patient: Sarah Lee",
        f"name{NOTE_SUFFIX}": "",
    }
    clean, quotes, notes = split_evidence(raw)

    assert clean == {"chest_pain": False, "name": "Sarah Lee"}
    assert quotes == {"name": "Patient: Sarah Lee"}
    assert notes == {"chest_pain": "explicitly denied"}


def test_split_truncates_an_overlong_note():
    # `maxLength` lives in the schema, but a provider without strict structured
    # output can ignore it — the display must not depend on the model obeying.
    raw = {"x": None, f"x{EVIDENCE_SUFFIX}": "", f"x{NOTE_SUFFIX}": "y" * 500}
    _clean, _quotes, notes = split_evidence(raw)
    assert len(notes["x"]) == NOTE_MAX_LENGTH


def test_split_indexes_notes_per_array_item():
    raw = {
        "symptoms": ["dyspnea", "chest pain"],
        f"symptoms{NOTE_SUFFIX}": ["", "not mentioned"],
    }
    clean, _quotes, notes = split_evidence(raw)
    assert clean == {"symptoms": ["dyspnea", "chest pain"]}
    assert notes == {"symptoms[1]": "not mentioned"}


def test_split_keeps_an_orphan_note_named_field_as_real_data():
    raw = {"clinical__note": "this is a real user field"}
    clean, _quotes, notes = split_evidence(raw)
    assert clean == raw
    assert notes == {}


def test_note_instruction_tells_the_model_when_to_use_it():
    from backend.src.utils.evidence import EVIDENCE_INSTRUCTION

    assert NOTE_SUFFIX in EVIDENCE_INSTRUCTION
    assert str(NOTE_MAX_LENGTH) in EVIDENCE_INSTRUCTION


def test_instruction_does_not_offer_a_denial_phrase_as_a_note():
    """Models copy example strings verbatim.

    Offering "explicitly denied" as a sample note got it applied to values the
    document was merely silent about — a claim about the text with nothing
    backing it. A stated negative belongs in the quote, where it is checkable.
    """
    from backend.src.utils.evidence import EVIDENCE_INSTRUCTION

    assert "explicitly denied" not in EVIDENCE_INSTRUCTION
    assert "not mentioned" in EVIDENCE_INSTRUCTION


def test_schema_descriptions_do_not_offer_a_denial_phrase_either():
    """The field descriptions are the model's other channel for example text."""
    import json

    schema = {
        "type": "object",
        "properties": {"chest_pain": {"type": "boolean"}},
    }
    rendered = json.dumps(augment_schema_with_evidence(schema))
    assert "explicitly denied" not in rendered


def test_instruction_asks_for_stated_negatives_to_be_quoted():
    from backend.src.utils.evidence import EVIDENCE_INSTRUCTION

    lowered = EVIDENCE_INSTRUCTION.lower()
    assert "negative finding" in lowered
    assert "quote that sentence" in lowered
