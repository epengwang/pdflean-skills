#!/usr/bin/env python3
"""Contract processing pipeline on the PDFLean cloud API (stdlib only).

Pipeline: extract text/fields -> scan for personal data (PII) ->
optionally produce a truly redacted copy with the found values burned out.

Usage:
  PDFLEAN_API_KEY=... python3 contract_pipeline.py contract.pdf \
      [--kind invoice|generic] [--redact-out redacted.pdf] [--report report.json]

Outputs:
  - prints a human-readable summary (fields found, PII findings by type)
  - with --report, writes the full JSON evidence (extract + PII findings)
  - with --redact-out, writes the redacted PDF

Billing: one credit per API step (extract; scan-pii; redact). Failed jobs
are not charged. All processing happens on PDFLean's cloud API.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.join(HERE, "..", "..", "pdflean-pdf-toolkit", "scripts", "pdflean.py")


def run_toolkit(*args):
    cmd = [sys.executable, TOOLKIT, *args]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stderr.strip(), file=sys.stderr)
        sys.exit(out.returncode)
    return out.stdout


def collect_text(node, acc):
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("text", "content", "markdown") and isinstance(v, str):
                acc.append(v)
            else:
                collect_text(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_text(v, acc)


def collect_pii_values(node, acc):
    """Collect literal personal-data values from a PII scan result."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("value", "match", "text") and isinstance(v, str) and len(v) >= 2:
                acc.add(v)
            else:
                collect_pii_values(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_pii_values(v, acc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--kind", default="generic", choices=["invoice", "generic"])
    ap.add_argument("--redact-out")
    ap.add_argument("--report")
    a = ap.parse_args()

    print(f"[1/3] extracting fields (kind={a.kind}) ...")
    extract_raw = run_toolkit("extract", a.pdf, "--kind", a.kind)
    try:
        extract = json.loads(extract_raw)
    except ValueError:
        extract = {"raw": extract_raw}

    texts = []
    collect_text(extract, texts)
    full_text = "\n".join(texts)
    if not full_text.strip():
        print("extraction returned no text; cannot run the PII scan. "
              "Raw extract output kept for diagnosis.", file=sys.stderr)
        if a.report:
            with open(a.report, "w", encoding="utf-8") as f:
                json.dump({"extract": extract, "pii": None}, f, ensure_ascii=False, indent=2)
        sys.exit(2)

    print(f"[2/3] scanning {len(full_text)} characters for personal data ...")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(full_text[:200_000])
        tf_path = tf.name
    try:
        pii_raw = run_toolkit("scan-pii", tf_path)
    finally:
        os.unlink(tf_path)
    try:
        pii = json.loads(pii_raw)
    except ValueError:
        pii = {"raw": pii_raw}

    values = set()
    collect_pii_values(pii, values)
    values = sorted(v for v in values if v.strip())
    print(f"      PII findings: {len(values)} distinct values")

    redacted_path = None
    if a.redact_out:
        if not values:
            print("[3/3] no PII values found; redaction skipped.")
        else:
            print(f"[3/3] redacting {len(values)} values ...")
            run_toolkit("redact", a.redact_out, a.pdf, "--terms", ",".join(values))
            redacted_path = a.redact_out

    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump({"extract": extract, "pii": pii, "redacted_values": values},
                      f, ensure_ascii=False, indent=2)
        print(f"report: {a.report}")
    if redacted_path:
        print(f"redacted: {redacted_path}")
    print("done.")


if __name__ == "__main__":
    main()
