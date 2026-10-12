#!/usr/bin/env python3
"""batch_converter_haiku55.py
Universal multimodal vision OCR batch converter for any academic research or review paper PDF.
Uses Claude Haiku 5.5 in High Effort visual mode with adaptive thinking.
"""
import fitz  # PyMuPDF
import base64
import requests
import json
import os
import sys
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

def find_references_start_page(doc):
    """Dynamically scan for the page where the reference section begins."""
    total = len(doc)
    # Search backwards from the end
    for pno in range(total - 1, -1, -1):
        text = doc[pno].get_text().lower()
        if re.search(r"\b(references|bibliography|literature cited)\b", text):
            # Check if previous page also has references
            prev_has_refs = False
            if pno > 0:
                prev_text = doc[pno - 1].get_text().lower()
                if re.search(r"\b(references|bibliography|literature cited)\b", prev_text):
                    prev_has_refs = True
            if not prev_has_refs:
                return pno
    return total  # No references section found

def plan_dynamic_batches(total_pages, ref_start_page):
    """Partition any paper into content-coherent body and reference batches."""
    batches = []
    
    # 1. Body pages (from page 0 to ref_start_page)
    body_chunk_size = 3  # 3 pages per batch is optimal for high-effort thinking
    curr = 0
    batch_idx = 1
    while curr < ref_start_page:
        end = min(curr + body_chunk_size, ref_start_page)
        # If only 1 page remains before references, merge it into current batch
        if ref_start_page - end == 1:
            end = ref_start_page
            
        pages = list(range(curr, end))
        batches.append({
            "id": f"batch_{batch_idx}_body",
            "type": "body",
            "pages": pages,
            "filename": f"part_{batch_idx}_pages_{curr+1}_to_{end}.md",
            "desc": f"Body Pages {curr+1} to {end}"
        })
        curr = end
        batch_idx += 1
        
    # 2. Reference pages (from ref_start_page to total_pages)
    ref_chunk_size = 2  # 2 pages per batch prevents token starvation on dense bibliographies
    curr_ref = ref_start_page
    ref_part_idx = 1
    while curr_ref < total_pages:
        end_ref = min(curr_ref + ref_chunk_size, total_pages)
        pages = list(range(curr_ref, end_ref))
        batches.append({
            "id": f"batch_{batch_idx}_refs_part_{ref_part_idx}",
            "type": "references",
            "pages": pages,
            "filename": f"part_{batch_idx}_refs_{ref_part_idx}_pages_{curr_ref+1}_to_{end_ref}.md",
            "desc": f"References Pages {curr_ref+1} to {end_ref}"
        })
        curr_ref = end_ref
        ref_part_idx += 1
        batch_idx += 1
        
    return batches

def convert_pdf_to_markdown(pdf_path, output_dir=None, docx_benchmark=None, api_key=None):
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API key is required (set ANTHROPIC_API_KEY environment variable).")
        
    if not output_dir:
        output_dir = os.path.splitext(pdf_path)[0] + "_markdown_output"
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    ref_start = find_references_start_page(doc)
    
    print(f"=== UNIVERSAL ACADEMIC PDF CONVERTER ===")
    print(f"Source PDF: {pdf_path}")
    print(f"Total Pages: {total_pages}")
    print(f"Reference Section Detected at Page: {ref_start + 1}")
    
    batches = plan_dynamic_batches(total_pages, ref_start)
    print(f"Generated {len(batches)} dynamic batches for high-effort processing:\n")
    for b in batches:
        print(f"  • {b['desc']} (Pages: {[p+1 for p in b['pages']]})")
        
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    converted_parts = []
    
    for idx, b in enumerate(batches):
        print(f"\n==========================================")
        print(f"Processing Batch {idx+1}/{len(batches)}: {b['desc']}")
        
        content = []
        for pno in b["pages"]:
            page = doc[pno]
            pix = page.get_pixmap(dpi=150)
            b64_img = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_img
                }
            })
            
        page_numbers_str = ", ".join(str(p+1) for p in b["pages"])
        
        if b["type"] == "body":
            prompt = f"""You are an OCR and document layout parsing engine assisting the author in digitizing their scientific paper into structured Markdown format.
Task: Perform complete, high-fidelity OCR transcription of Pages {page_numbers_str} into clean Markdown.

Strict Rules:
1. Verbatim fidelity: Transcribe every heading, section, paragraph, number, parameter, and reference citation [N] exactly as printed. No summarizing or skipping.
2. Two-column reading flow: Transcribe the entire left column top-to-bottom first, then proceed to the right column.
3. Tables: Render all tables completely into standard Markdown tables (| ... |). Maintain all columns, units, values, and footnotes. Do not truncate rows or use ellipsis (...).
4. Figures: Transcribe figure captions verbatim and insert placeholder tag: *[Image: Fig. N. Caption text [Ref].]*
5. Mathematical & Chemical Notation: Use LaTeX notation ($...$ for inline, $$...$$ for display).
6. Page Furniture: Exclude running headers, journal logos, and page numbers.
7. Return ONLY clean Markdown."""
        else:
            prompt = f"""You are an OCR and reference bibliography formatting assistant for the author.
Task: Transcribe the reference entries on Pages {page_numbers_str} into structured Markdown list format.

Strict Rules:
1. Verbatim fidelity: Transcribe every single reference entry completely without skipping, omitting, or using ellipsis.
2. Structure: Format each entry cleanly: `[N] Authors, Article Title, Journal Volume (Year) Pages, DOI.`
3. Completeness: Ensure all authors, article titles, journal names, years, volume/issue numbers, page ranges, and DOIs are preserved.
4. Return ONLY clean Markdown."""
            
        content.append({"type": "text", "text": prompt})
        
        payload = {
            "model": "claude-haiku-5-5",
            "max_tokens": 64000,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
            "messages": [{"role": "user", "content": content}]
        }
        
        print("  Sending visual OCR request to Claude Haiku 5.5 High Effort...")
        start_time = time.time()
        
        max_retries = 3
        success = False
        for attempt in range(max_retries):
            try:
                r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=300)
                elapsed = time.time() - start_time
                if r.status_code == 200:
                    data = r.json()
                    text_blocks = [blk.get("text", "") for blk in data.get("content", []) if blk.get("type") == "text"]
                    out_text = "\n\n".join(text_blocks)
                    
                    part_path = os.path.join(output_dir, b["filename"])
                    with open(part_path, "w", encoding="utf-8") as fp:
                        fp.write(out_text)
                    converted_parts.append(out_text)
                    
                    usage = data.get("usage", {})
                    print(f"  ✓ SUCCESS in {elapsed:.1f}s (Tokens: in={usage.get('input_tokens')}, out={usage.get('output_tokens')})")
                    print(f"    Saved: {b['filename']} ({len(out_text)} chars, {len(out_text.split())} words)")
                    success = True
                    break
                else:
                    print(f"  Attempt {attempt+1} failed: HTTP {r.status_code} - {r.text[:200]}")
                    time.sleep(5)
            except Exception as e:
                print(f"  Attempt {attempt+1} exception: {e}")
                time.sleep(5)
                
        if not success:
            print(f"Failed to convert batch {b['id']}. Aborting.")
            sys.exit(1)
            
    # Stitch Master Markdown
    print("\n==========================================")
    print("Stitching all converted batches into Master Markdown...")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    master_path = os.path.join(output_dir, f"{base_name}.md")
    master_text = "\n\n".join(converted_parts)
    with open(master_path, "w", encoding="utf-8") as fp:
        fp.write(master_text)
        
    print(f"✓ Master File Generated: {master_path}")
    print(f"  Total Characters: {len(master_text)}")
    print(f"  Total Words: {len(master_text.split())}")
    
    # Audit references
    refs = sorted(set(int(r) for r in re.findall(r"\[(\d+)\]", master_text) if int(r) <= 500))
    if refs:
        print(f"  References Audited: [1] to [{max(refs)}] (Total unique: {len(refs)})")
        
    return master_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_converter_haiku55.py <input.pdf> [output_dir] [optional_benchmark.docx]")
        sys.exit(1)
    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    docx = sys.argv[3] if len(sys.argv) > 3 else None
    convert_pdf_to_markdown(pdf, out, docx)
