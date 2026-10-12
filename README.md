# PDF to Verbatim Markdown (`pdf-to-markdown-verbatim`)

An automated workflow and agent skill for autonomous AI agents converting **academic research and review paper PDFs** into **faithful, word-for-word Markdown (`.md`)** using **Claude Haiku 5.5 High Effort multimodal vision OCR**.

---

## 🌟 Lessons Learned: The 8 Failure Modes & Preventive Measures

Standard text extractors and naive single-prompt LLM calls fail on academic papers published in journals (*Elsevier*, *IEEE*, *Springer Nature*, *Taylor & Francis*, *Wiley*). Complex two-column layouts, open borderless tables, dense reference lists, and publisher cover sheets require systematic guards.

This repository codifies the **8 core failure modes discovered in practice** and the **battle-tested preventive measures**:

| ❌ Failure Mode | 💡 Root Cause | ✅ Battle-Tested Preventive Measure |
| :--- | :--- | :--- |
| **1. Copyright / Safety Refusals** | Generic prompts like *"transcribe this paper word-for-word"* trigger commercial safety filters. | **Author-Context Framing & Refusal Sentinel**: Frame prompt as author-assisted archival; automated retry if refusal detected. |
| **2. Token Starvation in High Effort** | `thinking: adaptive` + `effort: high` generates thousands of reasoning tokens, exhausting output limits. | Set `max_tokens: 64000`, partition into 3-page body chunks, and auto-continue if `stop_reason == "max_tokens"`. |
| **3. Two-Column Reading Interleaving** | Raw text extractors parse horizontally by Y-coordinate, scrambling left and right columns. | **Visual Multimodal OCR**: Render pages at 150 DPI PNG. Vision model reads left-to-right, column-by-column. |
| **4. Table Truncation Across Page Breaks** | Wide data tables lose columns or get abbreviated with ellipsis (`...`). | Strict prompt rules instructing complete Markdown tables (`\| ... \|`), preserving every row, unit, and empty cell (`-`). |
| **5. Corrupted Glyphs & OS Encoding Crashes** | PDF fonts remap degree symbols (`\x03C`), micro ($\mu\text{m}$), and arrows. Windows `cp1252` crashes. | Pure-Python cross-platform PyMuPDF architecture with UTF-8 stdout reconfigured and visual glyph reading. |
| **6. Truncated Reference Bibliographies** | Dense reference sections contain ~1,400 words/page, exceeding token limits when combined. | Dedicated bibliography sub-batching (processing no more than ~40–60 references per call). |
| **7. Publisher Cover-Sheet Folio Offset Drop** | Unnumbered cover sheets offset printed folios ($P_{\text{folio}} = P_{\text{pdf}} - 1$), causing image skips. | **Folio-Offset Prompt Invariant**: Directs the vision model to process all $N$ supplied images sequentially based on visual reality. |
| **8. Rotated / Landscape Table Fragmentation** | Multi-parameter characterization tables are set in landscape orientation (rotated 90°). | **Rotational Coordinate Alignment**: Cognitive transformation parsing columns along rotated baselines without row fracturing. |

---

## 📂 Repository Contents

* [`SKILL.md`](SKILL.md) — The comprehensive universal Agent Skill specification detailing layout invariants, grid rules, and multi-paper case studies.
* [`SKILL_SYSTEM_PROMPT.md`](SKILL_SYSTEM_PROMPT.md) — Lean, token-efficient cached system prompt (~1,200 tokens) sent over the API wire to save cache-creation tokens.
* [`batch_converter_haiku55.py`](batch_converter_haiku55.py) — Universal Python batch converter supporting Real-Time and Message Batches API (50% discount), active prompt caching, continuation on `max_tokens`, rate-limit tracking, and advisor tool integration.
* [`verify_md.py`](verify_md.py) — Strict quantitative verification suite (evaluates 6-word n-gram Precision & Recall, number multiset distributions, table row/column grid invariance, reference sequence gaps, and optional author `.docx` draft parity).
* [`requirements.txt`](requirements.txt) — Python dependencies (`pymupdf`, `requests`, `markdown`, `python-docx`).

---

## 🚀 Quick Start for Agents & Developers

### 1. Installation

Requires Python 3.10+ (pure Python; no external Poppler or Tesseract system binaries needed):

```bash
pip install -r requirements.txt
```

### 2. Set API Key

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-anthropic-api-key"

# Linux / macOS
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 3. Run Conversion

```bash
# Standard Synchronous Real-Time Mode:
python batch_converter_haiku55.py path/to/paper.pdf

# Option A: Message Batches API (50% Flat Discount + 1h Batch Prompt Cache TTL):
python batch_converter_haiku55.py path/to/paper.pdf --batch

# Hybrid Executor-Advisor Mode (Haiku 5.5 + Sonnet 5.5 Advisor on complex tables):
python batch_converter_haiku55.py path/to/paper.pdf --batch --advisor sonnet-5-5

# With Author Manuscript Benchmark Comparison:
python batch_converter_haiku55.py path/to/paper.pdf --docx path/to/draft.docx
```

The converter will:
1. Scan the PDF and detect where the References section starts (using line-anchored regex).
2. Dynamically plan 3-page body chunks and 1–2 page reference chunks (with a dedicated `transition` chunk for the conclusion/references boundary).
3. Render pages at 150 DPI and invoke Claude Haiku 5.5 with adaptive thinking (`effort: "high"`).
4. Inject cached system prompt (`SKILL_SYSTEM_PROMPT.md`, comfortably exceeding Haiku 5.5's 512-token cache minimum).
5. Recover from truncation (`max_tokens`) with automatic continuation turns.
6. Assemble all chunks into `output_dir/<paper_name>.md` and compile a companion `output_dir/<paper_name>.html` preview.
7. Save detailed telemetry in `output_dir/conversion_telemetry.json` and thinking traces in `{batch_id}_thinking_trace.json`.
8. Automatically run `verify_md.py` for immediate quantitative validation.

---

### 4. Quantitative Verification (`verify_md.py`)

Run the standalone verification suite:

```bash
python verify_md.py path/to/paper.pdf path/to/output.md [--docx path/to/draft.docx] [--recall-threshold 70]
```

**Metrics Evaluated:**
* **6-Word N-Gram Precision & Recall**: Precision evaluates faithfulness (preventing hallucinations), while Recall evaluates coverage (detects dropped pages or omitted paragraphs). Sets non-zero exit code if recall falls below threshold.
* **Strict Numerical Value Audit**: Compares numbers via multiset frequency distributions (`collections.Counter`), eliminating substring false positives.
* **Table Grid Invariance**: Audits every Markdown table line-by-line to ensure every row contains the exact same column count as the header, detecting shifted cells and missing placeholders.
* **PyMuPDF Table Discovery**: Compares table count detected by PyMuPDF (`page.find_tables()`) with Markdown tables generated.
* **Reference Continuity & Gap Analysis**: Audits numbered citations (`[1]` to `[N]`) and reports any missing sequence indices.
* **Author Draft Benchmark (.docx)**: Compares paragraph and table counts against pre-publication author drafts.

---

## 📊 Empirical Case Studies

The conversion architecture has been evaluated across four peer-reviewed papers spanning multiple publishers:

| Case Study Paper | Venue & Publisher | Type | Pages & Batches | References Parity | Tables & Figures | Peak $\mathcal{R}_{cog}$ | Cost (Haiku 5.5 Batch) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Review Article** (*Food colorants*) | *Mater. Today Proc.* (Elsevier) | Review | 15 pp. (5 batches) | 149 / 149 (100%) | 6 Tables (Table 1: 30 rows $\times$ 11 cols) | 52.4% | \$0.0218 USD (~₹1.89 INR) |
| **Research Article 1** (*Soy Protein*) | *J. Food Sci. Technol.* (Springer) | Primary Research | 15 pp. (6 batches) | 51 / 51 (100%) | 1 Main Table, 4 Figs + 7 ESM Tables | 57.5% | \$0.0146 USD (~₹1.27 INR) |
| **Research Article 2** (*Sodium Alginate*) | *J. Macromol. Sci. B* (Taylor & Francis) | Primary Research | 28 pp. (10 batches) | 75 / 75 (100%) | 6 Tables, 5 Figs (Table 1 90° rotated) | 52.0% | \$0.0202 USD (~₹1.75 INR) |
| **Research Article 3** (*DES Betanin*) | *Biomass Conv. Bioref.* (Springer Nature) | Primary Research | 13 pp. (6 batches) | 46 / 46 (100%) | 6 Tables, 4 Figs + Table S1, Figs S1–S4 | 63.4% | \$0.0212 USD (~₹1.84 INR) |

---

## 📜 License

MIT License. Open-source and free for all researchers, developers, and AI agents.
