import io
import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(
    page_title="The Sen Labs - Diagnostic Reporting", layout="wide"
)
st.title("The Sen Labs - Clinical Diagnostic System")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# 1. Patient Details
st.subheader("1. Patient & Sample Information")
c1, c2, c3 = st.columns(3)
with c1:
  p_name = st.text_input("Patient Name", value="")
  p_age = st.text_input("Age", value="")
with c2:
  p_sex = st.selectbox("Sex", ["Male (M)", "Female (F)", "Other"])
  p_doctor = st.text_input("Referred By (Doctor)", value="Self")
with c3:
  p_contact = st.text_input("Lab Contact / Helpline", value="9076816740")
  sample_id = st.text_input(
      "Sample ID / Lab No.",
      value=f"TSL-{datetime.now().strftime('%y%m%d%H%M')}",
  )

# 2. Multi-Test Profile Selector (DEFAULT EMPTY)
st.subheader("2. Select Test Profiles for Patient")
selected_profiles = st.multiselect(
    "Select investigations prescribed for this patient:",
    [
        "Complete Blood Count (CBC + GBP)",
        "Liver Function Test (LFT)",
        "Kidney Function Test (KFT / RFT)",
        "Lipid Profile",
        "Widal Agglutination Test",
        "Typhidot (IgM / IgG)",
        "Malaria Card & Smear (MP)",
        "Blood Glucose",
    ],
    default=[],
)


def safe_float(val):
  try:
    if str(val).strip() == "":
      return None
    return float(str(val).strip().replace(",", "."))
  except:
    return None


def compress_image_for_fast_ai(img_file):
  img = Image.open(img_file)
  if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
  img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
  out_bytes = io.BytesIO()
  img.save(out_bytes, format="JPEG", quality=82, optimize=True)
  return out_bytes.getvalue()


final_report_sections = {}

# ----------------- SECTION 1: CBC + GBP -----------------
if "Complete Blood Count (CBC + GBP)" in selected_profiles:
  st.markdown("---")
  st.subheader("🩸 Complete Blood Count (CBC) with Machine OCR")

  cbc_source = st.radio(
      "Choose Photo Source for CBC Analyzer:",
      ("📁 Upload Image / Slip", "📸 Live Camera"),
      horizontal=True,
  )
  cbc_img = (
      st.file_uploader(
          "Upload machine screen or slip",
          type=["jpg", "jpeg", "png"],
          key="cbc_file",
      )
      if cbc_source == "📁 Upload Image / Slip"
      else st.camera_input("Capture machine display", key="cbc_live")
  )

  if "cbc_raw_data" not in st.session_state:
    st.session_state.cbc_raw_data = {}

  if cbc_img and st.button("⚡ Extract CBC via Machine OCR"):
    if not api_key:
      st.error("Pehle sidebar me Gemini API Key dalein!")
    else:
      with st.spinner("Extracting parameters rapidly..."):
        try:
          client = genai.Client(api_key=api_key)
          optimized = compress_image_for_fast_ai(cbc_img)
          prompt = """
                    Extract all hematology values from this analyzer display/printout.
                    Keys: WBC, RBC, HGB, HCT, MCV, MCH, MCHC, RDWA, RDW_PERCENT, PLT, MPV, PDW, PCT, LPCR,
                    LYM_PERCENT, LYM_ABSOLUTE, MID_PERCENT, MID_ABSOLUTE, GRAN_PERCENT, GRAN_ABSOLUTE.
                    Output strictly JSON format. No markdown backticks.
                    """
          for m in ["gemini-2.5-flash", "gemini-3.5-flash-lite"]:
            try:
              resp = client.models.generate_content(
                  model=m,
                  contents=[
                      types.Part.from_bytes(
                          data=optimized, mime_type="image/jpeg"
                      ),
                      prompt,
                  ],
              )
              cleaned = re.sub(
                  r"^```json\s*|\s*```$", "", resp.text.strip(), flags=re.M
              ).strip()
              st.session_state.cbc_raw_data = json.loads(cleaned)
              st.success("Extracted successfully!")
              break
            except:
              continue
        except Exception as e:
          st.error(f"OCR Error: {e}")

  cbc_cols = st.columns(4)
  c_raw = st.session_state.cbc_raw_data

  with cbc_cols[0]:
    hgb = st.text_input(
        "Hemoglobin (Hb)",
        value=str(c_raw.get("HGB", c_raw.get("Hemoglobin", ""))),
    )
    rbc = st.text_input("Total RBC Count", value=str(c_raw.get("RBC", "")))
    hct = st.text_input(
        "Hematocrit (PCV)", value=str(c_raw.get("HCT", c_raw.get("PCV", "")))
    )
  with cbc_cols[1]:
    wbc = st.text_input(
        "Total WBC / TLC", value=str(c_raw.get("WBC", c_raw.get("TLC", "")))
    )
    gran_p = st.text_input(
        "Neutrophils / Gran (%)", value=str(c_raw.get("GRAN_PERCENT", ""))
    )
    lym_p = st.text_input(
        "Lymphocytes (%)", value=str(c_raw.get("LYM_PERCENT", ""))
    )
    mid_p = st.text_input(
        "Monocytes / Mid (%)", value=str(c_raw.get("MID_PERCENT", ""))
    )
  with cbc_cols[2]:
    plt = st.text_input(
        "Platelet Count (PLT)",
        value=str(c_raw.get("PLT", c_raw.get("Platelets", ""))),
    )
    mpv = st.text_input("MPV", value=str(c_raw.get("MPV", "")))
    pdw = st.text_input("PDW", value=str(c_raw.get("PDW", "")))
    pct = st.text_input("Plateletcrit (PCT)", value=str(c_raw.get("PCT", "")))
    lpcr = st.text_input("P-LCR", value=str(c_raw.get("LPCR", "")))
  with cbc_cols[3]:
    rdwa = st.text_input("RDW - SD (RDWa)", value=str(c_raw.get("RDWA", "")))
    rdw_cv = st.text_input(
        "RDW - CV (%)", value=str(c_raw.get("RDW_PERCENT", ""))
    )

    hgb_f, rbc_f, hct_f = safe_float(hgb), safe_float(rbc), safe_float(hct)
    calc_mcv = str(c_raw.get("MCV", ""))
    calc_mch = str(c_raw.get("MCH", ""))
    calc_mchc = str(c_raw.get("MCHC", ""))
    if not calc_mcv and hct_f and rbc_f and rbc_f > 0:
      calc_mcv = f"{(hct_f * 10) / rbc_f:.1f}"
    if not calc_mch and hgb_f and rbc_f and rbc_f > 0:
      calc_mch = f"{(hgb_f * 10) / rbc_f:.1f}"
    if not calc_mchc and hgb_f and hct_f and hct_f > 0:
      calc_mchc = f"{(hgb_f * 100) / hct_f:.1f}"

    mcv = st.text_input("MCV (Calculated / Analyzer)", value=calc_mcv)
    mch = st.text_input("MCH (Calculated / Analyzer)", value=calc_mch)
    mchc = st.text_input("MCHC (Calculated / Analyzer)", value=calc_mchc)

  st.markdown("##### 🔬 GBP / Peripheral Smear Findings")
  g_col1, g_col2 = st.columns(2)
  with g_col1:
    gbp_rbc = st.text_input(
        "RBC Morphology",
        value="Normocytic normochromic red cells with normal central pallor.",
    )
    gbp_wbc = st.text_input(
        "WBC Morphology",
        value=(
            "Mature neutrophils & lymphocytes seen. No atypical or blast cells."
        ),
    )
  with g_col2:
    gbp_plt = st.text_input(
        "Platelets on Smear",
        value="Adequate on smear, seen singly and in small aggregates.",
    )
    gbp_imp = st.text_input(
        "Diagnostic Impression",
        value="Complete hemogram within biological reference intervals.",
    )

  final_report_sections["CBC"] = {
      "items": {
          "Hemoglobin (Hb)": (hgb, "g/dL", "13.0 - 17.0"),
          "Total RBC Count": (rbc, "10^6/uL", "4.50 - 5.50"),
          "Packed Cell Volume (PCV/HCT)": (hct, "%", "40.0 - 50.0"),
          "Mean Corpuscular Volume (MCV)": (mcv, "fL", "80.0 - 100.0"),
          "Mean Corpuscular Hemoglobin (MCH)": (mch, "pg", "27.0 - 32.0"),
          "Mean Corpuscular Hb Conc. (MCHC)": (mchc, "g/dL", "31.5 - 35.5"),
          "RDW - SD (RDWa)": (rdwa, "fL", "39.0 - 46.0"),
          "RDW - CV": (rdw_cv, "%", "11.5 - 14.5"),
          "Total Leukocyte Count (WBC/TLC)": (wbc, "10^3/uL", "4.0 - 10.0"),
          "Granulocytes / Neutrophils (%)": (gran_p, "%", "40.0 - 70.0"),
          "Lymphocytes (%)": (lym_p, "%", "20.0 - 40.0"),
          "Mid Cells / Monocytes (%)": (mid_p, "%", "2.0 - 8.0"),
          "Platelet Count (PLT)": (plt, "10^3/uL", "150 - 450"),
          "Mean Platelet Volume (MPV)": (mpv, "fL", "7.5 - 11.5"),
          "Platelet Distribution Width (PDW)": (pdw, "%", "9.0 - 17.0"),
          "Plateletcrit (PCT)": (pct, "%", "0.10 - 0.50"),
          "Platelet Large Cell Ratio (P-LCR)": (lpcr, "%", "15.0 - 35.0"),
      },
      "gbp": {"rbc": gbp_rbc, "wbc": gbp_wbc, "plt": gbp_plt, "imp": gbp_imp},
  }

# ----------------- SECTION 2: LFT (AUTO CALCULATIONS) -----------------
if "Liver Function Test (LFT)" in selected_profiles:
  st.markdown("---")
  st.subheader("🧪 Liver Function Test (LFT) - Self Calculating")
  l_c1, l_c2, l_c3 = st.columns(3)
  with l_c1:
    b_tot = st.text_input("Bilirubin Total (mg/dL)", value="")
    b_dir = st.text_input("Bilirubin Direct (mg/dL)", value="")
    bt_f, bd_f = safe_float(b_tot), safe_float(b_dir)
    b_ind = (
        f"{max(0.0, bt_f - bd_f):.2f}"
        if (bt_f is not None and bd_f is not None)
        else ""
    )
    st.info(f"✨ Auto Indirect Bilirubin: {b_ind or '--'} mg/dL")
  with l_c2:
    sgot = st.text_input("SGOT / AST (U/L)", value="")
    sgpt = st.text_input("SGPT / ALT (U/L)", value="")
    alp = st.text_input("Alkaline Phosphatase (ALP) (U/L)", value="")
    sgot_f, sgpt_f = safe_float(sgot), safe_float(sgpt)
    de_ritis = (
        f"{(sgot_f / sgpt_f):.2f}"
        if (sgot_f and sgpt_f and sgpt_f > 0)
        else ""
    )
    if de_ritis:
      st.caption(f"De Ritis Ratio (AST/ALT): {de_ritis}")
  with l_c3:
    t_prot = st.text_input("Total Protein (g/dL)", value="")
    alb = st.text_input("Serum Albumin (g/dL)", value="")
    tp_f, alb_f = safe_float(t_prot), safe_float(alb)
    glob = (
        f"{max(0.0, tp_f - alb_f):.2f}"
        if (tp_f is not None and alb_f is not None)
        else ""
    )
    glob_f = safe_float(glob)
    ag_ratio = (
        f"{(alb_f / glob_f):.2f}"
        if (alb_f and glob_f and glob_f > 0)
        else ""
    )
    st.info(f"✨ Auto Globulin: {glob or '--'} | A:G Ratio: {ag_ratio or '--'}")

  final_report_sections["LFT"] = {
      "Serum Bilirubin Total": (b_tot, "mg/dL", "0.2 - 1.2"),
      "Serum Bilirubin Direct": (b_dir, "mg/dL", "0.0 - 0.3"),
      "Serum Bilirubin Indirect (Calculated)": (b_ind, "mg/dL", "0.2 - 0.9"),
      "SGOT / AST": (sgot, "U/L", "5 - 40"),
      "SGPT / ALT": (sgpt, "U/L", "5 - 45"),
      "AST : ALT (De Ritis) Ratio": (de_ritis, "Ratio", "0.8 - 1.5"),
      "Alkaline Phosphatase (ALP)": (alp, "U/L", "80 - 306"),
      "Serum Total Protein": (t_prot, "g/dL", "6.4 - 8.3"),
      "Serum Albumin": (alb, "g/dL", "3.5 - 5.2"),
      "Serum Globulin (Calculated)": (glob, "g/dL", "2.0 - 3.5"),
      "A : G Ratio (Calculated)": (ag_ratio, "Ratio", "1.2 - 2.2"),
  }

# ----------------- SECTION 3: KFT (AUTO CALCULATIONS) -----------------
if "Kidney Function Test (KFT / RFT)" in selected_profiles:
  st.markdown("---")
  st.subheader("🫘 Kidney Function Test (KFT / RFT) - Self Calculating")
  k_c1, k_c2, k_c3 = st.columns(3)
  with k_c1:
    urea = st.text_input("Blood Urea (mg/dL)", value="")
    creat = st.text_input("Serum Creatinine (mg/dL)", value="")
    u_f, cr_f = safe_float(urea), safe_float(creat)
    bun = f"{(u_f / 2.14):.2f}" if u_f is not None else ""
    u_cr_ratio = f"{(u_f / cr_f):.1f}" if (u_f and cr_f and cr_f > 0) else ""
    st.info(f"✨ Auto BUN: {bun or '--'} | Urea/Creat Ratio: {u_cr_ratio or '--'}")
  with k_c2:
    uric = st.text_input("Serum Uric Acid (mg/dL)", value="")
    calcium = st.text_input("Serum Calcium (mg/dL)", value="")
  with k_c3:
    sod = st.text_input("Serum Sodium (Na+) (mEq/L)", value="")
    pot = st.text_input("Serum Potassium (K+) (mEq/L)", value="")
    chlor = st.text_input("Serum Chloride (Cl-) (mEq/L)", value="")

  final_report_sections["KFT"] = {
      "Blood Urea": (urea, "mg/dL", "15.0 - 45.0"),
      "Serum Creatinine": (creat, "mg/dL", "0.6 - 1.4"),
      "Blood Urea Nitrogen (BUN) (Calculated)": (bun, "mg/dL", "7.0 - 20.0"),
      "Urea / Creatinine Ratio": (u_cr_ratio, "Ratio", "20.0 - 35.0"),
      "Serum Uric Acid": (uric, "mg/dL", "3.5 - 7.2"),
      "Serum Calcium": (calcium, "mg/dL", "8.5 - 10.5"),
      "Serum Sodium (Na+)": (sod, "mEq/L", "135 - 145"),
      "Serum Potassium (K+)": (pot, "mEq/L", "3.5 - 5.0"),
      "Serum Chloride (Cl-)": (chlor, "mEq/L", "96 - 106"),
  }

# ----------------- SECTION 4: LIPID PROFILE (FRIEDEWALD EQUATIONS) -----------------
if "Lipid Profile" in selected_profiles:
  st.markdown("---")
  st.subheader("❤️ Lipid Profile - Self Calculating (Friedewald Equation)")
  lp_c1, lp_c2 = st.columns(2)
  with lp_c1:
    chol = st.text_input("Total Cholesterol (mg/dL)", value="")
    trig = st.text_input("Serum Triglycerides (mg/dL)", value="")
    hdl = st.text_input("HDL Cholesterol (Good) (mg/dL)", value="")
  with lp_c2:
    ch_f, tr_f, hd_f = safe_float(chol), safe_float(trig), safe_float(hdl)
    vldl = f"{(tr_f / 5.0):.1f}" if tr_f is not None else ""
    vldl_f = safe_float(vldl)
    ldl = (
        f"{(ch_f - hd_f - vldl_f):.1f}" if (ch_f and hd_f and vldl_f) else ""
    )
    tc_hdl = f"{(ch_f / hd_f):.2f}" if (ch_f and hd_f and hd_f > 0) else ""
    non_hdl = f"{(ch_f - hd_f):.1f}" if (ch_f and hd_f) else ""
    st.info(
        f"✨ Auto VLDL: {vldl or '--'} | Auto LDL: {ldl or '--'} | TC/HDL Ratio:"
        f" {tc_hdl or '--'}"
    )

  final_report_sections["LIPID"] = {
      "Total Cholesterol": (chol, "mg/dL", "< 200 (Desirable)"),
      "Serum Triglycerides": (trig, "mg/dL", "< 150 (Normal)"),
      "HDL Cholesterol (Good)": (hdl, "mg/dL", "> 40 (Optimal)"),
      "LDL Cholesterol (Bad) (Calculated)": (ldl, "mg/dL", "< 100 (Optimal)"),
      "VLDL Cholesterol (Calculated)": (vldl, "mg/dL", "5.0 - 30.0"),
      "Non-HDL Cholesterol (Calculated)": (non_hdl, "mg/dL", "< 130"),
      "Total Chol / HDL Ratio (Calculated)": (tc_hdl, "Ratio", "3.0 - 5.0"),
  }

# ----------------- SECTION 5: SEROLOGY & RAPID -----------------
serology_dict = {}
if "Widal Agglutination Test" in selected_profiles:
  st.markdown("---")
  st.subheader("🌡️ Widal Agglutination Slide / Tube Test")
  w1, w2, w3, w4 = st.columns(4)
  with w1:
    wo = st.selectbox(
        "S. typhi 'O'",
        ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"],
        key="w_o",
    )
  with w2:
    wh = st.selectbox(
        "S. typhi 'H'",
        ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"],
        key="w_h",
    )
  with w3:
    wah = st.selectbox(
        "S. paratyphi 'AH'", ["Negative", "1:20", "1:40", "1:80"], key="w_ah"
    )
  with w4:
    wbh = st.selectbox(
        "S. paratyphi 'BH'", ["Negative", "1:20", "1:40", "1:80"], key="w_bh"
    )
  serology_dict["Salmonella typhi 'O'"] = (wo, "Titer", "Significant >= 1:80")
  serology_dict["Salmonella typhi 'H'"] = (wh, "Titer", "Significant >= 1:160")
  serology_dict["Salmonella paratyphi 'AH'"] = (
      wah,
      "Titer",
      "Negative / Non-significant",
  )
  serology_dict["Salmonella paratyphi 'BH'"] = (
      wbh,
      "Titer",
      "Negative / Non-significant",
  )

if "Typhidot (IgM / IgG)" in selected_profiles:
  st.markdown("---")
  st.subheader("🧪 Typhidot Rapid Card Test")
  t1, t2 = st.columns(2)
  with t1:
    ty_m = st.selectbox(
        "Typhidot IgM (Acute Phase)",
        ["Non-Reactive (Negative)", "Reactive (Positive)"],
        key="ty_m",
    )
  with t2:
    ty_g = st.selectbox(
        "Typhidot IgG (Convalescent/Carrier)",
        ["Non-Reactive (Negative)", "Reactive (Positive)"],
        key="ty_g",
    )
  serology_dict["Typhidot IgM Antibody"] = (
      ty_m,
      "Qualitative",
      "Non-Reactive (Negative)",
  )
  serology_dict["Typhidot IgG Antibody"] = (
      ty_g,
      "Qualitative",
      "Non-Reactive (Negative)",
  )

if "Malaria Card & Smear (MP)" in selected_profiles:
  st.markdown("---")
  st.subheader("🦟 Malaria Diagnostic Profile")
  m1, m2, m3 = st.columns(3)
  with m1:
    mp_smear = st.selectbox(
        "Peripheral Smear for MP",
        [
            "Not Seen",
            "P. vivax trophozoites seen",
            "P. falciparum ring forms seen",
        ],
        key="mp_smear",
    )
  with m2:
    mp_pv = st.selectbox(
        "P. vivax Antigen (Rapid)", ["Negative", "Positive"], key="mp_pv"
    )
  with m3:
    mp_pf = st.selectbox(
        "P. falciparum Antigen (Rapid)", ["Negative", "Positive"], key="mp_pf"
    )
  serology_dict["Malarial Parasite (Smear)"] = (
      mp_smear,
      "Microscopy",
      "No Parasites Seen",
  )
  serology_dict["P. vivax Antigen"] = (
      mp_pv,
      "Immunochromatography",
      "Negative",
  )
  serology_dict["P. falciparum Antigen"] = (
      mp_pf,
      "Immunochromatography",
      "Negative",
  )

if "Blood Glucose" in selected_profiles:
  st.markdown("---")
  st.subheader("🍬 Blood Glucose Profile")
  g1, g2, g3 = st.columns(3)
  with g1:
    glu_f = st.text_input("Fasting Blood Sugar (FBS)", value="", key="glu_f")
  with g2:
    glu_pp = st.text_input(
        "Post Prandial Blood Sugar (PPBS)", value="", key="glu_pp"
    )
  with g3:
    glu_r = st.text_input("Random Blood Sugar (RBS)", value="", key="glu_r")
  if glu_f:
    serology_dict["Blood Glucose (Fasting)"] = (glu_f, "mg/dL", "70.0 - 100.0")
  if glu_pp:
    serology_dict["Blood Glucose (PP)"] = (glu_pp, "mg/dL", "70.0 - 140.0")
  if glu_r:
    serology_dict["Blood Glucose (Random)"] = (glu_r, "mg/dL", "70.0 - 140.0")

if serology_dict:
  final_report_sections["SEROLOGY"] = serology_dict


# ----------------- SAFE PDF REPORT MANAGER CLASS -----------------
class PDFReportManager:

  def __init__(self, buffer, p_dict):
    self.c = canvas.Canvas(buffer, pagesize=letter)
    self.width, self.height = letter
    self.p = p_dict
    self.curr_y = self.height - 134
    self.now_dt = datetime.now()
    self.report_dt_str = self.now_dt.strftime("%d-%b-%Y %I:%M:%S %p")
    self.coll_dt_str = self.now_dt.strftime("%d-%b-%Y %I:%M %p")
    self.draw_header()

  def draw_header(self):
    self.c.setFillColor(colors.HexColor("#1e3a8a"))
    self.c.rect(0, self.height - 60, self.width, 60, fill=True, stroke=False)
    self.c.setFillColor(colors.white)
    self.c.setFont("Helvetica-Bold", 17)
    self.c.drawString(32, self.height - 30, "THE SEN LABS")
    self.c.setFont("Helvetica", 7.8)
    self.c.drawString(
        32,
        self.height - 46,
        "ADVANCED PATHOLOGY & CLINICAL BIOCHEMISTRY | AUTOMATED DIAGNOSTICS",
    )
    self.c.drawRightString(
        self.width - 32, self.height - 34, f"Helpdesk: +91 {self.p['contact']}"
    )

    self.c.setFillColor(colors.HexColor("#f8fafc"))
    self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
    self.c.roundRect(
        32, self.height - 122, self.width - 64, 56, 3, fill=True, stroke=True
    )

    self.c.setFillColor(colors.HexColor("#475569"))
    self.c.setFont("Helvetica-Bold", 7.5)
    self.c.drawString(42, self.height - 80, "Patient Name:")
    self.c.drawString(42, self.height - 94, "Age / Sex:")
    self.c.drawString(42, self.height - 108, "Referred By:")

    self.c.setFont("Helvetica", 7.5)
    self.c.drawString(108, self.height - 80, f"Mr./Ms. {self.p['name']}")
    self.c.drawString(
        108, self.height - 94, f"{self.p['age']} Yrs / {self.p['sex']}"
    )
    self.c.drawString(108, self.height - 108, f"Dr. {self.p['doctor']}")

    self.c.setFont("Helvetica-Bold", 7.5)
    self.c.drawString(310, self.height - 80, "Sample ID:")
    self.c.drawString(310, self.height - 94, "Collection Time:")
    self.c.drawString(310, self.height - 108, "Reporting Date & Time:")

    self.c.setFont("Helvetica", 7.5)
    self.c.drawString(405, self.height - 80, self.p["sample_id"])
    self.c.drawString(405, self.height - 94, self.coll_dt_str)
    self.c.drawString(405, self.height - 108, self.report_dt_str)

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

  def print_section(self, title, data_dict, bar_hex):
    active_rows = {
        k: v for k, v in data_dict.items() if str(v[0]).strip() != ""
    }
    if not active_rows:
      return

    needed = 26 + (len(active_rows) * 11)
    if self.curr_y - needed < 65:
      self.draw_footer()
      self.c.showPage()
      self.draw_header()
      self.curr_y = self.height - 134

    self.c.setFillColor(colors.HexColor(bar_hex))
    self.c.rect(
        32, self.curr_y - 12, self.width - 64, 12, fill=True, stroke=False
    )
    self.c.setFillColor(colors.white)
    self.c.setFont("Helvetica-Bold", 7)
    self.c.drawString(38, self.curr_y - 9, title)

    self.c.setFillColor(colors.HexColor("#e2e8f0"))
    self.c.rect(
        32, self.curr_y - 25, self.width - 64, 12, fill=True, stroke=False
    )
    self.c.setFillColor(colors.HexColor("#0f172a"))
    self.c.setFont("Helvetica-Bold", 6.8)
    self.c.drawString(38, self.curr_y - 22, "TEST / PARAMETER")
    self.c.drawString(245, self.curr_y - 22, "OBSERVED VALUE")
    self.c.drawString(320, self.curr_y - 22, "UNIT")
    self.c.drawString(400, self.curr_y - 22, "BIOLOGICAL REFERENCE RANGE")

    y = self.curr_y - 36
    self.c.setFont("Helvetica", 6.8)
    for param, (val, unit, ref) in active_rows.items():
      self.c.setFillColor(colors.HexColor("#0f172a"))
      self.c.drawString(38, y, str(param))

      self.c.setFont("Helvetica-Bold", 6.8)
      self.c.drawString(245, y, str(val))
      self.c.setFont("Helvetica", 6.8)

      self.c.drawString(320, y, str(unit))
      self.c.drawString(400, y, str(ref))

      self.c.setStrokeColor(colors.HexColor("#f1f5f9"))
      self.c.line(32, y - 2, self.width - 32, y - 2)
      y -= 10.8

    self.curr_y = y - 6

  def print_gbp_box(self, gbp_data):
    if self.curr_y - 65 < 65:
      self.draw_footer()
      self.c.showPage()
      self.draw_header()
      self.curr_y = self.height - 134

    self.c.setFillColor(colors.HexColor("#1e3a8a"))
    self.c.rect(
        32, self.curr_y - 10, self.width - 64, 11, fill=True, stroke=False
    )
    self.c.setFillColor(colors.white)
    self.c.setFont("Helvetica-Bold", 7)
    self.c.drawString(
        38,
        self.curr_y - 7,
        "GENERAL BLOOD PICTURE (PERIPHERAL BLOOD SMEAR EXAMINATION)",
    )

    box_top = self.curr_y - 11
    self.c.setFillColor(colors.HexColor("#f8fafc"))
    self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
    self.c.rect(32, box_top - 46, self.width - 64, 46, fill=True, stroke=True)

    gy = box_top - 9
    for label, txt in [
        ("RBC Morphology", gbp_data["rbc"]),
        ("WBC Morphology", gbp_data["wbc"]),
        ("Platelets on Smear", gbp_data["plt"]),
        ("Diagnostic Impression", gbp_data["imp"]),
    ]:
      self.c.setFont("Helvetica-Bold", 6.8)
      self.c.setFillColor(colors.HexColor("#0f172a"))
      self.c.drawString(38, gy, f"{label}:")
      self.c.setFont("Helvetica", 6.8)
      self.c.setFillColor(colors.HexColor("#334155"))
      self.c.drawString(125, gy, txt[:105])
      gy -= 9.5

    self.curr_y = box_top - 54

  def finish(self):
    self.draw_footer()
    self.c.save()


# ----------------- REPORT ACTION -----------------
st.markdown("---")
if not selected_profiles:
  st.info(
      "👆 Kripya Section 2 me se kam se kam ek test profile select karein"
      " (jaise CBC, LFT, KFT ya Widal)."
  )
else:
  if st.button("🖨️ Generate Professional Pathology Report (PDF)"):
    buf = io.BytesIO()
    p_info = {
        "name": p_name or "Anonymous",
        "age": p_age or "--",
        "sex": p_sex,
        "doctor": p_doctor or "Self",
        "contact": p_contact or "9076816740",
        "sample_id": sample_id,
    }

    doc = PDFReportManager(buf, p_info)

    # 1. CBC
    if "CBC" in final_report_sections:
      doc.print_section(
          "COMPLETE BLOOD COUNT (AUTOMATED HEMATOLOGY PROFILE)",
          final_report_sections["CBC"]["items"],
          "#0f766e",
      )
      doc.print_gbp_box(final_report_sections["CBC"]["gbp"])

    # 2. LFT
    if "LFT" in final_report_sections:
      doc.print_section(
          "CLINICAL BIOCHEMISTRY - LIVER FUNCTION TEST (LFT)",
          final_report_sections["LFT"],
          "#854d0e",
      )

    # 3. KFT
    if "KFT" in final_report_sections:
      doc.print_section(
          "CLINICAL BIOCHEMISTRY - KIDNEY FUNCTION TEST (KFT)",
          final_report_sections["KFT"],
          "#7c2d12",
      )

    # 4. Lipid
    if "LIPID" in final_report_sections:
      doc.print_section(
          "CLINICAL BIOCHEMISTRY - LIPID PROFILE",
          final_report_sections["LIPID"],
          "#be123c",
      )

    # 5. Serology
    if "SEROLOGY" in final_report_sections:
      doc.print_section(
          "SEROLOGY & RAPID CLINICAL IMMUNOLOGY",
          final_report_sections["SEROLOGY"],
          "#4338ca",
      )

    doc.finish()
    buf.seek(0)

    st.download_button(
        label="📥 Download Tailored Pathology Report (PDF)",
        data=buf,
        file_name=f"{p_name or 'Patient'}_Pathology_Report.pdf",
        mime="application/pdf",
    )
