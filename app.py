import io
import json
import re
from google import genai
from google.genai import types
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(page_title="The Sen Labs", layout="centered")
st.title("The Sen Labs - Diagnostic Reporting")

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
uploaded_file = st.file_uploader(
    "Or upload image from gallery", type=["jpg", "jpeg", "png"]
)

active_image = camera_photo or uploaded_file

if "extracted_tests" not in st.session_state:
  st.session_state.extracted_tests = {}

if active_image and st.button("Extract Data from Photo"):
  if not api_key:
    st.error("Pehle sidebar me apni API Key dalein!")
  else:
    with st.spinner("Analyzing machine screen and reading values..."):
      try:
        client = genai.Client(api_key=api_key)
        prompt = """
                Extract all hematology/CBC test parameters and values from this analyzer display/printout.
                Standardize names: Hemoglobin, TLC (WBC), RBC, Platelets, PCV (Hematocrit), MCV, MCH, MCHC, RDW, Neutrophils/Granulocytes, Lymphocytes, Monocytes/Mid Cells, MPV.
                Return strictly a JSON dictionary with parameter name as key and value as string/number.
                No backticks, no markdown.
                """
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=active_image.getvalue(),
                    mime_type=active_image.type or "image/jpeg",
                ),
                prompt,
            ],
        )
        raw_text = response.text.strip()
        cleaned_json = re.sub(
            r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE
        ).strip()
        st.session_state.extracted_tests = json.loads(cleaned_json)
        st.success("Values extracted! Check and edit below if required.")
      except Exception as err:
        st.error(f"Extraction error: {err}")

# Standard Medical Reference Ranges & Units
REF_DATA = {
    "Hemoglobin": {"unit": "g/dL", "ref": "13.0 - 17.0"},
    "TLC (WBC)": {"unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "WBC": {"unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "RBC": {"unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "Platelets": {"unit": "10^3/uL", "ref": "150 - 450"},
    "PCV (Hematocrit)": {"unit": "%", "ref": "40.0 - 50.0"},
    "Hematocrit": {"unit": "%", "ref": "40.0 - 50.0"},
    "MCV": {"unit": "fL", "ref": "80.0 - 100.0"},
    "MCH": {"unit": "pg", "ref": "27.0 - 32.0"},
    "MCHC": {"unit": "g/dL", "ref": "31.5 - 35.5"},
    "RDW": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDW_Percent": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDWa": {"unit": "fL", "ref": "39.0 - 46.0"},
    "Neutrophils/Granulocytes": {"unit": "%", "ref": "40.0 - 70.0"},
    "Granulocytes_Percent": {"unit": "%", "ref": "40.0 - 70.0"},
    "Granulocytes_Absolute": {"unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "Lymphocytes": {"unit": "%", "ref": "20.0 - 40.0"},
    "Lymphocytes_Percent": {"unit": "%", "ref": "20.0 - 40.0"},
    "Lymphocytes_Absolute": {"unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "Monocytes/Mid Cells": {"unit": "%", "ref": "2.0 - 8.0"},
    "Mid_Cells_Percent": {"unit": "%", "ref": "2.0 - 8.0"},
    "Mid_Cells_Absolute": {"unit": "10^3/uL", "ref": "0.1 - 0.8"},
    "MPV": {"unit": "fL", "ref": "7.5 - 11.5"},
    "PDW": {"unit": "%", "ref": "9.0 - 17.0"},
    "LPCR": {"unit": "%", "ref": "15.0 - 35.0"},
    "PCT": {"unit": "%", "ref": "0.10 - 0.50"},
}

if st.session_state.extracted_tests:
  st.subheader("Verify & Edit Values")
  final_data = {}
  for test, val in st.session_state.extracted_tests.items():
    clean_label = test.replace("_", " ")
    final_data[test] = st.text_input(f"{clean_label}", value=str(val))

  if st.button("Generate Professional PDF Report"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    # Lab Header Banner
    c.setFillColor(colors.HexColor("#1a365d"))
    c.rect(0, height - 70, width, 70, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, height - 38, "THE SEN LABS")
    c.setFont("Helvetica", 9)
    c.drawString(
        40,
        height - 54,
        "ADVANCED PATHOLOGY & CLINICAL LABORATORY | AUTOMATED HEMATOLOGY",
    )
    c.drawRightString(
        width - 40, height - 42, f"Helpdesk: +91 {p_contact}[span_0](start_span)[span_0](end_span)[span_1](start_span)[span_1](end_span)"
    )

    # Patient Details Box
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(40, height - 145, width - 80, 62, 4, fill=True, stroke=True)
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(52, height - 98, "Patient Name:")
    c.drawString(52, height - 116, "Age / Sex:")
    c.drawString(52, height - 134, "Referred By:")

    c.setFont("Helvetica", 8.5)
    c.drawString(130, height - 98, f"Mr. {p_name}[span_2](start_span)[span_2](end_span)[span_3](start_span)[span_3](end_span)")
    c.drawString(130, height - 116, f"{p_age} Yrs / {p_sex}[span_4](start_span)[span_4](end_span)[span_5](start_span)[span_5](end_span)")
    c.drawString(130, height - 134, f"Dr. {p_doctor}[span_6](start_span)[span_6](end_span)[span_7](start_span)[span_7](end_span)")

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(330, height - 98, "Sample ID:")
    c.drawString(330, height - 116, "Sample Type:")
    c.drawString(330, height - 134, "Report Date:")

    c.setFont("Helvetica", 8.5)
    c.drawString(405, height - 98, "TSL-EDTA-8167[span_8](start_span)[span_8](end_span)[span_9](start_span)[span_9](end_span)")
    c.drawString(405, height - 116, "Whole Blood (EDTA)[span_10](start_span)[span_10](end_span)[span_11](start_span)[span_11](end_span)")
    c.drawString(405, height - 134, "07-Sep-2026 11:30 AM[span_12](start_span)[span_12](end_span)[span_13](start_span)[span_13](end_span)")

    # Department Banner
    c.setFillColor(colors.HexColor("#0d9488"))
    c.rect(40, height - 165, width - 80, 15, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(
        46, height - 162, "DEPARTMENT OF HEMATOLOGY - COMPLETE BLOOD COUNT"
    )

    # Table Header
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.rect(40, height - 185, width - 80, 16, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, height - 181, "INVESTIGATION / PARAMETER")
    c.drawString(250, height - 181, "RESULT")
    c.drawString(325, height - 181, "UNIT")
    c.drawString(410, height - 181, "REFERENCE RANGE")

    # Table Rows
    y = height - 200
    c.setFont("Helvetica", 8)

    for key, val in final_data.items():
      ref_info = REF_DATA.get(key, {"unit": "-", "ref": "Clinical Correlation"})
      clean_name = key.replace("_", " ")

      c.setFillColor(colors.HexColor("#0f172a"))
      c.drawString(46, y, str(clean_name))

      c.setFont("Helvetica-Bold", 8)
      c.drawString(250, y, str(val))
      c.setFont("Helvetica", 8)

      c.drawString(325, y, str(ref_info["unit"]))
      c.drawString(410, y, str(ref_info["ref"]))

      c.setStrokeColor(colors.HexColor("#f1f5f9"))
      c.line(40, y - 3, width - 40, y - 3)

      y -= 15
      if y < 90:
        c.showPage()
        y = height - 50

    # Verification Signatures
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(40, 75, width - 40, 75)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(50, 60, "Amit Kumar Verma[span_14](start_span)[span_14](end_span)[span_15](start_span)[span_15](end_span)")
    c.drawString(width - 190, 60, "Dr. R. K. Banerjee[span_16](start_span)[span_16](end_span)[span_17](start_span)[span_17](end_span)")
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(
        50, 50, "Chief Lab Technologist (DMLT / B.Sc MLT)[span_18](start_span)[span_18](end_span)[span_19](start_span)[span_19](end_span)"
    )
    c.drawString(
        width - 190, 50, "Consultant Pathologist (MD Path)[span_20](start_span)[span_20](end_span)[span_21](start_span)[span_21](end_span)"
    )

    c.save()
    buf.seek(0)

    st.download_button(
        label="📥 Download Professional Pathology PDF",
        data=buf,
        file_name=f"{p_name.replace(' ', '_')}_CBC_Report.pdf",
        mime="application/pdf",
