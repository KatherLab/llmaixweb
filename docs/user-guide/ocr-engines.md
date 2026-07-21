# OCR engines

Before an LLM can extract data, your files must be turned into plain text —
[preprocessing](preprocessing.md). For PDFs and images this is done by an **OCR
/ text-extraction engine**. The app offers **three selectable engines** (below),
plus an optional local Docling fallback your administrator can enable. Pick
whichever suits your document type; your administrator controls which appear in
the [preprocessing panel](preprocessing.md#choosing-an-ocr-engine).

The engine cards you see in the panel use display names and subtitles that an
administrator can customise; the underlying engine keys are fixed:

| Card (default label) | Engine key | Backend |
| --- | --- | --- |
| **Quick (Local OCR)** | `docling_tesseract` | docling-serve (Docling + Tesseract) |
| **Mistral OCR API** | `mistral_ocr` | Mistral cloud or self-hosted DeepSeek-OCR-2 |
| **Vision LLM API** | `llm_vision` | any OpenAI-compatible vision model |

!!! note "Text and tables skip OCR entirely"
    CSV, XLSX, and TXT files are imported as structured text, so no OCR engine is
    involved — the choices below apply only to **PDFs and images**.

## 1. Quick (Local OCR) — no API needed

Uses **Docling-serve** (a remote service running Docling + Tesseract) to extract
text. It detects whether a PDF already has embedded text and uses it directly;
for scanned pages or images it runs Tesseract OCR locally.

- **Best for:** any document; works offline, no extra cost.
- **Limitations:** slower for large batches; Tesseract accuracy varies with image
  quality.
- **Language:** Tesseract runs in **auto-detect** mode by default. Under
  **Advanced options** you can pin a specific language (English, German, French,
  Spanish, Italian, Portuguese, Dutch, Polish, Russian, Simplified Chinese, or
  Latin), which helps on noisy scans in a known language.
- **Force OCR:** treat all PDF pages as images (bypasses embedded text) — see
  [below](#force-ocr).

!!! note "Requires docling-serve"
    This engine calls the docling-serve service (`DOCLING_SERVE_ENABLED`,
    `DOCLING_SERVE_URL`). If a PDF has no embedded text and docling-serve is
    disabled — and no local fallback is configured — preprocessing fails with a
    message asking you to enable it or upload a PDF that contains selectable text.

## 2. Mistral OCR API

Sends pages to a Mistral OCR-compatible API — either the official Mistral cloud
service or a self-hosted DeepSeek-OCR-2 instance
([KatDocExtract](https://github.com/KatherLab/KatDocExtract)).

- **Best for:** complex layouts, tables, and forms — higher accuracy than local
  OCR.
- **Limitations:** requires an API key and network access (or a GPU + compose
  overlay).
- **Overrides:** under **Advanced options** you can supply a per-run **API Key**
  and **Model** (placeholder `mistral-ocr-latest`); leave them blank to use the
  server defaults.

!!! tip "Embedded-text shortcut"
    The engine checks for embedded PDF text first. If enough is found, it uses
    Docling without OCR, saving the API call. Disable this with **Force OCR**.

## 3. Vision LLM OCR

Sends pages as images to any OpenAI-compatible vision model (GPT-4o, Gemma via
vLLM, etc.).

- **Best for:** documents that need understanding of layout and visual context.
- **Limitations:** slower and more expensive than dedicated OCR; requires a
  vision-capable model.
- Uses the same embedded-text shortcut as Mistral OCR — pages are only sent to
  the vision model when needed.
- **Prompt:** the instruction sent with each page is editable in the panel and
  defaults to *"Extract all text from this image and return it as clean
  markdown."*
- **Overrides:** under **Advanced options** you can set a per-run **API Key**,
  **Base URL** (e.g. `https://api.openai.com/v1`), **Model**, and a **Max image
  dimension** (400–4096 px) that bounds how large each page image is sent. Blank
  fields fall back to the server defaults.

## 4. Local Docling fallback (optional)

When `DOCLING_LOCAL_FALLBACK=true`, the backend can run Docling **locally** as a
fallback if docling-serve is unavailable. This requires the `docling-slim`
package (in the dev dependency group). With the fallback enabled, a PDF that has
no embedded text can still be processed on the local machine rather than failing.

## Force OCR

When enabled, the embedded-text pre-check is **skipped** and every page goes
through the selected engine. Useful for PDFs with garbled or incomplete embedded
text. The toggle appears in the panel only when the selection contains PDFs and
an engine is enabled.

!!! info "How the embedded-text check works"
    For PDFs, the pipeline first probes for selectable text. A PDF counts as
    "has embedded text" once it exceeds a character threshold
    (`DOCLING_MIN_EXTRACTED_CHARS_PDF`, **100 characters** by default). Above the
    threshold the text is extracted directly and no OCR runs (unless **Force OCR**
    is on); below it, the page is sent to the selected OCR engine. Images always
    go through OCR — there is no embedded text to reuse.

## Self-hosted engines

Run OCR entirely on your own hardware with the optional compose overlays:

```bash
# Local Mistral-compatible OCR (DeepSeek-OCR-2 + KatDocExtract, GPU)
docker compose -f compose.yml -f compose.deepseek.yml up -d

# Local vision LLM endpoint (e.g. Gemma via vLLM, GPU)
docker compose -f compose.yml -f compose.vllm.yml up -d
```

Then point `MISTRAL_API_BASE` / `VISION_OCR_API_BASE` at the respective service.
See [Configuration](../operations/configuration.md) and the
[compose overlays](../getting-started/installation.md#compose-files).
