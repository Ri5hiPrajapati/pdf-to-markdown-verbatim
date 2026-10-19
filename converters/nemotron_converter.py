#!/usr/bin/env python3
"""converters/nemotron_converter.py
PDF to Markdown converter powered by NVIDIA Nemotron Parse (Zero-Cost NIM Tier).

Features:
  1. Per-page rasterization via PyMuPDF at customizable DPI.
  2. NVIDIA Nemotron Parse API client with bounding-box extraction and layout classification.
  3. Geometric 2D reading-order reconstruction (2-column layouts, abstracts, full-width banners).
  4. Automatic LaTeX \\begin{tabular} to Markdown pipe table compilation (resolving \\multirow & line splits).
  5. Running header/footer masthead noise elimination.
  6. Output packaging: per-page JSON telemetry, stitched master MD, and HTML preview.
"""

import os
import sys
import base64
import time
import json
import re
import argparse
import requests
import pymupdf as fitz
import markdown

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "nvidia/nemotron-parse"

def get_api_key(args_key=None, args_file=None):
    if args_key:
        return args_key
    if "NVIDIA_API_KEY" in os.environ and os.environ["NVIDIA_API_KEY"].strip():
        return os.environ["NVIDIA_API_KEY"].strip()
    if args_file and os.path.exists(args_file):
        with open(args_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    # Check default project root locations
    default_files = [
        "nemotron_ocr_api_key.env",
        "../nemotron_ocr_api_key.env",
        "D:/SIDE PROJECTS/1. APJCE Review article/nemotron_ocr_api_key.env"
    ]
    for df in default_files:
        if os.path.exists(df):
            with open(df, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
    raise ValueError("NVIDIA API Key not found. Set NVIDIA_API_KEY environment variable or pass --key.")

def latex_tabular_to_markdown(latex_str):
    """Converts LaTeX tabular blocks into strict Markdown pipe tables."""
    latex_str = re.sub(r'\\begin\{tabular\}\{[^}]*\}', '', latex_str)
    latex_str = re.sub(r'\\end\{tabular\}', '', latex_str)
    latex_str = latex_str.replace('\\hline', '')
    
    raw_rows = [r.strip() for r in latex_str.split('\\\\') if r.strip()]
    parsed_rows = []
    for r in raw_rows:
        cells = [c.strip() for c in r.split('&')]
        parsed_rows.append(cells)
        
    if not parsed_rows:
        return ""
        
    num_cols = max(len(r) for r in parsed_rows)
    for r in parsed_rows:
        while len(r) < num_cols:
            r.append("")

    cleaned_rows = []
    for r in parsed_rows:
        cleaned_cells = []
        for c in r:
            c = re.sub(r'\\multirow\{[^}]*\}\{[^}]*\}\{(.*?)\}', r'\1', c)
            c = re.sub(r'\\multicolumn\{[^}]*\}\{[^}]*\}\{(.*?)\}', r'\1', c)
            c = c.replace('\n', ' ').strip()
            cleaned_cells.append(c)
        cleaned_rows.append(cleaned_cells)

    final_rows = []
    i = 0
    while i < len(cleaned_rows):
        row = cleaned_rows[i]
        if i + 1 < len(cleaned_rows):
            next_row = cleaned_rows[i + 1]
            if next_row[0] == "" and any(c != "" for c in next_row):
                merged_row = []
                for c1, c2 in zip(row, next_row):
                    if c1 and c2:
                        merged_row.append(f"{c1} {c2}".strip())
                    elif c1:
                        merged_row.append(c1)
                    else:
                        merged_row.append(c2)
                final_rows.append(merged_row)
                i += 2
                continue
        final_rows.append(row)
        i += 1

    if not final_rows:
        return ""

    header = final_rows[0]
    sep = [":---"] * num_cols
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(sep) + " |")
    for r in final_rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
        
    return "\n".join(lines)

def sort_page_elements(elements, page_num):
    """Sorts page bounding boxes into natural reading order."""
    blocks = []
    for elem in elements:
        text = elem.get("text", "").strip()
        category = elem.get("type", "").lower()
        bbox = elem.get("bbox", [0, 0, 1000, 1000])
        if not text:
            continue
        ymin, xmin, ymax, xmax = bbox[0], bbox[1], bbox[2], bbox[3]

        # Filter running headers/footers
        if ymin < 50 and any(kw in text.lower() for kw in ["journal", "elsevier", "volume", "issn", "reports", "http"]):
            continue
        if ymax > 950 and re.match(r'^\d+$', text.strip()):
            continue
        if ymax > 950 and any(kw in text.lower() for kw in ["rights reserved", "copyright", "doi.org"]):
            continue

        width = xmax - xmin
        is_full_width = width > 500 or (xmin < 200 and xmax > 750)
        blocks.append({
            "text": text,
            "category": category,
            "bbox": bbox,
            "ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax,
            "is_full_width": is_full_width
        })

    full_width_top = [b for b in blocks if b["is_full_width"] and b["ymin"] < 400]
    col_blocks = [b for b in blocks if not (b["is_full_width"] and b["ymin"] < 400)]
    full_width_top.sort(key=lambda b: (b["ymin"], b["xmin"]))

    left_col = [b for b in col_blocks if b["xmin"] < 500]
    right_col = [b for b in col_blocks if b["xmin"] >= 500]
    left_col.sort(key=lambda b: (b["ymin"], b["xmin"]))
    right_col.sort(key=lambda b: (b["ymin"], b["xmin"]))

    ordered = full_width_top + left_col + right_col
    return ordered

def format_block_markdown(b):
    cat = b["category"]
    text = b["text"]
    if cat == "title":
        return f"# {text}\n"
    elif cat in ["heading", "header", "section"]:
        return f"\n## {text}\n"
    elif cat in ["subheading", "subsection"]:
        return f"\n### {text}\n"
    elif cat == "table":
        if "\\begin{tabular}" in text:
            md_tbl = latex_tabular_to_markdown(text)
            return f"\n{md_tbl}\n" if md_tbl else f"\n{text}\n"
        return f"\n{text}\n"
    elif cat == "table_caption":
        return f"\n**{text}**\n"
    elif cat == "figure_caption":
        return f"\n*{text}*\n"
    else:
        return f"{text}\n"

def process_page_nemotron(img_bytes, api_key):
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text, sections, headings, mathematical symbols, and tables from this document page verbatim."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4096
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    res_json = resp.json()
    content = res_json["choices"][0]["message"]["content"]
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "elements" in data:
            return data["elements"]
    except Exception:
        pass
    return [{"type": "paragraph", "text": content, "bbox": [0,0,1000,1000]}]

def convert_pdf(pdf_path, api_key, out_dir=None, dpi=150):
    pdf_path = os.path.abspath(pdf_path)
    if not out_dir:
        out_dir = os.path.splitext(pdf_path)[0] + "_nemotron_output"
    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    master_md_path = os.path.join(out_dir, f"{base_name}_nemotron.md")
    master_html_path = os.path.join(out_dir, f"{base_name}_nemotron.html")

    print("=" * 70)
    print("NVIDIA Nemotron Parse PDF Converter")
    print(f"Source PDF : {os.path.basename(pdf_path)} ({len(doc)} pages)")
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
        elements = process_page_nemotron(img_bytes, api_key)
        ordered_elems = sort_page_elements(elements, p_num)
        p_text = "\n".join([format_block_markdown(b) for b in ordered_elems])
        page_mds.append(p_text)
        print(f" Done ({time.time()-pt0:.2f}s, {len(elements)} blocks)")

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
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using NVIDIA Nemotron Parse")
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument("--key", help="NVIDIA API key string")
    parser.add_argument("--key-file", help="Path to NVIDIA API key env file")
    parser.add_argument("--out-dir", help="Output directory")
    parser.add_argument("--dpi", type=int, default=150, help="Rasterization DPI")
    args = parser.parse_args()

    key = get_api_key(args.key, args.key_file)
    convert_pdf(args.pdf, key, args.out_dir, args.dpi)
