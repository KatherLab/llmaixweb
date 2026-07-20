# Documents

**Documents** are the text outputs of [preprocessing](preprocessing.md) — the
content that gets sent to the LLM. This tab is for browsing, organizing, and
reprocessing them; you don't upload here.

The tab has two sub-tabs: **All Documents** and **Document Groups**.

## Finding documents

The filter bar offers:

- **Search** — matches document text, document name, **and** the original
  filename together.
- **OCR Engine** — *Embedded Text (pypdf)*, *Local OCR (Tesseract)*, *Mistral
  OCR*, *Vision LLM*.
- **Date Range** — presets or a custom *From / To* range (click **Apply**).
- **Include archived versions** — also show non-latest document versions (their
  history).

## The documents table

Columns:

- **Document** — name (falls back to the original filename), with the original
  filename or file size as a sub-line.
- **Configuration** — the preprocessing config, with an OCR method sub-line.
- **Model** — the OCR/vision model used, or `—` for local OCR.
- **Created** — the only sortable column.

Each row has **View** and **Download**. Select documents with the checkboxes;
**Select all documents** selects every match across all pages. Default page size
is 50.

## Batch actions

Selecting documents reveals a toolbar:

- **Create Group** — bundle the selection into a [document group](#document-groups).
- **Reprocess** — re-run preprocessing. Optional **Force reprocess (ignore
  existing results)**.
- **Delete** — remove documents (with an optional cascade).
- **Export** — *coming soon* (currently disabled).

!!! warning "Reprocess works on whole files, not rows"
    Reprocessing runs on the **source file**, not individual rows. Selecting a
    few rows from a row-by-row CSV/XLSX reprocesses the **entire file** (all
    rows). Mixed selections are grouped by configuration into separate runs.

!!! danger "Delete cascade"
    Deleting a document that's referenced by a trial, group, or evaluation
    requires confirming a **cascade** that also removes those dependents. The
    dialog shows a usage preview and requires ticking *"I understand that this
    action is permanent."*

## The document viewer

**View** opens a slide-over. Depending on the source, a segmented control lets
you show **Text / File / Both**:

- **Text** — the extracted text, rendered as Markdown, with a **find-in-document**
  bar (Enter = next, Shift+Enter = previous, Esc = clear).
- **File** — the original PDF or image preview.
- **Both** — original and text side by side.

Documents whose text *is* the content (plain-text files, and row-by-row
spreadsheet rows) show **Text Only**.

Navigate the whole corpus with the header arrows or **←/→** keys. An
**extraction-method badge** (Text Extraction, Local OCR, Force OCR, Mistral OCR,
Vision LLM) shows how the text was produced. The info sidebar lists created date,
file size, text length, the preprocessing configuration, and the raw metadata.

### Version history

If a document was reprocessed, the **History** button opens the version
sidebar. Each version is labelled `v1`, `v2`, … and marked **Current** or
**Archived**. Click a version to view its text; **Restore This Version** makes an
archived version current again.

!!! note "Restore never reprocesses"
    Restoring copies the archived version's exact text into a new latest
    version — nothing is re-OCR'd or re-extracted.

## Document groups

A **document group** is a named set of documents you can run a
[trial](trials.md) against. Groups can be:

- **Manual** — created via **Create Group** (from the batch bar or the Groups
  tab).
- **Auto-generated** — created during preprocessing (e.g. one group per
  row-by-row spreadsheet import), marked with an **Auto** badge.

The Groups table shows the name, document count, configuration, tags, type, and
created date. You can **View**, **Edit** (manual groups only), and **Delete**.

!!! note
    A group used by a trial cannot be deleted (the delete action is disabled with
    an explanatory tooltip). Deleting a group can optionally also delete its
    documents where they aren't referenced elsewhere.

## Next step

Define what to extract in **[Schemas & prompts](schemas-and-prompts.md)**.
