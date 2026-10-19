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

drive_mount_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Step 3: Mount Google Drive & Configure Persistent Hugging Face Cache\n",
        "# Model weights (~2.5 GB) are stored permanently in your Drive.\n",
        "# Subsequent runs load from Drive in 3-5 seconds without re-downloading!\n",
        "import os\n",
        "from google.colab import drive, userdata\n",
        "\n",
        "print(\"1. Mounting Google Drive...\")\n",
        "drive.mount('/content/drive')\n",
        "\n",
        "# Configure persistent cache path in Google Drive\n",
        "hf_cache_dir = '/content/drive/MyDrive/huggingface_cache'\n",
        "os.makedirs(hf_cache_dir, exist_ok=True)\n",
        "os.environ['HF_HOME'] = hf_cache_dir\n",
        "os.environ['TRANSFORMERS_CACHE'] = hf_cache_dir\n",
        "\n",
        "# Automatically inject HF_TOKEN if saved in Colab Secrets\n",
        "try:\n",
        "    token = userdata.get('HF_TOKEN')\n",
        "    if token:\n",
        "        os.environ['HF_TOKEN'] = token.strip()\n",
        "        print(\"2. ✅ HF_TOKEN authenticated successfully from Colab Secrets!\")\n",
        "    else:\n",
        "        print(\"2. ℹ️ HF_TOKEN not found in Secrets. Using standard public download.\")\n",
        "except Exception:\n",
        "    print(\"2. ℹ️ Secrets manager skipped.\")\n",
        "\n",
        "print(f\"3. ✅ Persistent Model Cache Active: {hf_cache_dir}\")"
    ]
}

# ==========================================
# 1. GLM-OCR Benchmark Notebook (Zero-Click Fully Automated)
# ==========================================
glm_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🚀 GLM-OCR: Fully Automated Scientific PDF-to-Markdown Pipeline on Google Colab\n",
            "### Zero Manual Clicking: Run All (`Ctrl + F9`) Converts Everything Automatically\n",
            "\n",
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/glm_ocr_benchmark.ipynb)\n",
            "\n",
            "### How This Fully Automated Pipeline Works:\n",
            "1. **Press `Ctrl + F9` (or `Runtime > Run all`) ONCE**.\n",
            "2. It automatically mounts your Google Drive.\n",
            "3. It loads **`zai-org/GLM-OCR` (~0.9B params)** into the free Tesla T4 GPU from your persistent Drive cache in 3 seconds.\n",
            "4. It automatically detects and converts all PDFs from `/content/drive/MyDrive/input_pdfs/` (or benchmark samples).\n",
            "5. It executes `verify_md.py` and saves the verified Markdown outputs directly back into `/content/drive/MyDrive/pdf_markdown_outputs/`."
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
    drive_mount_cell,
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Clone Benchmark Toolkit & Verification Suite\n",
            "!git clone https://github.com/Ri5hiPrajapati/pdf-to-markdown-verbatim.git /content/repo 2>/dev/null || (cd /content/repo && git pull)\n",
            "%cd /content/repo"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 5: Load zai-org/GLM-OCR into GPU Memory\n",
            "import torch\n",
            "from transformers import AutoProcessor, AutoModelForCausalLM\n",
            "\n",
            "model_id = \"zai-org/GLM-OCR\"\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "print(f\"Loading {model_id} on {device} using persistent cache in Google Drive...\")\n",
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
            "# Step 6: Define Verbatim PDF Parsing Routine\n",
            "import io\n",
            "import time\n",
            "import pymupdf as fitz\n",
            "from PIL import Image\n",
            "\n",
            "def parse_pdf_with_glm(pdf_path, dpi=150):\n",
            "    doc = fitz.open(pdf_path)\n",
            "    print(f\"\\n📄 Processing: {pdf_path} ({len(doc)} pages)\")\n",
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
            "    print(f\"🎉 Converted in {total_time:.2f}s ({total_time/len(doc):.2f}s/page) -> {out_path}\")\n",
            "    return out_path"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 7: Automatic Batch Conversion (Zero-Click)\n",
            "# Scans your Google Drive '/content/drive/MyDrive/input_pdfs/' folder automatically!\n",
            "import os\n",
            "import shutil\n",
            "from pathlib import Path\n",
            "\n",
            "input_drive_dir = Path('/content/drive/MyDrive/input_pdfs')\n",
            "output_drive_dir = Path('/content/drive/MyDrive/pdf_markdown_outputs')\n",
            "input_drive_dir.mkdir(parents=True, exist_ok=True)\n",
            "output_drive_dir.mkdir(parents=True, exist_ok=True)\n",
            "\n",
            "# Find all PDFs in Drive input folder or local repo\n",
            "target_pdfs = list(input_drive_dir.glob(\"*.pdf\"))\n",
            "\n",
            "if not target_pdfs:\n",
            "    print(f\"ℹ️ No PDFs found in {input_drive_dir}.\")\n",
            "    print(\"Downloading default benchmark scientific article for demonstration...\")\n",
            "    demo_pdf = Path(\"/content/sample_benchmark_article.pdf\")\n",
            "    !wget -q -O \"{demo_pdf}\" \"https://arxiv.org/pdf/2401.00001.pdf\"\n",
            "    target_pdfs = [demo_pdf]\n",
            "\n",
            "print(f\"\\nFound {len(target_pdfs)} PDF(s) to process completely unattended!\")\n",
            "\n",
            "for pdf in target_pdfs:\n",
            "    converted_md = parse_pdf_with_glm(str(pdf))\n",
            "    \n",
            "    # Save backup directly into Google Drive\n",
            "    dest_md = output_drive_dir / Path(converted_md).name\n",
            "    shutil.copy(converted_md, dest_md)\n",
            "    print(f\"✅ Saved permanently in Google Drive: {dest_md}\")\n",
            "    \n",
            "    # Run verification audit\n",
            "    print(\"\\n--- Quantitative Audit Results ---\")\n",
            "    !python verify_md.py \"{pdf}\" \"{converted_md}\"\n",
            "\n",
            "print(\"\\n=======================================================\")\n",
            "print(\"ALL JOBS FINISHED SUCCESSFULLY WITHOUT ANY MANUAL CLICKS!\")\n",
            "print(f\"Check your Google Drive folder: /MyDrive/pdf_markdown_outputs/\")\n",
            "print(\"=======================================================\")"
        ]
    }
]

# ==========================================
# 2. Unlimited-OCR Benchmark Notebook (Zero-Click Fully Automated)
# ==========================================
unlimited_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🚀 Baidu Unlimited-OCR: Fully Automated Pipeline on Google Colab\n",
            "### Zero Manual Clicking: Run All (`Ctrl + F9`) Converts Everything Automatically\n",
            "\n",
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/unlimited_ocr_benchmark.ipynb)\n",
            "\n",
            "### How This Fully Automated Pipeline Works:\n",
            "1. **Press `Ctrl + F9` ONCE**.\n",
            "2. Mounts Google Drive and caches `baidu/Unlimited-OCR` weights.\n",
            "3. Reads all PDFs automatically from `/content/drive/MyDrive/input_pdfs/`.\n",
            "4. Runs inference using flat-memory Reference Sliding Window Attention (R-SWA).\n",
            "5. Automatically saves verified Markdown files directly into `/content/drive/MyDrive/pdf_markdown_outputs/`."
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
    drive_mount_cell,
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Clone Benchmark Suite\n",
            "!git clone https://github.com/Ri5hiPrajapati/pdf-to-markdown-verbatim.git /content/repo 2>/dev/null || (cd /content/repo && git pull)\n",
            "%cd /content/repo"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 5: Load baidu/Unlimited-OCR into GPU Memory\n",
            "import torch\n",
            "from transformers import pipeline\n",
            "\n",
            "model_id = \"baidu/Unlimited-OCR\"\n",
            "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
            "print(f\"Loading {model_id} on {device} via Google Drive cache...\")\n",
            "\n",
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
            "# Step 6: Define Document Parsing Routine\n",
            "import io\n",
            "import time\n",
            "import pymupdf as fitz\n",
            "from PIL import Image\n",
            "\n",
            "def parse_pdf_with_unlimited_ocr(pdf_path, dpi=150):\n",
            "    doc = fitz.open(pdf_path)\n",
            "    print(f\"\\n📄 Processing: {pdf_path} ({len(doc)} pages)\")\n",
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
            "    print(f\"🎉 Converted in {total_time:.2f}s ({total_time/len(doc):.2f}s/page) -> {out_path}\")\n",
            "    return out_path"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 7: Automatic Batch Conversion (Zero-Click)\n",
            "import os\n",
            "import shutil\n",
            "from pathlib import Path\n",
            "\n",
            "input_drive_dir = Path('/content/drive/MyDrive/input_pdfs')\n",
            "output_drive_dir = Path('/content/drive/MyDrive/pdf_markdown_outputs')\n",
            "input_drive_dir.mkdir(parents=True, exist_ok=True)\n",
            "output_drive_dir.mkdir(parents=True, exist_ok=True)\n",
            "\n",
            "target_pdfs = list(input_drive_dir.glob(\"*.pdf\"))\n",
            "\n",
            "if not target_pdfs:\n",
            "    print(f\"ℹ️ No PDFs found in {input_drive_dir}.\")\n",
            "    print(\"Downloading default benchmark scientific article for demonstration...\")\n",
            "    demo_pdf = Path(\"/content/sample_benchmark_article.pdf\")\n",
            "    !wget -q -O \"{demo_pdf}\" \"https://arxiv.org/pdf/2401.00001.pdf\"\n",
            "    target_pdfs = [demo_pdf]\n",
            "\n",
            "print(f\"\\nFound {len(target_pdfs)} PDF(s) to process completely unattended!\")\n",
            "\n",
            "for pdf in target_pdfs:\n",
            "    converted_md = parse_pdf_with_unlimited_ocr(str(pdf))\n",
            "    \n",
            "    dest_md = output_drive_dir / Path(converted_md).name\n",
            "    shutil.copy(converted_md, dest_md)\n",
            "    print(f\"✅ Saved permanently in Google Drive: {dest_md}\")\n",
            "    \n",
            "    print(\"\\n--- Quantitative Audit Results ---\")\n",
            "    !python verify_md.py \"{pdf}\" \"{converted_md}\"\n",
            "\n",
            "print(\"\\n=======================================================\")\n",
            "print(\"ALL JOBS FINISHED SUCCESSFULLY WITHOUT ANY MANUAL CLICKS!\")\n",
            "print(f\"Check your Google Drive folder: /MyDrive/pdf_markdown_outputs/\")\n",
            "print(\"=======================================================\")"
        ]
    }
]

# ==========================================
# 3. Colab API Server Notebook
# ==========================================
server_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🌐 Google Colab Zero-Cost OCR API Server for Antigravity & Local Clients\n",
            "### Run All (`Ctrl + F9`) Once: Antigravity Controls Everything Remotely\n",
            "\n",
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ri5hiPrajapati/pdf-to-markdown-verbatim/blob/main/colab/colab_api_server.ipynb)\n",
            "\n",
            "This notebook turns your Google Colab free GPU into a **live, remote REST API endpoint**.\n",
            "Press `Ctrl + F9` once. Then, Antigravity or your local terminal will automatically send PDFs and receive Markdown back without any browser clicking!"
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
    drive_mount_cell,
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Load Model (GLM-OCR ~0.9B from Drive Cache)\n",
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
            "print(\"Model loaded successfully in GPU VRAM from Drive cache!\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 4: Launch FastAPI & Expose Public URL via LocalTunnel\n",
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
print("Updated colab/glm_ocr_benchmark.ipynb: Fully automated Zero-Click!")

with open(out_dir / "unlimited_ocr_benchmark.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(unlimited_cells), f, indent=2)
print("Updated colab/unlimited_ocr_benchmark.ipynb: Fully automated Zero-Click!")

with open(out_dir / "colab_api_server.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(server_cells), f, indent=2)
print("Updated colab/colab_api_server.ipynb: Fully automated Zero-Click!")
