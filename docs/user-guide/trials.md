# Trials

A **trial** runs an LLM over a set of documents to extract structured data
matching your schema. Each document produces one result. This page covers
creating, running, and inspecting trials.

!!! info "Prerequisites"
    The **Start New Trial** button is disabled until the project has at least
    one **schema**, one **prompt**, and one **document**. The button's tooltip
    tells you which is missing.

## Creating a trial

**Start New Trial** opens a dialog with a **Simple / Advanced** toggle. Four
inputs are required:

1. **Prompt** — the extraction instructions (preview it inline).
2. **Schema** — the output structure (preview its fields inline).
3. **LLM Model** — chosen from the models your endpoint exposes. Not every model
   supports structured JSON output; see [model compatibility](#model-compatibility).
4. **Documents** — which documents to run over.

An optional **name** and **description** can be added (collapsed under *Add name
/ notes* in Simple mode).

### Selecting documents

The document panel has three tabs:

- **Individual** — search and tick documents; **Select All** picks every
  matching document across pages.
- **Groups** — pick a single [document group](documents.md#document-groups) to
  run against its members.
- **Smart** — **Load from Previous Trial**, or **Filter by Date Range** (with
  *Last 7 days* / *Last 30 days* shortcuts).

### Advanced settings

In Advanced mode you can set (all optional — blank uses model defaults):

- **Max Completion Tokens**
- **Temperature** (0–2)
- **Reasoning Effort** — *Use model default / Low / Medium / High* (only some
  models support this).

### Using a different API

Under **Use Custom API Settings** you can point the trial at any
OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, llama.cpp, …) with its own
**API Key** and **Base URL**. The app tests the connection and reloads the model
list when you change these.

!!! note "Your API key is protected"
    Custom API keys are stored **encrypted**, never returned in API responses,
    and never included in exports.

### Model compatibility

The model list shows the raw model IDs your endpoint reports — appearing in the
list doesn't guarantee structured-output support. When you click **Start Trial**,
the app first runs a quick compatibility check (that the model accepts a JSON
schema request) and stops with an explanation if it fails. In Advanced mode you
can run this check manually from the **Model & Schema Compatibility** card.

## Running, progress, and status

Trials run as background tasks (or, for admins only, synchronously via an
API-level option). The trials table shows live **progress** (`done / total`) and
a status: **Pending → Processing → Ready** (completed), **Failed**, or
**Cancelled**.

!!! tip "Snapshots are frozen"
    A trial stores a **snapshot** of the schema and prompt as they were when it
    ran. Editing or deleting the source schema/prompt afterward does not change
    what the trial displays, exports, or re-runs.

### Cancelling

Active trials can be **Cancelled**. A dialog offers to keep already-processed
results.

!!! warning "Partial results on cancel"
    By default a cancelled trial **discards** its partial results (they are
    rolled back). Treat cancellation as "stop and throw away", not "stop and
    keep", unless you know your deployment changed this default.

### Retrying failures

**Retry** clones the trial into a new one (preserving the custom endpoint, key,
document set, name, and description). If the trial had per-document failures you
can choose **Retry failed documents only** or **Re-run all documents**.

## Viewing results

**Results** opens a slide-over. The header shows the model, prompt, document set,
total **token** usage, and links to the frozen schema/prompt. A **left rail**
lets you search and filter documents by result status:

- **Success**, **Failed**, **Incomplete**, **Invalid JSON**, **Schema invalid**,
  **Refused**, **Provider error**.

Navigate documents with the header arrows or **←/→** keys. For each document you
can open up to three panels side by side:

- **Source Document** — the original file preview or the extracted text.
- **Result** — the extracted JSON (with **Copy JSON**).
- **Reasoning** — the model's reasoning content, when present.
- **Metadata** — token usage, finish reason, and any JSON error.

Failed documents show an error banner with **tuning advice** (suggested prompt
or setting changes). The **"{N} errors"** header link lists all failures; click
one to jump to that document.

## Filtering and managing trials

The filter bar offers search plus **Status**, **Schema**, **Prompt**, **Document
Group**, **LLM Model**, **Errors** (*Has errors / No errors*), and **Date Range**
filters.

- **Rename** — change a trial's name/description.
- **Delete** — removes the trial *and its results and any evaluations based on
  it* (running trials must be cancelled first). Batch-delete via the selection
  bar.

## Downloading results

**Download** exports results as:

- **JSON (per-document, ZIP)** — one JSON file per document plus `metadata.json`.
- **CSV (table)** — optionally bundled with document text and source files in a
  ZIP.

**Include document content** adds the document text and source files. Sensitive
keys (API keys) are always stripped from exports. For an unfinished trial, the
export contains only the successfully extracted documents (labelled a *partial*
download).

## Next step

To measure how good a trial's results are, upload
**[ground truth](ground-truth.md)** and run an **[evaluation](evaluation.md)**.
