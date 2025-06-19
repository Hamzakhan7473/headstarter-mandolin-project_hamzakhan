from google.api_core import types  # Add this import for types.Part
import json
import re
import fitz  # PyMuPDF for PDF manipulation
from io import BytesIO

def extract_json(text):
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    raw = text[start:end+1]
    raw = re.sub(r'(?m)^\s*([A-Za-z0-9_]+)\s*:', r'"\1":', raw)
    raw = re.sub(r',\s*([}\]])', r'\1', raw)
    return raw

# Wrap referral context extraction code exactly

def extract_patient_info(referral_bytes, pa_bytes):
    """
    Runs the user-provided Gemini prompt to extract patient info.
    """
    pdf1 = types.Part.from_bytes(data=referral_bytes, mime_type='application/pdf')
    pdf2 = types.Part.from_bytes(data=pa_bytes, mime_type='application/pdf')
    # Define the referral prompt to be used in the Gemini model
    REFERRAL_PROMPT = "Please extract the patient information from the provided referral and PA documents in JSON format."

    # Import or initialize your Gemini client here
    from google.generativeai import Client
    client = Client()  # Adjust initialization as needed

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            pdf1,
            pdf2,
            REFERRAL_PROMPT
        ]
    ).text
    print(response)
    raw = extract_json(response)
    return json.loads(raw)

# Wrap existing page-by-page logic into functions

def make_page_part(pdf_bytes, page_no):
    """
    Create a one-page PDF part from the given PDF bytes.
    Tries to copy the form page; on XRef errors, falls back to image-based PDF.
    """
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    # Attempt to copy with widgets
    try:
        dst = fitz.open()  # new empty PDF
        dst.insert_pdf(src, from_page=page_no-1, to_page=page_no-1)
        # remove any leftover widget annotations to avoid XRef errors
        for w in dst[0].widgets() or []:
            dst[0].delete_widget(w)
        buf = BytesIO()
        dst.save(buf)
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="application/pdf")
    except Exception:
        # Fallback: render page as image PDF
        page = src[page_no-1]
        pix = page.get_pixmap()
        new_pdf = fitz.open()
        rect = page.rect
        new_page = new_pdf.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)
        buf = BytesIO()
        new_pdf.save(buf)
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="application/pdf")


def extract_fields_with_positions(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    fields = []
    for page_num, page in enumerate(doc, start=1):
        for w in page.widgets() or []:
            fields.append({
                "name":  w.field_name,
                "type":  "checkbox" if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX else "text",
                "value": w.field_value,
                "page":  page_num,
                "rect":  list(map(float, w.rect))
            })
    return fields