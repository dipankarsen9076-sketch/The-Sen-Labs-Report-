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

st.set_page_config(page_title="The Sen Labs - Multi-Diagnostic Reporting", layout="wide")
st.title("The Sen Labs - Diagnostic Reporting System")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# 1. Patient Details
st.subheader("1. Patient & Sample Information")
c1, c2, c3 = st.columns(3)
with c1:
    p_name = st.text_input("Patient Name", value="Dipankar Sen")
    p_age = st.text_input("Age", value="26")
with c2:
    p_sex = st.selectbox("Sex", ["Male (M)", "Female (F)", "Other"])
    p_doctor = st.text_input("Referred By (Doctor)", value="Self")
with c3:
    p_contact = st.text_input("Lab Contact / Helpline", value="9076816740")
    sample_id = st.text_input("Sample ID / Lab No.", value="TSL-2026-9081")

# 2. Multi-Test Profile Selector
st.subheader("2. Select Test Profiles for Patient")
selected_profiles = st.multiselect(
    "Choose all tests prescribed for this patient:",
    [
        "Complete Blood Count (CBC + GBP)",
        "Liver Function Test (LFT)",
        "Kidney Function Test (KFT / RFT)",
        "Lipid Profile",
        "Widal Agglutination Test",
        "Typhidot (IgM / IgG)",
        "Malaria Card & Smear (MP)",
        "Blood Glucose"
    ],
    default=["Complete Blood Count (CBC + GBP)"]
)

# Helper function to compress photos for speed
def compress_image_for_fast_ai(img_file):
    img = Image.open(img_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    out_bytes = io.BytesIO()
    img.save(out_bytes, format="JPEG", quality=82, optimize=True)
    return out_bytes.getvalue()

if "cbc_data" not in st.session_state:
    st.session_state.cbc_data = {}

# Section: CBC + GBP
cbc_inputs = {}
gbp_rbc = "Predominantly normocytic normochromic. Central pallor normal."
gbp_wbc = "Mature neutrophils and lymphocytes. No atypical or blast cells."
gbp_plt = "Adequate on smear, seen singly and clumps."
gbp_imp = "Hematological parameters within normal limits."

if "Complete Blood Count (CBC + GBP)" in selected_profiles:
    st.markdown("---")
    st.subheader("🩸 Complete Blood Count (CBC) Parameters")
    
    input_mode = st.radio(
        "CBC Analyzer Photo Input:",
        ("📁 Upload from Gallery", "📸 Live Camera"),
        horizontal=True
    )
    active_image = None
    if input_mode == "📁 Upload from Gallery":
        active_image = st.file_uploader("Upload machine screen/slip photo", type=["jpg", "jpeg", "png"], key="cbc_upload")
    else:
        active_image = st.camera_input("Capture machine display", key="cbc_cam")
        
    if active_image and st.button("⚡ Extract CBC Parameters (Fast OCR)"):
        if not api_key:
            st.error("Pehle sidebar me Gemini API Key dalein!")
        else:
            with st.spinner("Extracting machine parameters..."):
                try:
                    client = genai.Client(api_key=api_key)
                    optimized_bytes = compress_image_for_fast_ai(active_image)
                    prompt = """
                    Extract ALL hematology parameters and numeric values from this analyzer display/printout.
                    Keys: WBC, RBC, HGB, HCT, MCV, MCH, MCHC, RDWA, RDW_PERCENT, PLT, MPV, PDW, PCT, LPCR,
                    LYM_PERCENT, LYM_ABSOLUTE, MID_PERCENT, MID_ABSOLUTE, GRAN_PERCENT, GRAN_ABSOLUTE.
                    Output strictly JSON format. No backticks.
                    """
                    candidate_models = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
                    for m_name in candidate_models:
                        try:
                            resp = client.models.generate_content(
                                model=m_name,
                                contents=[
                                    types.Part.from_bytes(data=optimized_bytes, mime_type="image/jpeg"),
                                    prompt
                                ]
                            )
                            cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.text.strip(), flags=re.M).strip()
                            st.session_state.cbc_data = json.loads(cleaned)
                            st.success(f"Extracted {len(st.session_state.cbc_data)} parameters!")
                            break
                        except:
                            continue
                except Exception as e:
                    st.error(f"Extraction error: {e}")

    if not st.session_state.cbc_data:
        st.session_state.cbc_data = {
            "HGB": "13.5", "WBC": "7.5", "RBC": "4.80", "PLT": "240", "HCT": "42.0",
            "MCV": "87.5", "MCH": "28.5", "MCHC": "32.5", "RDWA": "42.0", "RDW_PERCENT": "13.2",
            "GRAN_PERCENT": "62.0", "GRAN_ABSOLUTE": "4.6", "LYM_PERCENT": "30.0", "LYM_ABSOLUTE": "2.2",
            "MID_PERCENT": "8.0", "MID_ABSOLUTE": "0.6", "MPV": "9.5", "PDW": "13.0", "PCT": "0.22", "LPCR": "22.5"
        }

    cols = st.columns(4)
    idx = 0
    for k, v in st.session_state.cbc_data.items():
        with cols[idx % 4]:
            cbc_inputs[k] = st.text_input(k.replace('_', ' '), value=str(v), key=f"cbc_{k}")
        idx += 1

    st.markdown("#### 🔬 General Blood Picture (GBP Findings)")
    gbp_col1, gbp_col2 = st.columns(2)
    with gbp_col1:
        gbp_rbc = st.text_input("RBC Morphology", value=gbp_rbc)
        gbp_wbc = st.text_input("WBC Morphology", value=gbp_wbc)
    with gbp_col2:
        gbp_plt = st.text_input("Platelets on Smear", value=gbp_plt)
        gbp_imp = st.text_input("Diagnostic Impression", value=gbp_imp)

# Section: LFT
lft_inputs = {}
if "Liver Function Test (LFT)" in selected_profiles:
    st.markdown("---")
    st.subheader("🧪 Liver Function Test (LFT)")
    lft_cols = st.columns(3)
    with lft_cols[0]:
        lft_inputs["Bilirubin Total"] = st.text_input("Bilirubin Total", "0.8")
        lft_inputs["Bilirubin Direct"] = st.text_input("Bilirubin Direct", "0.2")
        lft_inputs["Bilirubin Indirect"] = st.text_input("Bilirubin Indirect", "0.6")
    with lft_cols[1]:
        lft_inputs["SGOT / AST"] = st.text_input("SGOT / AST", "28")
        lft_inputs["SGPT / ALT"] = st.text_input("SGPT / ALT", "32")
        lft_inputs["Alkaline Phosphatase (ALP)"] = st.text_input("Alkaline Phosphatase (ALP)", "185")
    with lft_cols[2]:
        lft_inputs["Total Protein"] = st.text_input("Total Protein", "7.2")
        lft_inputs["Serum Albumin"] = st.text_input("Serum Albumin", "4.3")
        lft_inputs["Serum Globulin"] = st.text_input("Serum Globulin", "2.9")
        lft_inputs["A:G Ratio"] = st.text_input("A:G Ratio", "1.48")

# Section: KFT
kft_inputs = {}
if "Kidney Function Test (KFT / RFT)" in selected_profiles:
    st.markdown("---")
    st.subheader("🫘 Kidney Function Test (KFT / RFT)")
    kft_cols = st.columns(3)
    with kft_cols[0]:
        kft_inputs["Blood Urea"] = st.text_input("Blood Urea", "24.0")
        kft_inputs["Serum Creatinine"] = st.text_input("Serum Creatinine", "0.9")
    with kft_cols[1]:
        kft_inputs["Serum Uric Acid"] = st.text_input("Serum Uric Acid", "4.8")
        kft_inputs["Blood Urea Nitrogen (BUN)"] = st.text_input("Blood Urea Nitrogen (BUN)", "11.2")
    with kft_cols[2]:
        kft_inputs["Serum Calcium"] = st.text_input("Serum Calcium", "9.4")
        kft_inputs["Serum Sodium (Na+)"] = st.text_input("Serum Sodium (Na+)", "138")
        kft_inputs["Serum Potassium (K+)"] = st.text_input("Serum Potassium (K+)", "4.2")

# Section: Lipid Profile
lipid_inputs = {}
if "Lipid Profile" in selected_profiles:
    st.markdown("---")
    st.subheader("❤️ Lipid Profile")
    lip_cols = st.columns(3)
    with lip_cols[0]:
        lipid_inputs["Total Cholesterol"] = st.text_input("Total Cholesterol", "175")
        lipid_inputs["Triglycerides"] = st.text_input("Serum Triglycerides", "130")
    with lip_cols[1]:
        lipid_inputs["HDL Cholesterol"] = st.text_input("HDL (Good)", "46")
        lipid_inputs["LDL Cholesterol"] = st.text_input("LDL (Bad)", "103")
    with lip_cols[2]:
        lipid_inputs["VLDL Cholesterol"] = st.text_input("VLDL Cholesterol", "26")
        lipid_inputs["TC / HDL Ratio"] = st.text_input("TC / HDL Ratio", "3.8")

# Section: Serology / Rapid Tests
serology_inputs = {}
if "Widal Agglutination Test" in selected_profiles:
    st.markdown("---")
    st.subheader("🌡️ Widal Agglutination Test (Slide / Tube)")
    w_cols = st.columns(4)
    with w_cols[0]:
        serology_inputs["Salmonella typhi 'O'"] = st.selectbox("S. typhi 'O'", ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"], index=0)
    with w_cols[1]:
        serology_inputs["Salmonella typhi 'H'"] = st.selectbox("S. typhi 'H'", ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"], index=0)
    with w_cols[2]:
        serology_inputs["Salmonella paratyphi 'AH'"] = st.selectbox("S. paratyphi 'AH'", ["Negative", "1:20", "1:40", "1:80"], index=0)
    with w_cols[3]:
        serology_inputs["Salmonella paratyphi 'BH'"] = st.selectbox("S. paratyphi 'BH'", ["Negative", "1:20", "1:40", "1:80"], index=0)

if "Typhidot (IgM / IgG)" in selected_profiles:
    st.markdown("---")
    st.subheader("🧪 Typhidot Rapid Card")
    t_cols = st.columns(2)
    with t_cols[0]:
        serology_inputs["Typhidot IgM (Acute Infection)"] = st.selectbox("Typhidot IgM", ["Non-Reactive (Negative)", "Reactive (Positive)"])
    with t_cols[1]:
        serology_inputs["Typhidot IgG (Past/Carrier)"] = st.selectbox("Typhidot IgG", ["Non-Reactive (Negative)", "Reactive (Positive)"])

if "Malaria Card & Smear (MP)" in selected_profiles:
    st.markdown("---")
    st.subheader("🦟 Malaria Examination")
    m_cols = st.columns(3)
    with m_cols[0]:
        serology_inputs["Malarial Parasite (Smear)"] = st.selectbox("Peripheral Smear Examination", ["Not Seen", "P. vivax seen", "P. falciparum seen"])
    with m_cols[1]:
        serology_inputs["P. vivax Antigen (Rapid Card)"] = st.selectbox("P. vivax Antigen", ["Negative", "Positive"])
    with m_cols[2]:
        serology_inputs["P. falciparum Antigen (Rapid Card)"] = st.selectbox("P. falciparum Antigen", ["Negative", "Positive"])

if "Blood Glucose" in selected_profiles:
    st.markdown("---")
    st.subheader("🍬 Blood Glucose")
    bg_cols = st.columns(3)
    with bg_cols[0]:
        serology_inputs["Blood Glucose (Fasting)"] = st.text_input("Fasting (F)", "92")
    with bg_cols[1]:
        serology_inputs["Blood Glucose (PP)"] = st.text_input("Post Prandial (PP)", "128")
    with bg_cols[2]:
        serology_inputs["Blood Glucose (Random)"] = st.text_input("Random (RBS)", "110")

# Reference Database
MASTER_REFS = {
    "hgb": {"name": "Hemoglobin (Hb)", "unit": "g/dL", "ref": "13.0 - 17.0"},
    "rbc": {"name": "Total RBC Count", "unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "hct": {"name": "Packed Cell Volume (PCV/HCT)", "unit": "%", "ref": "40.0 - 50.0"},
    "mcv": {"name": "Mean Corpuscular Volume (MCV)", "unit": "fL", "ref": "80.0 - 100.0"},
    "mch": {"name": "Mean Corpuscular Hemoglobin (MCH)", "unit": "pg", "ref": "27.0 - 32.0"},
    "mchc": {"name": "Mean Corpuscular Hb Conc. (MCHC)", "unit": "g/dL", "ref": "31.5 - 35.5"},
    "rdwa": {"name": "RDW - SD (RDWa)", "unit": "fL", "ref": "39.0 - 46.0"},
    "rdw_percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "wbc": {"name": "Total Leukocyte Count (WBC/TLC)", "unit": "10^3/uL", "ref": "4.0 - 10.0"},
    "gran_percent": {"name": "Granulocytes / Neutrophils (%)", "unit": "%", "ref": "40.0 - 70.0"},
    "gran_absolute": {"name": "Granulocytes Absolute (#)", "unit": "10^3/uL", "ref": "2.0 - 7.0"},
    "lym_percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "lym_absolute": {"name": "Lymphocytes Absolute (#)", "unit": "10^3/uL", "ref": "1.0 - 3.0"},
    "mid_percent": {"name": "Mid Cells / Monocytes (%)", "unit": "%", "ref": "2.0 - 8.0"},
    "mid_absolute": {"name": "Mid Cells / Monocytes Absolute (#)", "unit": "10^3/uL", "ref": "0.1 - 0.8"},
    "plt": {"name": "Platelet Count (PLT)", "unit": "10^3/uL", "ref": "150 - 450"},
    "mpv": {"name": "Mean Platelet Volume (MPV)", "unit": "fL", "ref": "7.5 - 11.5"},
    "pdw": {"name": "Platelet Distribution Width (PDW)", "unit": "%", "ref": "9.0 - 17.0"},
    "pct": {"name": "Plateletcrit (PCT)", "unit": "%", "ref": "0.10 - 0.50"},
    "lpcr": {"name": "Platelet Large Cell Ratio (P-LCR)", "unit": "%", "ref": "15.0 - 35.0"},
    "Bilirubin Total": {"name": "Serum Bilirubin Total", "unit": "mg/dL", "ref": "0.2 - 1.2"},
    "Bilirubin Direct": {"name": "Serum Bilirubin Direct", "unit": "mg/dL", "ref": "0.0 - 0.3"},
    "Bilirubin Indirect": {"name": "Serum Bilirubin Indirect", "unit": "mg/dL", "ref": "0.2 - 0.9"},
    "SGOT / AST": {"name": "SGOT / AST", "unit": "U/L", "ref": "5 - 40"},
    "SGPT / ALT": {"name": "SGPT / ALT", "unit": "U/L", "ref": "5 - 45"},
    "Alkaline Phosphatase (ALP)": {"name": "Alkaline Phosphatase (ALP)", "unit": "U/L", "ref": "80 - 306"},
    "Total Protein": {"name": "Serum Total Protein", "unit": "g/dL", "ref": "6.4 - 8.3"},
    "Serum Albumin": {"name": "Serum Albumin", "unit": "g/dL", "ref": "3.5 - 5.2"},
    "Serum Globulin": {"name": "Serum Globulin", "unit": "g/dL", "ref": "2.0 - 3.5"},
    "A:G Ratio": {"name": "A : G Ratio", "unit": "Ratio", "ref": "1.2 - 2.2"},
    "Blood Urea": {"name": "Blood Urea", "unit": "mg/dL", "ref": "15 - 45"},
    "Serum Creatinine": {"name": "Serum Creatinine", "unit": "mg/dL", "ref": "0.6 - 1.4"},
    "Serum Uric Acid": {"name": "Serum Uric Acid", "unit": "mg/dL", "ref": "3.5 - 7.2"},
    "Blood Urea Nitrogen (BUN)": {"name": "Blood Urea Nitrogen (BUN)", "unit": "mg/dL", "ref": "7 - 20"},
    "Serum Calcium": {"name": "Serum Calcium", "unit": "mg/dL", "ref": "8.5 - 10.5"},
    "Serum Sodium (Na+)": {"name": "Serum Sodium (Na+)", "unit": "mEq/L", "ref": "135 - 145"},
    "Serum Potassium (K+)": {"name": "Serum Potassium (K+)", "unit": "mEq/L", "ref": "3.5 - 5.0"},
    "Total Cholesterol": {"name": "Total Cholesterol", "unit": "mg/dL", "ref": "< 200 (Desirable)"},
    "Triglycerides": {"name": "Serum Triglycerides", "unit": "mg/dL", "ref": "< 150 (Normal)"},
    "HDL Cholesterol": {"name": "HDL Cholesterol", "unit": "mg/dL", "ref": "> 40 (Optimal)"},
    "LDL Cholesterol": {"name": "LDL Cholesterol", "unit": "mg/dL", "ref": "< 100 (Optimal)"},
    "VLDL Cholesterol": {"name": "VLDL Cholesterol", "unit": "mg/dL", "ref": "5 - 30"},
    "TC / HDL Ratio": {"name": "TC / HDL Ratio", "unit": "Ratio", "ref": "3.0 - 5.0"},
    "Blood Glucose (Fasting)": {"name": "Blood Glucose (Fasting)", "unit": "mg/dL", "ref": "70 - 100"},
    "Blood Glucose (PP)": {"name": "Blood Glucose (Post Prandial)", "unit": "mg/dL", "ref": "70 - 140"},
    "Blood Glucose (Random)": {"name": "Blood Glucose (Random)", "unit": "mg/dL", "ref": "70 - 140"},
}

def lookup_any_ref(key):
    clean = key.strip().lower()
    if clean in MASTER_REFS:
        return MASTER_REFS[clean]
    for k, v in MASTER_REFS.items():
        if k.lower() == clean:
            return v
    return {"name": key, "unit": "-", "ref": "Clinical Correlation"}

st.markdown("---")

# PDF Generator Class to manage multi-page layout safely
class PathologyReportDoc:
    def __init__(self, buffer):
        self.c = canvas.Canvas(buffer, pagesize=letter)
        self.width, self.height = letter
        self.current_y = self.height - 128
        self.report_time = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        self.draw_header()

    def draw_header(self):
        self.c.setFillColor(colors.HexColor("#1e3a8a"))
        self.c.rect(0, self.height - 62, self.width, 62, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 17)
        self.c.drawString(32, self.height - 32, "THE SEN LABS")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(32, self.height - 48, "ADVANCED PATHOLOGY & CLINICAL LABORATORY | ACCREDITED DIAGNOSTIC SERVICES")
        self.c.drawRightString(self.width - 32, self.height - 35, f"Helpdesk: +91 {p_contact}")
        
        self.c.setFillColor(colors.HexColor("#f8fafc"))
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.roundRect(32, self.height - 116, self.width - 64, 48, 3, fill=True, stroke=True)
        
        self.c.setFillColor(colors.HexColor("#475569"))
        self.c.setFont("Helvetica-Bold", 7.5)
        self.c.drawString(42, self.height - 80, "Patient Name:")
        self.c.drawString(42, self.height - 93, "Age / Sex:")
        self.c.drawString(42, self.height - 106, "Referred By:")
        
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(108, self.height - 80, f"Mr. {p_name}")
        self.c.drawString(108, self.height - 93, f"{p_age} Yrs / {p_sex}")
        self.c.drawString(108, self.height - 106, f"Dr. {p_doctor}")
        
        self.c.setFont("Helvetica-Bold", 7.5)
        self.c.drawString(320, self.height - 80, "Sample ID:")
        self.c.drawString(320, self.height - 93, "Sample Type:")
        self.c.drawString(320, self.height - 106, "Report Date:")
        
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(385, self.height - 80, sample_id)
        self.c.drawString(385, self.height - 93, "Whole Blood / Serum")
        self.c.drawString(385, self.height - 106, self.report_time)

    def draw_footer(self):
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.line(32, 54, self.width - 32, 54)
        self.c.setFont("Helvetica-Bold", 7.5)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.drawString(42, 42, "Dipankar Sen")
        self.c.drawString(self.width - 190, 42, "Dr. R. K. Banerjee")
        self.c.setFont("Helvetica", 6.8)
        self.c.setFillColor(colors.HexColor("#64748b"))
        self.c.drawString(42, 32, "Medical Lab Technologist (DMLT / BSS)")
        self.c.drawString(self.width - 190, 32, "Consultant Pathologist (MD Path)")

    def add_section(self, title, items_dict, bar_color="#0f766e"):
        needed_height = 28 + (len(items_dict) * 11)
        if self.current_y - needed_height < 65:
            self.draw_footer()
            self.c.showPage()
            self.draw_header()
            self.current_y = self.height - 128
            
        self.c.setFillColor(colors.HexColor(bar_color))
        self.c.rect(32, self.current_y - 12, self.width - 64, 12, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(38, self.current_y - 9, title)
        
        self.c.setFillColor(colors.HexColor("#e2e8f0"))
        self.c.rect(32, self.current_y - 25, self.width - 64, 12, fill=True, stroke=False)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.setFont("Helvetica-Bold", 6.8)
        self.c.drawString(38, self.current_y - 22, "TEST / PARAMETER")
        self.c.drawString(245, self.current_y - 22, "RESULT")
        self.c.drawString(315, self.current_y - 22, "UNIT")
        self.c.drawString(395, self.current_y - 22, "REFERENCE RANGE")
        
        y = self.current_y - 36
        self.c.setFont("Helvetica", 6.8)
        for k, val in items_dict.items():
            meta = lookup_any_ref(k)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(38, y, str(meta["name"]))
            
            self.c.setFont("Helvetica-Bold", 6.8)
            self.c.drawString(245, y, str(val))
            self.c.setFont("Helvetica", 6.8)
            
            self.c.drawString(315, y, str(meta["unit"]))
            self.c.drawString(395, y, str(meta["ref"]))
            
            self.c.setStrokeColor(colors.HexColor("#f1f5f9"))
            self.c.line(32, y - 2, self.width - 32, y - 2)
            y -= 10.8
            
        self.current_y = y - 4

    def add_gbp(self, rbc_text, wbc_text, plt_text, imp_text):
        if self.current_y - 70 < 65:
            self.draw_footer()
            self.c.showPage()
            self.draw_header()
            self.current_y = self.height - 128
            
        self.c.setFillColor(colors.HexColor("#1e3a8a"))
        self.c.rect(32, self.current_y - 10, self.width - 64, 11, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(38, self.current_y - 7, "GENERAL BLOOD PICTURE (PERIPHERAL SMEAR FINDINGS)")
        
        box_top = self.current_y - 11
        self.c.setFillColor(colors.HexColor("#f8fafc"))
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.rect(32, box_top - 52, self.width - 64, 52, fill=True, stroke=True)
        
        gy = box_top - 10
        self.c.setFont("Helvetica-Bold", 7)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.drawString(40, gy, "RBC:")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(80, gy, rbc_text[:95])
        
        gy -= 10
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(40, gy, "WBC:")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(80, gy, wbc_text[:95])
        
        gy -= 10
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(40, gy, "PLT:")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(80, gy, plt_text[:95])
        
        gy -= 10
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(40, gy, "Impression:")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(95, gy, imp_text[:90])
        
        self.current_y = box_top - 62

    def finish(self):
        self.draw_footer()
        self.c.save()

if st.button("🖨️ Generate Comprehensive Pathology Report (PDF)"):
    buf = io.BytesIO()
    doc = PathologyReportDoc(buf)
    
    # 1. CBC
    if "Complete Blood Count (CBC + GBP)" in selected_profiles:
        doc.add_section("COMPLETE BLOOD COUNT (AUTOMATED HEMATOLOGY)", cbc_inputs, "#0f766e")
        doc.add_gbp(gbp_rbc, gbp_wbc, gbp_plt, gbp_imp)
        
    # 2. LFT
    if "Liver Function Test (LFT)" in selected_profiles and lft_inputs:
        doc.add_section("CLINICAL BIOCHEMISTRY - LIVER FUNCTION TEST (LFT)", lft_inputs, "#854d0e")
        
    # 3. KFT
    if "Kidney Function Test (KFT / RFT)" in selected_profiles and kft_inputs:
        doc.add_section("CLINICAL BIOCHEMISTRY - KIDNEY FUNCTION TEST (KFT)", kft_inputs, "#7c2d12")
        
    # 4. Lipid Profile
    if "Lipid Profile" in selected_profiles and lipid_inputs:
        doc.add_section("CLINICAL BIOCHEMISTRY - LIPID PROFILE", lipid_inputs, "#be123c")
        
    # 5. Serology / Rapid
    if serology_inputs:
        doc.add_section("SEROLOGY & CLINICAL IMMUNOLOGY", serology_inputs, "#4338ca")
        
    doc.finish()
    buf.seek(0)
    
    st.download_button(
        label="📥 Download Complete Multi-Profile Pathology PDF",
        data=buf,
        file_name=f"{p_name.replace(' ', '_')}_Diagnostics_Report.pdf",
        mime="application/pdf"
    )
