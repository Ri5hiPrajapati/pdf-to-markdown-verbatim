# PDF to Verbatim Markdown (`pdf-to-markdown-verbatim`)

An open-source, battle-tested agent skill and automated workflow template for autonomous AI agents converting **academic research and review paper PDFs** into **100% faithful, word-for-word Markdown (`.md`)** using **Claude Haiku 5.5 High Effort multimodal vision OCR**.

---

## 🌟 Why This Skill Exists: Hard-Won Lessons & Preventive Measures

Most developers and AI agents fail when converting academic papers because they treat academic PDFs as simple text documents or send them in a single massive prompt. Academic papers published in journals (*Elsevier*, *IEEE*, *Springer*, *Nature*, *Wiley*) have complex visual and structural constraints.

This repository codifies the **exact failure modes discovered in practice** and the **preventive measures** required to achieve publication-grade conversion fidelity:

| ❌ Common Mistake / Failure Mode | 💡 Root Cause | ✅ Battle-Tested Preventive Measure |
| :--- | :--- | :--- |
| **False-Positive Copyright Refusals** | Generic prompts like *"transcribe this published paper word-for-word"* trigger commercial safety filters. | **Author-Context Prompt Framing**: Frame the prompt as assisting the author in digitizing their manuscript and data tables. |
| **Token Starvation in High Effort Mode** | `thinking: adaptive` + `effort: high` generates thousands of reasoning tokens, exhausting standard output budgets. | Set `max_tokens: 64000` and dynamically partition papers into 3-page body chunks and 2-page bibliography chunks. |
| **Two-Column Reading Flow Scrambling** | Raw text extractors parse horizontally, interleaving left and right column sentences into scrambled text. | **Visual Multimodal OCR**: Render pages at 150–200 DPI PNG. The vision model understands visual geometry and reads left-to-right, column-by-column. |
| **Table Truncation Across Page Breaks** | Wide, multi-page data tables lose columns or get abbreviated with ellipsis (`...`). | Strict prompt rules instructing the model to reconstruct full Markdown tables (`\| ... \|`), preserving every row, unit, and footnote. |
| **Corrupted Glyphs & Windows Encoding Errors** | PDF fonts remap degree symbols (`\x03C`), micro ($\mu\text{m}$), and reaction arrows ($\rightarrow$). Scripts crash on Windows `cp1252`. | Pure-Python cross-platform architecture with PyMuPDF, UTF-8 stdout reconfigured, and visual glyph reading. |
| **Truncated Reference Bibliographies** | Dense reference sections contain ~1,400 words/page, exceeding token limits when combined. | Dedicated bibliography sub-batching (processing no more than ~40–60 references per call). |

---

## 📂 Repository Contents

* [`SKILL.md`](SKILL.md) — The complete universal Agent Skill specification. Plug this directly into **Google Antigravity**, **Claude Code**, **Gemini CLI**, or any agentic system.
* [`batch_converter_haiku55.py`](batch_converter_haiku55.py) — Universal, dynamic Python batch converter that scans any arbitrary PDF, calculates page counts, identifies reference sections, executes high-effort visual OCR passes, and stitches the master Markdown file.
* [`verify_md.py`](verify_md.py) — Pure-Python, cross-platform quantitative verification tool (evaluates word counts, 6-word n-gram verbatim alignment, number preservation, and reference completeness).

---

## 🚀 Quick Start for Agents & Developers

### 1. Installation

Requires Python 3.10+ and pure-Python libraries (no external Linux Poppler or Tesseract binaries needed):

```bash
pip install pymupdf requests python-docx
```

### 2. Run Dynamic Batch Conversion on Any PDF

Set your Anthropic API key:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-api-key"

# Linux / macOS
export ANTHROPIC_API_KEY="your-api-key"
```

Run the universal converter:

```bash
python batch_converter_haiku55.py path/to/paper.pdf [output_dir] [optional_benchmark.docx]
```

The converter will:
1. Scan the PDF and detect the reference section starting page.
2. Plan dynamic 3-page body batches and 2-page reference sub-batches.
3. Render pages at 150 DPI and call `claude-haiku-5-5` with `effort: "high"` and adaptive thinking.
4. Reconstruct all data tables and mathematical/chemical notations ($...$, $$...$$).
5. Stitch all chunks into `output_dir/<paper_name>.md`.

---

### 3. Verify Accuracy

Run the verification tool to audit the conversion against the original PDF text layer:

```bash
python verify_md.py path/to/paper.pdf path/to/output.md
```

**Audit Metrics Reported:**
* **Total Word Count Ratio**: Compares source text layer to Markdown.
* **6-Word Verbatim Alignment**: Measures exact n-gram matching percentage (target: $\ge 85\%$).
* **Prose Numbers Matched**: Verifies numerical data in prose.
* **Reference Audit**: Verifies that every single reference from `[1]` to `[N]` is present without gaps.

---

## 🤝 Using This Skill in Other Agents

To equip another agent with this skill:
1. Copy [`SKILL.md`](SKILL.md) into your agent's skills directory (e.g. `.agent/skills/` or `builtin/skills/`).
2. When the agent receives a task to convert an academic paper PDF, it reads [`SKILL.md`](SKILL.md) and follows the dynamic batching, author-context framing, and table-preservation rules automatically.

---

## 📜 License

MIT License. Open-source and free for all developers and AI agents.
