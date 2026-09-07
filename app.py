
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import json
import re

st.set_page_config(page_title="The Sen Labs", layout="centered")
st.title("The Sen Labs - Diagnostic Reporting")

# API Key handling
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# Patient Information
st.subheader("Patient Details")
p_name = st.text_input("Patient Name", value="Dipankar Sen")
col1, col2 = st.columns(2)
with col1:
    p_age = st.text_input("Age", value="26")
    p_doctor = st.text_input("Referred By", value="Self")
with col2:
    p_sex = st.selectbox("Sex", ["Male (M)", "Female (F)", "Other"])
    p_contact = st.text_input("Lab Contact", value="9076816740")

# Photo Capture / Upload
st.subheader("Analyzer Screen / Printout Slip")
camera_photo = st.camera_input("Take photo from camera")
uploaded_file = st.file_uploader("Or upload image from gallery", type=["jpg", "jpeg", "png"])

active_image = camera_photo or uploaded_file

if "extracted_tests" not in st.session_state:
    st.session_state.extracted_tests = {}

if active_image and st.button("Extract Data from Photo"):
    if not api_key:
        st.error("Pehle sidebar me apni API Key dalein!")
    else:
        with st.spinner("Analyzing machine screen and reading values..."):
            try:
                # Initialize GenAI Client with new auth token
                client = genai.Client(api_key=api_key)
                
                prompt = """
                Examine this laboratory analyzer display or printed slip.
                Extract all test parameters and numeric results (e.g., Hb, TLC/WBC, RBC, Platelets, MCV, MCH, Neutrophils, Lymphocytes, ESR, Glucose).
                Output strictly a valid JSON object where keys are standard test names and values are strings/numbers.
                Do not include markdown triple backticks.
                """
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=active_image.getvalue(),
                            mime_type=active_image.type or "image/jpeg"
                        ),
                        prompt
                    ]
                )
                
                raw_text = response.text.strip()
                cleaned_json = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
                st.session_state.extracted_tests = json.loads(cleaned_json)
                st.success("Values extracted! Check and edit below if required.")
            except Exception as err:
                st.error(f"Extraction error: {err}")

# Edit and Generate Section
if st.session_state.extracted_tests:
    st.subheader("Verify & Edit Values")
    final_data = {}
    for test, val in st.session_state.extracted_tests.items():
        final_data[test] = st.text_input(f"{test}", value=str(val))
    
    if st.button("Generate & Download PDF"):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "THE SEN LABS")
        c.setFont("Helvetica", 9)
        c.drawString(50, 736, f"Contact: +91 {p_contact}  |  Clinical Pathology & Diagnostics")
        c.line(50, 725, 550, 725)
        
        # Patient Details
        c.setFont("Helvetica", 9)
        c.drawString(50, 705, f"Patient Name: {p_name}")
        c.drawString(320, 705, f"Age / Sex: {p_age} Yrs / {p_sex}")
        c.drawString(50, 688, f"Referred By: Dr. {p_doctor}")
        c.drawString(320, 688, "Date: 07-Sep-2026")
        c.line(50, 678, 550, 678)
        
        # Table Headers
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, 655, "Investigation / Parameter")
        c.drawString(320, 655, "Observed Value")
        c.line(50, 648, 550, 648)
        
        # Test Results
        c.setFont("Helvetica", 9)
        y = 630
        for t_name, t_val in final_data.items():
            c.drawString(50, y, str(t_name))
            c.drawString(320, y, str(t_val))
            y -= 20
            if y < 100:
                c.showPage()
                y = 740
                
        # Signatures
        c.line(50, 95, 550, 95)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(50, 80, "Prepared by: Medical Lab Technologist")
        c.drawString(370, 80, "Verified by: Consultant Pathologist")
        
        c.save()
        buf.seek(0)
        
        st.download_button(
            label="📥 Download Pathology Report (PDF)",
            data=buf,
            file_name=f"{p_name.replace(' ', '_')}_Report.pdf",
            mime="application/pdf"
        )
