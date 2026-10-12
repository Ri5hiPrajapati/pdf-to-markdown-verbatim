#!/usr/bin/env python3
"""verify_md.py SOURCE.pdf OUTPUT.md [BENCHMARK.docx]
Quantitative, cross-platform fidelity checker for PDF-to-Markdown conversions.
No external system binaries required.
"""
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import re
import sys
import unicodedata
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬀ": "ff", "ﬄ": "ffl"}

def norm(s):
    for a, b in LIG.items():
        s = s.replace(a, b)
    s = s.replace("−", "-").replace(" ", " ").replace("´", "")
    return unicodedata.normalize("NFC", s)

def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = []
    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            if b[6] == 0:  # text block
                txt = b[4].strip()
                if txt:
                    full_text.append(txt)
    return norm("\n".join(full_text))

def extract_md_text(md_path):
    raw = open(md_path, encoding="utf-8").read()
    raw = re.split(r"^#+\s*Conversion notes", raw, flags=re.M | re.I)[0]
    raw = re.sub(r"\$\$.*?\$\$", " ", raw, flags=re.S)
    raw = re.sub(r"\$[^$\n]+\$", " ", raw)
    raw = re.sub(r"^\*?\[Image[^\n]*$", " ", raw, flags=re.M)
    raw = re.sub(r"\[([^\]]*)\]\((https?://[^)]*)\)", r"\1 \2", raw)
    raw = raw.replace("*", " ").replace("|", " ").replace("---", " ")
    return norm(raw)

def main(pdf_path, md_path):
    print(f"=== VERIFYING: {md_path} AGAINST SOURCE: {pdf_path} ===")
    src = extract_pdf_text(pdf_path)
    out = extract_md_text(md_path)
    
    words_src = re.findall(r"[^\W_]+(?:\.\d+)?", src)
    words_md = re.findall(r"[^\W_]+(?:\.\d+)?", out)
    
    print(f"Word Counts: Source PDF text layer={len(words_src)}, Markdown output={len(words_md)}")
    
    # Check 6-word verbatim n-grams
    n = 6
    gs = {tuple(words_src[i:i+n]) for i in range(len(words_src) - n + 1)}
    hits = sum(tuple(words_md[i:i+n]) in gs for i in range(len(words_md) - n + 1))
    tot = max(1, len(words_md) - n + 1)
    print(f"6-word verbatim alignment: {hits}/{tot} ({100 * hits / tot:.1f}%)")
    
    # Check numbers
    nums_src = Counter(re.findall(r"\d+(?:\.\d+)?", src))
    nums_md = Counter(re.findall(r"\d+(?:\.\d+)?", out))
    diff_nums = nums_src - nums_md
    print(f"Prose numbers matched: {len(nums_src) - len(diff_nums)}/{len(nums_src)}")
    
    # Check references (Numbered style or Author-Year style)
    refs_found = sorted(set(int(r) for r in re.findall(r"\[(\d+)\]", out) if int(r) <= 500))
    if refs_found:
        print(f"Numbered References detected: [1] to [{max(refs_found)}] (Total unique cited/listed: {len(refs_found)})")
    else:
        # Check Author-Year style references (e.g. Springer, Nature, APA)
        m = re.search(r"(?:^|\n)#{1,3}\s*References?\b", out, re.I)
        if m:
            ref_part = out[m.start():]
            # Strip ESM / Supplementary material if appended afterwards
            m_esm = re.search(r"(?:^|\n)#{1,3}\s*(?:Electronic\s+)?Supplementary", ref_part, re.I)
            if m_esm:
                ref_part = ref_part[:m_esm.start()]
            author_year_refs = re.findall(r"\(([12]\d{3})\)", ref_part)
            if author_year_refs:
                print(f"Author-Year References detected: {len(author_year_refs)} entries cited/listed in bibliography")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_md.py <source.pdf> <output.md>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
