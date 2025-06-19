# app/main.py

import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from io import BytesIO

from app.extractor import extract_patient_info, extract_field_contexts_and_mappings
from app.filler import extract_fields_with_positions, fill_pdf_form_and_save
from app.gemini import API_KEY # Import API_KEY to check if it's set for UI guidance

# --- STREAMLIT UI ---
st.set_page_config(layout="wide", page_title="MedFill - Automate Insurance Forms")

st.title("SimplifyMed - Automate Insurance Forms")
st.markdown("Upload your Prior Authorization (PA) form and patient's referral package to automatically extract information and fill the PA form.")

# Check for API Key
if not API_KEY:
    st.warning("🚨 **GEMINI_API_KEY** environment variable not set. Please set it to use the application.")
    st.info("You can set it in your terminal before running: `export GEMINI_API_KEY='your_api_key_here'`")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    pa_file = st.file_uploader("📤 Upload Prior Authorization (PA) Form PDF", type=["pdf"])

with col2:
    ref_file = st.file_uploader("📤 Upload Patient Referral Package PDF", type=["pdf"])

if st.button("🚀 Process and Fill Form", type="primary"):
    if not pa_file or not ref_file:
        st.error("❗ Please upload both the PA form and the referral package to proceed.")
        st.stop()

    st.info("Processing your documents... This may take a few moments.")

    # Read file bytes
    pa_bytes = pa_file.read()
    ref_bytes = ref_file.read()

    with st.spinner("1/3: Extracting patient information from referral package..."):
        try:
            patient_info = extract_patient_info(ref_bytes, pa_bytes)
            st.success("✅ Patient information extracted successfully!")
            st.subheader("Extracted Patient Information:")
            st.json(patient_info)
        except Exception as e:
            st.error(f"❌ Failed to extract patient information: {e}. Please check the referral package format or Gemini API key.")
            st.stop()

    # 2) Extract PA fields
    with st.spinner("2/3: Identifying form fields in the PA form..."):
        try:
            fields = extract_fields_with_positions(pa_bytes)
            if not fields:
                st.warning("⚠️ No interactive form fields found in the PA form. The PDF might be flat or corrupted.")
                # You could add a fallback here for flat PDF filling using `fill_flat_pdf`
                # if that's a requirement for forms without interactive fields.
                st.stop()

            fields_by_page = {}
            for f in fields:
                fields_by_page.setdefault(f["page"], []).append({
                    "id":    f["name"],
                    "type":  f["type"],
                    "rect":  f["rect"]
                })
            st.success(f"Found {len(fields)} interactive fields across {len(fields_by_page)} pages.")
        except Exception as e:
            st.error(f" Failed to extract fields from PA form: {e}")
            st.stop()

    # 3) Page-by-page context and mapping
    with st.spinner("3/3: Generating field contexts and mapping patient data to fields..."):
        try:
            field_mapping = extract_field_contexts_and_mappings(pa_bytes, fields_by_page, patient_info)
            if not field_mapping:
                st.warning("No data was mapped to form fields. This could mean no relevant information was found or the mapping was not successful.")
                st.stop()
            st.success(f" Successfully mapped {len(field_mapping)} fields!")
            st.subheader("Mapped Field Values (for debugging):")
            st.json(field_mapping)

        except Exception as e:
            st.error(f"Failed to generate field mappings: {e}")
            st.stop()

    # 4) Fill PDF and offer download
    with st.spinner("Filling the PDF form..."):
        try:
            # Create a temporary output path for the filled PDF
            output_dir = "temp_filled_pdfs"
            os.makedirs(output_dir, exist_ok=True)
            output_file_name = f"filled_PA_{pa_file.name.replace('.pdf', '')}_{os.urandom(4).hex()}.pdf"
            output_pdf_path = os.path.join(output_dir, output_file_name)

            pdf_filled = fill_pdf_form_and_save(pa_bytes, field_mapping, output_pdf_path)

            if pdf_filled:
                with open(output_pdf_path, "rb") as f:
                    filled_pdf_bytes = f.read()

                st.download_button(
                    label="⬇️ Download Filled PA Form",
                    data=filled_pdf_bytes,
                    file_name="filled_PA_form.pdf",
                    mime="application/pdf",
                    help="Click to download the PA form with extracted data filled in."
                )
                st.success("🎉 Your filled PA form is ready for download!")
                # Clean up the temporary file
                os.remove(output_pdf_path)
            else:
                st.error("❗ Could not save the filled PDF. Check previous error messages.")

        except Exception as e:
            st.error(f"❌ An error occurred during the final PDF saving step: {e}")

st.markdown("---")
st.info("Developed with PyMuPDF and Google Gemini.")