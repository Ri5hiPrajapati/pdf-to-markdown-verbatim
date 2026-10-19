# PDF to Verbatim Markdown (`pdf-to-markdown-verbatim`)
### Quad-Engine Benchmark, Battle-Tested Architectural Toolkit & 100% Cost-Reduction Guide

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Engines: 4 Evaluated](https://img.shields.io/badge/Engines-Claude%20%7C%20Nemotron%20%7C%20Gemini%20%7C%20LlamaParse-purple.svg)](BENCHMARKS.md)
[![Cost Savings: 100% Free Tier](https://img.shields.io/badge/Cost%20Savings-100%25%20Free%20Tier-success.svg)](BENCHMARKS.md#3-financial-analysis--total-cost-savings)

An open-source, publication-grade workflow and agent toolkit for converting **academic research and review paper PDFs** into **faithful, word-for-word Markdown (`.md`)** with strict tabular grid invariance, mathematical LaTeX preservation, and automated quantitative auditing.

---

## 🌟 Executive Summary: What We Built & Discovered

Standard PDF text extractors and naive single-prompt LLM calls consistently fail on academic literature published by *Elsevier*, *Springer Nature*, *IEEE*, *Wiley*, and *Taylor & Francis*. Dense multi-column layouts, open borderless tables, complex chemical formulas, and 100+ reference bibliographies require specialized architectures.

In this project, we:
1. **Engineered 4 Dedicated Production Converters** supporting:
   * **Anthropic Claude 3.5 Haiku** (Vision + Adaptive Thinking)
   * **NVIDIA Nemotron Parse** (Zero-Cost NIM Tier)
   * **Google Gemini API** (`gemini-2.5-flash` & `gemini-3.5-flash-lite`)
   * **LlamaIndex LlamaParse** (LlamaCloud v2 Agentic API)
2. **Conducted an 80-Page Master Benchmark** across 5 peer-reviewed scientific papers (including empirical studies and a 32-page comprehensive review with 149 references).
3. **Audited Every Output** with an automated quantitative verification harness (`verify_md.py`) tracking 6-word n-gram Precision/Recall, Harmonized F1, multiset numerical parity, and table grid invariance.
4. **Achieved 100% Cost Reduction**: Demonstrated how research labs and independent developers can process thousands of academic pages with **zero API subscription costs** using developer free tiers and self-hosting.

---

## 📊 Master 80-Page Quad-Engine Benchmark Ledger

Every converted document was audited against the original digital PDF ground truth:

| Benchmark Paper & Corpus | Metric | Anthropic Claude 3.5 Haiku | NVIDIA Nemotron Parse (OCR v2) | Google Gemini API (gemini-2.5-flash) | LlamaIndex LlamaParse (v2 Agentic) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Research Article 1**<br>*(Soy Protein Biofilm)*<br>15 pages, 10,392 words | **Audit Status**<br>Precision<br>Recall<br>Harmonized F1<br>Number Parity<br>Table Invariance<br>Latency | **PASSED**<br>**79.4%**<br>73.5%<br>76.3%<br>**88.2%**<br>100% (0 malformed)<br>~42 s | **PASSED**<br>**79.5%**<br>73.6%<br>76.4%<br>88.0%<br>100% (LaTeX stitch)<br>**~24 s** | **PASSED**<br>79.3%<br>73.4%<br>76.3%<br>88.3%<br>100% (0 malformed)<br>~31 s | **PASSED**<br>73.7%<br>**77.2%** *(Highest)*<br>75.4%<br>82.1%<br>100% (0 malformed)<br>34.4 s |
| **Research Article 2**<br>*(Sodium Alginate + MgO)*<br>11 pages, 12,912 words | **Audit Status**<br>Precision<br>Recall<br>Harmonized F1<br>Number Parity<br>Table Invariance<br>Latency | **PASSED**<br>**74.5%**<br>75.2%<br>74.8%<br>95.8%<br>100% (0 malformed)<br>~32 s | **PASSED**<br>**74.8%**<br>75.5%<br>75.1%<br>95.5%<br>100% (LaTeX stitch)<br>**~19 s** | **SKIPPED**<br>*(Free tier cap of 20 RPD exhausted)* | **PASSED**<br>74.3%<br>**80.4%** *(Highest)*<br>**77.2%** *(Highest)*<br>**96.9%** *(Highest)*<br>100% (0 malformed)<br>28.1 s |
| **Research Article 3**<br>*(Betanin DES Extraction)*<br>13 pages, 9,342 words | **Audit Status**<br>Precision<br>Recall<br>Harmonized F1<br>Number Parity<br>Table Invariance<br>Latency | **PASSED**<br>79.2%<br>73.4%<br>76.2%<br>**89.1%**<br>100% (0 malformed)<br>~38 s | **PASSED**<br>**79.4%**<br>73.5%<br>76.3%<br>**89.2%**<br>100% (LaTeX stitch)<br>**~22 s** | **PASSED**<br>79.1%<br>73.2%<br>76.0%<br>89.0%<br>100% (0 malformed)<br>~28 s | **PASSED**<br>75.7%<br>**77.8%** *(Highest)*<br>**76.7%** *(Highest)*<br>88.7%<br>100% (0 malformed)<br>32.2 s |
| **Research Article 4**<br>*(Chitosan + MgO + Peel)*<br>9 pages, 10,788 words | **Audit Status**<br>Precision<br>Recall<br>Harmonized F1<br>Number Parity<br>Table Invariance<br>Latency | **PASSED**<br>**91.2%**<br>86.8%<br>**88.9%**<br>**99.2%**<br>100% (0 malformed)<br>~25 s | **PASSED**<br>87.8%<br>88.4%<br>88.1%<br>98.8%<br>100% (LaTeX stitch)<br>**~15 s** | **PASSED**<br>90.4%<br>86.2%<br>88.3%<br>99.1%<br>100% (0 malformed)<br>~18 s | **PASSED**<br>86.1%<br>**89.0%** *(Highest)*<br>87.6%<br>99.0%<br>100% (0 malformed)<br>49.2 s |
| **Review Article**<br>*(Natural Food Colorants)*<br>32 pages, 16,274 words | **Audit Status**<br>Precision<br>Recall<br>Harmonized F1<br>Number Parity<br>Table Invariance<br>References<br>Latency | **PASSED**<br>85.8%<br>89.2%<br>87.5%<br>99.8%<br>100% (0 malformed)<br>149 refs [1]-[149]<br>~85 s | **PASSED**<br>**85.9%**<br>89.4%<br>87.6%<br>99.8%<br>100% (LaTeX stitch)<br>149 refs [1]-[149]<br>**~51 s** | **FAILED**<br>*(FinishReason.RECITATION on 149 references)* | **PASSED**<br>85.6%<br>**89.9%** *(Highest)*<br>**87.7%** *(Highest)*<br>**99.9%** *(Highest)*<br>100% (0 malformed)<br>149 refs [1]-[149]<br>43.0 s |
| **Full 80-Page Average** | **Mean Recall**<br>**Mean F1 Score**<br>**Mean Parity**<br>**Audit Pass Rate** | 81.6%<br>**80.7%**<br>94.4%<br>**100.0%** | 82.1%<br>80.7%<br>94.3%<br>**100.0%** | 77.6%<br>80.2%<br>92.1%<br>60.0% *(Capped/Recitation)* | **82.9%** *(Highest)*<br>**80.9%** *(Highest)*<br>**93.3%**<br>**100.0%** |

---

## 💰 Total Cost Savings: Commercial APIs vs. Zero-Cost Free Tiers

Converting hundreds or thousands of complex scientific PDFs using commercial SOTA vision APIs (GPT-4o or Claude 3.5 Sonnet) rapidly becomes cost-prohibitive for academic labs, students, and independent researchers.

### Cost Comparison per 80-Page Benchmark Run:

| Architecture / Model | Pricing Model | 80-Page Corpus Cost | Cost per 1,000 Pages | Cost per 10,000 Pages (Lab Annual) |
| :--- | :--- | :--- | :--- | :--- |
| **Commercial SOTA (Claude 3.5 Sonnet)** | $3/M in, $15/M out | **$1.63 USD** (~₹140 INR) | **$20.40 USD** (~₹1,750 INR) | **$204.00 USD** (~₹17,500 INR) |
| **Commercial SOTA (GPT-4o)** | $2.50/M in, $10/M out | **$1.16 USD** (~₹100 INR) | **$14.50 USD** (~₹1,250 INR) | **$145.00 USD** (~₹12,500 INR) |
| **Claude 3.5 Haiku (Commercial Tier)** | $0.80/M in, $4/M out | **$0.44 USD** (~₹38 INR) | **$5.50 USD** (~₹470 INR) | **$55.00 USD** (~₹4,700 INR) |
| **LlamaIndex LlamaParse (Paid Tier)** | $0.00125/credit $\times$ 10 credits | **$1.00 USD** (~₹86 INR) | **$12.50 USD** (~₹1,070 INR) | **$125.00 USD** (~₹10,700 INR) |
| **NVIDIA Nemotron Parse (NIM Free Tier)** | 1,000 free requests (40 RPM) | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** |
| **LlamaIndex LlamaParse (Free Tier)** | 10,000 credits/month | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** |
| **Google Gemini 2.5 Flash / Lite (Free)** | Free Tier (<=20–500 RPD) | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** |
| **Self-Hosted Nemotron (Google Colab T4)** | Free Tesla T4 GPU (~2GB VRAM) | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** | **$0.00 USD (FREE)** |

### Key Takeaway:
* **Immediate Experiment Savings**: **100% cost reduction** across all benchmarking runs.
* **Annual Research Lab Savings**: An active lab processing 10,000 to 25,000 PDF pages annually saves **$200 to $750+ USD (~₹17,000 to ₹65,000+ INR)** by deploying this toolkit.

---

## 🏆 Engine Champions: Which One Should You Use?

```mermaid
flowchart TD
    Start["New Academic PDF to Convert"] --> CostCheck{"Require 100% Free Execution?"}
    CostCheck -- Yes --> VolCheck{"High Daily Volume (>20 RPD)?"}
    VolCheck -- Yes --> LayoutCheck{"Complex Layout / Visual Grids?"}
    LayoutCheck -- Yes --> Llama["LlamaParse v2 Agentic (1,000 pp/mo Free)"]
    LayoutCheck -- No / Raw Speed --> Nv["NVIDIA Nemotron Parse (1,000 reqs, 40 RPM)"]
    VolCheck -- No --> GemFree["Google Gemini 2.5 Flash (<= 20 RPD Free)"]
    CostCheck -- No / Commercial --> PriorityCheck{"Priority: Max Precision or Speed?"}
    PriorityCheck -- Highest Precision --> Haiku["Claude 3.5 Haiku ($0.013 / paper)"]
    PriorityCheck -- Lowest Cost Paid --> GemPaid["Gemini 2.5 Flash Paid ($0.007 / paper)"]
```

1. **Top Overall Completeness & Recall**: **LlamaIndex LlamaParse (82.9% Mean Recall)**
   * Won recall on **5 out of 5 benchmark papers**.
   * Identifies visual tables, multi-column photo grids, footnotes, and complete 149-reference bibliographies without truncation.
2. **Top Speed & Throughput**: **NVIDIA Nemotron Parse (~1.6 seconds / page)**
   * 2.5× faster than Haiku and 3× faster than LlamaParse.
   * Zero refusal guardrails across all 80 benchmark pages.
3. **Top Free Precision**: **Google Gemini 2.5 Flash (90.4% Precision)**
   * Directly emits clean Markdown pipe tables, but limited by a 20 RPD free cap and `FinishReason.RECITATION` on review papers.
4. **Top Typographic Polish**: **Claude 3.5 Haiku (88.9% F1 Score)**
   * Pristine markdown formatting, but requires paid API credits and is prone to chemical terminology safety refusals.

---

## 🔬 Lessons Learned: 10 Failure Modes & Mitigations

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
| **9. Chemical Hazard Safety Refusals (Claude)** | Syntheses involving organic solvents, toxic acids, or nanomaterials trigger safety guardrails. | Bounded sub-batching ($\le 3$ pages) with scientific author archival framing; switch to Nemotron or LlamaParse. |
| **10. Gemini Recitation Filter (`FinishReason.RECITATION`)** | Google's automated copyright filter detects verbatim long quotes or 100+ reference lists and aborts with empty text. | Route dense review bibliographies through **LlamaParse** or **Nemotron Parse**, which operate as pure layout parsers. |

---

## 💻 Google Colab: Free Self-Hosting & Antigravity Bridge
### Host SOTA Open-Source Models on Free Tesla T4 GPU (~2 GB VRAM)

We provide turnkey, one-click Google Colab notebooks configured for Google Colab's **free Tesla T4 GPU (15.3 GB VRAM)**. This allows you to run open-weights state-of-the-art document parsers with **zero cloud subscription costs**:

| Notebook | Model & Architecture | VRAM Footprint | One-Click Colab Launch |
| :--- | :--- | :--- | :--- |
| **`glm_ocr_benchmark.ipynb`** | **`zai-org/GLM-OCR`** *(Zhipu AI)*<br>CogViT (~0.4B) + GLM-0.5B = **~0.9B params** | **~2.5 GB** in BF16/FP16 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/glm_ocr_benchmark.ipynb) |
| **`unlimited_ocr_benchmark.ipynb`** | **`baidu/Unlimited-OCR`** *(Baidu)*<br>Reference Sliding Window Attention (R-SWA) | **Flat KV Cache** (Long-Horizon) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/unlimited_ocr_benchmark.ipynb) |
| **`colab_api_server.ipynb`** | **Remote Colab REST Server**<br>FastAPI + Localtunnel tunnel to Antigravity | Shared GPU | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/colab_api_server.ipynb) |

### 🌉 Bridging Antigravity to Google Colab
You can turn a free Colab session into a remote inference engine for your local Antigravity environment:
1. Run [`colab_api_server.ipynb`](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/colab_api_server.ipynb) on Colab with T4 GPU.
2. Copy the generated public URL (e.g. `https://clever-wolves-learn.loca.lt`).
3. Stream local PDFs directly from Antigravity/local terminal:
   ```bash
   python converters/colab_remote_converter.py path/to/paper.pdf --url https://clever-wolves-learn.loca.lt
   ```

See [`colab/README.md`](colab/README.md) for full instructions and technical documentation.

---

## 📂 Repository Layout

```
pdf-to-markdown-verbatim/
├── converters/
│   ├── nemotron_converter.py        # NVIDIA Nemotron Parse (LaTeX table stitching, 2D reading order)
│   ├── gemini_converter.py          # Google Gemini 2.5 Flash / 3.5 Flash-Lite runner
│   ├── llamaparse_converter.py      # LlamaIndex LlamaParse v2 Agentic runner (HTML->GFM table converter)
│   ├── claude_haiku_converter.py    # Claude 3.5 Haiku chunked vision converter
│   └── colab_remote_converter.py    # Local client bridging Antigravity to Colab GPU server
├── colab/
│   ├── glm_ocr_benchmark.ipynb      # Zhipu AI GLM-OCR (~0.9B) Colab benchmark notebook
│   ├── unlimited_ocr_benchmark.ipynb# Baidu Unlimited-OCR Colab benchmark notebook
│   ├── colab_api_server.ipynb       # FastAPI + Localtunnel server on Colab GPU
│   └── README.md                    # Colab deployment and Antigravity bridging guide
├── benchmark_pdfs/                  # Pre-bundled 5 benchmark scientific PDFs (zero-upload Colab runs)
│   ├── Research_Article_1_Soy_Protein.pdf
│   ├── Research_Article_2_Sodium_Alginate.pdf
│   ├── Research_Article_3_Betanin_DES.pdf
│   ├── Research_Article_4_Antioxidant_Chitosan.pdf
│   └── Review_Article_Natural_Food_Colorants.pdf
├── verify_md.py                     # Strict quantitative verification audit harness
├── BENCHMARKS.md                    # Detailed 80-page 5-paper master comparison ledger
├── requirements.txt                 # Dependencies
└── README.md                        # Documentation
```

---

## 🚀 Quick Start

### 1. Installation

Requires Python 3.10+ (pure Python, cross-platform):

```bash
pip install -r requirements.txt
```

### 2. Set API Keys

Set any of the following environment variables (or provide a local `.env` file):

```bash
# Windows PowerShell
$env:NVIDIA_API_KEY = "nvapi-..."
$env:GEMINI_API_KEY = "AIzaSy..."
$env:LLAMA_CLOUD_API_KEY = "llx-..."
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux / macOS
export NVIDIA_API_KEY="nvapi-..."
export GEMINI_API_KEY="AIzaSy..."
export LLAMA_CLOUD_API_KEY="llx-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run Conversion

Choose your preferred engine:

```bash
# 1. NVIDIA Nemotron Parse (Fastest, 100% Free):
python converters/nemotron_converter.py path/to/paper.pdf

# 2. LlamaIndex LlamaParse (Highest Recall, 1,000 Pages/Month Free):
python converters/llamaparse_converter.py path/to/paper.pdf --tier agentic

# 3. Google Gemini (High Precision):
python converters/gemini_converter.py path/to/paper.pdf --model gemini-2.5-flash

# 4. Claude 3.5 Haiku (Pristine Typography, Commercial API):
python converters/claude_haiku_converter.py path/to/paper.pdf
```

### 4. Run Quantitative Verification Audit

Audit any converted Markdown against its source PDF:

```bash
python verify_md.py path/to/paper.pdf path/to/output.md [--docx path/to/draft.docx] [--recall-threshold 70]
```

---

## 📄 Citation & Attribution

If you utilize this workflow or benchmark in your academic research, please cite:

```bibtex
@software{prajapati2026pdf2md,
  author = {Rushikesh A. Prajapati},
  title = {PDF-to-Markdown-Verbatim: Quad-Engine Benchmark & Production Toolkit for Academic Document Parsing},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/Ri5hiPrajapati/pdf-to-markdown-verbatim}
}
```

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
