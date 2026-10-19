#!/usr/bin/env python3
"""converters/gemini_converter.py
End-to-end PDF to Markdown verbatim transcription powered by Google Gemini API.

Features:
  1. Per-page rasterization via PyMuPDF at 150 DPI.
  2. High-fidelity verbatim transcription using google-genai SDK.
  3. Direct generation of GitHub Flavored Markdown pipe tables.
  4. Automatic elimination of running headers, footers, and page folios.
  5. Caching and assembly: stitched Master Markdown and interactive HTML preview.
"""

import os
import sys
import time
import json
import re
import argparse

sys.stdout.reconfigure(encoding='utf-8')
import pymupdf as fitz
import markdown
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are an expert scientific document transcription engine.
Your task is to transcribe the provided academic publication page image into 100% faithful, verbatim GitHub Flavored Markdown.

CRITICAL RULES:
1. VERBATIM FIDELITY: Transcribe every word, number, decimal point, equation, and chemical formula exactly as printed. Do NOT summarize, rephrase, omit, or abbreviate anything.
2. EXCLUSION OF PAGE FURNITURE: Do NOT transcribe running headers, running footers, or printed page folio numbers.
3. TABLE RECONSTRUCTION:
   - Convert all tables into standard Markdown pipe tables (| Col 1 | Col 2 |).
   - Ensure the number of cells in every row matches the header column count exactly.
   - Preserve all numerical values with ± standard deviations and statistical significance superscripts.
   - Include the table caption immediately preceding the table and table footnotes immediately following it.
4. MATHEMATICAL FORMULAS: Transcribe inline math using $...$ and display equations using $$...$$.
5. HEADINGS: Use markdown hierarchy (# for Title, ## for main sections, ### for subsections).
6. REFERENCES: Transcribe every reference/bibliography entry completely without dropping authors, titles, journals, or DOIs.
7. OUTPUT ONLY: Return ONLY the clean markdown content. Do NOT include markdown code fences (```markdown), conversational greetings, or concluding remarks.
"""

def get_api_key(args_key=None, args_file=None):
    if args_key:
        return args_key
    if "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"].strip():
        return os.environ["GEMINI_API_KEY"].strip()
    if args_file and os.path.exists(args_file):
        with open(args_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    default_files = [
        "gemini_api_key.env",
        "../gemini_api_key.env",
        "D:/SIDE PROJECTS/1. APJCE Review article/gemini_api_key.env"
    ]
    for df in default_files:
        if os.path.exists(df):
            with open(df, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
    raise ValueError("Gemini API Key not found. Set GEMINI_API_KEY environment variable or pass --key.")

def clean_markdown_output(text):
    text = re.sub(r"^```markdown\s*", "", text, flags=re.I)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def convert_pdf(pdf_path, api_key, out_dir=None, model=DEFAULT_MODEL, dpi=150):
    pdf_path = os.path.abspath(pdf_path)
    if not out_dir:
        out_dir = os.path.splitext(pdf_path)[0] + "_gemini_output"
    os.makedirs(out_dir, exist_ok=True)

    client = genai.Client(api_key=api_key)
    doc = fitz.open(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    master_md_path = os.path.join(out_dir, f"{base_name}_gemini.md")
    master_html_path = os.path.join(out_dir, f"{base_name}_gemini.html")

    print("=" * 70)
    print("Google Gemini Scientific Document Converter")
    print(f"Source PDF : {os.path.basename(pdf_path)} ({len(doc)} pages)")
    print(f"Model      : {model}")
    print(f"Output Dir : {out_dir}")
    print("=" * 70)

    page_mds = []
    t0 = time.time()
    for idx, page in enumerate(doc):
        p_num = idx + 1
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        print(f"Processing Page {p_num}/{len(doc)}...", end="", flush=True)
        pt0 = time.time()
        
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    "Transcribe this academic page image into clean, faithful Markdown according to the instructions."
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.0
                )
            )
            raw_text = response.text if response.text else ""
            cleaned_text = clean_markdown_output(raw_text)
            page_mds.append(cleaned_text)
            print(f" Done ({time.time()-pt0:.2f}s, {len(cleaned_text)} chars)")
        except Exception as e:
            print(f" FAILED ({e})")
            page_mds.append(f"<!-- Page {p_num} Error: {e} -->")

    full_md = "\n\n---\n\n".join(page_mds)
    with open(master_md_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    try:
        html_body = markdown.markdown(full_md, extensions=['tables', 'fenced_code'])
    except Exception:
        html_body = f"<pre>{full_md}</pre>"

    html_page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{base_name}</title>
<style>body{{font-family:system-ui;max-width:960px;margin:40px auto;padding:0 20px;line-height:1.6;}}table{{border-collapse:collapse;width:100%;margin:16px 0;}}th,td{{border:1px solid #ddd;padding:8px;}}th{{background:#f4f4f4;}}</style>
</head><body>{html_body}</body></html>"""
    with open(master_html_path, "w", encoding="utf-8") as f:
        f.write(html_page)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"SUCCESS: Converted {len(doc)} pages in {elapsed:.2f}s ({elapsed/len(doc):.2f}s/page)")
    print(f"Master MD   : {master_md_path}")
    print(f"HTML Preview: {master_html_path}")
    print("=" * 70)
    return master_md_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using Google Gemini API")
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument("--key", help="Gemini API key string")
    parser.add_argument("--key-file", help="Path to Gemini API key env file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name (e.g., gemini-2.5-flash, gemini-3.5-flash-lite)")
    parser.add_argument("--out-dir", help="Output directory")
    parser.add_argument("--dpi", type=int, default=150, help="Rasterization DPI")
    args = parser.parse_args()

    key = get_api_key(args.key, args.key_file)
    convert_pdf(args.pdf, key, args.out_dir, args.model, args.dpi)
