# Schemas & prompts

This tab defines **what** to extract (the schema) and **how** to instruct the
LLM (the prompt). It has two sub-tabs: **JSON Schemas** and **Extraction
Prompts**.

!!! tip "The schema is injected automatically"
    You do **not** paste the schema JSON into your prompt. The selected schema is
    automatically included in the LLM call when a trial runs.

## Schemas

A **schema** is a JSON schema describing your desired output structure — nested
objects, arrays, and every JSON type.

### Creating a schema

**Create Schema** opens a full-screen editor with a **Simple / Advanced** toggle.
New schemas are pre-seeded with a few starter medical fields. A validity pill
shows **Valid / Invalid** — a schema needs at least one field to be saveable.

Use **Templates** for common medical structures (Patient Information, Medical
History, Lab Results, Prescription) that demonstrate nested objects, arrays of
objects, enums, and formats.

### Simple editor

A flat, drag-to-reorder list of fields. Each field has:

- **Field name** (e.g. `patient_name`)
- **Type** — Text, Number, Integer, Yes/No, Date, Date & Time, Email
- **Required** — the star toggle (adds it to the schema's required list)
- **Description**
- **Options** (Text fields only) — a list of allowed values (an enum)

!!! note "Advanced fields are read-only here"
    Fields the simple editor can't represent (nested groups, lists, non-text
    enums, constraints) appear as **locked amber rows** and are preserved
    untouched — switch to **Advanced** to edit them. Empty or duplicate field
    names block saving.

### Advanced editor

Advanced mode adds:

- A **Visual Editor** (tree of blocks) and a **Raw JSON** editor (with a
  **Format** button), optionally shown **side by side** (*Split view*).
- **Developer options** — JSON-Schema type names and advanced field settings.

The visual editor supports arbitrarily deep **objects** (groups of fields) and
**arrays** (lists, including lists of objects). The property editor exposes
type-specific settings:

- **Text** — min/max length, **format** (email, URL, date, date-time, time,
  IPv4/IPv6, UUID), regex **pattern**, allowed values (enum).
- **Number** — min/max, *multiple of*, **Integer only**.
- **List (array)** — min/max items, *items must be unique*.
- **Group (object)** — which child fields are **required**, and (developer mode)
  whether to allow additional properties.
- **Additional** — default value, read-only flag, examples.

Property keys must be valid identifiers (letters, numbers, underscores; not
starting with a number).

### Viewing, editing, deleting

**View Schema** shows the fields (with a raw-JSON toggle and **Copy**). There is
no separate file import/export — the **Raw JSON** editor is how you paste a
schema in, and **Copy** is how you take one out.

!!! note
    A schema referenced by a trial cannot be deleted.

## Prompts

A **prompt** tells the LLM how to extract. Prompts pair a **system prompt** (the
model's role and rules, applied to every document) with a **user prompt**
(per-document instructions).

### The document-content placeholder

Where you write `{document_content}`, the document's text is substituted in. If
your prompt doesn't contain the placeholder, the document text is **appended
automatically** at trial time (shown as an *Auto-injected* hint in the list).

### Creating a prompt

**Create Prompt** opens an editor with a **Simple / Advanced** toggle.

- **Simple** — a single **Extraction Instruction** (used as the user prompt); no
  system prompt is sent. **Preview** shows the real message the model receives.
- **Advanced** — separate **System Prompt** and **User Prompt** textareas, an
  **Insert {document_content}** helper, and per-field **Preview**. At least one
  prompt must be present and the placeholder must appear in one of them.

Use **Use Template** to apply the built-in medical extraction prompt (which
switches you to Advanced mode).

!!! warning "Simple mode drops the system prompt"
    Saving in Simple mode sends an empty system prompt. Editing a prompt that has
    a system prompt automatically opens in Advanced mode so you don't wipe it by
    accident.

!!! note
    A prompt referenced by a trial cannot be deleted.

## Next step

With a schema and a prompt ready, run a **[trial](trials.md)**.
