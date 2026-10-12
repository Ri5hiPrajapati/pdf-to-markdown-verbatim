---
name: pdf-to-markdown-verbatim
description: Convert research-article PDFs to word-for-word Markdown (text layer or OCR), extract tables and numbers, and verify the result against the source with an accuracy report.
---

# PDF to verbatim Markdown, with verification

Use when the person wants a faithful, word-for-word Markdown copy of a PDF (usually a research article), or wants tables and numbers pulled out of it as data. Not for summaries. It works with any model; the checks do not depend on which model transcribes.

## Ground rules

1. **Transcribe, do not improve.** No paraphrasing, summarising, reordering or silent correction. Spelling slips, odd capitalisation, wrong cross-references and inconsistent terms in the source stay as printed and are listed in the notes.
2. **Never promise 100%.** Report what was measured and what still needs a human eye.
3. **Two sources of truth.** For a born-digital PDF the text layer is the reference for wording and numbers. The rendered page is the reference for symbols, equations, tables and anything the text layer garbles.
4. **Extract, do not retype.** Build the Markdown from text pulled out by a tool, not from memory of the document.
5. **Disclose every deliberate edit** in a Conversion notes section at the end of the file.

## Workflow

### 1. Triage
- `pdfinfo f.pdf` (page count), `pdffonts f.pdf` (no embedded fonts usually means a scan), `pdftotext -f 1 -l 1 f.pdf -` (is the text clean?).
- Born-digital with clean text: route A. Scanned, image-only, or badly garbled text: route B.

### 2. Extract
- **Route A.** `pdftotext f.pdf raw.txt` for prose; `pdftotext -layout` for tables and columns. Keep the raw files for the checks. In two-column papers, check the reading order; if columns interleave, extract per page with `-layout` or crop each column.
- **Route B (OCR).** `pdftoppm -r 300 -png f.pdf page`, then `tesseract page-01.png out -l eng --psm 3` for each page. Check `which tesseract` first (ocrmypdf may be missing). If no OCR engine exists, read each page image and transcribe visually. OCR is weaker on Greek letters, sub/superscripts, units and tables, so expect more errors, check every page by eye, and say so in the report. There is no text layer to diff against, so step 4a does not apply; compare the page images with the output instead.

### 3. Build the Markdown
- Remove page furniture only: running headers and footers, page numbers, download or licence stamps, watermarks, "check for updates" badges.
- Rejoin line-end hyphenation, reflow to paragraphs, keep real hyphens, expand ligatures, keep Unicode symbols (± μ ° ≈).
- Headings keep their wording and numbering.
- Equations go to LaTeX: `$$...$$` with the printed equation number as `\qquad (n)`; inline math as `$...$`.
- Tables become Markdown tables with units and headers as printed; flatten merged headers into extra columns.
- Figures are not embedded unless asked. Keep the caption verbatim and add `*[Image not included. See Figure N, page P.]*`. Numbers printed inside figures are added only after reading the page image, inside the placeholder, and flagged as read visually.
- References stay verbatim. Light formatting (numbering, italic journal, bold year) is fine if disclosed; do not change author names, punctuation or wording.
- A defective glyph in the text layer (missing ±, broken Greek) is repaired only after confirming it on the rendered page, and each repair is listed.
- Visible errors in the source (typos, a wrong equation cross-reference) stay as printed and are flagged in the notes, never silently fixed.

### 4. Verify
a. **Automated** (route A): `python3 -I verify_md.py paper.pdf paper.md` (script at the end of this file). Investigate every flagged item and decide: fix it, or keep it and disclose it.
b. **Visual, always.** Rasterise the pages that hold equations, tables, symbols and figure values: `pdftoppm -r 150 -f N -l N -png f.pdf p`. For a doubtful glyph, crop at 300 dpi (`-x -y -W -H`); `pdftotext -f N -l N -bbox` gives word coordinates to aim the crop. Check every equation (symbols, exponents, coefficients), every table cell, and the numbers in the abstract.
c. Re-run 4a after any fix.

How to read the script output:
- Expected noise: equation tokens (equations are skipped), any metadata line you added, figure-panel numbers, edits you disclosed.
- Real problems: a word missing from prose; a case-only difference you did not intend (a silent edit); a number in the Markdown that is not in the source; a source prose number missing from the Markdown.
- The script compares against the PDF's own text layer, so it cannot catch a defect inside that layer. The visual checks cover that gap.

### 5. Conversion notes (end of the .md)
Use the heading `## Conversion notes`; the script ignores everything after it. List:
- what was removed (page furniture), reflowed or expanded
- each symbol or character repair, with the original form
- how equations and tables were checked, and against which page
- figure values read visually
- errors in the original, kept as printed
- formatting changes in the reference list

### 6. Report to the person
State plainly: not 100%; what the automated check measured (word, phrase and number matches); what was checked by eye; what is left for them (equations, tables, symbols, figure values, anything they will cite). Do not claim accuracy on the strength of the model's own say-so.

## Data extraction (tables and numbers)
When the person wants data, not just text:
- One row per measurement: quantity, value, uncertainty, unit, conditions, source (page, table or figure), method (text layer, table, read from figure), confidence.
- Values read from figures are marked as such and given lower confidence. Do not digitise curves silently.
- Cross-check numbers with the script's number checks, and compare the abstract's numbers with the body.
- Keep the paper's units; add converted columns separately.
- Keep the paper's claims apart from your own checks (for example an inconsistency you noticed), in a separate column or section.
- Deliver as CSV or XLSX with the source column intact.

## Cost and effort notes
- On a free chat plan, convert one PDF per chat with a single clear request, then run the checks. Every extra tool turn re-reads the whole conversation.
- Text extraction first uses far fewer input tokens than sending the PDF natively. Look up current prices and limits rather than quoting them from memory.
- Smaller models tend to lose accuracy on equations and tables. Test three papers (equation-heavy, table-heavy, ordinary) before trusting a model for a batch.

## verify_md.py

```python
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
    s = s.replace("−", "-").replace(" ", " ").replace("´", "")
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
```
