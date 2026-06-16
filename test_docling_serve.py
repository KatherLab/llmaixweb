#!/usr/bin/env python3
"""Test docling-serve OCR on 9874562_notext.pdf"""

from pathlib import Path

import httpx

PDF_PATH = Path(__file__).parent / "backend" / "tests" / "files" / "9874562_notext.pdf"

pdf_bytes = PDF_PATH.read_bytes()

response = httpx.post(
    "http://localhost:5001/v1/convert/file",
    files={"files": (PDF_PATH.name, pdf_bytes, "application/pdf")},
    data={
        "from_formats": "pdf",
        "to_formats": "md",
        "do_ocr": "true",
        # "force_ocr": "true",
        "ocr_preset": "tesseract",
        "ocr_lang": ["auto"],
    },
    timeout=600,
)

print(f"Status: {response.status_code}")
print(f"Response:\n{response.text}")
