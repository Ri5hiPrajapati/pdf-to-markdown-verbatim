import json
from pathlib import Path

def make_notebook(cells, gpu=True):
    nb = {
        'cells': cells,
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'name': 'python3'},
            'language_info': {'name': 'python'}
        },
        'nbformat': 4,
        'nbformat_minor': 0
    }
    if gpu:
        nb['metadata']['accelerator'] = 'GPU'
        nb['metadata']['colab'] = {'gpuType': 'T4', 'provenance': []}
    return nb

# ==========================================
# 1. GLM-OCR Benchmark Notebook
# ==========================================
glm_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🚀 GLM-OCR: Open-Source Scientific PDF-to-Markdown Benchmark on Google Colab (Free T4 GPU)\n",
            "\n",
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/glm_ocr_benchmark.ipynb)\n",
            "\n",
            "This notebook runs **Zhipu AI's GLM-OCR** (`zai-org/GLM-OCR`) on Google Colab's free **Tesla T4 GPU (15.3 GB VRAM)**.\n",
            "\n",
            "### Model Specifications:\n",
            "* **Architecture**: CogViT visual encoder (~0.4B) + GLM-0.5B language decoder = **~0.9B total parameters**.\n",
            "* **VRAM Footprint**: **~2.5 GB in BF16/FP16** (easily runs on Colab's 15 GB T4 with >12 GB headroom).\n",
            "* **Capabilities**: Specialized in scientific layouts, dense multi-column academic text, mathematical LaTeX, and multi-row tables."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 1: Verify Hardware Accelerator\n",
            "!nvidia-smi"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 2: Install Dependencies\n",
            "!pip install -q transformers>=4.45.0 torch torchvision pymupdf pillow accelerate markdown"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Clone Benchmark Toolkit & Verification Harness\n",
            "!git clone https://github.com/Ri5hiPrajapati/pdf-to-markdown-verbatim.git\n",
            "%cd pdf-to-markdown-verbatim"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Load zai-org/GLM-OCR into GPU Memory\n",
            "import torch\n",
            "from transformers import AutoProcessor, AutoModelForCausalLM\n",
            "\n",
            "model_id = \"zai-org/GLM-OCR\"\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "print(f\"Loading {model_id} on {device}...\")\n",
            "\n",
            "processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)\n",
            "model = AutoModelForCausalLM.from_pretrained(\n",
            "    model_id,\n",
            "    device_map=\"auto\",\n",
            "    torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,\n",
            "    trust_remote_code=True\n",
            ")\n",
            "\n",
            "print(\"✅ GLM-OCR successfully loaded into VRAM!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 5: Define Verbatim PDF Parsing Pipeline\n",
            "import io\n",
            "import time\n",
            "import pymupdf as fitz\n",
            "from PIL import Image\n",
            "\n",
            "def parse_pdf_with_glm(pdf_path, dpi=150):\n",
            "    doc = fitz.open(pdf_path)\n",
            "    print(f\"Processing: {pdf_path} ({len(doc)} pages)\")\n",
            "    \n",
            "    page_mds = []\n",
            "    t0 = time.time()\n",
            "    \n",
            "    for idx, page in enumerate(doc):\n",
            "        pt0 = time.time()\n",
            "        pix = page.get_pixmap(dpi=dpi)\n",
            "        image = Image.open(io.BytesIO(pix.tobytes(\"png\"))).convert(\"RGB\")\n",
            "        \n",
            "        messages = [\n",
            "            {\n",
            "                \"role\": \"user\",\n",
            "                \"content\": [\n",
            "                    {\"type\": \"image\", \"image\": image},\n",
            "                    {\"type\": \"text\", \"text\": \"Text Recognition: Extract all text, headings, equations, and tables verbatim into Markdown.\"}\n",
            "                ]\n",
            "            }\n",
            "        ]\n",
            "        \n",
            "        inputs = processor.apply_chat_template(\n",
            "            messages,\n",
            "            tokenize=True,\n",
            "            add_generation_prompt=True,\n",
            "            return_dict=True,\n",
            "            return_tensors=\"pt\"\n",
            "        ).to(model.device)\n",
            "        \n",
            "        with torch.no_grad():\n",
            "            outputs = model.generate(**inputs, max_new_tokens=4096)\n",
            "            \n",
            "        # Decode only newly generated tokens\n",
            "        prompt_len = inputs[\"input_ids\"].shape[-1]\n",
            "        generated_text = processor.decode(outputs[0][prompt_len:], skip_special_tokens=True).strip()\n",
            "        page_mds.append(generated_text)\n",
            "        print(f\"  • Page {idx+1}/{len(doc)}: done in {time.time()-pt0:.2f}s ({len(generated_text)} chars)\")\n",
            "        \n",
            "    total_time = time.time() - t0\n",
            "    full_markdown = \"\\n\\n---\\n\\n\".join(page_mds)\n",
            "    out_path = pdf_path.replace(\".pdf\", \"_glm_ocr.md\")\n",
            "    with open(out_path, \"w\", encoding=\"utf-8\") as f:\n",
            "        f.write(full_markdown)\n",
            "        \n",
            "    print(f\"\\n🎉 Conversion complete in {total_time:.2f}s ({total_time/len(doc):.2f}s/page)!\")\n",
            "    print(f\"Saved to: {out_path}\")\n",
            "    return out_path"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 6: Upload a Benchmark PDF (e.g. Research Article 4)\n",
            "from google.colab import files\n",
            "print(\"Upload your benchmark PDF file (or cancel to use default demo):\")\n",
            "uploaded = files.upload()\n",
            "\n",
            "if uploaded:\n",
            "    target_pdf = list(uploaded.keys())[0]\n",
            "else:\n",
            "    # If no upload, download sample\n",
            "    target_pdf = \"sample_paper.pdf\"\n",
            "    !wget -q -O sample_paper.pdf \"https://arxiv.org/pdf/2401.00001.pdf\"\n",
            "\n",
            "converted_md = parse_pdf_with_glm(target_pdf)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 7: Run Quantitative Audit via verify_md.py\n",
            "!python verify_md.py \"{target_pdf}\" \"{converted_md}\""
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 8: Download Converted Markdown\n",
            "files.download(converted_md)"
        ]
    }
]

# ==========================================
# 2. Unlimited-OCR Benchmark Notebook
# ==========================================
unlimited_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🚀 Baidu Unlimited-OCR: Open-Source Scientific PDF-to-Markdown Benchmark on Google Colab\n",
            "\n",
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/unlimited_ocr_benchmark.ipynb)\n",
            "\n",
            "This notebook runs **Baidu's Unlimited-OCR** (`baidu/Unlimited-OCR`) on Google Colab's free **Tesla T4 GPU (15.3 GB VRAM)**.\n",
            "\n",
            "### Model Specifications:\n",
            "* **Architecture**: Reference Sliding Window Attention (R-SWA) + High-compression Vision Encoder (DeepSeek-OCR lineage).\n",
            "* **Key Innovation**: Flat, constant KV cache during autoregressive generation, eliminating out-of-memory errors on long multi-page documents.\n",
            "* **Output**: Native structured Markdown with formulas and table alignments."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 1: Verify Hardware Accelerator\n",
            "!nvidia-smi"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 2: Install Dependencies\n",
            "!pip install -q transformers>=4.45.0 torch torchvision pymupdf pillow accelerate einops addict easydict psutil markdown"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Clone Benchmark Toolkit & Verification Harness\n",
            "!git clone https://github.com/Ri5hiPrajapati/pdf-to-markdown-verbatim.git\n",
            "%cd pdf-to-markdown-verbatim"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Load baidu/Unlimited-OCR into GPU Memory\n",
            "import torch\n",
            "from transformers import AutoModel, AutoTokenizer, pipeline\n",
            "\n",
            "model_id = \"baidu/Unlimited-OCR\"\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "print(f\"Loading {model_id} on {device}...\")\n",
            "\n",
            "# Load using pipeline or AutoModel\n",
            "pipe = pipeline(\"image-text-to-text\", model=model_id, trust_remote_code=True, device=0 if torch.cuda.is_available() else -1)\n",
            "print(\"✅ Baidu Unlimited-OCR loaded successfully!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 5: Define Document Parsing Routine\n",
            "import io\n",
            "import time\n",
            "import pymupdf as fitz\n",
            "from PIL import Image\n",
            "\n",
            "def parse_pdf_with_unlimited_ocr(pdf_path, dpi=150):\n",
            "    doc = fitz.open(pdf_path)\n",
            "    print(f\"Processing: {pdf_path} ({len(doc)} pages)\")\n",
            "    \n",
            "    page_mds = []\n",
            "    t0 = time.time()\n",
            "    \n",
            "    for idx, page in enumerate(doc):\n",
            "        pt0 = time.time()\n",
            "        pix = page.get_pixmap(dpi=dpi)\n",
            "        img = Image.open(io.BytesIO(pix.tobytes(\"png\"))).convert(\"RGB\")\n",
            "        \n",
            "        messages = [\n",
            "            {\n",
            "                \"role\": \"user\",\n",
            "                \"content\": [\n",
            "                    {\"type\": \"image\", \"image\": img},\n",
            "                    {\"type\": \"text\", \"text\": \"Extract all text, sections, formulas, and tables from this page verbatim into Markdown.\"}\n",
            "                ]\n",
            "            }\n",
            "        ]\n",
            "        \n",
            "        result = pipe(text=messages)\n",
            "        out_text = result[0][\"generated_text\"] if isinstance(result, list) else str(result)\n",
            "        page_mds.append(out_text)\n",
            "        print(f\"  • Page {idx+1}/{len(doc)}: done in {time.time()-pt0:.2f}s ({len(out_text)} chars)\")\n",
            "        \n",
            "    total_time = time.time() - t0\n",
            "    full_markdown = \"\\n\\n---\\n\\n\".join(page_mds)\n",
            "    out_path = pdf_path.replace(\".pdf\", \"_unlimited_ocr.md\")\n",
            "    with open(out_path, \"w\", encoding=\"utf-8\") as f:\n",
            "        f.write(full_markdown)\n",
            "        \n",
            "    print(f\"\\n🎉 Conversion complete in {total_time:.2f}s ({total_time/len(doc):.2f}s/page)!\")\n",
            "    print(f\"Saved to: {out_path}\")\n",
            "    return out_path"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 6: Upload a Benchmark PDF\n",
            "from google.colab import files\n",
            "print(\"Upload your benchmark PDF file:\")\n",
            "uploaded = files.upload()\n",
            "\n",
            "if uploaded:\n",
            "    target_pdf = list(uploaded.keys())[0]\n",
            "else:\n",
            "    target_pdf = \"sample_paper.pdf\"\n",
            "    !wget -q -O sample_paper.pdf \"https://arxiv.org/pdf/2401.00001.pdf\"\n",
            "\n",
            "converted_md = parse_pdf_with_unlimited_ocr(target_pdf)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 7: Run Quantitative Audit via verify_md.py\n",
            "!python verify_md.py \"{target_pdf}\" \"{converted_md}\""
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 8: Download Converted Markdown\n",
            "files.download(converted_md)"
        ]
    }
]

# ==========================================
# 3. Colab API Server (FastAPI + LocalTunnel)
# ==========================================
server_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🌐 Google Colab Zero-Cost OCR API Server for Antigravity & Local Clients\n",
            "\n",
            "This notebook turns your Google Colab free GPU into a **live, remote REST API endpoint**.\n",
            "You can send PDFs from your local PC (or Antigravity) to this Colab server and receive converted Markdown back instantly!"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 1: Install Server Dependencies\n",
            "!pip install -q fastapi uvicorn pyngrok nest-asyncio pymupdf transformers torch accelerate pillow"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 2: Load Model (GLM-OCR ~0.9B)\n",
            "import torch\n",
            "from transformers import AutoProcessor, AutoModelForCausalLM\n",
            "\n",
            "model_id = \"zai-org/GLM-OCR\"\n",
            "processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)\n",
            "model = AutoModelForCausalLM.from_pretrained(\n",
            "    model_id,\n",
            "    device_map=\"auto\",\n",
            "    torch_dtype=torch.float16,\n",
            "    trust_remote_code=True\n",
            ")\n",
            "print(\"Model loaded successfully in GPU VRAM!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Launch FastAPI & Expose Public URL via LocalTunnel\n",
            "from fastapi import FastAPI, UploadFile, File\n",
            "from fastapi.responses import JSONResponse\n",
            "import uvicorn\n",
            "import threading\n",
            "import io\n",
            "import pymupdf as fitz\n",
            "from PIL import Image\n",
            "\n",
            "app = FastAPI(title=\"Colab OCR Engine\")\n",
            "\n",
            "@app.post(\"/parse\")\n",
            "async def parse_endpoint(file: UploadFile = File(...)):\n",
            "    contents = await file.read()\n",
            "    doc = fitz.open(stream=contents, filetype=\"pdf\")\n",
            "    page_mds = []\n",
            "    \n",
            "    for idx, page in enumerate(doc):\n",
            "        pix = page.get_pixmap(dpi=150)\n",
            "        img = Image.open(io.BytesIO(pix.tobytes(\"png\"))).convert(\"RGB\")\n",
            "        messages = [\n",
            "            {\n",
            "                \"role\": \"user\",\n",
            "                \"content\": [\n",
            "                    {\"type\": \"image\", \"image\": img},\n",
            "                    {\"type\": \"text\", \"text\": \"Extract all text, sections, and tables verbatim into Markdown.\"}\n",
            "                ]\n",
            "            }\n",
            "        ]\n",
            "        inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors=\"pt\").to(model.device)\n",
            "        with torch.no_grad():\n",
            "            outputs = model.generate(**inputs, max_new_tokens=4096)\n",
            "        prompt_len = inputs[\"input_ids\"].shape[-1]\n",
            "        text = processor.decode(outputs[0][prompt_len:], skip_special_tokens=True).strip()\n",
            "        page_mds.append(text)\n",
            "        \n",
            "    return {\"status\": \"success\", \"pages\": len(doc), \"markdown\": \"\\n\\n---\\n\\n\".join(page_mds)}\n",
            "\n",
            "def run_server():\n",
            "    uvicorn.run(app, host=\"0.0.0.0\", port=8000)\n",
            "\n",
            "threading.Thread(target=run_server, daemon=True).start()\n",
            "print(\"Server running on port 8000.\")\n",
            "\n",
            "# Expose via localtunnel\n",
            "!npx localtunnel --port 8000"
        ]
    }
]

out_dir = Path("D:/SIDE PROJECTS/pdf-to-markdown-verbatim/colab")
out_dir.mkdir(parents=True, exist_ok=True)

with open(out_dir / "glm_ocr_benchmark.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(glm_cells), f, indent=2)
print("Created colab/glm_ocr_benchmark.ipynb")

with open(out_dir / "unlimited_ocr_benchmark.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(unlimited_cells), f, indent=2)
print("Created colab/unlimited_ocr_benchmark.ipynb")

with open(out_dir / "colab_api_server.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(server_cells), f, indent=2)
print("Created colab/colab_api_server.ipynb")
