#!/usr/bin/env python3
"""converters/colab_remote_converter.py
Client to send local PDF documents to a self-hosted Google Colab GPU server.

Usage:
  1. Open colab/colab_api_server.ipynb in Google Colab and run all cells.
  2. Copy the public URL printed at the end (e.g., https://curvy-otters-sing.loca.lt).
  3. Run this script locally:
     python converters/colab_remote_converter.py path/to/paper.pdf --url https://curvy-otters-sing.loca.lt
"""

import os
import sys
import time
import argparse
import requests
from pathlib import Path

def parse_pdf_via_colab(pdf_path, server_url, out_dir=None):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    base_name = pdf_path.stem
    if not out_dir:
        out_dir = pdf_path.parent / f"{base_name}_colab_output"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    endpoint = server_url.rstrip("/") + "/parse"
    print("=" * 70)
    print("Google Colab Remote OCR Client")
    print(f"Target PDF : {pdf_path.name}")
    print(f"Server URL : {endpoint}")
    print(f"Output Dir : {out_dir}")
    print("=" * 70)

    t0 = time.time()
    print("Uploading PDF to Google Colab GPU runtime for inference...", flush=True)
    
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        headers = {"Bypass-Tunnel-Reminder": "true"} # Required for localtunnel
        resp = requests.post(endpoint, files=files, headers=headers, timeout=300)

    resp.raise_for_status()
    data = resp.json()
    elapsed = time.time() - t0

    pages = data.get("pages", 0)
    markdown_text = data.get("markdown", "")

    out_md_path = out_dir / f"{base_name}_colab.md"
    out_md_path.write_text(markdown_text, encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"SUCCESS: Received {pages} pages in {elapsed:.2f}s ({elapsed/max(pages, 1):.2f}s/page)!")
    print(f"Markdown output saved to: {out_md_path}")
    print("=" * 70)
    return str(out_md_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send PDF to remote Google Colab OCR instance")
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument("--url", required=True, help="Public Colab tunnel URL (e.g. https://xxx.loca.lt)")
    parser.add_argument("--out-dir", help="Output directory")
    args = parser.parse_args()

    parse_pdf_via_colab(args.pdf, args.url, args.out_dir)
