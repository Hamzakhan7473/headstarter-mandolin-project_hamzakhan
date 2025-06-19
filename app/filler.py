import fitz # PyMuPDF
from io import BytesIO
import os

def extract_fields_with_positions(pdf_bytes: bytes) -> list:
    """
    Extracts interactive form fields from a PDF along with their properties.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    fields = []
    for page_num, page in enumerate(doc, start=1):
        for w in page.widgets() or []:
            fields.append({
                "name":  w.field_name,
                "type":  "checkbox" if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX else "text",
                "value": w.field_value, # Current value
                "page":  page_num,
                "rect":  list(map(float, w.rect))
            })
    doc.close()
    return fields

def fill_pdf_form_and_save(pa_bytes: bytes, field_mapping: dict, output_path: str) -> bool:
    """
    Fills an interactive PDF form with the provided field_mapping and saves it.
    """
    print(f"[INFO] Attempting to fill PDF form and save to {output_path}...")
    try:
        doc = fitz.open(stream=pa_bytes, filetype="pdf")
        
        # Check if the PDF has form fields
        if not doc.is_form_pdf:
            print("[WARNING] The provided PDF is not an interactive form PDF. Cannot fill fields.")
            doc.close()
            return False

        filled_count = 0
        for page in doc:
            for w in page.widgets() or []:
                fid = w.field_name
                if fid in field_mapping:
                    val = field_mapping[fid]
                    # Convert to appropriate type for PyMuPDF
                    if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                        # PyMuPDF expects "Yes" or "Off" for checkboxes
                        w.field_value = "Yes" if bool(val) else "Off"
                    else:
                        w.field_value = str(val) # Convert all other types to string
                    
                    # Update the field in the document
                    w.update()
                    filled_count += 1
                    # print(f"  [DEBUG] Filled '{fid}' with '{w.field_value}'") # Debug print

        if filled_count > 0:
            doc.save(output_path, garbage=4, deflate=True) # Optimize and compress
            print(f"[SUCCESS] PDF form filled ({filled_count} fields) and saved to: {output_path}")
            return True
        else:
            print("[INFO] No fields were filled in the PDF. It might be a flat PDF or no matching data.")
            doc.save(output_path) # Save original even if no fields filled
            return False
        
    except Exception as e:
        print(f"[ERROR] An error occurred during PDF form filling: {e}")
        return False
    finally:
        if 'doc' in locals() and not doc.is_closed:
            doc.close()