# PDF to Verbatim Markdown (`pdf-to-markdown-verbatim`)

An agent skill and systematic workflow for converting scientific research articles and technical PDFs into word-for-word, faithful Markdown (via digital text layer extraction or OCR), extracting tabular/numerical data, and mathematically verifying accuracy against the source.

---

## 📌 Features

- **Strict Verbatim Fidelity**: No paraphrasing, summarizing, or silent corrections.
- **Two Sources of Truth**: 
  - Text layer for prose and numerical metrics.
  - Rendered page images for equations, complex symbols, and tables.
- **Formula & Table Translation**:
  - Formulas converted directly to LaTeX display (`$$...$$ \qquad (n)`) and inline (`$...$`) math.
  - Tables converted to standardized Markdown format preserving units and columns.
- **Automated & Visual Verification**:
  - Automated diffing of word frequency, 6-word n-gram verbatim alignment, silent case/hyphen edits, and numerical preservation.
  - Visual check guidance for formulas, figures, and abstract values.
- **Auditable Conversion Notes**: A dedicated section to disclose every deliberate edit, repairs of defective glyphs, and dropped page furniture.

---

## 📂 Repository Contents

- [`SKILL.md`](SKILL.md) - The complete agent skill definition for Antigravity / Claude / ChatGPT / Gemini.
- [`verify_md.py`](verify_md.py) - Python script to quantitatively compare the Markdown conversion against the source PDF's text layer.

---

## 🚀 Quick Start

### 1. Verification Script Usage

Requires `pdftotext` (from `poppler-utils`):

```bash
python verify_md.py path/to/paper.pdf path/to/paper.md
```

The script evaluates:
1. **Total word count comparison** (source vs. markdown).
2. **Missing/Extra words** (identifies omitted phrases or hallucinations).
3. **6-Word phrase verbatim match percentage**.
4. **Case-only silent edits**.
5. **Numerical accuracy** (flags any mismatched numbers in prose).

---

## 📜 License

MIT License.
