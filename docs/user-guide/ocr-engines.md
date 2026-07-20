# OCR engines

Before an LLM can extract data, your files must be turned into plain text —
[preprocessing](preprocessing.md). For PDFs and images this is done by an **OCR
/ text-extraction engine**. The app offers **three selectable engines** (below),
plus an optional local Docling fallback your administrator can enable. Pick
whichever suits your document type; your administrator controls which appear in
the [preprocessing panel](preprocessing.md#choosing-an-ocr-engine).

## 1. Quick (Local OCR) — no API needed

Uses **Docling-serve** (a remote service running Docling + Tesseract) to extract
text. It detects whether a PDF already has embedded text and uses it directly;
for scanned pages or images it runs Tesseract OCR locally.

- **Best for:** any document; works offline, no extra cost.
- **Limitations:** slower for large batches; Tesseract accuracy varies with image
  quality.
- **Force OCR:** treat all PDF pages as images (bypasses embedded text) — see
  [below](#force-ocr).

## 2. Mistral OCR API

Sends pages to a Mistral OCR-compatible API — either the official Mistral cloud
service or a self-hosted DeepSeek-OCR-2 instance
([KatDocExtract](https://github.com/KatherLab/KatDocExtract)).

- **Best for:** complex layouts, tables, and forms — higher accuracy than local
  OCR.
- **Limitations:** requires an API key and network access (or a GPU + compose
  overlay).

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

## 4. Local Docling fallback (optional)

When `DOCLING_LOCAL_FALLBACK=true`, the backend can run Docling **locally** as a
fallback if docling-serve is unavailable. This requires the `docling-slim`
package (in the dev dependency group).

## Force OCR

When enabled, the embedded-text pre-check is **skipped** and every page goes
through the selected engine. Useful for PDFs with garbled or incomplete embedded
text.

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
