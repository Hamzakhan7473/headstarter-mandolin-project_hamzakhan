# layout.py – Streamlit UI Components for Smart Form Filler

import streamlit as st

def show_title():
    st.set_page_config(page_title="🧠 MedForm Auto-Filler", layout="wide")
    st.title("📄 Smart PA Form Filler")
    st.markdown("AI-powered pipeline to extract data from referrals and auto-fill Prior Authorization PDFs.")

def upload_section():
    st.subheader("🗂️ Upload Documents")
    col1, col2 = st.columns(2)
    with col1:
        pa_file = st.file_uploader("Upload Prior Authorization Form (PDF)", type=["pdf"])
    with col2:
        referral_file = st.file_uploader("Upload Referral Package (PDF)", type=["pdf"])
    return pa_file, referral_file

def show_results(output_bytes):
    st.success("✅ Form filled successfully!")
    st.download_button(
        label="📥 Download Filled PDF",
        data=output_bytes,
        file_name="filled_form.pdf",
        mime="application/pdf"
    )

def show_error(msg):
    st.error(f"❌ {msg}")