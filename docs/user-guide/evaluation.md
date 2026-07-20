# Evaluation

An **evaluation** compares a completed trial's results against
[ground truth](ground-truth.md) and computes accuracy metrics. This is how you
measure and debug extraction quality.

## Creating an evaluation

An evaluation is the combination of **a trial + a ground-truth file + field
mappings**. From the Evaluation dashboard:

1. Select a ground-truth file that has **field mappings** configured.
2. Click **Evaluate Trial** and pick a **completed** trial from the list.

Trials without mappings for their schema (or with no results) are greyed out.
Already-evaluated trials are marked, and re-evaluating asks for confirmation.

!!! note "Only matched documents are scored"
    Documents whose identifier can't be matched to a ground-truth entry are
    reported separately and **excluded** from the accuracy figure. If a trial has
    a low match rate you'll get a warning listing the unmatched documents.

Evaluations are **auto-invalidated** and recomputed when their inputs change —
editing the ground-truth file, its ID column, or the field mappings, or re-running
the trial.

## The evaluations table

Each row shows the trial, model, **overall accuracy** (with a colored bar: green
≥90%, red <50%), the document count (and how many matched), and a status
(**Scored** or **Has Errors**). Rows have **Analysis** and **Delete**.

!!! note
    Deleting an evaluation keeps the trial and ground truth — you can re-evaluate
    anytime.

## Metrics explained

- **Accuracy** = correct fields ÷ total fields, over matched documents only.
- **Precision / Recall / F1** are computed from per-field outcomes:
    - A correct field is a true positive.
    - A **missing** field counts as a false negative.
    - An **extra** field counts as a false positive.
    - A **wrong value** (a substitution) counts as **both** a false positive and
      a false negative.

!!! info "Why a wrong value hurts twice"
    Counting a substitution as both FP and FN is the standard information-
    extraction convention. It means a set of fully-wrong-but-present values does
    **not** score 100% recall.

## Analysis page

**Analysis** opens a detailed view:

- **Overall metrics** cards (accuracy, precision, recall, F1), with a note on how
  many documents were matched vs. excluded.
- **Fields** list — sortable **Worst first** or A→Z, each with its accuracy and
  error count. Click a field to filter the document table to it and (for
  categorical fields) show its **confusion matrix**.
- **Filter bar** — search documents and filter by status (*Failed*, *Has wrong
  values*, *Has missing fields*, *High ≥90%*, *Low <50%*).
- **Confusion matrix** (categorical/boolean fields) — expected rows × predicted
  columns; click a cell to filter documents to that expected→predicted case.
- **Document table** — per-document accuracy, wrong/total counts, and status;
  click a row for the failure detail.

### Per-document failure detail

The failure drawer shows, for one document, up to three panels (navigate with
**←/→** or **J/K**, close with **Esc**):

- **Source** — the original file or extracted text.
- **Comparison** — a field-by-field *Expected vs. Predicted* table with the error
  type, a suggestion, and the comparison-method chip used.
- **Output** — the raw structured result.
- **Reasoning** — the model's reasoning, when present.

## Exporting

**Export Results** (or **Export** from the analysis page) opens the export
dialog:

- **Format** — CSV, Excel (xlsx), or ZIP (advanced).
- **Select Evaluations** — one or more (the current one is pre-selected).
- **Options** — include document-level metrics, field-by-field data, and error
  analysis; for ZIP, optionally include document and ground-truth content.

Exports of clinical data are audited. A ZIP that includes original content can be
large (you'll get a warning).
