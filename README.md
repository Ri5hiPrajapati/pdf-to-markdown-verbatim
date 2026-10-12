# PDF to Verbatim Markdown (`pdf-to-markdown-verbatim`)

A production-grade agent skill and systematic workflow for converting scientific research articles and technical PDFs into word-for-word, faithful Markdown using **multimodal vision OCR (Claude Haiku 5.5 High Effort)**, reconstructing complex multi-column tables, equations, and dense bibliographies, and benchmarking against author Word drafts (`.docx`).

---

## 📌 Features

- **Multimodal Visual OCR First**: Processes rendered high-resolution page images (150–200 DPI) to naturally resolve multi-column flows, spanning banners, and complex table geometries.
- **Strict Verbatim Fidelity**: No paraphrasing, summarizing, or silent omissions. Preserves all original wording, notation, and typos.
- **Dual Ground Truth Benchmarking**:
  - **Final Published PDF**: The primary ground truth for final publication text and reference count.
  - **Author Manuscript Draft (`.docx`)**: The structural benchmark (~99% content match) used to audit paragraph continuity and detect visual OCR ambiguities.
- **Author-Context Prompt Framing**: Eliminates false-positive LLM copyright refusals by framing conversion within author manuscript digitization.
- **Complete Table & Reference Preservation**:
  - Reconstructs full Markdown tables with all columns, parameter units, and footnotes.
  - Splits dense reference bibliographies into sub-batches to prevent token starvation.
- **Cross-Platform & Pure-Python**: Uses `pymupdf` (`fitz`) and `python-docx`—runs seamlessly on Windows, Linux, and macOS without external system dependencies like Linux Poppler or Tesseract.

---

## 📂 Repository Contents

- [`SKILL.md`](SKILL.md) - The complete, battle-tested agent skill definition for Antigravity, Claude, and Gemini assistants.
- [`batch_converter_haiku55.py`](batch_converter_haiku55.py) - Automated sequential batch converter using Claude Haiku 5.5 with adaptive thinking and high effort.
- [`verify_md.py`](verify_md.py) - Pure-Python cross-platform verification script for quantitative accuracy auditing.

---

## 🚀 Quick Start

### 1. Requirements

```bash
pip install pymupdf requests python-docx
```

### 2. Run Batch Conversion

Set your Anthropic API key and run:

```bash
export ANTHROPIC_API_KEY="your-api-key"
python batch_converter_haiku55.py path/to/paper.pdf path/to/benchmark.docx output_directory/
```

### 3. Verify Accuracy

```bash
python verify_md.py path/to/paper.pdf path/to/output.md
```

The script evaluates:
1. **Total word count comparison** (source PDF text layer vs. Markdown).
2. **6-Word phrase verbatim n-gram match percentage**.
3. **Prose numbers and units matched**.
4. **References audit** (checks every reference from `[1]` to `[N]` with missing number detection).

---

## 📜 License

MIT License.
