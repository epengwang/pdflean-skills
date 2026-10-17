#!/usr/bin/env python3
"""PDFLean API thin client (stdlib only).

All document processing happens on PDFLean's cloud API. This script only
prepares requests, polls job status and downloads results.

Usage:
  PDFLEAN_API_KEY=... python3 pdflean.py <command> [args]

Commands:
  me                                  Show the account behind the API key
  usage                               Show credit balance and recent usage
  merge out.pdf in1.pdf in2.pdf [...] Merge 2-10 PDFs (1 credit)
  split out-prefix.pdf in.pdf --ranges "1-3,5"
                                      Split a PDF by page ranges (1 credit)
  compress out.pdf in.pdf             Compress a PDF (1 credit)
  linearize out.pdf in.pdf            Linearize a PDF (Fast Web View)
  office out in.docx                  Convert Office/ODF documents
  typst out.pdf in.typ                Render Typst/Markdown source to PDF
  ocr out.pdf scan.pdf                OCR a scan into a searchable PDF (per-page billing)
  ocr-text image.png                  OCR an image to text (prints text)
  validate-pdfa in.pdf                PDF/A compliance report (prints JSON)
  validate-pdfua in.pdf               PDF/UA accessibility report (prints JSON)
  validate-signature in.pdf           Digital signature report (prints JSON)
  sign out.pdf in.pdf                 Digitally sign a PDF
  redact out.pdf in.pdf --terms "Zhang San,ID 123" [--areas "x,y,w,h,page;..."]
                                      True redaction (burned-in black boxes)
  extract in.pdf [--kind invoice|generic]
                                      Extract text and structured fields (prints JSON)
  docling in.pdf [--format md|json]   Structured layout parse (prints result)
  scan-pii textfile.txt               Scan text for personal data (prints JSON)

Files are sent base64-inlined; the API accepts up to 8 MB per inline file.
Paid calls cost credits per the API price list; failed jobs are not charged.
"""
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid

BASE = os.environ.get("PDFLEAN_API_BASE", "https://pdflean.com/api/v1")
KEY = os.environ.get("PDFLEAN_API_KEY", "")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def request(method, path, body=None, raw=False):
    if not KEY:
        die("PDFLEAN_API_KEY is not set. Create a key in your PDFLean account "
            "and export it as an environment variable; never hardcode it.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Idempotency-Key", str(uuid.uuid4()))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        die(f"network error: {e}")
    if raw:
        return payload
    try:
        return json.loads(payload)
    except ValueError:
        return {"raw": payload.decode(errors="replace")}


def b64(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > 8 * 1024 * 1024:
        die(f"{path} exceeds the 8 MB inline limit of the API")
    return base64.b64encode(data).decode()


def job_id_of(resp):
    for k in ("jobId", "job_id", "runId", "id"):
        if isinstance(resp, dict) and resp.get(k):
            return resp[k]
        if isinstance(resp, dict) and isinstance(resp.get("data"), dict) and resp["data"].get(k):
            return resp["data"][k]
    return None


def wait_job(jid):
    while True:
        st = request("GET", f"/jobs/{jid}")
        status = (st.get("status") or st.get("data", {}).get("status") or "").lower()
        if status in ("succeeded", "success", "completed", "done"):
            return st
        if status in ("failed", "error", "canceled"):
            die(f"job {jid} failed: {json.dumps(st)[:400]}")
        time.sleep(2)


def run_file_job(path, body, out_path):
    resp = request("POST", path, body)
    jid = job_id_of(resp)
    if not jid:
        die(f"unexpected response (no job id): {json.dumps(resp)[:400]}")
    wait_job(jid)
    payload = request("GET", f"/jobs/{jid}/download", raw=True)
    with open(out_path, "wb") as f:
        f.write(payload)
    print(out_path)


def run_report_job(path, body):
    resp = request("POST", path, body)
    jid = job_id_of(resp)
    if jid:
        wait_job(jid)
        payload = request("GET", f"/jobs/{jid}/download", raw=True)
        print(payload.decode(errors="replace"))
    else:
        print(json.dumps(resp, ensure_ascii=False, indent=2))


def main(argv):
    if not argv:
        die(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "me":
        print(json.dumps(request("GET", "/me"), ensure_ascii=False, indent=2))
    elif cmd == "usage":
        print(json.dumps(request("GET", "/usage"), ensure_ascii=False, indent=2))
    elif cmd == "merge":
        out, ins = args[0], args[1:]
        if not (2 <= len(ins) <= 10):
            die("merge needs 2-10 input PDFs")
        run_file_job("/pdf/merge", {"files": [b64(p) for p in ins]}, out)
    elif cmd == "split":
        out, src = args[0], args[1]
        ranges = args[args.index("--ranges") + 1] if "--ranges" in args else die("split needs --ranges")
        run_file_job("/pdf/split", {"file": b64(src), "ranges": ranges}, out)
    elif cmd == "compress":
        run_file_job("/pdf/compress", {"file": b64(args[1])}, args[0])
    elif cmd == "linearize":
        run_file_job("/convert/linearize", {"file": b64(args[1])}, args[0])
    elif cmd == "office":
        run_file_job("/convert/office", {"file": b64(args[1])}, args[0])
    elif cmd == "typst":
        with open(args[1], "rb") as f:
            src = base64.b64encode(f.read()).decode()
        run_file_job("/convert/typst", {"source": src}, args[0])
    elif cmd == "ocr":
        run_file_job("/ocr", {"file": b64(args[1])}, args[0])
    elif cmd == "ocr-text":
        run_report_job("/ocr/text", {"file": b64(args[0])})
    elif cmd == "validate-pdfa":
        run_report_job("/validate/pdfa", {"file": b64(args[0])})
    elif cmd == "validate-pdfua":
        run_report_job("/validate/pdfua", {"file": b64(args[0])})
    elif cmd == "validate-signature":
        run_report_job("/validate/signature", {"file": b64(args[0])})
    elif cmd == "sign":
        run_file_job("/sign", {"file": b64(args[1])}, args[0])
    elif cmd == "redact":
        out, src = args[0], args[1]
        body = {"file": b64(src)}
        if "--terms" in args:
            body["terms"] = [t.strip() for t in args[args.index("--terms") + 1].split(",") if t.strip()]
        if "--areas" in args:
            body["areas"] = args[args.index("--areas") + 1]
        if "terms" not in body and "areas" not in body:
            die("redact needs --terms and/or --areas")
        run_file_job("/redact", body, out)
    elif cmd == "extract":
        kind = args[args.index("--kind") + 1] if "--kind" in args else "generic"
        run_report_job("/extract", {"file": b64(args[0]), "kind": kind})
    elif cmd == "docling":
        fmt = args[args.index("--format") + 1] if "--format" in args else "md"
        run_report_job("/docling", {"file": b64(args[0]), "format": fmt})
    elif cmd == "scan-pii":
        with open(args[0], "r", encoding="utf-8") as f:
            text = f.read()
        if len(text) > 200_000:
            die("scan-pii input exceeds 200k characters")
        print(json.dumps(request("POST", "/scan/pii", {"text": text}), ensure_ascii=False, indent=2))
    else:
        die(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
