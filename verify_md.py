#!/usr/bin/env python3
"""verify_md.py SOURCE.pdf OUTPUT.md
Compare a Markdown conversion against the PDF's own text layer.
Catches dropped or changed words, silent case/hyphen edits, and altered numbers.
It cannot catch errors the PDF's text layer itself contains, and it skips
equations ($...$), which must be checked visually against the rendered page."""
import re, subprocess, sys, unicodedata
from collections import Counter

LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬀ": "ff", "ﬄ": "ffl"}
SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def norm(s):
    for a, b in LIG.items():
        s = s.replace(a, b)
    s = s.replace("−", "-").replace(" ", " ").replace("´", "")
    return unicodedata.normalize("NFC", s.translate(SUB).translate(SUP))


def source_text(pdf):
    raw = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = [norm(p) for p in raw.split("\f")]
    seen = Counter()
    for p in pages:
        seen.update({l.strip() for l in p.splitlines() if l.strip()})
    limit = min(3, len(pages))  # running headers/footers repeat on many pages
    furniture = {l for l, c in seen.items() if c >= limit and len(l) > 3}
    lines = [l for p in pages for l in p.splitlines() if l.strip() not in furniture]
    text = "\n".join(lines)
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text), lines


def md_text(path):
    s = norm(open(path, encoding="utf-8").read())
    s = re.split(r"^#+\s*Conversion notes", s, flags=re.M | re.I)[0]  # ignore your own notes section
    s = re.sub(r"\$\$.*?\$\$", " ", s, flags=re.S)  # display equations
    s = re.sub(r"\$[^$\n]+\$", " ", s)  # inline equations
    s = re.sub(r"^\*?\[Image[^\n]*$", " ", s, flags=re.M)  # figure placeholders
    s = re.sub(r"^>.*$", " ", s, flags=re.M)  # blockquotes you added
    s = re.sub(r"\[([^\]]*)\]\((https?://[^)]*)\)", r"\1 \2", s)
    s = s.replace("\\*", "").replace("*", " ").replace("|", " ").replace("---", " ")
    return re.sub(r"^#+\s*", "", s, flags=re.M)


def toks(s):  # hyphens/dashes dropped so line-break hyphens do not matter
    s = re.sub(r"[-–—─]", "", s)
    return re.findall(r"[^\W_]+(?:\.\d+)?", s)


def nums(s):
    return Counter(re.findall(r"\d+(?:\.\d+)?", s))


def main(pdf, md):
    src, src_lines = source_text(pdf)
    out = md_text(md)
    A, B = toks(src), toks(out)
    Al, Bl = Counter(t.lower() for t in A), Counter(t.lower() for t in B)
    miss, extra = Al - Bl, Bl - Al
    print(f"words: source {sum(Al.values())}, markdown {sum(Bl.values())}")
    print(f"source words absent from markdown: {sum(miss.values())}  |  markdown words absent from source: {sum(extra.values())}")
    print("  absent from markdown (top 25):", miss.most_common(25))
    print("  absent from source   (top 25):", extra.most_common(25))
    n = 6
    gs = {tuple(t.lower() for t in A[i:i + n]) for i in range(len(A) - n + 1)}
    hits = sum(tuple(t.lower() for t in B[i:i + n]) in gs for i in range(len(B) - n + 1))
    tot = max(1, len(B) - n + 1)
    print(f"6-word phrases found verbatim in source: {hits}/{tot} ({100 * hits / tot:.1f}%)")
    Ac, Bc = Counter(A) - Counter(B), Counter(B) - Counter(A)
    case_only = [(a, b) for a in Ac for b in Bc if a.lower() == b.lower() and a != b]
    print("case-only differences (silent edits):", case_only or "none")
    prose = "\n".join(l for l in src_lines if len(l.strip()) >= 50)  # skips figure axis ticks
    n_md, n_all, n_prose = nums(out), nums(src), nums(prose)
    print("numbers in markdown not found anywhere in source:", dict(n_md - n_all) or "none")
    gone = n_prose - n_md
    print("numbers in source prose lines missing from markdown:", dict(gone) or "none")
    print(f"prose numbers matched: {sum(n_prose.values()) - sum(gone.values())}/{sum(n_prose.values())}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
