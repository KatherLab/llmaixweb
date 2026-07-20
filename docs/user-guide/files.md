# Files

The **Files** tab is where you upload and organize the source documents for a
project. It is the entry point of the workflow — everything downstream operates
on what you upload here.

Supported types: **PDF, PNG, JPG/JPEG, DOC, DOCX, CSV, XLSX, TXT**.

## Uploading files

- Click **Upload Files** (top-right), or on an empty project **drag files onto
  the dropzone** or use **Browse Files**.
- You can select multiple files at once. Uploads run **one file at a time**;
  a progress panel shows *"Uploading file X of Y"*, an overall bar, and a live
  *"N succeeded · M failed"* count.
- **Cancelling** mid-batch keeps files already uploaded and skips the rest —
  you'll be asked to confirm (**Cancel uploads** / **Keep uploading**).
- If some files fail, the modal stays open with a **Failed uploads** list
  (each showing the filename and reason) so you can retry them.

!!! info "Duplicate detection"
    Files are hashed (SHA-256) on upload. Uploading a file that already exists in
    the project is rejected as a duplicate — the app tells you which existing
    file it matched, rather than creating a copy.

There is a maximum file size (enforced during upload); oversized files are
rejected.

## Finding files

When a project has files, a filter bar appears above the table:

- **Search** — matches filenames (debounced as you type).
- **Status** — `All`, **Not Processed**, **Processing**, **Completed**,
  **Failed** (derived from each file's latest preprocessing run).
- **File Type** — PDF, PNG, JPEG, CSV, XLSX, XLS, TXT, DOC, DOCX.
- **Date Range** — Today, Yesterday, Last 7 Days, Last 30 Days, or a
  **Custom Range** (pick *From* / *To* and click **Apply**).

Active filters show as removable chips; **Clear All Filters** resets everything.

## The files table

Columns — **File**, **Type**, **Size**, **Uploaded**, **Status** — are all
sortable (default: newest first). Each row has actions:

- :material-clock: **Preprocessing History** — see every run for this file.
- :material-eye: **Preview** — open the file preview.
- :material-download: **Download** — download the original file.
- :material-delete: **Delete** — remove the file (see [Deleting](#deleting-files)).

Select rows with the checkboxes (or the header **select-all**). Page sizes are
**25 / 50 / 100 / 250**.

!!! tip "Select all across pages"
    With a large project, the **Select all {total}** button in the info callout
    selects every file matching the current filters — across all pages — so you
    can preprocess a whole project in one go.

## Previewing files

The preview opens as a slide-over with prev/next navigation (**←/→**) and a
Download button. Rendering depends on the type:

- **PDF** — inline viewer.
- **Images** — shown directly.
- **CSV/XLSX** — a table of the first 50 rows, using your saved parse settings;
  the **ID column** and **Text columns** are highlighted, and long text cells
  expand on click (with a **Copy** button).
- **TXT** — plain-text view.
- Other types fall back to a **Download File** button.

## Configuring CSV / XLSX imports

Spreadsheets need an **import configuration** before they can be preprocessed.
Until configured, the file shows a yellow **Needs Import Config** badge; click
**Configure** to open the import dialog.

The dialog previews the first 25 rows and offers:

**Parse options**

- **Encoding** (e.g. `utf-8`, `latin1`).
- **Delimiter** (CSV only) — Comma, Semicolon, or Tab.
- **File contains header row** toggle.
- **Sheet** selector (XLSX with multiple sheets).

**Import strategy**

- **One document per row** (`row_by_row`) — each row becomes its own document.
- **Treat whole file as one document** (`full_document`) — the entire table
  becomes a single document.

**Row-by-row options** (when *One document per row* is selected)

- **Text Columns** *(required)* — tick the column(s) whose text the LLM should
  extract. Their contents are concatenated into each document (typically the
  report / notes / findings column). At least one is required.
- **Case / Document ID Column** — names each document (e.g. `CASE-001`).
  Defaults to **(Row number)**. Likely ID columns are marked *(Recommended)*.

!!! warning "IDs must be unique"
    If you choose an ID column, the app checks that its values are **unique
    across the whole file**. Duplicate or empty IDs block saving — either fix the
    data or fall back to **(Row number)**. This prevents documents from
    colliding or being named `nan`.

Saving stores the configuration on the file. Closing with unsaved edits prompts
you to **Discard** or **Keep editing**. When configuring several files in a
batch, the dialog advances to the next unconfigured file automatically.

## Deleting files

Delete a single file with its trash action, or several at once via the
**Delete** button in the batch bar (up to 200 at a time).

Before deleting, the dialog shows an **impact preview** — how many documents,
trials, groups, extraction results, and evaluation metrics depend on the file —
and a cascade checkbox.

!!! danger "Cascading deletes"
    - A file that is **currently being preprocessed** cannot be deleted; cancel
      the preprocessing run first.
    - A file **linked to documents** requires confirming the cascade, which also
      removes dependent trials, groups, and evaluation data. This is
      irreversible — take a [backup](../operations/backup-restore.md) if unsure.

## Batch actions

Selecting one or more files reveals a floating action bar:

- A **"N needs config"** warning if any selected spreadsheet lacks import config.
- **Configure Preprocessing** (or **Configure Files First** if configuration is
  still needed) — see [Preprocessing](preprocessing.md).
- **Delete** and **Clear** selection.

## Next step

Once your files are uploaded (and any spreadsheets configured), select them and
move on to **[Preprocessing](preprocessing.md)** to extract their text.
