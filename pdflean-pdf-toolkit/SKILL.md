---
name: pdflean-pdf-toolkit
description: Process PDF and Office documents through the PDFLean cloud API — merge, split, compress, linearize, convert Office files, OCR scans and images, validate PDF/A, PDF/UA and digital signatures, sign PDFs, apply true redaction, extract structured fields (including invoices), parse document layout, and scan text for personal data. Use when a task involves producing or checking a processed document file or a compliance/extraction report. Requires the user's own PDFLEAN_API_KEY; calls are billed in API credits and failed jobs are not charged.
---

# PDFLean PDF Toolkit

Thin wrapper over the PDFLean public API (https://pdflean.com/api/v1).
The script in `scripts/pdflean.py` uses only the Python standard library.

## Setup

1. The user creates an API key in their PDFLean account (API keys page).
2. Export it — never write it into files or prompts:

   `export PDFLEAN_API_KEY="..."`

3. Sanity check before first real work: `python3 scripts/pdflean.py me`
   and `python3 scripts/pdflean.py usage` (shows credit balance).

## How it works

- Every processing call is an asynchronous job: the script posts the job,
  polls `GET /jobs/{id}`, then downloads the result from
  `GET /jobs/{id}/download`. Report-type calls (validate, extract,
  docling, ocr-text, scan-pii) print JSON/text to stdout instead.
- Files are sent base64-inlined. Per-file inline limit: 8 MB. For larger
  files, tell the user to use the PDFLean web app or a workflow run.
- Billing: standard tasks cost 1 credit per call, OCR is billed per page,
  status and download calls are free, failed jobs are not charged.
  Check `usage` before batch work.

## Command map (intent → command)

- Combine several PDFs → `merge out.pdf a.pdf b.pdf ...` (2–10 inputs)
- Extract page ranges → `split out.pdf in.pdf --ranges "1-3,5"`
- Shrink a PDF for email/upload portals → `compress out.pdf in.pdf`
- Prepare for fast web viewing → `linearize out.pdf in.pdf`
- Convert Word/Excel/PowerPoint/ODF → `office out.pdf in.docx`
- Render Typst/Markdown to PDF → `typst out.pdf source.typ`
- Make a scan searchable → `ocr out.pdf scan.pdf`
- Read text from an image → `ocr-text image.png`
- Archive compliance check → `validate-pdfa in.pdf`
- Accessibility check → `validate-pdfua in.pdf`
- Check a signed document → `validate-signature in.pdf`
- Sign a document → `sign out.pdf in.pdf`
- Permanently remove sensitive strings → `redact out.pdf in.pdf --terms "..."`
  (true redaction: content is burned out, not covered by a black box)
- Pull fields from invoices or forms → `extract in.pdf --kind invoice`
- Get Markdown/JSON of a document's layout → `docling in.pdf --format md`
- Find personal data in text → `scan-pii text.txt` (200k characters max)

## Rules for the agent

- These endpoints process files on PDFLean's cloud servers. Do not use
  this skill for documents the user wants kept strictly on-device; point
  them to PDFLean's browser-local tools instead.
- Confirm the exact input files and the credit cost before running batch
  jobs (more than 5 calls). Single calls can run directly.
- Always report which output file was produced and the job outcome; if a
  job fails, quote the API error and stop — do not retry paid calls in a
  loop.
