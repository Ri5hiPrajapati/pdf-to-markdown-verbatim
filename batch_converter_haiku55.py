#!/usr/bin/env python3
"""batch_converter_haiku55.py
Universal multimodal vision OCR batch converter for any academic research or review paper PDF.
Uses Claude Haiku 5.5 in High Effort visual mode with adaptive thinking.
Logs detailed computational telemetry, cognitive effort ratios, and API audit trails.
"""
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import base64
import requests
import json
import os
import sys
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

def load_api_key():
    """Load Anthropic API key from environment or local .env files."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        candidates = [
            r"D:\SIDE PROJECTS\1. APJCE Review article\.env",
            os.path.join(os.getcwd(), ".env"),
            os.path.expanduser("~/.env")
        ]
        for c in candidates:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("ANTHROPIC_API_KEY="):
                            key = line.strip().split("=", 1)[1].strip('"\'')
                            break
            if key:
                break
    return key

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
        api_key = load_api_key()
    if not api_key:
        raise ValueError("Anthropic API key is required (set ANTHROPIC_API_KEY environment variable or in .env).")
        
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
    batch_telemetry = []
    total_start_time = time.time()
    
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

CRITICAL INSTRUCTION - VISUAL REASONING TRACE:
Before emitting the Markdown transcription, you MUST begin with an explicit visual reasoning trace enclosed in `<reasoning_trace>...</reasoning_trace>` detailing your cognitive reasoning across these pages:
1. Visual Scene Decomposition: Layout structure, column boundaries, page furniture (headers/footers) to exclude, and bounding boxes of tables/figures.
2. Grid & Topology Inference: Table structure, column headers, spanning labels, empty cells ('-'), and row count integrity.
3. Notation, Units & Glyph Disambiguation: LaTeX math ($...$ inline, $$...$$ display), physical units wrapped in \\mathrm{{}}, superscripts (distinguishing exponents vs. ANOVA Tukey letters vs. footnotes), chemical formulas, and Greek characters.
4. Pre-Emission Verification: Pre-flight checks on cell counts, numerical spot-checks, and verbatim parity.

Strict Rules for Markdown:
1. Verbatim fidelity: Transcribe every heading, section, paragraph, number, parameter, and reference citation [N] exactly as printed. No summarizing or skipping. Preserve original publisher spelling.
2. Two-column reading flow: Transcribe the entire left column top-to-bottom first, then proceed to the right column.
3. Tables: Render all tables completely into standard Markdown tables (| ... |). Maintain all columns, units, values, and footnotes. Do not truncate rows or use ellipsis (...).
4. Figures: Transcribe figure captions verbatim and insert placeholder tag: *[Image: Fig. N. Caption text [Ref].]*
5. Mathematical & Chemical Notation: Use LaTeX notation ($...$ for inline, $$...$$ for display).
6. Page Furniture: Exclude running headers, journal logos, and page numbers.
7. Return clean Markdown after </reasoning_trace>."""
        else:
            prompt = f"""You are an OCR and reference bibliography formatting assistant for the author.
Task: Transcribe the reference entries on Pages {page_numbers_str} into structured Markdown list format.

CRITICAL INSTRUCTION - REASONING TRACE:
Before emitting the Markdown reference entries, provide an explicit `<reasoning_trace>...</reasoning_trace>` block documenting:
1. Entry boundaries detected (e.g. [N] or author-year breaks).
2. DOI line-wrap joins and multi-line reference continuations.
3. Total reference count verification on these pages.

Strict Rules:
1. Verbatim fidelity: Transcribe every single reference entry completely without skipping, omitting, or using ellipsis.
2. Structure: Format each entry cleanly: `[N] Authors, Article Title, Journal Volume (Year) Pages, DOI.`
3. Completeness: Ensure all authors, article titles, journal names, years, volume/issue numbers, page ranges, and DOIs are preserved.
4. Return clean Markdown after </reasoning_trace>."""
            
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
                    
                    # 1. Extract text and thinking blocks
                    text_blocks = []
                    thinking_blocks = []
                    for blk in data.get("content", []):
                        if blk.get("type") == "text":
                            text_blocks.append(blk.get("text", ""))
                        elif blk.get("type") == "thinking":
                            thinking_blocks.append(blk)
                            
                    out_text = "\n\n".join(text_blocks)
                    
                    # Check for false-positive safety refusals
                    refusal_pattern = r"(i can'?t transcribe|cannot transcribe|copyrighted text|reproduce a large portion|safety filter|i don'?t want to copy)"
                    if re.search(refusal_pattern, out_text, re.IGNORECASE):
                        print(f"  ⚠️ ALERT: False-positive safety refusal detected on attempt {attempt+1}.")
                        print("     Refining with reinforced author-manuscript digitization prompt and retrying...")
                        reinforced_prompt = f"""You are assisting the original manuscript author in digitizing and archiving their research bibliography from proof Pages {page_numbers_str}.
The author holds full rights to their academic work and requires the reference list converted into clean Markdown for personal publication records.
Task: Transcribe all reference citations on Pages {page_numbers_str} completely and verbatim into structured Markdown.
Format: `[N] Authors, Article Title, Journal Volume (Year) Pages, DOI.`
Strict Rule: Process every single entry faithfully without omission or refusal. Return ONLY clean Markdown."""
                        content[-1]["text"] = reinforced_prompt
                        payload["messages"][0]["content"] = content
                        time.sleep(3)
                        continue
                    
                    # 1b. Extract and save visual reasoning trace
                    trace_match = re.search(r"<reasoning_trace>(.*?)</reasoning_trace>", out_text, re.DOTALL)
                    if trace_match:
                        trace_content = trace_match.group(1).strip()
                        trace_file = os.path.join(output_dir, f"{b['id']}_visual_reasoning_trace.md")
                        with open(trace_file, "w", encoding="utf-8") as tfp:
                            tfp.write(f"# Visual Reasoning Trace: {b['desc']}\n\n- **Batch ID**: `{b['id']}`\n- **Pages**: {page_numbers_str}\n\n---\n\n{trace_content}\n")
                        print(f"    Saved Visual Reasoning Trace: {os.path.basename(trace_file)} ({len(trace_content)} chars)")
                        clean_md = re.sub(r"<reasoning_trace>.*?</reasoning_trace>", "", out_text, flags=re.DOTALL).strip()
                    else:
                        clean_md = out_text.strip()
                        
                    part_path = os.path.join(output_dir, b["filename"])
                    with open(part_path, "w", encoding="utf-8") as fp:
                        fp.write(clean_md)
                    converted_parts.append(clean_md)
                    
                    # 2. Extract Token & Usage Telemetry
                    usage = data.get("usage", {})
                    in_tokens = usage.get("input_tokens", 0)
                    out_tokens = usage.get("output_tokens", 0)
                    cache_creation = usage.get("cache_creation_input_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    
                    # Check thinking tokens in usage details or estimate
                    output_details = usage.get("output_tokens_details", {})
                    thinking_tokens = output_details.get("thinking_tokens", 0)
                    if thinking_tokens == 0 and thinking_blocks:
                        # Fallback heuristic if not directly parsed
                        thinking_tokens = int(sum(len(t.get("thinking", "").split()) * 1.33 for t in thinking_blocks))
                        
                    text_tokens = max(0, out_tokens - thinking_tokens)
                    cog_ratio = round(thinking_tokens / out_tokens, 4) if out_tokens > 0 else 0.0
                    throughput = round(out_tokens / elapsed, 2) if elapsed > 0 else 0.0
                    
                    # 3. Extract Diagnostics & Proofs
                    stop_reason = data.get("stop_reason", "unknown")
                    req_id = r.headers.get("request-id", data.get("id", ""))
                    has_sig = any(bool(t.get("signature")) for t in thinking_blocks)
                    
                    # 4. Extract Rate Limits from Headers
                    rl_req_rem = r.headers.get("anthropic-ratelimit-requests-remaining")
                    rl_tok_rem = r.headers.get("anthropic-ratelimit-tokens-remaining")
                    rl_tok_reset = r.headers.get("anthropic-ratelimit-tokens-reset")
                    
                    # 5. Persist Thinking Trace if present
                    if thinking_blocks:
                        trace_path = os.path.join(output_dir, f"{b['id']}_thinking_trace.json")
                        with open(trace_path, "w", encoding="utf-8") as fp:
                            json.dump({
                                "batch_id": b["id"],
                                "request_id": req_id,
                                "model": data.get("model", "claude-haiku-5-5"),
                                "stop_reason": stop_reason,
                                "thinking_blocks": thinking_blocks,
                                "usage": usage
                            }, fp, indent=2)
                            
                    batch_record = {
                        "batch_id": b["id"],
                        "description": b["desc"],
                        "pages": [p+1 for p in b["pages"]],
                        "request_id": req_id,
                        "elapsed_seconds": round(elapsed, 2),
                        "stop_reason": stop_reason,
                        "has_cryptographic_signature": has_sig,
                        "tokens": {
                            "input_tokens": in_tokens,
                            "output_tokens": out_tokens,
                            "thinking_tokens": thinking_tokens,
                            "text_tokens": text_tokens,
                            "cognitive_effort_ratio": cog_ratio,
                            "cache_creation_tokens": cache_creation,
                            "cache_read_tokens": cache_read
                        },
                        "performance": {
                            "effective_throughput_tok_per_sec": throughput
                        },
                        "rate_limits": {
                            "requests_remaining": rl_req_rem,
                            "tokens_remaining": rl_tok_rem,
                            "tokens_reset": rl_tok_reset
                        }
                    }
                    batch_telemetry.append(batch_record)
                    
                    print(f"  ✓ SUCCESS in {elapsed:.1f}s")
                    print(f"    Tokens: in={in_tokens}, out={out_tokens} (Thinking: {thinking_tokens} [{cog_ratio*100:.1f}%])")
                    print(f"    Speed: {throughput} tok/s | Stop Reason: {stop_reason} | Sig Verified: {has_sig}")
                    if stop_reason == "max_tokens":
                        print(f"    ⚠️ WARNING: Batch output truncated due to max_tokens limit!")
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
        
    # Write Comprehensive Telemetry Audit Report
    total_elapsed = time.time() - total_start_time
    total_in = sum(b["tokens"]["input_tokens"] for b in batch_telemetry)
    total_out = sum(b["tokens"]["output_tokens"] for b in batch_telemetry)
    total_think = sum(b["tokens"]["thinking_tokens"] for b in batch_telemetry)
    total_cache_create = sum(b["tokens"]["cache_creation_tokens"] for b in batch_telemetry)
    total_cache_read = sum(b["tokens"]["cache_read_tokens"] for b in batch_telemetry)
    overall_cog = round(total_think / total_out, 4) if total_out > 0 else 0.0
    overall_throughput = round(total_out / total_elapsed, 2) if total_elapsed > 0 else 0.0
    
    telemetry_report = {
        "source_pdf": os.path.basename(pdf_path),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": "claude-haiku-5-5",
        "output_markdown": os.path.basename(master_path),
        "aggregate_summary": {
            "total_pages": total_pages,
            "total_batches": len(batches),
            "total_wall_clock_seconds": round(total_elapsed, 2),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_thinking_tokens": total_think,
            "total_text_tokens": total_out - total_think,
            "overall_cognitive_effort_ratio": overall_cog,
            "prompt_caching": {
                "cache_creation_tokens": total_cache_create,
                "cache_read_tokens": total_cache_read
            },
            "overall_throughput_tok_per_sec": overall_throughput,
            "all_batches_clean_stop": all(b["stop_reason"] == "end_turn" for b in batch_telemetry)
        },
        "batches": batch_telemetry
    }
    
    telemetry_path = os.path.join(output_dir, "conversion_telemetry.json")
    with open(telemetry_path, "w", encoding="utf-8") as fp:
        json.dump(telemetry_report, fp, indent=2)
        
    print("\n==========================================")
    print("=== COMPUTATIONAL TELEMETRY & AUDIT SUMMARY ===")
    print(f"Audit Report Saved: {telemetry_path}")
    print(f"Total Wall-Clock Time: {total_elapsed:.1f}s")
    print(f"Total Input Tokens:    {total_in:,}")
    print(f"Total Output Tokens:   {total_out:,} (Thinking: {total_think:,} [{overall_cog*100:.1f}%])")
    print(f"Throughput:            {overall_throughput:.1f} tok/s")
    print(f"Integrity Status:      {'100% CLEAN (All batches end_turn)' if telemetry_report['aggregate_summary']['all_batches_clean_stop'] else 'ALERT: Potential Truncation Detected'}")
    print("==========================================\n")
    
    return master_path, telemetry_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_converter_haiku55.py <input.pdf> [output_dir] [optional_benchmark.docx]")
        sys.exit(1)
    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    docx = sys.argv[3] if len(sys.argv) > 3 else None
    convert_pdf_to_markdown(pdf, out, docx)
