import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import io
import json
import re
from datetime import datetime

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
uploaded_file = st.file_uploader("Or upload image from gallery", type=["jpg", "jpeg", "png"])

active_image = camera_photo or uploaded_file

if "extracted_tests" not in st.session_state:
    st.session_state.extracted_tests = {}

if active_image and st.button("Extract Data from Photo"):
    if not api_key:
        st.error("Pehle sidebar me apni API Key dalein!")
    else:
        with st.spinner("Analyzing machine screen and extracting all parameters..."):
            client = genai.Client(api_key=api_key)
            prompt = """
            You are a senior clinical hematology technologist.
            Extract EVERY SINGLE lab test parameter and numerical value from this 3-part/5-part hematology analyzer or printout.
            Capture:
            - WBC, RBC, HGB / Hemoglobin, HCT / Hematocrit, MCV, MCH, MCHC
            - RDWa (or RDW-SD), RDW percent (or RDW-CV)
            - PLT / Platelets, MPV, PDW, PCT, LPCR / P-LCR
            - LYM absolute (#), LYM percent (%)
            - MID absolute (#), MID percent (%)
            - GRAN absolute (#), GRAN percent (%)
            
            Return strictly a valid single JSON dictionary:
            {"PARAMETER_NAME": "VALUE", ...}
            Do not skip any line. No markdown formatting, no backticks.
            """
            
            candidate_models = [
                "gemini-3.5-flash",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite"
            ]
            success = False
            last_err = ""
            
            for m_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=m_name,
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
                    st.success(f"Extracted all {len(st.session_state.extracted_tests)} parameters successfully!")
                    success = True
                    break
                except Exception as err:
                    last_err = str(err)
                    continue
            
            if not success:
                st.error(f"Extraction busy/error. Please click again. ({last_err})")

# Comprehensive Clinical Hematology Reference Database
MASTER_REFS = {
    # Hemoglobin & RBC Indices
    "hgb": {"name": "Hemoglobin (HGB)", "unit": "g/dL", "ref": "13.0 - 17.0"},
    "hemoglobin": {"name": "Hemoglobin (HGB)", "unit": "g/dL", "ref": "13.0 - 17.0"},
    "rbc": {"name": "Total RBC Count", "unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "hct": {"name": "Packed Cell Volume (PCV/HCT)", "unit": "%", "ref": "40.0 - 50.0"},
    "hematocrit": {"name": "Packed Cell Volume (PCV/HCT)", "unit": "%", "ref": "40.0 - 50.0"},
    "mcv": {"name": "Mean Corpuscular Volume (MCV)", "unit": "fL", "ref": "80.0 - 100.0"},
    "mch": {"name": "Mean Corpuscular Hemoglobin (MCH)", "unit": "pg", "ref": "27.0 - 32.0"},
    "mchc": {"name": "Mean Corpuscular Hb Conc. (MCHC)", "unit": "g/dL", "ref": "31.5 - 35.5"},
    "rdw percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "rdw_percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "rdw": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "rdwa": {"name": "RDW - SD (RDWa)", "unit": "fL", "ref": "39.0 - 46.0"},
    "rdw-sd": {"name": "RDW - SD (RDWa)", "unit": "fL", "ref": "39.0 - 46.0"},

    # Leukocyte Profile & Differential Count
    "wbc": {"name": "Total Leukocyte Count (WBC/TLC)", "unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "tlc": {"name": "Total Leukocyte Count (WBC/TLC)", "unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "gran percent": {"name": "Granulocytes / Neutrophils (%)", "unit": "%", "ref": "40.0 - 70.0"},
    "gran_percent": {"name": "Granulocytes / Neutrophils (%)", "unit": "%", "ref": "40.0 - 70.0"},
    "gran absolute": {"name": "Granulocytes Absolute (#)", "unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "gran_absolute": {"name": "Granulocytes Absolute (#)", "unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "lym percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "lym_percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "lym absolute": {"name": "Lymphocytes Absolute (#)", "unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "lym_absolute": {"name": "Lymphocytes Absolute (#)", "unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "mid percent": {"name": "Mid Cells / Monocytes (%)", "unit": "%", "ref": "2.0 - 8.0"},
    "mid_percent": {"name": "Mid Cells / Monocytes (%)", "unit": "%", "ref": "2.0 - 8.0"},
    "mid absolute": {"name": "Mid Cells Absolute (#)", "unit": "10^3/uL", "ref": "0.1 - 0.8"},
    "mid_absolute": {"name": "Mid Cells Absolute (#)", "unit": "10^3/uL", "ref": "0.1 - 0.8"},

    # Platelet Indices
    "plt": {"name": "Platelet Count (PLT)", "unit": "10^3/uL", "ref": "150 - 450"},
    "platelets": {"name": "Platelet Count (PLT)", "unit": "10^3/uL", "ref": "150 - 450"},
    "mpv": {"name": "Mean Platelet Volume (MPV)", "unit": "fL", "ref": "7.5 - 11.5"},
    "pdw": {"name": "Platelet Distribution Width (PDW)", "unit": "%", "ref": "9.0 - 17.0"},
    "pct": {"name": "Plateletcrit (PCT)", "unit": "%", "ref": "0.10 - 0.50"},
    "lpcr": {"name": "Platelet Large Cell Ratio (P-LCR)", "unit": "%", "ref": "15.0 - 35.0"},
    "p-lcr": {"name": "Platelet Large Cell Ratio (P-LCR)", "unit": "%", "ref": "15.0 - 35.0"},
}

def resolve_meta(raw_key):
    cleaned = raw_key.strip().lower().replace("_", " ")
    if cleaned in MASTER_REFS:
        return MASTER_REFS[cleaned]
    for k, v in MASTER_REFS.items():
        if k == cleaned or k in cleaned:
            return v
    return {"name": raw_key.replace("_", " ").upper(), "unit": "-", "ref": "Clinical Correlation"}

if st.session_state.extracted_tests:
    st.subheader(f"Verify & Edit Values ({len(st.session_state.extracted_tests)} parameters)")
    final_data = {}
    
    cols = st.columns(2)
    idx = 0
    for test, val in st.session_state.extracted_tests.items():
        meta = resolve_meta(test)
        with cols[idx % 2]:
            final_data[test] = st.text_input(f"{meta['name']}", value=str(val), key=f"inp_{test}")
        idx += 1
    
    if st.button("Generate Complete Professional PDF Report"):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        report_time = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        
        # Header Banner
        c.setFillColor(colors.HexColor("#1e3a8a"))
        c.rect(0, height - 68, width, 68, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 19)
        c.drawString(36, height - 36, "THE SEN LABS")
        c.setFont("Helvetica", 8.5)
        c.drawString(36, height - 52, "ADVANCED PATHOLOGY & CLINICAL LABORATORY | AUTOMATED HEMATOLOGY")
        c.drawRightString(width - 36, height - 40, f"Helpdesk: +91 {p_contact}")
        
        # Patient Details Box
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.roundRect(36, height - 138, width - 72, 60, 4, fill=True, stroke=True)
        
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(48, height - 94, "Patient Name:")
        c.drawString(48, height - 110, "Age / Sex:")
        c.drawString(48, height - 126, "Referred By:")
        
        c.setFont("Helvetica", 8)
        c.drawString(120, height - 94, f"Mr. {p_name}")
        c.drawString(120, height - 110, f"{p_age} Yrs / {p_sex}")
        c.drawString(120, height - 126, f"Dr. {p_doctor}")
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(330, height - 94, "Sample ID:")
        c.drawString(330, height - 110, "Sample Type:")
        c.drawString(330, height - 126, "Report Date:")
        
        c.setFont("Helvetica", 8)
        c.drawString(405, height - 94, "TSL-CBC-8167")
        c.drawString(405, height - 110, "Whole Blood (EDTA)")
        c.drawString(405, height - 126, report_time)
        
        # Department Banner
        c.setFillColor(colors.HexColor("#0f766e"))
        c.rect(36, height - 156, width - 72, 14, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(42, height - 153, "COMPLETE BLOOD COUNT (AUTOMATED 3-PART HEMATOLOGY PROFILE)")
        
        # Table Header
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.rect(36, height - 173, width - 72, 14, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(44, height - 170, "INVESTIGATION / PARAMETER")
        c.drawString(245, height - 170, "RESULT")
        c.drawString(320, height - 170, "UNIT")
        c.drawString(405, height - 170, "BIOLOGICAL REFERENCE RANGE")
        
        # Table Rows
        y = height - 188
        c.setFont("Helvetica", 7.5)
        
        for key, val in final_data.items():
            meta = resolve_meta(key)
            
            c.setFillColor(colors.HexColor("#0f172a"))
            c.drawString(44, y, str(meta["name"]))
            
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(245, y, str(val))
            c.setFont("Helvetica", 7.5)
            
            c.drawString(320, y, str(meta["unit"]))
            c.drawString(405, y, str(meta["ref"]))
            
            c.setStrokeColor(colors.HexColor("#f1f5f9"))
            c.line(36, y - 2, width - 36, y - 2)
            
            y -= 13.0
            if y < 85:
                break
                
        # Verification Signatures
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.line(36, 72, width - 36, 72)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawString(46, 58, "Dipankar Sen")
        c.drawString(width - 190, 58, "Dr. R. K. Banerjee")
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(46, 48, "Medical Lab Technologist (DMLT / BSS)")
        c.drawString(width - 190, 48, "Consultant Pathologist (MD Path)")
        
        c.save()
        buf.seek(0)
        
        st.download_button(
            label="Download Complete Pathology PDF",
            data=buf,
            file_name=f"{p_name.replace(' ', '_')}_CBC_Report.pdf",
            mime="application/pdf"
        )
