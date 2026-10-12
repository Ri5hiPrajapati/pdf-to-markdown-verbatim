#!/usr/bin/env python3
"""batch_converter_haiku55.py
Multimodal vision OCR conversion of academic PDFs to verbatim Markdown using Claude Haiku 5.5 High Effort.
"""
import fitz  # PyMuPDF
import base64
import requests
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

def convert_pdf_to_markdown(pdf_path, docx_benchmark_path, api_key, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Loaded PDF: {pdf_path} ({total_pages} pages)")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    batches = [
        {
            "name": "section_1_carotenoids.md",
            "pages": [0, 1, 2, 3],
            "desc": "Front matter, Section 1 Intro, Section 2 Carotenoids, Table 1, Fig 1"
        },
        {
            "name": "section_2_anthocyanins.md",
            "pages": [4, 5, 6],
            "desc": "Section 2.5 Stability, Table 2, Section 3 Anthocyanins, Table 3"
        },
        {
            "name": "section_3_betanins_conclusions.md",
            "pages": [7, 8, 9, 10],
            "desc": "Section 3.4-3.5, Table 4, Section 4 Betanins, Table 5, Table 6, Fig 3, Section 5 Conclusions"
        },
        {
            "name": "section_4a_refs.md",
            "pages": [11, 12],
            "desc": "References [1] to [66]"
        },
        {
            "name": "section_4b_refs.md",
            "pages": [13, 14],
            "desc": "References [67] to [149]"
        }
    ]
    
    converted_parts = []
    
    for idx, b in enumerate(batches):
        print(f"\n--- Processing Batch {idx+1}/{len(batches)}: {b['desc']} ---")
        content = []
        for pno in b["pages"]:
            pix = doc[pno].get_pixmap(dpi=150)
            b64_img = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64_img}
            })
            
        prompt = f"""You are an OCR and document layout parsing engine assisting the author in digitizing their scientific paper into structured Markdown format.
Task: Perform complete, high-fidelity OCR transcription of Pages {[p+1 for p in b['pages']]} into clean Markdown.
Content to transcribe: {b['desc']}.
Strict Rules:
- Verbatim fidelity: transcribe every word, number, unit, and reference citation [N] exactly as printed.
- Follow two-column reading flow.
- Reconstruct all tables completely in standard Markdown format without truncating rows.
- Output clean Markdown only."""
        
        content.append({"type": "text", "text": prompt})
        
        payload = {
            "model": "claude-haiku-5-5",
            "max_tokens": 64000,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
            "messages": [{"role": "user", "content": content}]
        }
        
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=300)
        if r.status_code == 200:
            data = r.json()
            text_blocks = [blk.get("text", "") for blk in data.get("content", []) if blk.get("type") == "text"]
            out_text = "\n\n".join(text_blocks)
            part_path = os.path.join(output_dir, b["name"])
            with open(part_path, "w", encoding="utf-8") as fp:
                fp.write(out_text)
            converted_parts.append(out_text)
            print(f"Batch {idx+1} completed: {len(out_text)} chars saved to {b['name']}")
        else:
            print(f"Error in Batch {idx+1}: {r.status_code} - {r.text[:200]}")
            sys.exit(1)
            
    # Stitch Master File
    master_text = "\n\n".join(converted_parts)
    master_path = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_path))[0] + ".md")
    with open(master_path, "w", encoding="utf-8") as fp:
        fp.write(master_text)
    print(f"\nMaster Markdown Created: {master_path} ({len(master_text)} characters)")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python batch_converter_haiku55.py <input.pdf> <benchmark.docx> <output_dir>")
        sys.exit(1)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    convert_pdf_to_markdown(sys.argv[1], sys.argv[2], api_key, sys.argv[3])
