import os
import json
import google.generativeai as genai

# Configure Gemini API key
genai.configure(api_key="")

# Load Gemini 1.5 Flash model
model = genai.GenerativeModel("models/gemini-1.5-flash")

def extract_with_gemini(sections: dict, drug_name: str = "") -> dict:
    """
    Extracts relevant prior authorization (PA) fields using Gemini from a referral note.
    Returns a clean dictionary with the necessary keys.
    """

    # Construct base prompt
    prompt = f"""
You are a helpful medical assistant.

Based on the referral notes provided below, extract the following structured JSON object.

If any value is not available, leave it as an empty string.

JSON format:
{{
  "patient_name": "string",
  "date_of_birth": "string",
  "insurance_id": "string",
  "diagnosis": "string",
  "prior_treatments": "string",
  "provider_npi": "string",
  "drug_requested": "{drug_name or '[Unknown]'}",
  "medical_justification": "string"
}}

--- Referral Notes Below ---
"""

    for section, text in sections.items():
        if text.strip():
            prompt += f"\n### {section}:\n{text.strip()}"

    try:
        # Generate response
        response = model.generate_content(prompt)
        content = response.text.strip()

        print(f"\n[⚠️ Gemini] Raw Output:\n{content}\n")

        # Attempt to locate JSON block
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        json_text = content[json_start:json_end]

        # Parse JSON
        parsed = json.loads(json_text)

        # Required fields
        required_fields = [
            "patient_name", "date_of_birth", "insurance_id", "diagnosis",
            "prior_treatments", "provider_npi", "drug_requested", "medical_justification"
        ]

        # Clean output
        result = {field: parsed.get(field, "").strip() for field in required_fields}
        return result

    except Exception as e:
        print(f"[Gemini Error] {e}")
        return {
            "patient_name": "",
            "date_of_birth": "",
            "insurance_id": "",
            "diagnosis": "",
            "prior_treatments": "",
            "provider_npi": "",
            "drug_requested": drug_name,
            "medical_justification": ""
        }
