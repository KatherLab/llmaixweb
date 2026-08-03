"""Evidence mode — have the model cite the text each value came from.

Provenance highlighting in the results viewer works by string-matching an
extracted value against the document text. That is best-effort: normalized
dates, reworded values and inferred booleans have no literal counterpart in
the source. Evidence mode removes the guesswork for the cases that matter by
asking the model itself where it read each value.

Mechanics: the user's schema is sent to the model in an *augmented* copy where
every leaf field gains a sibling ``<field>__evidence`` string. The model fills
it with the verbatim document span supporting that value. On the way back the
evidence keys are split out again, so the stored ``TrialResult.result`` keeps
exactly the shape the user's schema describes — evaluation, ground-truth
mapping and exports never see the extra keys — and the quotes land in
``additional_content["evidence"]`` as a ``{json path: quote}`` map.

Values with no quote get a second companion, ``<field>__note``: a few words on
why there is nothing to cite, so that "the document is silent on this" is
distinguishable from "the model had a source". The note is deliberately capped
at a handful of words, and the prompt refuses it any claim *about* the document:
a model asked to justify itself will produce something fluent even when it
guessed, and a persuasive rationale attached to a wrong value is worse than none
at all. A stated negative ("denies chest pain") is therefore quoted like any
other value rather than described in a note — a claim in a quote is checkable,
the same claim in a note is not.

The path syntax matches the frontend's (``patient.name``,
``medications[0].dose``), so the viewer can look up a leaf's quote directly.
"""

from __future__ import annotations

import copy
from typing import Any

EVIDENCE_SUFFIX = "__evidence"
NOTE_SUFFIX = "__note"

#: Hard ceiling on a note, enforced in the schema. Room for "not mentioned",
#: not for an argument.
NOTE_MAX_LENGTH = 80

#: Appended to the user message when evidence mode is on. Kept explicit about
#: the "quote, don't paraphrase" requirement — a paraphrased span cannot be
#: located in the document and degrades to ordinary fuzzy matching.
EVIDENCE_INSTRUCTION = (
    "\n\nFor every extracted field there is a companion field with the same name "
    f"plus the suffix `{EVIDENCE_SUFFIX}`. Fill each companion field with the exact "
    "verbatim text from the document that the value was read from — copy the "
    "characters as they appear, do not paraphrase, translate, reformat or "
    "summarize them. Keep the quote short (the sentence or phrase carrying the "
    "value). A negative finding is still read from the document: when the text "
    'states the negative ("no chest pain", "denies fever", "no evidence of '
    'embolism"), quote that sentence like any other — a value of false is not '
    "the same thing as an absent value. Only when the document says nothing at "
    "all about a field, or the value was inferred or calculated rather than "
    f"read, leave the quote empty and instead put at most {NOTE_MAX_LENGTH} characters "
    f'in the `{NOTE_SUFFIX}` companion saying so — for example "not mentioned" or '
    '"inferred from admission date". Never claim in a note that the document '
    "states something; if it states it, quote it. When you did quote the "
    f"document, leave `{NOTE_SUFFIX}` empty. Both companion fields are provenance "
    "metadata only; they must not change the extracted values themselves."
)

#: Translations of the above. Same three rules in each: quote verbatim, quote a
#: stated negative like any other value, and never assert in a note something
#: that could have been quoted.
_EVIDENCE_INSTRUCTIONS = {
    "en": EVIDENCE_INSTRUCTION,
    "de": (
        "\n\nZu jedem extrahierten Feld gibt es ein Begleitfeld mit demselben Namen "
        f"und dem Suffix `{EVIDENCE_SUFFIX}`. Trage dort den exakten wörtlichen Text "
        "aus dem Dokument ein, aus dem der Wert stammt — übernimm die Zeichen "
        "unverändert, paraphrasiere, übersetze, formatiere und kürze sie nicht. "
        "Halte das Zitat kurz (der Satz oder Ausdruck, der den Wert enthält). Auch "
        "ein negativer Befund stammt aus dem Dokument: Wenn der Text die Verneinung "
        'ausspricht („keine Brustschmerzen", „verneint Fieber", „kein Hinweis auf '
        'eine Embolie"), zitiere diesen Satz wie jeden anderen — der Wert false ist '
        "nicht dasselbe wie ein fehlender Wert. Nur wenn das Dokument zu einem Feld "
        "gar nichts sagt oder der Wert abgeleitet bzw. berechnet statt gelesen wurde, "
        f"lass das Zitat leer und schreibe stattdessen höchstens {NOTE_MAX_LENGTH} Zeichen "
        f'in das Begleitfeld `{NOTE_SUFFIX}` — zum Beispiel „nicht erwähnt" oder '
        '„aus dem Aufnahmedatum abgeleitet". Behaupte in einer Notiz niemals, das '
        "Dokument sage etwas; wenn es das sagt, zitiere es. Wenn du zitiert hast, "
        f"lass `{NOTE_SUFFIX}` leer. Beide Begleitfelder sind nur Herkunftsangaben; "
        "sie dürfen die extrahierten Werte selbst nicht verändern."
    ),
    "fr": (
        "\n\nChaque champ extrait possède un champ compagnon portant le même nom "
        f"suivi du suffixe `{EVIDENCE_SUFFIX}`. Renseignez-y le texte exact, mot pour "
        "mot, du document d'où provient la valeur — recopiez les caractères tels "
        "quels, sans paraphraser, traduire, reformater ni résumer. Gardez la "
        "citation courte (la phrase ou l'expression qui porte la valeur). Un "
        "constat négatif provient lui aussi du document : lorsque le texte énonce "
        "la négation (« pas de douleur thoracique », « nie toute fièvre », « aucun "
        "signe d'embolie »), citez cette phrase comme n'importe quelle autre — la "
        "valeur false n'est pas la même chose qu'une valeur absente. Uniquement "
        "lorsque le document ne dit rien du tout sur un champ, ou que la valeur a "
        "été déduite ou calculée plutôt que lue, laissez la citation vide et "
        f"écrivez au plus {NOTE_MAX_LENGTH} caractères dans le compagnon `{NOTE_SUFFIX}` — "
        "par exemple « non mentionné » ou « déduit de la date d'admission ». "
        "N'affirmez jamais dans une note que le document énonce quelque chose ; "
        "s'il l'énonce, citez-le. Lorsque vous avez cité le document, laissez "
        f"`{NOTE_SUFFIX}` vide. Les deux champs compagnons sont des métadonnées de "
        "provenance uniquement ; ils ne doivent pas modifier les valeurs extraites."
    ),
    "es": (
        "\n\nCada campo extraído tiene un campo acompañante con el mismo nombre más "
        f"el sufijo `{EVIDENCE_SUFFIX}`. Complételo con el texto exacto y literal del "
        "documento del que se leyó el valor: copie los caracteres tal como aparecen, "
        "sin parafrasear, traducir, reformatear ni resumir. Mantenga la cita breve "
        "(la frase o expresión que contiene el valor). Un hallazgo negativo también "
        "se lee del documento: cuando el texto expresa la negación («sin dolor "
        "torácico», «niega fiebre», «sin evidencia de embolia»), cite esa frase como "
        "cualquier otra; el valor false no es lo mismo que un valor ausente. Solo "
        "cuando el documento no dice nada sobre un campo, o el valor se dedujo o "
        "calculó en lugar de leerse, deje la cita vacía y escriba como máximo "
        f"{NOTE_MAX_LENGTH} caracteres en el acompañante `{NOTE_SUFFIX}`: por ejemplo «no "
        "mencionado» o «deducido de la fecha de ingreso». Nunca afirme en una nota "
        "que el documento dice algo; si lo dice, cítelo. Cuando haya citado el "
        f"documento, deje `{NOTE_SUFFIX}` vacío. Ambos campos acompañantes son solo "
        "metadatos de procedencia; no deben alterar los valores extraídos."
    ),
}


def evidence_instruction(language: str = "en") -> str:
    """The evidence instructions, in the trial's prompt language."""
    return _EVIDENCE_INSTRUCTIONS.get(language, EVIDENCE_INSTRUCTION)


#: JSON-schema types that carry a value a human could point at in the document.
_LEAF_TYPES = {"string", "number", "integer", "boolean"}


def evidence_requested(advanced_options: dict | None) -> bool:
    """Whether the trial's advanced options asked for evidence quotes."""
    if not advanced_options:
        return False
    return bool(advanced_options.get("evidence_mode"))


def _types_of(node: dict) -> set[str]:
    """The declared type(s) of a schema node, tolerating unions and omissions."""
    raw = node.get("type")
    if isinstance(raw, list):
        return {str(t) for t in raw if t != "null"}
    if isinstance(raw, str):
        return {raw}
    # Untyped nodes are common in hand-written schemas — infer from shape.
    if "properties" in node:
        return {"object"}
    if "items" in node:
        return {"array"}
    if "enum" in node:
        return {"string"}
    return set()


def _is_leaf(node: Any) -> bool:
    """True for a scalar field (the kind that gets its own evidence sibling)."""
    if not isinstance(node, dict):
        return False
    types = _types_of(node)
    return bool(types) and types <= _LEAF_TYPES


def _is_primitive_array(node: Any) -> bool:
    """True for an array of scalars — evidence is a parallel array of quotes."""
    if not isinstance(node, dict) or "array" not in _types_of(node):
        return False
    items = node.get("items")
    return _is_leaf(items)


def _evidence_property(field_name: str, for_array: bool) -> dict:
    """The schema for one ``<field>__evidence`` companion property."""
    description = (
        f"Verbatim quote from the document supporting each item of '{field_name}', "
        "in the same order. Empty string where a value is not stated."
        if for_array
        else f"Verbatim quote from the document supporting '{field_name}'. "
        "Empty string if the value is not stated in the document."
    )
    if for_array:
        return {
            "type": "array",
            "items": {"type": "string"},
            "description": description,
        }
    return {"type": "string", "description": description}


def _note_property(field_name: str, for_array: bool) -> dict:
    """The schema for one ``<field>__note`` companion property.

    ``maxLength`` is the point, not a detail: it is what stops a note from
    becoming an argument for a value the model actually guessed.
    """
    description = (
        f"At most a few words on why '{field_name}' has no quote — e.g. "
        '"not mentioned" or "inferred". A negative the document states must be '
        "quoted, not described here. Empty when a quote is given."
    )
    if for_array:
        return {
            "type": "array",
            "items": {"type": "string", "maxLength": NOTE_MAX_LENGTH},
            "description": description,
        }
    return {
        "type": "string",
        "maxLength": NOTE_MAX_LENGTH,
        "description": description,
    }


def _augment_node(node: Any) -> Any:
    """Recursively add evidence siblings to every object node under ``node``."""
    if not isinstance(node, dict):
        return node

    out = dict(node)

    items = out.get("items")
    if isinstance(items, dict):
        out["items"] = _augment_node(items)

    props = out.get("properties")
    if not isinstance(props, dict):
        return out

    new_props: dict[str, Any] = {}
    added: list[str] = []
    for key, sub in props.items():
        new_props[key] = _augment_node(sub)
        evidence_key = f"{key}{EVIDENCE_SUFFIX}"
        note_key = f"{key}{NOTE_SUFFIX}"
        # A schema that already defines a companion name keeps its own field;
        # silently overwriting a user's property would corrupt their output.
        if evidence_key in props:
            continue
        is_leaf = _is_leaf(sub)
        if not (is_leaf or _is_primitive_array(sub)):
            continue
        new_props[evidence_key] = _evidence_property(key, for_array=not is_leaf)
        added.append(evidence_key)
        if note_key not in props:
            new_props[note_key] = _note_property(key, for_array=not is_leaf)
            added.append(note_key)

    out["properties"] = new_props

    # Strict structured-output modes require every property to be listed in
    # `required`. Only extend a `required` list that is already exhaustive —
    # otherwise the schema's own optionality is the user's deliberate choice and
    # forcing quotes to be mandatory would change extraction behaviour.
    required = out.get("required")
    if added and isinstance(required, list) and set(props) <= set(required):
        out["required"] = list(required) + added

    return out


def augment_schema_with_evidence(schema: dict | None) -> dict | None:
    """Return a copy of ``schema`` with ``<field>__evidence`` siblings added."""
    if not isinstance(schema, dict):
        return schema
    return _augment_node(copy.deepcopy(schema))


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _collect(
    value: Any, base_path: str, out: dict[str, str], limit: int | None
) -> None:
    """Record a companion value (string, or one entry per array item) into ``out``."""

    def store(path: str, text: Any) -> None:
        if not isinstance(text, str) or not text.strip():
            return
        cleaned = text.strip()
        # Belt and braces: `maxLength` is in the schema, but a provider without
        # strict structured output can ignore it, and an unbounded "note" is
        # exactly what this feature is designed not to display.
        out[path] = cleaned[:limit] if limit else cleaned

    if isinstance(value, list):
        for i, item in enumerate(value):
            store(f"{base_path}[{i}]", item)
    else:
        store(base_path, value)


def _split_node(
    node: Any,
    prefix: str,
    quotes: dict[str, str],
    notes: dict[str, str],
) -> Any:
    """Strip evidence/note keys out of ``node``, collecting them as we go."""
    if isinstance(node, list):
        return [
            _split_node(item, f"{prefix}[{i}]", quotes, notes)
            for i, item in enumerate(node)
        ]

    if not isinstance(node, dict):
        return node

    clean: dict[str, Any] = {}
    for key, value in node.items():
        companion: tuple[str, dict[str, str], int | None] | None = None
        if key.endswith(EVIDENCE_SUFFIX):
            companion = (key[: -len(EVIDENCE_SUFFIX)], quotes, None)
        elif key.endswith(NOTE_SUFFIX):
            companion = (key[: -len(NOTE_SUFFIX)], notes, NOTE_MAX_LENGTH)

        # Only treat it as provenance when it actually accompanies a field. A
        # user schema may legitimately contain a field literally named
        # `foo__evidence` with no `foo` beside it; that one is real data.
        if companion is None or companion[0] not in node:
            clean[key] = _split_node(value, _join(prefix, key), quotes, notes)
            continue

        base, target, limit = companion
        _collect(value, _join(prefix, base), target, limit)

    return clean


def split_evidence(data: Any) -> tuple[Any, dict[str, str], dict[str, str]]:
    """Separate an augmented result into ``(clean_result, quotes, notes)``.

    Both maps are keyed by JSON path (``patient.name``, ``medications[0].dose``).
    ``quotes`` holds the verbatim spans the model cited; ``notes`` holds its
    short reason where there was nothing to quote. Blank entries are dropped
    rather than stored as empty strings.
    """
    quotes: dict[str, str] = {}
    notes: dict[str, str] = {}
    return _split_node(data, "", quotes, notes), quotes, notes
