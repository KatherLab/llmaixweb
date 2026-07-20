# Preprocessing

**Preprocessing** turns your uploaded files into plain **text** that an LLM can
read. For PDFs and images this means OCR / text extraction; for spreadsheets it
converts rows or the whole table into text.

!!! note "Not a separate tab"
    Preprocessing is driven from the **Files** tab: select the files you want to
    process, then open the configuration panel from the batch action bar. Each
    file's runs and results are tracked in its **Preprocessing History**.

## Choosing an OCR engine

When your selection contains files that need OCR (PDFs and images), pick one of
the engines your administrator has enabled. For a detailed description of each
engine and when to use it, see **[OCR engines](ocr-engines.md)**.

| Engine | Best for | Notes |
| --- | --- | --- |
| **Quick (Local OCR)** | Everyday scans, no API needed | Docling / Tesseract, runs locally. |
| **Mistral OCR** | Complex layouts | API-based (hosted Mistral or self-hosted DeepSeek-OCR-2). |
| **Vision LLM** | Complex / difficult documents | Any OpenAI-compatible vision model. |

!!! info "Text-only files need no OCR"
    CSV, XLSX, and TXT files are imported as structured text and never touch an
    OCR engine. If your selection is only text/table files, you'll see a
    *"No OCR engine needed"* notice and can start immediately.

If your selection needs OCR but **no engine is enabled**, the panel blocks the
run and tells you to enable one in [system settings](../admin/settings.md).

## Options

- **Force OCR for PDFs** — skip embedded-text extraction and OCR every page.
  Useful when a PDF's embedded text is wrong or missing. Only shown when the
  selection contains PDFs.
- **Advanced options** (per engine):
    - *Local OCR* — **Tesseract Language** (auto-detect by default, or pick a
      specific language).
    - *Mistral OCR* — **API Key** and **Model** overrides (leave empty to use
      the server defaults).
    - *Vision LLM* — **API Key**, **Base URL**, **Model**, a **prompt** for the
      vision model, and a **max image dimension**.

!!! tip "Embedded text is reused"
    For a PDF that already contains selectable text, that text is extracted
    directly and the result is identical regardless of the OCR engine — unless
    you enable **Force OCR**.

## Starting a run

Click **Start Processing**. Before dispatching, the app may show a preview
dialog if it detects:

- **PDFs with embedded text** — informs you the text will be extracted directly.
- **Existing documents with the same configuration** — running again creates new
  **versions** and archives the old ones. You can tick **Only process files
  without existing documents** to skip already-processed files.
- **Existing documents with a different configuration** — both versions are kept
  side by side.

Each run is additive: *"Existing runs and documents are preserved."*

## Progress, cancellation, and completion

- A global banner shows **"Preprocessing — X of Y files · Z failed"** with a
  progress bar and an ETA. Progress updates live.
- **Cancel** stops the run; files still in progress are marked failed. You'll be
  asked to confirm.
- When the last run finishes, a completion callout summarizes
  **"N documents created · M files failed"** with **View errors** and
  **View documents** shortcuts.

## Preprocessing history

Each file's :material-clock: **Preprocessing History** slide-over lists every
run (engine, start time, duration, status) with:

- A live progress bar for active runs.
- A **per-file breakdown** with processing time and, on failure, a **View
  error** expander.
- **Warnings** — e.g. *"N skipped rows"* for row-by-row imports where the
  selected text columns were empty (each skipped row is listed with a reason).
- Links to the resulting **documents** or **group**.
- **Retry failed files**, **Cancel** (active runs), and **Run new
  preprocessing** actions.

## Non-obvious behaviors

- File **status** reflects each file's own subtask — so if one file in a batch
  fails, the others still show their true status.
- Spreadsheets must be [import-configured](files.md#configuring-csv-xlsx-imports)
  before they can be preprocessed; the UI blocks and guides you through it.
- Row-by-row imports skip rows whose selected text columns are all empty, and
  report them as warnings rather than failing the whole file.

## Next step

The text this step produces becomes your **[Documents](documents.md)**.
