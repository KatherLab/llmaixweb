# Ground truth

**Ground truth** is a file of known-correct values used to measure a trial's
accuracy. You upload it, tell the app how documents are identified, and map each
ground-truth column to a schema field. Ground truth is managed inside the
**Evaluation** tab.

## Uploading

**Upload Ground Truth** accepts four formats:

- **CSV** — flattened fields; dot notation (`contact.email`) builds nesting.
- **JSON** — a single file with a document map, or multiple files (each document
  needs an `id` matching your document identifiers).
- **ZIP** — multiple JSON files.
- **Excel (.xlsx)** — dot-paths build nesting; multiple sheets are merged by ID.

Give it an optional **name**. Dropping a file auto-selects the matching format;
dropping several JSON files zips them together automatically. After upload, the
app opens the mapping configurator right away.

!!! info "How documents are matched"
    Ground-truth entries are matched to trial results by identifier. For
    JSON/ZIP each entry needs an `id`; for CSV/XLSX you choose the **ID column**
    in the next step.

## Selecting the ID field

In the mapping dialog:

- **CSV/XLSX** — pick the **Document ID** column (required; matches your document
  identifiers).
- **JSON/ZIP** — use the document **filename**, or a **field** from the data.

!!! warning "Changing the ID field invalidates evaluations"
    Changing the ID column clears cached data and **invalidates existing
    evaluations** that used this ground truth.

## Mapping fields

The full-screen **Configure Ground Truth Mapping** dialog has three columns:

- **Left — Schema fields** — pick the schema; its fields show as a tree with type
  badges. Required, unmapped leaves are flagged; mapped leaves get a check.
- **Center — Mappings** — create each mapping (schema field → ground-truth
  field). **Auto-map matching names** maps fields whose normalized names match.
  **Clear all mappings** resets them.
- **Right — Ground-truth fields** — the parsed columns/fields plus a live data
  sample.

Saving persists the ID column (if changed) and the mappings. You can't save until
a schema is chosen, at least one mapping exists, and the ID field is set.

!!! warning "Editing mappings invalidates evaluations"
    Saving new mappings deletes evaluations for trials using that schema, so they
    can be recomputed against the new mapping.

## Comparison methods

Each mapping has a **comparison method**, defaulted from the field type. Pick the
one that fits the field:

| Method | Correct when… | Options |
| --- | --- | --- |
| **exact** | strings are equal (case-insensitive) | case-sensitive toggle |
| **fuzzy** | similarity ≥ a threshold | **threshold** (default 85), optional partial/substring match |
| **numeric** | values within a tolerance | **tolerance** (default 0.001), absolute or relative (±%) |
| **boolean** | both parse to the same true/false | recognizes yes/no, 1/0, y/n, etc. |
| **category** | category labels match | optional synonyms; builds a confusion matrix |
| **date** | dates are equal | parses common date formats |

Arrays are compared order-independently (every expected element must match a
distinct predicted one, with no extras).

!!! warning "Fuzzy substring matching is off by default"
    Substring matching is opt-in because it can invert meaning in medical text
    (e.g. *"cancer"* matching *"non-cancer"*). Enable it only when you're sure.

The dialog also shows amber **hints** when a comparison method is unusual for a
field's type, or when the schema and ground-truth types don't line up.

## Managing ground-truth files

The **Manage** view lists each file with its format, mapping count, and a preview
of its mappings. You can **Configure mappings**, **Rename**, or **Delete**.

!!! danger
    Deleting a ground-truth file also deletes all **evaluations** that used it.

## Next step

With mappings configured, create an **[evaluation](evaluation.md)**.
