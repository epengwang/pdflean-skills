# PDFLean Skills

Agent skills that let an AI assistant work with PDFs through the PDFLean public API. Skills are thin wrappers: all processing happens through the API with your own API key, and usage is metered in API credits.

## Skills in this repo

### pdflean-pdf-toolkit
General-purpose PDF operations: merge, split, compress, linearize, convert Office documents, OCR, validate PDF/A and PDF/UA, verify signatures, sign, redact, extract structured data, convert documents to Markdown/JSON (Docling), and scan for PII.

### pdflean-contract-pipeline
A three-step contract review pipeline: extract structured fields, scan for personal data, and optionally redact — with a JSON evidence report for every step.

## Requirements

- A PDFLean API key (create one in your PDFLean account). Set it as an environment variable:
  `export PDFLEAN_API_KEY=your_key_here`
- Python 3 (standard library only, no extra packages).

## Install

Copy the skill folders into your agent's skills directory, for example:

- Claude Code: `~/.claude/skills/`
- ZCode: `~/.zcode/skills/` or your workspace `.agents/skills/`
- Other SKILL.md-compatible hosts: their documented skills folder.

## Notes

- Files are sent to the API as base64; the API accepts files up to 8 MB per call.
- Failed API jobs are not charged.
- Website: https://pdflean.com — API documentation: https://pdflean.com/workflows/api
