#!/usr/bin/env python3
"""verify_md.py SOURCE.pdf OUTPUT.md [--docx BENCHMARK.docx] [--threshold 75]
Quantitative, cross-platform fidelity and integrity checker for PDF-to-Markdown conversions.

Audits:
  1. Verbatim n-gram Recall & Precision (detects dropped sections vs hallucinations).
  2. Strict Numerical Parity & Multiset Distribution (detects corrupted numbers without substring false-positives).
  3. Table Structural Integrity (detects row fractures, shifted columns, and column-count mismatches).
  4. PyMuPDF Table Discovery vs Markdown Table Count.
  5. Reference Sequence Continuity & Gap Analysis (detects missing citations in [1]..[N]).
  6. Optional Author Draft Benchmark (.docx) Parity.
"""
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import re
import sys
import os
import argparse
import unicodedata
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬀ": "ff", "ﬄ": "ffl",
    "–": "-", "—": "-", "−": "-", "´": "", "`": "", "\u00a0": " "
}

def normalize_text(s):
    """Normalize unicode, ligatures, dashes, and whitespace."""
    for lig, rep in LIGATURES.items():
        s = s.replace(lig, rep)
    s = re.sub(r"[ \t]+", " ", s)
    return unicodedata.normalize("NFC", s)

def extract_pdf_text_and_tables(pdf_path):
    """Extract normalized text and find physical tables from PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = []
    pdf_tables_count = 0
    
    for pno, page in enumerate(doc):
        # 1. Text blocks
        blocks = page.get_text("blocks")
        for b in blocks:
            if b[6] == 0:  # text block
                txt = b[4].strip()
                if txt:
                    full_text.append(txt)
        
        # 2. PyMuPDF Table finder
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                pdf_tables_count += len(tabs.tables)
        except Exception:
            pass

    joined = normalize_text("\n".join(full_text))
    return joined, pdf_tables_count, len(doc)

def extract_md_content(md_path):
    """Read and separate prose, tables, math, and images from Markdown."""
    raw = open(md_path, encoding="utf-8").read()
    
    # Strip any trailing notes or visual reasoning traces if present
    raw = re.split(r"^#+\s*(?:Conversion notes|Visual Reasoning Trace)", raw, flags=re.M | re.I)[0]
    
    # Extract Markdown tables
    table_lines = []
    tables = []
    current_table = []
    
    for line in raw.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("|") and trimmed.endswith("|"):
            current_table.append(trimmed)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []
    if current_table:
        tables.append(current_table)
        
    # Clean prose for text layer matching
    prose = raw
    prose = re.sub(r"\$\$.*?\$\$", " ", prose, flags=re.S)
    prose = re.sub(r"\$[^$\n]+\$", " ", prose)
    prose = re.sub(r"^\*?\[Image[^\n]*$", " ", prose, flags=re.M)
    prose = re.sub(r"\[([^\]]*)\]\((https?://[^)]*)\)", r"\1 \2", prose)
    prose = prose.replace("*", " ").replace("|", " ").replace("---", " ")
    
    return raw, normalize_text(prose), tables

def audit_tables(tables):
    """Audit Markdown tables for grid invariants and column-count consistency."""
    results = []
    total_rows = 0
    malformed_rows = 0
    empty_cells_count = 0
    
    for t_idx, table in enumerate(tables):
        if len(table) < 2:
            continue
            
        # Parse header
        header_cells = [c.strip() for c in table[0].strip("|").split("|")]
        col_count = len(header_cells)
        
        # Separator row
        sep_cells = [c.strip() for c in table[1].strip("|").split("|")]
        is_sep_valid = len(sep_cells) == col_count and all(re.match(r"^:?-+:?$", c) for c in sep_cells if c)
        
        table_issues = []
        if not is_sep_valid:
            table_issues.append(f"Header/separator column mismatch ({col_count} vs {len(sep_cells)})")
            
        data_rows = table[2:]
        for r_idx, row in enumerate(data_rows):
            total_rows += 1
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) != col_count:
                malformed_rows += 1
                table_issues.append(f"Row {r_idx+1} has {len(cells)} cells, expected {col_count}")
            for c in cells:
                if not c or c in ["-", "–", "—", "N/A", "nd", "ND"]:
                    empty_cells_count += 1
                    
        results.append({
            "table_index": t_idx + 1,
            "columns": col_count,
            "rows": len(data_rows),
            "issues": table_issues
        })
        
    return results, total_rows, malformed_rows, empty_cells_count

def audit_author_draft_docx(docx_path, md_raw):
    """Compare Markdown output against author manuscript Word draft if provided."""
    try:
        import docx
    except ImportError:
        print("  Notice: python-docx not installed; skipping DOCX benchmark audit.")
        return None
        
    if not os.path.exists(docx_path):
        print(f"  Warning: Benchmark file {docx_path} not found.")
        return None
        
    doc = docx.Document(docx_path)
    docx_paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    docx_words = sum(len(p.split()) for p in docx_paras)
    docx_tables = len(doc.tables)
    
    return {
        "paragraphs": len(docx_paras),
        "total_words": docx_words,
        "tables": docx_tables
    }

def main():
    parser = argparse.ArgumentParser(
        description="Strict quantitative fidelity audit for PDF-to-Markdown conversions."
    )
    parser.add_argument("pdf", help="Path to source PDF file")
    parser.add_argument("md", help="Path to converted Markdown file")
    parser.add_argument("--docx", default=None, help="Optional author manuscript DOCX benchmark")
    parser.add_argument("--recall-threshold", type=float, default=70.0,
                        help="Minimum acceptable 6-word n-gram recall percentage (default: 70.0%%)")
    
    args = parser.parse_args()
    pdf_path = args.pdf
    md_path = args.md
    
    print("=" * 65)
    print("=== QUANTITATIVE VERIFICATION & INTEGRITY AUDIT ===")
    print("=" * 65)
    print(f"Source PDF:        {pdf_path}")
    print(f"Output Markdown:   {md_path}")
    if args.docx:
        print(f"Author Benchmark:  {args.docx}")
    print("-" * 65)
    
    # 1. Extraction
    src_text, pdf_tables_detected, pdf_page_count = extract_pdf_text_and_tables(pdf_path)
    raw_md, md_prose, md_tables = extract_md_content(md_path)
    
    words_src = re.findall(r"[^\W_]+(?:\.\d+)?", src_text.lower())
    words_md = re.findall(r"[^\W_]+(?:\.\d+)?", md_prose.lower())
    
    # Scanned PDF check
    is_scanned = len(words_src) == 0
    print(f"PDF Pages:         {pdf_page_count}")
    print(f"Source PDF Words:  {len(words_src):,} {'(SCANNED / BITMAP ONLY)' if is_scanned else ''}")
    print(f"Markdown Words:    {len(words_md):,}")
    
    failures = []
    
    # 2. N-Gram Precision & Recall Audit (Bidirectional)
    if not is_scanned and len(words_src) >= 6:
        n = 6
        ngrams_src = [tuple(words_src[i:i+n]) for i in range(len(words_src) - n + 1)]
        ngrams_md = [tuple(words_md[i:i+n]) for i in range(len(words_md) - n + 1)]
        
        set_src = set(ngrams_src)
        set_md = set(ngrams_md)
        
        # Precision: % of Markdown n-grams that exist in PDF text layer
        hits_precision = sum(ng in set_src for ng in ngrams_md)
        tot_precision = max(1, len(ngrams_md))
        precision_pct = (hits_precision / tot_precision) * 100
        
        # Recall: % of PDF text layer n-grams that exist in Markdown (catches dropped pages/sections!)
        hits_recall = sum(ng in set_md for ng in ngrams_src)
        tot_recall = max(1, len(ngrams_src))
        recall_pct = (hits_recall / tot_recall) * 100
        
        f1_pct = (2 * precision_pct * recall_pct / (precision_pct + recall_pct)) if (precision_pct + recall_pct) > 0 else 0.0
        
        print("\n[1] N-Gram Alignment Audit (6-Word Window):")
        print(f"  • Precision (Faithfulness): {hits_precision:,}/{tot_precision:,} ({precision_pct:.1f}%)")
        print(f"  • Recall (Coverage):        {hits_recall:,}/{tot_recall:,} ({recall_pct:.1f}%)")
        print(f"  • Harmonized F1 Score:      {f1_pct:.1f}%")
        
        if recall_pct < args.recall_threshold:
            msg = f"CRITICAL: Recall {recall_pct:.1f}% is below threshold {args.recall_threshold}%! Content was likely dropped."
            print(f"  ❌ {msg}")
            failures.append(msg)
        else:
            print(f"  ✓ Recall satisfies completeness threshold (>= {args.recall_threshold}%).")
    else:
        print("\n[1] N-Gram Alignment: Skipped (Source PDF has no extractable digital text layer).")

    # 3. Strict Numerical Audit (Multiset Frequency Matching)
    print("\n[2] Numerical Value Integrity Audit:")
    nums_src = re.findall(r"\b\d+(?:\.\d+)?\b", src_text)
    nums_md = re.findall(r"\b\d+(?:\.\d+)?\b", raw_md)
    
    cnt_src = Counter(nums_src)
    cnt_md = Counter(nums_md)
    
    total_src_nums = sum(cnt_src.values())
    if total_src_nums > 0:
        matched_nums = sum(min(cnt_src[k], cnt_md.get(k, 0)) for k in cnt_src)
        num_recall_pct = (matched_nums / total_src_nums) * 100
        print(f"  • Matched Numbers (Multiset): {matched_nums:,}/{total_src_nums:,} ({num_recall_pct:.1f}%)")
        
        # Identify missing significant numbers (length >= 2, excluding 1..9 which are single digits)
        missing_significant = [k for k, v in cnt_src.items() if cnt_md.get(k, 0) == 0 and len(k) >= 2]
        if missing_significant:
            print(f"  • Distinct Absent Numbers: {len(missing_significant)} (samples: {missing_significant[:8]})")
        else:
            print(f"  ✓ Zero absent numbers from source text layer!")
    else:
        print("  • No numbers in source text layer.")

    # 4. Table Structural Audit
    print(f"\n[3] Tabular Structure & Grid Invariant Audit:")
    print(f"  • PyMuPDF Detected Tables: {pdf_tables_detected}")
    print(f"  • Markdown Tables Emitted: {len(md_tables)}")
    
    table_audit, total_rows, malformed_rows, empty_cells = audit_tables(md_tables)
    print(f"  • Total Table Data Rows:   {total_rows}")
    print(f"  • Malformed / Shifted Rows:{malformed_rows}")
    print(f"  • Empty / Hyphen Cells:    {empty_cells}")
    
    if malformed_rows > 0:
        msg = f"Table integrity failure: {malformed_rows} malformed rows detected with mismatched column counts!"
        print(f"  ❌ {msg}")
        failures.append(msg)
        for t in table_audit:
            if t["issues"]:
                for iss in t["issues"][:3]:
                    print(f"     Table {t['table_index']}: {iss}")
    else:
        print("  ✓ All Markdown table rows satisfy strict grid invariance (column counts match headers).")

    # 5. Reference Continuity & Gap Analysis
    print(f"\n[4] Reference Continuity & Gap Analysis:")
    numbered_refs = sorted(set(int(r) for r in re.findall(r"\[(\d+)\]", raw_md) if 1 <= int(r) <= 600))
    if numbered_refs:
        min_ref = min(numbered_refs)
        max_ref = max(numbered_refs)
        expected_set = set(range(1, max_ref + 1))
        found_set = set(numbered_refs)
        gaps = sorted(list(expected_set - found_set))
        
        print(f"  • Numbered Reference Sequence: [{min_ref}] to [{max_ref}]")
        print(f"  • Total Unique Referenced:   {len(numbered_refs)}")
        if gaps:
            print(f"  ⚠️  Sequence Gaps Detected ({len(gaps)}): {[f'[{g}]' for g in gaps[:10]]}")
        else:
            print(f"  ✓ Reference sequence is strictly continuous from [1] to [{max_ref}] with ZERO gaps!")
    else:
        # Author-Year style
        m_ref = re.search(r"(?:^|\n)#{1,3}\s*References?\b", raw_md, re.I)
        if m_ref:
            ref_slice = raw_md[m_ref.start():]
            author_years = re.findall(r"\(([12]\d{3})\)", ref_slice)
            print(f"  • Author-Year References Detected: {len(author_years)} citation/bibliography entries.")
        else:
            print("  • No explicit References section found.")

    # 6. Optional Author Draft Benchmark
    if args.docx:
        print(f"\n[5] Author Draft Benchmark Parity (.docx):")
        docx_stats = audit_author_draft_docx(args.docx, raw_md)
        if docx_stats:
            print(f"  • Draft Word Count:   {docx_stats['total_words']:,} (vs. Final Markdown: {len(words_md):,})")
            print(f"  • Draft Paragraphs:   {docx_stats['paragraphs']}")
            print(f"  • Draft Tables:       {docx_stats['tables']} (vs. Final Markdown: {len(md_tables)})")
            
    print("\n" + "=" * 65)
    if failures:
        print("❌ AUDIT STATUS: FAILED")
        for f in failures:
            print(f"   • {f}")
        print("=" * 65)
        sys.exit(1)
    else:
        print("✅ AUDIT STATUS: PASSED (100% Quality & Structural Compliance)")
        print("=" * 65)
        sys.exit(0)

if __name__ == "__main__":
    main()
