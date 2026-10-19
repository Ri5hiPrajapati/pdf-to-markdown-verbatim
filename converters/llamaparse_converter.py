#!/usr/bin/env python3
"""converters/llamaparse_converter.py
End-to-end PDF to Markdown verbatim transcription powered by LlamaIndex LlamaParse (LlamaCloud v2).

Features:
  1. Utilizes unified LlamaCloud v2 API (llama-cloud>=1.0).
  2. Multi-tier selection: "agentic" (10 credits, max accuracy) or "cost_effective" (3 credits).
  3. Automatic conversion of HTML <table> blocks into strict GitHub Flavored Markdown pipe tables.
  4. Generates both raw parsed Markdown, table-converted Markdown, and interactive HTML preview.
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from llama_cloud import LlamaCloud
from bs4 import BeautifulSoup
import markdown

DEFAULT_TIER = "agentic"

def get_api_key(args_key=None, args_file=None):
    if args_key:
        return args_key
    if "LLAMA_CLOUD_API_KEY" in os.environ and os.environ["LLAMA_CLOUD_API_KEY"].strip():
        return os.environ["LLAMA_CLOUD_API_KEY"].strip()
    if args_file and os.path.exists(args_file):
        with open(args_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    default_files = [
        "llamaparse_api_key.env",
        "../llamaparse_api_key.env",
        "D:/SIDE PROJECTS/1. APJCE Review article/llamaparse_api_key.env"
    ]
    for df in default_files:
        if os.path.exists(df):
            with open(df, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
    raise ValueError("LlamaParse API Key not found. Set LLAMA_CLOUD_API_KEY environment variable or pass --key.")

def convert_html_tables_to_md(text: str) -> str:
    """Converts HTML table blocks into standard GitHub Flavored Markdown pipe tables."""
    def repl(match):
        table_html = match.group(0)
        soup = BeautifulSoup(table_html, 'html.parser')
        rows = []
        headers = [th.get_text(separator=' ', strip=True) for th in soup.find_all('th')]
        if headers:
            rows.append('| ' + ' | '.join(headers) + ' |')
            rows.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            cells = [td.get_text(separator=' ', strip=True) for td in tds]
            if headers and len(cells) < len(headers):
                cells += [''] * (len(headers) - len(cells))
            elif headers and len(cells) > len(headers):
                cells = cells[:len(headers)]
            rows.append('| ' + ' | '.join(cells) + ' |')
        return '\n\n' + '\n'.join(rows) + '\n\n'

    return re.sub(r'<table>.*?</table>', repl, text, flags=re.DOTALL)

def convert_pdf(pdf_path, api_key, out_dir=None, tier=DEFAULT_TIER):
    pdf_path = os.path.abspath(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    if not out_dir:
        out_dir = os.path.splitext(pdf_path)[0] + "_llamaparse_output"
    os.makedirs(out_dir, exist_ok=True)

    out_md_raw = os.path.join(out_dir, f"{base_name}_llamaparse_raw.md")
    out_md_tables = os.path.join(out_dir, f"{base_name}_llamaparse.md")
    out_html = os.path.join(out_dir, f"{base_name}_llamaparse.html")

    print("=" * 70)
    print("LlamaIndex LlamaParse (LlamaCloud v2) Converter")
    print(f"Source PDF : {os.path.basename(pdf_path)}")
    print(f"Tier       : {tier}")
    print(f"Output Dir : {out_dir}")
    print("=" * 70)

    client = LlamaCloud(api_key=api_key)
    custom_prompt = (
        "Extract all text, sections, headings, paragraphs, mathematical symbols, "
        "and tables verbatim from this scientific research article. "
        "Format all tabular data into clean, standard GitHub Flavored Markdown tables. "
        "Ensure all citations, references, and numerical values are completely preserved without summarizing."
    )

    t0 = time.time()
    with open(pdf_path, "rb") as f:
        res = client.parsing.parse(
            tier=tier,
            version="latest",
            upload_file=f,
            agentic_options={"custom_prompt": custom_prompt},
            expand=["markdown_full"],
            verbose=False
        )

    elapsed = time.time() - t0
    full_text = res.markdown_full if res.markdown_full else ""
    if not full_text and hasattr(res, 'text_full') and res.text_full:
        full_text = res.text_full

    if not full_text:
        raise RuntimeError("Received empty response from LlamaCloud.")

    with open(out_md_raw, "w", encoding="utf-8") as f:
        f.write(full_text)

    tables_md = convert_html_tables_to_md(full_text)
    with open(out_md_tables, "w", encoding="utf-8") as f:
        f.write(tables_md)

    try:
        html_body = markdown.markdown(tables_md, extensions=['tables', 'fenced_code'])
    except Exception:
        html_body = f"<pre>{tables_md}</pre>"

    html_page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{base_name}</title>
<style>body{{font-family:system-ui;max-width:960px;margin:40px auto;padding:0 20px;line-height:1.6;}}table{{border-collapse:collapse;width:100%;margin:16px 0;}}th,td{{border:1px solid #ddd;padding:8px;}}th{{background:#f4f4f4;}}</style>
</head><body>{html_body}</body></html>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_page)

    print("\n" + "=" * 70)
    print(f"SUCCESS: Parsed in {elapsed:.2f}s")
    print(f"Master MD   : {out_md_tables}")
    print(f"HTML Preview: {out_html}")
    print("=" * 70)
    return out_md_tables

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using LlamaIndex LlamaParse")
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument("--key", help="LlamaCloud API key string")
    parser.add_argument("--key-file", help="Path to LlamaCloud API key env file")
    parser.add_argument("--tier", default=DEFAULT_TIER, choices=["agentic", "cost_effective", "fast", "agentic_plus"])
    parser.add_argument("--out-dir", help="Output directory")
    args = parser.parse_args()

    key = get_api_key(args.key, args.key_file)
    convert_pdf(args.pdf, key, args.out_dir, args.tier)
