"""
Acceleron Labs — Requirements Extraction Pipeline
==================================================
Run:  python acceleron_pipeline.py <path_to_file>

Install dependencies:
    pip install anthropic pymupdf pdfplumber pytesseract pillow openpyxl pandas
    sudo apt-get install tesseract-ocr        # Linux / Colab
"""

import os
import re
import sys
import json
import io

import anthropic
import pandas as pd


# ─────────────────────────────────────────────
# 0. CLIENT  (API key from environment only)
# ─────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL  = "claude-3-5-haiku-20241022"


# ─────────────────────────────────────────────
# 1. FILE TYPE DETECTION
# ─────────────────────────────────────────────
def detect_file_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[-1].lower().strip()
    if ext == ".pdf":
        return "pdf"
    elif ext in (".xlsx", ".xls"):
        return "excel"
    elif ext == ".txt":
        return "txt"
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ─────────────────────────────────────────────
# 2A. PDF — detect what's inside each page
# ─────────────────────────────────────────────
def _page_has_text(page) -> bool:
    """True if the page has selectable/digital text."""
    return bool(page.get_text("text").strip())


def _page_has_tables(page) -> bool:
    """True if pdfplumber finds at least one table on this page."""
    try:
        import pdfplumber
        with pdfplumber.open(page._parent.name) as pdf:
            pl_page = pdf.pages[page.number]
            tables = pl_page.extract_tables()
            return bool(tables and any(tables))
    except Exception:
        return False


# ─────────────────────────────────────────────
# 2B. EXTRACT — plain text via PyMuPDF
# ─────────────────────────────────────────────
def extract_text_pymupdf(file_path: str) -> str:
    import fitz
    doc  = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text


# ─────────────────────────────────────────────
# 2C. EXTRACT — tables via pdfplumber
# ─────────────────────────────────────────────
def extract_text_tables(file_path: str) -> str:
    import pdfplumber
    sentences = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    row = [str(cell).strip() for cell in row if cell]
                    if len(row) >= 2:
                        # Turn row into a readable sentence for the LLM
                        sentence = f"{row[0]}: {' | '.join(row[1:])}"
                        sentences.append(sentence)
                    elif len(row) == 1:
                        sentences.append(row[0])
    return "\n".join(sentences)


# ─────────────────────────────────────────────
# 2D. EXTRACT — scanned images via OCR
# ─────────────────────────────────────────────
def extract_text_ocr(file_path: str) -> str:
    import fitz
    import pytesseract
    from PIL import Image

    doc       = fitz.open(file_path)
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix  = page.get_pixmap(dpi=300)          # higher DPI = better OCR
        img  = Image.open(io.BytesIO(pix.tobytes()))
        text = pytesseract.image_to_string(img)
        full_text += text + "\n"
    return full_text


# ─────────────────────────────────────────────
# 2E. EXTRACT — Excel files
# ─────────────────────────────────────────────
def extract_text_excel(file_path: str) -> str:
    df   = pd.read_excel(file_path, sheet_name=None)  # read ALL sheets
    text = ""
    for sheet_name, sheet_df in df.items():
        text += f"\n[Sheet: {sheet_name}]\n"
        for col in sheet_df.columns:
            for val in sheet_df[col].dropna():
                text += str(val) + "\n"
    return text


# ─────────────────────────────────────────────
# 2F. SMART PDF ROUTER
#     Combines text + table + OCR as needed
# ─────────────────────────────────────────────
def extract_text_pdf(file_path: str) -> str:
    import fitz
    doc        = fitz.open(file_path)
    text_parts = []

    has_any_text   = any(_page_has_text(p) for p in doc)
    has_any_tables = False
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for p in pdf.pages:
                if p.extract_tables():
                    has_any_tables = True
                    break
    except Exception:
        pass

    if has_any_text:
        text_parts.append(extract_text_pymupdf(file_path))

    if has_any_tables:
        text_parts.append(extract_text_tables(file_path))

    if not has_any_text:
        # Scanned — fall back to OCR
        text_parts.append(extract_text_ocr(file_path))

    return "\n\n".join(text_parts)


# ─────────────────────────────────────────────
# 3. UNIFIED EXTRACTOR ENTRY POINT
# ─────────────────────────────────────────────
def extract_text(file_path: str) -> str:
    file_type = detect_file_type(file_path)
    print(f"[1/4] Detected file type: {file_type}")

    if file_type == "pdf":
        return extract_text_pdf(file_path)
    elif file_type == "excel":
        return extract_text_excel(file_path)
    elif file_type == "txt":
        with open(file_path, "r") as f:
            return f.read()


# ─────────────────────────────────────────────
# 4. CLEAN RAW TEXT
# ─────────────────────────────────────────────
def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)          # collapse whitespace
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # remove non-ASCII
    return text.strip()


# ─────────────────────────────────────────────
# 5. CHUNK  (avoids token limit crashes)
# ─────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 3000) -> list[str]:
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return chunks if chunks else [""]   # never return empty list


# ─────────────────────────────────────────────
# 6. PROMPT
# ─────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are given raw text from a government tender document.

Tasks:
1. Fix broken sentences and OCR errors.
2. Extract ALL requirements — do not skip any.
3. Classify each requirement as Hardware OR Software.
   - Hardware: CPU, RAM, storage, ports, power, physical specs, networking hardware
   - Software: OS, protocols, security, access control, logs, firmware, software tools

Return STRICT JSON ONLY — no explanation, no markdown:
{{
  "rows": [
    {{"Category": "Hardware", "Parameter": "RAM", "Value": "16 GB minimum"}},
    {{"Category": "Software", "Parameter": "Protocol", "Value": "TLS 1.2"}}
  ]
}}

Rules:
- One requirement per row.
- Do NOT merge multiple requirements into one row.
- Do NOT add requirements not present in the text.
- Do NOT hallucinate values.

TEXT:
{chunk}
"""

def build_prompt(chunk: str) -> str:
    return PROMPT_TEMPLATE.format(chunk=chunk)


# ─────────────────────────────────────────────
# 7. CALL LLM  (with error handling)
# ─────────────────────────────────────────────
def process_chunk(chunk: str) -> list[dict]:
    prompt   = build_prompt(chunk)
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 2048,
        messages   = [{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text

    # Strip markdown fences if model adds them
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        data = json.loads(raw)
        return data.get("rows", [])
    except json.JSONDecodeError:
        print(f"  [!] JSON parse failed for a chunk. Raw output:\n{raw[:300]}")
        return []


# ─────────────────────────────────────────────
# 8. RUN ALL CHUNKS & MERGE
# ─────────────────────────────────────────────
def process_all_chunks(chunks: list[str]) -> list[dict]:
    all_rows = []
    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i+1}/{len(chunks)}...")
        rows = process_chunk(chunk)
        all_rows.extend(rows)
    return all_rows


# ─────────────────────────────────────────────
# 9. EXPORT TO EXCEL  (two sheets)
# ─────────────────────────────────────────────
def export_to_excel(rows: list[dict], output_path: str = "output.xlsx"):
    if not rows:
        print("[!] No rows to export.")
        return

    df       = pd.DataFrame(rows)
    hardware = df[df["Category"].str.lower() == "hardware"]
    software = df[df["Category"].str.lower() == "software"]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        hardware.drop(columns=["Category"]).reset_index(drop=True).to_excel(
            writer, sheet_name="Hardware Requirements", index=False
        )
        software.drop(columns=["Category"]).reset_index(drop=True).to_excel(
            writer, sheet_name="Software Requirements", index=False
        )

    print(f"[4/4] Exported to {output_path}")
    print(f"      Hardware rows: {len(hardware)}  |  Software rows: {len(software)}")


# ─────────────────────────────────────────────
# 10. MAIN
# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python acceleron_pipeline.py <path_to_file>")
        sys.exit(1)

    file_path   = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.xlsx"

    # Step 1 — extract
    raw_text    = extract_text(file_path)
    print(f"[2/4] Extracted {len(raw_text)} characters")

    # Step 2 — clean + chunk
    cleaned     = clean_text(raw_text)
    chunks      = chunk_text(cleaned)
    print(f"[3/4] Processing {len(chunks)} chunk(s) through Claude...")

    # Step 3 — LLM
    rows        = process_all_chunks(chunks)
    print(f"      Total requirements found: {len(rows)}")

    # Step 4 — export
    export_to_excel(rows, output_path)


if __name__ == "__main__":
    main()
