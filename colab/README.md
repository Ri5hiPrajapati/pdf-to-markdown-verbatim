# Self-Hosting NVIDIA Nemotron Parse on Google Colab (Free Tier)

This guide shows how to run **NVIDIA Nemotron Parse** on Google Colab's **free Tesla T4 GPU (15–16 GB VRAM)** with zero API subscription costs.

---

## 1. Why Nemotron Parse Fits on Colab Free Tier

| Model Metric | Value |
| :--- | :--- |
| **Model Size** | **~885M – ~903M parameters** (<1B parameters) |
| **Architecture** | Vision-Encoder-Decoder (C-RADIO vision backbone + mBART decoder) |
| **VRAM at FP16 Precision** | **~2.0 GB** |
| **Colab Free Tier GPU** | **Tesla T4 (15.3 GB VRAM)** |
| **Available Headroom** | **>13 GB free VRAM** (Zero Out-Of-Memory risk) |

---

## 2. Quickstart Code for Google Colab

Create a new notebook in [Google Colab](https://colab.research.google.com), set Runtime to **T4 GPU** (`Runtime > Change runtime type > T4 GPU`), and run:

```python
# Step 1: Install Dependencies
!pip install -q transformers torch torchvision pymupdf pillow accelerate

# Step 2: Load Nemotron Parse Model & Processor
import torch
from transformers import AutoModelForVision2Seq, AutoProcessor
import fitz # PyMuPDF
from PIL import Image
import io

model_id = "nvidia/NVIDIA-Nemotron-Parse-2.0" # or "nvidia/Nemotron-3.5-Parse"

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading {model_id} on {device}...")

processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    trust_remote_code=True
).to(device)

print("Model loaded successfully into VRAM! Memory footprint: ~2 GB.")

# Step 3: Define PDF Page Parsing Function
def parse_pdf_page(pdf_path, page_num=0):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    pix = page.get_pixmap(dpi=150)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    
    prompt = "Extract all text, sections, headings, mathematical symbols, and tables from this document page verbatim."
    inputs = processor(images=image, text=prompt, return_tensors="pt").to(device, torch.float16)
    
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=4096)
        
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_text

# Step 4: Upload and Parse your PDF
from google.colab import files
uploaded = files.upload()

for filename in uploaded.keys():
    print(f"Parsing {filename}...")
    doc = fitz.open(filename)
    full_markdown = []
    for i in range(len(doc)):
        print(f"Page {i+1}/{len(doc)}")
        page_md = parse_pdf_page(filename, i)
        full_markdown.append(page_md)
        
    out_name = filename.replace(".pdf", "_converted.md")
    with open(out_name, "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(full_markdown))
    print(f"Saved to {out_name}")
    files.download(out_name)
```

---

## 3. Benefits of Self-Hosting
1. **Zero API Cost**: 100% free; does not consume developer cloud API credits.
2. **Infinite Requests**: Process hundreds of pages without running into 40 RPM or 1,000 credit caps.
3. **Complete Privacy**: Document data never leaves your private Colab runtime.
