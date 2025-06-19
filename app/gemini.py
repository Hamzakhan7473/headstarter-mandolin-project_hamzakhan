import os
import json
import re
import fitz  # PyMuPDF
from io import BytesIO
import google.generativeai as genai

# Load Gemini API Key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Configure Gemini
genai.configure(api_key=API_KEY)

def extract_json_from_text(text: str) -> str:
    """
    Extracts JSON string from LLM output, even if wrapped in markdown or noisy formatting.
    """
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        raw_json = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found in response.")
        raw_json = text[start:end+1]

    raw_json = re.sub(r'(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'"\1":', raw_json)
    raw_json = re.sub(r',\s*([}\]])', r'\1', raw_json)

    return raw_json

def call_gemini_api(model: str, contents: list) -> str:
    """
    Calls Gemini API using the specified model and content list.
    """
    try:
        chat_model = genai.GenerativeModel(model)
        response = chat_model.generate_content(contents)
        if hasattr(response, "text") and response.text:
            return response.text
        raise ValueError("Empty response from Gemini API.")
    except Exception as e:
        print(f"[ERROR] Gemini API call failed: {e}")
        raise

def pdf_part(pdf_bytes: bytes) -> dict:
    """
    Returns full PDF file as a Gemini-compatible content part.
    """
    return {
        "mime_type": "application/pdf",
        "data": pdf_bytes
    }

def make_page_part(pdf_bytes: bytes, page_no: int) -> dict:
    """
    Extracts a specific page as a new PDF and returns as Gemini-compatible content.
    Falls back to image-rendered page if widget copy fails.
    """
    src = fitz.open(stream=pdf_bytes, filetype="pdf")

    if not (1 <= page_no <= len(src)):
        raise ValueError(f"Page number {page_no} out of bounds for PDF with {len(src)} pages.")

    try:
        dst = fitz.open()
        dst.insert_pdf(src, from_page=page_no - 1, to_page=page_no - 1)
        buf = BytesIO()
        dst.save(buf)
        return {
            "mime_type": "application/pdf",
            "data": buf.getvalue()
        }
    except Exception as e:
        print(f"[WARNING] Widget copy failed for page {page_no}, falling back to image. Error: {e}")
        page = src[page_no - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        fallback_pdf = fitz.open()
        rect = page.rect
        new_page = fallback_pdf.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)
        buf = BytesIO()
        fallback_pdf.save(buf)
        return {
            "mime_type": "application/pdf",
            "data": buf.getvalue()
        }
    finally:
        src.close()
