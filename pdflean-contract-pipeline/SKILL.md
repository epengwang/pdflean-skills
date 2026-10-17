---
name: pdflean-contract-pipeline
description: Run the standard contract intake pipeline on the PDFLean cloud API — extract a contract's text and structured fields, scan the text for personal data (names, ID numbers, emails, phone numbers, bank details), report the findings, and optionally produce a truly redacted copy with the found personal values permanently burned out. Use when a user receives a contract or agreement and wants it checked, logged or sanitized before filing or forwarding. Requires the pdflean-pdf-toolkit skill in the same skills folder and the user's own PDFLEAN_API_KEY; each of the three steps costs 1 API credit.
---

# PDFLean Contract Pipeline

One command runs the three steps an operations or legal assistant
normally does by hand when a contract arrives:

1. **Extract** — pull the document's text and structured fields
   (`POST /extract`; use `--kind invoice` for invoices instead of
   contracts).
2. **Scan** — run the extracted text through personal-data detection
   (`POST /scan/pii`) and collect every distinct personal value found.
3. **Redact (optional)** — burn the found values out of a copy of the
   PDF (`POST /redact`, true redaction: the underlying text is removed,
   not hidden under a black rectangle).

## Run it

```
python3 scripts/contract_pipeline.py contract.pdf \
    --report evidence.json --redact-out contract-redacted.pdf
```

- `--report` writes the full JSON evidence (extraction result, PII
  findings, the exact list of redacted values) — keep it with the filing
  record.
- `--redact-out` is optional; without it the pipeline is read-only
  (extract + scan + report).
- The script prints a step-by-step summary and stops loudly if a step
  returns no usable data; it never guesses at missing fields.

## Rules for the agent

- Depends on the sibling skill `pdflean-pdf-toolkit` (same parent
  folder) for the API client; the API key comes from the
  `PDFLEAN_API_KEY` environment variable only.
- Processing happens on PDFLean's cloud servers. If the user says the
  contract must not leave their device, do not run this pipeline —
  explain the trade-off and stop.
- Show the user the PII findings summary before producing a redacted
  copy when the run is interactive; redaction is irreversible.
- Cost: 1 credit per step (2 credits read-only, 3 with redaction).
  Failed jobs are not charged.
