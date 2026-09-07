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
            You are a clinical hematology data extraction assistant.
            Carefully scan this 3-part / 5-part hematology analyzer display or thermal printout.
            Extract EVERY SINGLE parameter and index present in the image without skipping any.
            Include:
            - Hemoglobin (Hb), WBC / TLC, RBC, Hematocrit / HCT / PCV
            - MCV, MCH, MCHC, RDW-CV / RDW %, RDWa / RDW-SD
            - Platelets / PLT, MPV, PDW, PCT, LPCR / P-LCR, P-LCC
            - Differential Counts (both % and absolute):
              Granulocytes / Neutrophils (% and absolute)
              Lymphocytes (% and absolute)
              Mid Cells / Monocytes (% and absolute)
            Output strictly a valid JSON object where keys are the clean parameter names and values are strings or numbers.
            Do not omit any row shown in the image.
            Do not include markdown code block formatting or backticks.
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
                    st.success(f"Extracted {len(st.session_state.extracted_tests)} parameters successfully!")
                    success = True
                    break
                except Exception as err:
                    last_err = str(err)
                    continue
            
            if not success:
                st.error(f"Extraction busy/error. Please click again in 5 seconds. ({last_err})")

# Comprehensive Reference Ranges & Units Database
REF_DATA = {
    "Hemoglobin": {"unit": "g/dL", "ref": "13.0 - 17.0"},
    "Hb": {"unit": "g/dL", "ref": "13.0 - 17.0"},
    "WBC": {"unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "TLC": {"unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "TLC (WBC)": {"unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "RBC": {"unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "RBC Count": {"unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "Hematocrit": {"unit": "%", "ref": "40.0 - 50.0"},
    "HCT": {"unit": "%", "ref": "40.0 - 50.0"},
    "PCV": {"unit": "%", "ref": "40.0 - 50.0"},
    "PCV (Hematocrit)": {"unit": "%", "ref": "40.0 - 50.0"},
    "MCV": {"unit": "fL", "ref": "80.0 - 100.0"},
    "MCH": {"unit": "pg", "ref": "27.0 - 32.0"},
    "MCHC": {"unit": "g/dL", "ref": "31.5 - 35.5"},
    "RDW": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDW-CV": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDW_Percent": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDW %": {"unit": "%", "ref": "11.5 - 14.5"},
    "RDW-SD": {"unit": "fL", "ref": "39.0 - 46.0"},
    "RDWa": {"unit": "fL", "ref": "39.0 - 46.0"},
    "Platelets": {"unit": "10^3/uL", "ref": "150 - 450"},
    "PLT": {"unit": "10^3/uL", "ref": "150 - 450"},
    "MPV": {"unit": "fL", "ref": "7.5 - 11.5"},
    "PDW": {"unit": "%", "ref": "9.0 - 17.0"},
    "PCT": {"unit": "%", "ref": "0.10 - 0.50"},
    "LPCR": {"unit": "%", "ref": "15.0 - 35.0"},
    "P-LCR": {"unit": "%", "ref": "15.0 - 35.0"},
    "P-LCC": {"unit": "10^3/uL", "ref": "30 - 90"},
    "Granulocytes_Percent": {"unit": "%", "ref": "40.0 - 70.0"},
    "Granulocytes %": {"unit": "%", "ref": "40.0 - 70.0"},
    "Neutrophils %": {"unit": "%", "ref": "40.0 - 70.0"},
    "Granulocytes_Absolute": {"unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "Granulocytes #": {"unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "Neutrophils #": {"unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "Lymphocytes_Percent": {"unit": "%", "ref": "20.0 - 40.0"},
    "Lymphocytes %": {"unit": "%", "ref": "20.0 - 40.0"},
    "Lymphocytes": {"unit": "%", "ref": "20.0 - 40.0"},
    "Lymphocytes_Absolute": {"unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "Lymphocytes #": {"unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "Mid_Cells_Percent": {"unit": "%", "ref": "2.0 - 8.0"},
    "Mid_Cells %": {"unit": "%", "ref": "2.0 - 8.0"},
    "Monocytes %": {"unit": "%", "ref": "2.0 - 8.0"},
    "Mid_Cells_Absolute": {"unit": "10^3/uL", "ref": "0.1 - 0.8"},
    "Mid_Cells #": {"unit": "10^3/uL", "ref": "0.1 - 0.8"},
    "Monocytes #": {"unit": "10^3/uL", "ref": "0.1 - 0.8"},
}

def lookup_ref(param_name):
    norm = param_name.strip()
    if norm in REF_DATA:
        return REF_DATA[norm]
    for k, v in REF_DATA.items():
        if k.lower() == norm.lower():
            return v
    if "hb" in norm.lower() or "hemo" in norm.lower():
        return REF_DATA["Hemoglobin"]
    if "platelet" in norm.lower() or "plt" in norm.lower():
        return REF_DATA["Platelets"]
    if "wbc" in norm.lower() or "tlc" in norm.lower():
        return REF_DATA["WBC"]
    if "rbc" in norm.lower():
        return REF_DATA["RBC"]
    return {"unit": "-", "ref": "Clinical Correlation"}

if st.session_state.extracted_tests:
    st.subheader(f"Verify & Edit Values ({len(st.session_state.extracted_tests)} parameters found)")
    final_data = {}
    
    cols = st.columns(2)
    idx = 0
    for test, val in st.session_state.extracted_tests.items():
        clean_label = test.replace('_', ' ')
        with cols[idx % 2]:
            final_data[test] = st.text_input(f"{clean_label}", value=str(val), key=f"inp_{test}")
        idx += 1
    
    if st.button("Generate Complete Professional PDF Report"):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        
        # Header Banner
        c.setFillColor(colors.HexColor("#1a365d"))
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
        
        c.setFillColor(colors.HexColor("#334155"))
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
        c.drawString(405, height - 126, "07-Sep-2026 11:30 AM")
        
        # Department Banner
        c.setFillColor(colors.HexColor("#0d9488"))
        c.rect(36, height - 156, width - 72, 14, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(42, height - 153, "COMPLETE BLOOD COUNT (AUTOMATED HEMATOLOGY PROFILE)")
        
        # Table Header
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.rect(36, height - 173, width - 72, 14, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(44, height - 170, "INVESTIGATION / PARAMETER")
        c.drawString(250, height - 170, "RESULT")
        c.drawString(325, height - 170, "UNIT")
        c.drawString(410, height - 170, "BIOLOGICAL REFERENCE RANGE")
        
        # Table Rows
        y = height - 188
        c.setFont("Helvetica", 7.5)
        
        for key, val in final_data.items():
            ref_info = lookup_ref(key)
            clean_name = key.replace('_', ' ')
            
            c.setFillColor(colors.HexColor("#0f172a"))
            c.drawString(44, y, str(clean_name))
            
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(250, y, str(val))
            c.setFont("Helvetica", 7.5)
            
            c.drawString(325, y, str(ref_info["unit"]))
            c.drawString(410, y, str(ref_info["ref"]))
            
            c.setStrokeColor(colors.HexColor("#f1f5f9"))
            c.line(36, y - 2, width - 36, y - 2)
            
            y -= 13.2
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
            file_name=f"{p_name.replace(' ', '_')}_Complete_CBC.pdf",
            mime="application/pdf"
        )
