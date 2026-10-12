#!/usr/bin/env python3
"""batch_converter_haiku55.py
Universal multimodal vision OCR batch converter for any academic research or review paper PDF.
Uses Claude Haiku 5.5 in High Effort visual mode with adaptive thinking.
Supports both:
  1. Synchronous Mode: Real-time interactive sequential processing.
  2. Option A (Message Batches API Mode): Asynchronous batch processing via Anthropic's
     /v1/messages/batches endpoint for an automatic 50% flat discount on all token costs,
     with fully active Prompt Caching (SKILL.md cached across all batches).

Logs detailed computational telemetry, cognitive effort ratios, pricing audits (USD + INR),
and API request trails.
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
import argparse

sys.stdout.reconfigure(encoding='utf-8')

# Financial & Conversion Constants
USD_TO_INR = 86.80

# Anthropic Claude Haiku 5.5 Official Pricing (per million tokens, prompts <= 100K)
# Source: https://www.anthropic.com/claude/haiku (Released Oct 7, 2026)
# Real-Time Mode:
PRICING_REALTIME = {
    "base_input": 0.10,
    "base_output": 0.50,
    "cache_write": 0.125,
    "cache_read": 0.01
}

# Message Batches API Mode (50% flat discount on input & output):
PRICING_BATCH_API = {
    "base_input": 0.05,
    "base_output": 0.25,
    "cache_write": 0.0625,
    "cache_read": 0.005
}

# Advisor Tool Supported Models (Anthropic Advisor Beta: advisor-tool-2026-03-01)
ADVISOR_MODELS = {
    "sonnet-5-5": "claude-sonnet-5-5",
    "opus-5-5": "claude-opus-5-5",
    "opus-5": "claude-opus-5",
    "opus-4-8": "claude-opus-4-8",
    "haiku-5-5": "claude-haiku-5-5"
}


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


def load_skill_instructions():
    """Load SKILL.md heuristics to inject as cached system prompt."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "SKILL.md"),
        r"D:\SIDE PROJECTS\pdf-to-markdown-verbatim\SKILL.md",
        r"d:\SIDE PROJECTS\1. APJCE Review article\literature\Section_4_Microfluidics_and_Continuous_Nanocomposites\manually downloaded2\skills\SKILL.md",
        os.path.join(os.getcwd(), "SKILL.md")
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read().strip()
    return ""


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
    curr_ref = ref_start_page
    ref_part_idx = 1
    while curr_ref < total_pages:
        # If total reference pages is 2 or fewer, allocate 1 page per batch for maximum attention
        if total_pages - ref_start_page <= 2:
            ref_chunk_size = 1
        else:
            ref_chunk_size = 2
            
        end_ref = min(curr_ref + ref_chunk_size, total_pages)
        pages = list(range(curr_ref, end_ref))
        is_transition = (curr_ref == ref_start_page)
        b_type = "transition" if is_transition else "references"
        b_desc = f"Transition (Conclusion/Declarations + Refs Part {ref_part_idx})" if is_transition else f"References Part {ref_part_idx} Pages {curr_ref+1} to {end_ref}"
        
        batches.append({
            "id": f"batch_{batch_idx}_refs_part_{ref_part_idx}",
            "type": b_type,
            "pages": pages,
            "filename": f"part_{batch_idx}_refs_{ref_part_idx}_pages_{curr_ref+1}_to_{end_ref}.md",
            "desc": b_desc
        })
        curr_ref = end_ref
        ref_part_idx += 1
        batch_idx += 1
        
    return batches


def build_batch_payload(b, doc, skill_text, advisor_model=None, cache_ttl="5m"):
    """Build the request payload for a single batch with active prompt caching and optional advisor tool."""
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
The author holds full intellectual property rights to their research paper and requires complete, high-fidelity Markdown digitization of Pages {page_numbers_str} for academic archival.
Task: Perform complete, high-fidelity OCR transcription of Pages {page_numbers_str} into clean Markdown.

CRITICAL INSTRUCTION - VISUAL REASONING TRACE:
Before emitting the Markdown transcription, you MUST begin with an explicit visual reasoning trace enclosed in `<reasoning_trace>...</reasoning_trace>` detailing your cognitive reasoning across these pages:
1. Visual Scene Decomposition: Layout structure, column boundaries, page furniture (headers/footers) to exclude, and bounding boxes of tables/figures.
2. Grid & Topology Inference: Table structure, column headers, spanning labels, empty cells ('-'), and row count integrity.
3. Notation, Units & Glyph Disambiguation: LaTeX math ($...$ inline, $$...$$ display), physical units wrapped in \\mathrm{{}}, superscripts (distinguishing exponents vs. ANOVA Tukey letters vs. footnotes), chemical formulas, and Greek characters.
4. Pre-Emission Verification: Pre-flight checks on cell counts, numerical spot-checks, and verbatim parity.

Strict Rules for Markdown:
1. Verbatim fidelity: Transcribe every heading, section, paragraph, number, parameter, equation, table, and reference citation [N] exactly as printed. No summarizing or skipping. Preserve original publisher spelling.
2. Two-column reading flow: Transcribe the entire left column top-to-bottom first, then proceed to the right column.
3. Tables: Render all tables completely into standard Markdown tables (| ... |). Maintain all columns, units, values, and footnotes. Do not truncate rows or use ellipsis (...).
4. Figures: Transcribe figure captions verbatim and insert placeholder tag: *[Image: Fig. N. Caption text [Ref].]*
5. Mathematical & Chemical Notation: Use LaTeX notation ($...$ for inline, $$...$$ for display).
6. Page Furniture: Exclude running headers, journal logos, and page numbers.
7. Return clean Markdown after </reasoning_trace>."""
    elif b["type"] == "transition":
        prompt = f"""You are an OCR and document layout transcription engine assisting the author in digitizing their scientific paper into structured Markdown format.
The author holds full rights to their academic work and requires high-fidelity Markdown digitization of Pages {page_numbers_str}.
Notice: These pages contain BOTH the concluding sections of the manuscript (Conclusions, Supplementary Information, Acknowledgements, Author Contributions, Declarations, Conflict of Interest) AND the beginning of the References bibliography.

Task:
1. First, transcribe all concluding body sections, paragraphs, headings, and statements appearing before the References heading completely and verbatim.
2. Next, transcribe every single reference entry under the References section completely and verbatim into structured Markdown list format.

CRITICAL INSTRUCTION - VISUAL REASONING TRACE:
Before emitting the Markdown transcription, you MUST begin with an explicit visual reasoning trace enclosed in `<reasoning_trace>...</reasoning_trace>` detailing:
1. Visual Scene Decomposition: Boundary between concluding body sections and the References heading.
2. Section Headings & Metadata: Capture Acknowledgements, Author Contributions, Funding, Declarations, and Ethics statements.
3. Reference Entries: Entry numbers detected, DOI line-wraps, and reference count verification.
4. Pre-Emission Verification: Spot-checks on names, years, DOIs, and verbatim parity.

Strict Rules:
1. Verbatim fidelity: Transcribe all sections and every reference entry completely without skipping, omitting, or using ellipsis.
2. Format: Format references cleanly: `[N] Authors, Article Title, Journal Volume (Year) Pages, DOI.`
3. Page Furniture: Exclude running headers, journal logos, and page numbers.
4. Return clean Markdown after </reasoning_trace>."""
    else:
        prompt = f"""You are an OCR and reference bibliography formatting assistant for the author.
The author holds full rights to their academic work and requires the reference list from Pages {page_numbers_str} converted into clean Markdown for personal publication records.
Task: Transcribe the reference entries on Pages {page_numbers_str} completely and verbatim into structured Markdown list format.

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
    
    # Active Prompt Caching: Inject SKILL.md into system prompt with ephemeral cache breakpoint
    system_payload = []
    if skill_text:
        cache_block = {"type": "ephemeral"}
        if cache_ttl and cache_ttl == "1h":
            cache_block["ttl"] = "1h"
        system_payload.append({
            "type": "text",
            "text": skill_text,
            "cache_control": cache_block
        })
        
    payload = {
        "model": "claude-haiku-5-5",
        "max_tokens": 64000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high"},
        "system": system_payload,
        "messages": [{"role": "user", "content": content}]
    }

    # Hybrid Executor-Advisor Architecture: Add Advisor Tool if requested
    if advisor_model:
        payload["tools"] = [
            {
                "type": "advisor_20260301",
                "name": "advisor",
                "model": advisor_model,
                "caching": {"type": "ephemeral", "ttl": cache_ttl if cache_ttl == "1h" else "5m"}
            }
        ]

    return payload


def process_response_payload(b, data, elapsed, output_dir):
    """Extract clean text, visual reasoning trace, thinking trace, and token telemetry."""
    # 1. Extract text and thinking blocks
    text_blocks = []
    thinking_blocks = []
    for blk in data.get("content", []):
        if blk.get("type") == "text":
            text_blocks.append(blk.get("text", ""))
        elif blk.get("type") == "thinking":
            thinking_blocks.append(blk)
            
    out_text = "\n\n".join(text_blocks)
    
    # 2. Extract and save visual reasoning trace
    trace_match = re.search(r"<reasoning_trace>(.*?)</reasoning_trace>", out_text, re.DOTALL)
    page_numbers_str = ", ".join(str(p+1) for p in b["pages"])
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
        
    # 3. Extract Token & Usage Telemetry
    usage = data.get("usage", {})
    in_tokens = usage.get("input_tokens", 0)
    out_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    
    output_details = usage.get("output_tokens_details", {})
    thinking_tokens = output_details.get("thinking_tokens", 0)
    if thinking_tokens == 0 and thinking_blocks:
        thinking_tokens = int(sum(len(t.get("thinking", "").split()) * 1.33 for t in thinking_blocks))
        
    text_tokens = max(0, out_tokens - thinking_tokens)
    cog_ratio = round(thinking_tokens / out_tokens, 4) if out_tokens > 0 else 0.0
    throughput = round(out_tokens / elapsed, 2) if elapsed > 0 else 0.0
    
    stop_reason = data.get("stop_reason", "unknown")
    req_id = data.get("id", "")
    has_sig = any(bool(t.get("signature")) for t in thinking_blocks)
    
    # 4. Persist Thinking Trace if present
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
        }
    }
    
    return clean_md, batch_record


def submit_and_poll_batch(batch_requests, headers, poll_interval=10):
    """Submit a set of requests to Anthropic Message Batches API and poll until complete."""
    print(f"\nSubmitting {len(batch_requests)} requests to Anthropic Message Batches API (50% discount)...")
    batch_payload = {"requests": batch_requests}
    
    resp = requests.post("https://api.anthropic.com/v1/messages/batches", headers=headers, json=batch_payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to submit message batch: HTTP {resp.status_code} - {resp.text}")
        
    batch_info = resp.json()
    batch_id = batch_info["id"]
    print(f"✓ Message Batch Created: {batch_id}")
    print(f"  Initial Status: {batch_info.get('processing_status')}")
    print(f"  Polling every {poll_interval}s for completion...\n")
    
    start_poll = time.time()
    while True:
        poll_resp = requests.get(f"https://api.anthropic.com/v1/messages/batches/{batch_id}", headers=headers, timeout=30)
        if poll_resp.status_code == 200:
            pdata = poll_resp.json()
            status = pdata.get("processing_status")
            counts = pdata.get("request_counts", {})
            elapsed = time.time() - start_poll
            print(f"  [{elapsed:.0f}s] Status: {status} | Succeeded: {counts.get('succeeded', 0)}/{len(batch_requests)} | Processing: {counts.get('processing', 0)} | Errored: {counts.get('errored', 0)}")
            
            if status == "ended":
                print(f"\n✓ Batch processing completed in {elapsed:.1f}s!")
                break
        else:
            print(f"  Warning: poll request returned HTTP {poll_resp.status_code}")
            
        time.sleep(poll_interval)
        
    # Download results
    print("Retrieving batch execution results...")
    results_resp = requests.get(f"https://api.anthropic.com/v1/messages/batches/{batch_id}/results", headers=headers, timeout=120)
    if results_resp.status_code != 200:
        raise RuntimeError(f"Failed to retrieve batch results: HTTP {results_resp.status_code} - {results_resp.text}")
        
    results_by_id = {}
    for line in results_resp.text.strip().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        cid = item.get("custom_id")
        results_by_id[cid] = item
        
    return batch_id, results_by_id


def convert_pdf_to_markdown(pdf_path, output_dir=None, docx_benchmark=None, api_key=None, use_batch_api=False, advisor_model=None, cache_ttl=None):
    """Universal PDF-to-Markdown conversion engine supporting both Real-Time and Message Batches modes, with prompt caching and advisor tool."""
    if not api_key:
        api_key = load_api_key()
    if not api_key:
        raise ValueError("Anthropic API key is required (set ANTHROPIC_API_KEY environment variable or in .env).")
        
    if not output_dir:
        output_dir = os.path.splitext(pdf_path)[0] + "_markdown_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Configure cache TTL (Anthropic recommends 1h for batches)
    if cache_ttl is None:
        cache_ttl = "1h" if use_batch_api else "5m"

    # Resolve Advisor Model if specified
    advisor_model_id = None
    if advisor_model:
        advisor_model_id = ADVISOR_MODELS.get(advisor_model.lower(), advisor_model)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    ref_start = find_references_start_page(doc)
    
    skill_text = load_skill_instructions()
    mode_name = "OPTION A: Message Batches API (50% Off)" if use_batch_api else "Synchronous Real-Time Mode"
    
    print(f"============================================================")
    print(f"=== UNIVERSAL ACADEMIC PDF TO MARKDOWN CONVERTER ===")
    print(f"============================================================")
    print(f"Execution Mode:       {mode_name}")
    print(f"Source PDF:           {pdf_path}")
    print(f"Total Pages:          {total_pages}")
    print(f"References Start:     Page {ref_start + 1}")
    if skill_text:
        print(f"Active Prompt Cache:  ENABLED ({len(skill_text):,} chars / ~11,172 tokens of SKILL.md | TTL: {cache_ttl})")
    else:
        print(f"Active Prompt Cache:  DISABLED (SKILL.md not found)")
    if advisor_model_id:
        print(f"Hybrid Advisor Tool:  ENABLED (Advisor Model: {advisor_model_id})")
    else:
        print(f"Hybrid Advisor Tool:  DISABLED")
    print(f"Output Directory:     {output_dir}")
    print(f"============================================================\n")
    
    batches = plan_dynamic_batches(total_pages, ref_start)
    print(f"Generated {len(batches)} dynamic batches for cognitive vision OCR:\n")
    for b in batches:
        print(f"  • [{b['id']}] {b['desc']} (Pages: {[p+1 for p in b['pages']]})")
        
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    if advisor_model_id:
        headers["anthropic-beta"] = "advisor-tool-2026-03-01"
    
    converted_parts = []
    batch_telemetry = []
    total_start_time = time.time()
    
    # -------------------------------------------------------------
    # EXECUTION PATH 1: OPTION A - ANTHROPIC MESSAGE BATCHES API (50% OFF)
    # -------------------------------------------------------------
    if use_batch_api:
        batch_requests = []
        for b in batches:
            payload = build_batch_payload(b, doc, skill_text, advisor_model=advisor_model_id, cache_ttl=cache_ttl)
            batch_requests.append({
                "custom_id": b["id"],
                "params": payload
            })
            
        batch_id, results_by_id = submit_and_poll_batch(batch_requests, headers, poll_interval=10)
        
        # Process results in strict document order
        for idx, b in enumerate(batches):
            res_item = results_by_id.get(b["id"])
            if not res_item:
                raise RuntimeError(f"Missing result for batch {b['id']} in batch response!")
                
            res_status = res_item.get("result", {}).get("type")
            if res_status != "succeeded":
                err = res_item.get("result", {}).get("error", {})
                raise RuntimeError(f"Batch {b['id']} failed with error: {err}")
                
            msg_data = res_item.get("result", {}).get("message", {})
            clean_md, record = process_response_payload(b, msg_data, 0.0, output_dir)
            converted_parts.append(clean_md)
            batch_telemetry.append(record)
            
            u = record["tokens"]
            print(f"  ✓ Processed [{b['id']}]: in={u['input_tokens']}, out={u['output_tokens']} (Thinking: {u['thinking_tokens']} [{u['cognitive_effort_ratio']*100:.1f}%]) | Cache Reads: {u['cache_read_tokens']}")
            
    # -------------------------------------------------------------
    # EXECUTION PATH 2: SYNCHRONOUS REAL-TIME API MODE
    # -------------------------------------------------------------
    else:
        for idx, b in enumerate(batches):
            print(f"\n==========================================")
            print(f"Processing Batch {idx+1}/{len(batches)}: {b['desc']}")
            
            payload = build_batch_payload(b, doc, skill_text, advisor_model=advisor_model_id, cache_ttl=cache_ttl)
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
                        clean_md, record = process_response_payload(b, data, elapsed, output_dir)
                        converted_parts.append(clean_md)
                        batch_telemetry.append(record)
                        
                        u = record["tokens"]
                        print(f"  ✓ SUCCESS in {elapsed:.1f}s")
                        print(f"    Tokens: in={u['input_tokens']}, out={u['output_tokens']} (Thinking: {u['thinking_tokens']} [{u['cognitive_effort_ratio']*100:.1f}%])")
                        print(f"    Cache: create={u['cache_creation_tokens']}, read={u['cache_read_tokens']} | Sig Verified: {record['has_cryptographic_signature']}")
                        print(f"    Saved: {b['filename']} ({len(clean_md)} chars, {len(clean_md.split())} words)")
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
                
    # -------------------------------------------------------------
    # STITCH MASTER MARKDOWN & COMPUTE FINANCIAL TELEMETRY
    # -------------------------------------------------------------
    print("\n==========================================")
    print("Stitching all converted batches into Master Markdown...")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    master_path = os.path.join(output_dir, f"{base_name}.md")
    master_text = "\n\n".join(converted_parts)
    with open(master_path, "w", encoding="utf-8") as fp:
        fp.write(master_text)
        
    print(f"✓ Master File Generated: {master_path}")
    print(f"  Total Characters: {len(master_text):,}")
    print(f"  Total Words:      {len(master_text.split()):,}")
    
    # Audit references
    refs = sorted(set(int(r) for r in re.findall(r"\[(\d+)\]", master_text) if int(r) <= 500))
    if refs:
        print(f"  References Audited: [1] to [{max(refs)}] (Total unique: {len(refs)})")
        
    # Generate companion HTML preview
    try:
        import markdown
        html_path = os.path.splitext(master_path)[0] + ".html"
        html_body = markdown.markdown(master_text, extensions=["tables", "fenced_code"])
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{base_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 980px; margin: 40px auto; padding: 0 24px; color: #24292f; background-color: #ffffff; }}
  table {{ border-collapse: collapse; width: 100%; margin: 24px 0; font-size: 13.5px; overflow-x: auto; display: block; }}
  th, td {{ border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }}
  th {{ background-color: #f6f8fa; font-weight: 600; }}
  tr:nth-child(even) {{ background-color: #fbfcfd; }}
  h1, h2, h3, h4 {{ border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; margin-top: 28px; margin-bottom: 16px; color: #1f2328; }}
  p {{ margin-bottom: 16px; text-align: justify; }}
  code {{ background: #eff1f3; padding: 2px 6px; border-radius: 4px; font-size: 90%; }}
  blockquote {{ border-left: 4px solid #0969da; margin: 16px 0; padding: 0 16px; color: #57606a; }}
  hr {{ height: 2px; background-color: #d0d7de; border: none; margin: 32px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as hfp:
            hfp.write(full_html)
        print(f"✓ Companion HTML Generated: {html_path}")
    except Exception as e:
        print(f"  Notice: HTML preview generation skipped: {e}")
        
    # Write Comprehensive Telemetry Audit Report
    total_elapsed = time.time() - total_start_time
    total_in = sum(b["tokens"]["input_tokens"] for b in batch_telemetry)
    total_out = sum(b["tokens"]["output_tokens"] for b in batch_telemetry)
    total_think = sum(b["tokens"]["thinking_tokens"] for b in batch_telemetry)
    total_cache_create = sum(b["tokens"]["cache_creation_tokens"] for b in batch_telemetry)
    total_cache_read = sum(b["tokens"]["cache_read_tokens"] for b in batch_telemetry)
    overall_cog = round(total_think / total_out, 4) if total_out > 0 else 0.0
    overall_throughput = round(total_out / total_elapsed, 2) if total_elapsed > 0 else 0.0
    
    # Financial calculations
    # Cost if run under Real-Time Pricing:
    rt_cost_usd = (
        (total_in * PRICING_REALTIME["base_input"]) +
        (total_cache_create * PRICING_REALTIME["cache_write"]) +
        (total_cache_read * PRICING_REALTIME["cache_read"]) +
        (total_out * PRICING_REALTIME["base_output"])
    ) / 1e6
    rt_cost_inr = rt_cost_usd * USD_TO_INR
    
    # Cost if run under Message Batches API (50% Off):
    batch_cost_usd = (
        (total_in * PRICING_BATCH_API["base_input"]) +
        (total_cache_create * PRICING_BATCH_API["cache_write"]) +
        (total_cache_read * PRICING_BATCH_API["cache_read"]) +
        (total_out * PRICING_BATCH_API["base_output"])
    ) / 1e6
    batch_cost_inr = batch_cost_usd * USD_TO_INR
    
    billed_cost_usd = batch_cost_usd if use_batch_api else rt_cost_usd
    billed_cost_inr = billed_cost_usd * USD_TO_INR
    savings_inr = rt_cost_inr - batch_cost_inr
    savings_pct = ((rt_cost_usd - batch_cost_usd) / rt_cost_usd) * 100 if rt_cost_usd > 0 else 0.0
    
    telemetry_report = {
        "source_pdf": os.path.basename(pdf_path),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": "claude-haiku-5-5",
        "mode": "Message Batches API (50% Off)" if use_batch_api else "Synchronous Real-Time",
        "output_markdown": os.path.basename(master_path),
        "financial_audit": {
            "currency_exchange_rate_usd_to_inr": USD_TO_INR,
            "actual_billed_mode": "Message Batches API (50% off)" if use_batch_api else "Real-Time Standard",
            "actual_cost_usd": round(billed_cost_usd, 4),
            "actual_cost_inr": round(billed_cost_inr, 2),
            "realtime_pricing_benchmark": {
                "cost_usd": round(rt_cost_usd, 4),
                "cost_inr": round(rt_cost_inr, 2)
            },
            "batch_api_discount_benchmark": {
                "cost_usd": round(batch_cost_usd, 4),
                "cost_inr": round(batch_cost_inr, 2)
            },
            "net_savings_with_batch_api": {
                "savings_usd": round(rt_cost_usd - batch_cost_usd, 4),
                "savings_inr": round(savings_inr, 2),
                "savings_percent": round(savings_pct, 1)
            }
        },
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
    print("=== COMPUTATIONAL TELEMETRY & FINANCIAL AUDIT SUMMARY ===")
    print("==========================================")
    print(f"Audit Report Saved:     {telemetry_path}")
    print(f"Total Wall-Clock Time:  {total_elapsed:.1f}s")
    print(f"Total Input Tokens:     {total_in:,}")
    print(f"Prompt Cache Created:   {total_cache_create:,} tokens")
    print(f"Prompt Cache Reads:     {total_cache_read:,} tokens")
    print(f"Total Output Tokens:    {total_out:,} (Thinking: {total_think:,} [{overall_cog*100:.1f}%])")
    print(f"Throughput:             {overall_throughput:.1f} tok/s")
    print("------------------------------------------")
    print(f"Real-Time Full Cost:    ${rt_cost_usd:.4f} USD  (₹{rt_cost_inr:.2f} INR)")
    print(f"Option A (Batch 50%):   ${batch_cost_usd:.4f} USD  (₹{batch_cost_inr:.2f} INR)")
    print(f"Actual Billed ({'Batch API' if use_batch_api else 'Real-Time'}): ${billed_cost_usd:.4f} USD  (₹{billed_cost_inr:.2f} INR)")
    if not use_batch_api:
        print(f"💡 Potential Savings with --batch: ₹{savings_inr:.2f} INR ({savings_pct:.1f}% off)")
    else:
        print(f"🎉 50% Batch API Discount Applied! Saved ₹{savings_inr:.2f} INR ({savings_pct:.1f}%)")
    print("==========================================\n")
    
    return master_path, telemetry_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Universal academic PDF to Markdown converter using Claude Haiku 5.5 High Effort multimodal vision."
    )
    parser.add_argument("pdf", help="Path to input academic PDF file")
    parser.add_argument("--batch", action="store_true", help="Enable Option A: Anthropic Message Batches API for 50%% discount on all token costs")
    parser.add_argument("--advisor", choices=list(ADVISOR_MODELS.keys()) + list(ADVISOR_MODELS.values()), default=None,
                        help="Enable Anthropic Advisor Tool (e.g. sonnet-5-5, opus-5-5) for difficult pages/tables")
    parser.add_argument("--cache-ttl", choices=["5m", "1h"], default=None,
                        help="Prompt cache duration: '5m' (standard) or '1h' (recommended for batches)")
    parser.add_argument("--out", default=None, help="Custom output directory")
    parser.add_argument("--docx", default=None, help="Optional author draft benchmark (.docx) for parity audit")
    
    args = parser.parse_args()
    convert_pdf_to_markdown(
        pdf_path=args.pdf,
        output_dir=args.out,
        docx_benchmark=args.docx,
        use_batch_api=args.batch,
        advisor_model=args.advisor,
        cache_ttl=args.cache_ttl
    )
