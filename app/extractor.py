import json
from app.gemini import call_gemini_api, extract_json_from_text, make_page_part, pdf_part
from app.prompts import REFERRAL_EXTRACTION_PROMPT

def extract_patient_info(referral_bytes: bytes, pa_bytes: bytes) -> dict:
    """
    Runs the Gemini prompt to extract patient info from referral and PA context.
    """
    print("[INFO] Extracting patient information using Gemini...")

    try:
        response_text = call_gemini_api(
            model="gemini-1.5-flash-latest",
            contents=[
                pdf_part(referral_bytes),
                pdf_part(pa_bytes),
                REFERRAL_EXTRACTION_PROMPT
            ]
        )
        print(f"  [DEBUG] Raw Gemini response for patient info: {response_text[:500]}...")
        raw_json_str = extract_json_from_text(response_text)
        patient_info = json.loads(raw_json_str)
        print("[INFO] Patient information extracted successfully.")
        return patient_info
    except Exception as e:
        print(f"[ERROR] Failed to extract patient info with Gemini: {e}")
        raise

def extract_field_contexts_and_mappings(pa_bytes: bytes, fields_by_page: dict, patient_info: dict) -> dict:
    """
    Iterates page-by-page to extract field contexts and then generate mappings.
    Returns a combined dictionary of field_id:value mappings.
    """
    print("[INFO] Extracting field contexts and generating mappings page by page...")
    field_mapping = {}

    for page_no, page_fields in sorted(fields_by_page.items()):
        print(f"  [INFO] Processing page {page_no} for context and mapping...")
        page_part = make_page_part(pa_bytes, page_no)

        # ---- Context Extraction Prompt ----
        prompt_ctx = f"""
You are an AI assistant specialized in annotating medical forms. Your task is to analyze page {page_no} of an attached Prior Authorization form (PA form).

**Given:**
- A JSON list of interactive form fields detected on this specific page. Each field has an `id` (its unique name), `type` (e.g., "text", "checkbox"), and `rect` (bounding box coordinates).
- The actual PA form itself (as a PDF part).

**Instructions:**
For each form field object provided in the JSON list:
1.  **Identify the Question:** Determine the precise question or purpose of the field as it appears on the PA form. Be exact.
2.  **Provide Context:** Generate a concise context (max 25 words) for each field. This context should clarify its meaning, especially if the question is ambiguous or part of a larger section.
3.  **Output Format:** Return **only** a JSON array where each object represents a form field and includes its original `name` (id), `page`, and the newly extracted `question` and `context`.

**Example Output Format:**
[
  {{
    "name": "T67",
    "page": {page_no},
    "question": "Patient's Last Name:",
    "context": "The patient's legal surname as it appears on their identification or medical records."
  }}
]

Here are the fields:
{json.dumps(page_fields, indent=2)}
        """

        try:
            context_response = call_gemini_api(
                model="gemini-1.5-flash-latest",
                contents=[page_part, prompt_ctx]
            )
            print(f"  [DEBUG] Raw Gemini response for context extraction: {context_response[:500]}...")
            field_context = json.loads(extract_json_from_text(context_response))
        except Exception as e:
            print(f"  [ERROR] Failed to parse context JSON on page {page_no}: {e}")
            continue

        # ---- Field Mapping Prompt ----
        prompt_map = f"""
You're filling page {page_no} of a Prior Authorization form.
Given the patient_info and form field context, map the correct values.

Rules:
- Return only valid JSON: {{ "T1": "John", "CB1": true, ... }}
- Skip fields if data isn't available.
- Use 'true' / 'false' for checkboxes.
- Use context to ensure accurate mapping.

--- PATIENT INFO ---
{json.dumps(patient_info, indent=2)}

--- FIELD CONTEXT ---
{json.dumps(field_context, indent=2)}
        """

        try:
            mapping_response = call_gemini_api(
                model="gemini-1.5-flash-latest",
                contents=[page_part, prompt_map]
            )
            print(f"  [DEBUG] Raw Gemini response for mapping on page {page_no}: {mapping_response[:500]}...")
            mapping = json.loads(extract_json_from_text(mapping_response))
            field_mapping.update(mapping)
        except Exception as e:
            print(f"  [ERROR] Failed to parse mapping JSON on page {page_no}: {e}")
            continue

    print("[INFO] All pages processed.")
    return field_mapping
