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
  p_age = st.text_input("Age (Yrs)", value="")
with c2:
  p_sex = st.selectbox("Sex", ["Male (M)", "Female (F)", "Other"])
  p_doctor = st.text_input("Referred By (Doctor)", value="Self")
with c3:
  p_contact = st.text_input("Lab Contact / Helpline", value="9076816740")
  sample_id = st.text_input("Sample ID / Lab No.", value="TSL-2026-9081")

# 2. Multi-Test Profile Selector (Starts Clean / Empty)
st.subheader("2. Select Test Profiles for Patient")
selected_profiles = st.multiselect(
    "Jo test patient ke liye karne hain unhe select karein:",
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
    default=[],  # Koi test pehle se chuna hua nahi rahega
)


def compress_image_for_fast_ai(img_file):
  img = Image.open(img_file)
  if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
  img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
  out_bytes = io.BytesIO()
  img.save(out_bytes, format="JPEG", quality=82, optimize=True)
  return out_bytes.getvalue()


# Helper float parser
def parse_num(val):
  try:
    return float(str(val).strip().replace(",", "."))
  except:
    return None


# ----------------------------------------------------
# 3. Dynamic Test Sections (Only shows what is selected)
# ----------------------------------------------------

# SECTION: CBC (Only when selected)
cbc_inputs = {}
gbp_rbc, gbp_wbc, gbp_plt, gbp_imp = "", "", "", ""

if "Complete Blood Count (CBC + GBP)" in selected_profiles:
  st.markdown("---")
  st.subheader("🩸 Complete Blood Count (CBC + GBP)")

  input_mode = st.radio(
      "Machine Photo Input Method:",
      ("📁 Upload from Gallery", "📸 Live Camera"),
      horizontal=True,
  )
  active_image = None
  if input_mode == "📁 Upload from Gallery":
    active_image = st.file_uploader(
        "Upload machine screen/slip photo",
        type=["jpg", "jpeg", "png"],
        key="cbc_upl",
    )
  else:
    active_image = st.camera_input("Capture machine display", key="cbc_cam")

  if "extracted_cbc" not in st.session_state:
    st.session_state.extracted_cbc = {}

  if active_image and st.button("⚡ Extract CBC Parameters (Fast OCR)"):
    if not api_key:
      st.error("Pehle sidebar me Gemini API Key dalein!")
    else:
      with st.spinner("Extracting parameters..."):
        try:
          client = genai.Client(api_key=api_key)
          opt_bytes = compress_image_for_fast_ai(active_image)
          prompt = """
                    Extract ALL hematology parameters and numeric values from this analyzer display/printout.
                    Keys: WBC, RBC, HGB, HCT, MCV, MCH, MCHC, RDWA, RDW_PERCENT, PLT, MPV, PDW, PCT, LPCR,
                    LYM_PERCENT, LYM_ABSOLUTE, MID_PERCENT, MID_ABSOLUTE, GRAN_PERCENT, GRAN_ABSOLUTE.
                    Output strictly JSON format. No backticks.
                    """
          for m in ["gemini-2.5-flash", "gemini-3.5-flash-lite"]:
            try:
              resp = client.models.generate_content(
                  model=m,
                  contents=[
                      types.Part.from_bytes(
                          data=opt_bytes, mime_type="image/jpeg"
                      ),
                      prompt,
                  ],
              )
              cleaned = re.sub(
                  r"^```json\s*|\s*```$", "", resp.text.strip(), flags=re.M
              ).strip()
              st.session_state.extracted_cbc = json.loads(cleaned)
              st.success(
                  f"Extracted {len(st.session_state.extracted_cbc)} parameters!"
              )
              break
            except:
              continue
        except Exception as e:
          st.error(f"Extraction error: {e}")

  cbc_keys = [
      ("HGB", "Hemoglobin (Hb)"),
      ("RBC", "Total RBC Count"),
      ("HCT", "Packed Cell Volume (PCV/HCT)"),
      ("MCV", "Mean Corpuscular Volume (MCV)"),
      ("MCH", "Mean Corpuscular Hemoglobin (MCH)"),
      ("MCHC", "Mean Corpuscular Hb Conc. (MCHC)"),
      ("RDWA", "RDW - SD (RDWa)"),
      ("RDW_PERCENT", "RDW - CV"),
      ("WBC", "Total Leukocyte Count (WBC/TLC)"),
      ("GRAN_PERCENT", "Granulocytes / Neutrophils (%)"),
      ("GRAN_ABSOLUTE", "Granulocytes Absolute (#)"),
      ("LYM_PERCENT", "Lymphocytes (%)"),
      ("LYM_ABSOLUTE", "Lymphocytes Absolute (#)"),
      ("MID_PERCENT", "Mid Cells / Monocytes (%)"),
      ("MID_ABSOLUTE", "Mid Cells / Monocytes Absolute (#)"),
      ("PLT", "Platelet Count (PLT)"),
      ("MPV", "Mean Platelet Volume (MPV)"),
      ("PDW", "Platelet Distribution Width (PDW)"),
      ("PCT", "Plateletcrit (PCT)"),
      ("LPCR", "Platelet Large Cell Ratio (P-LCR)"),
  ]

  cols = st.columns(4)
  for idx, (k, label) in enumerate(cbc_keys):
    curr_val = st.session_state.extracted_cbc.get(k, "")
    with cols[idx % 4]:
      cbc_inputs[k] = st.text_input(label, value=str(curr_val), key=f"in_{k}")

  # GBP
  st.markdown("#### 🔬 General Blood Picture (GBP Findings)")
  hb_check = parse_num(cbc_inputs.get("HGB")) or 13.5
  mcv_check = parse_num(cbc_inputs.get("MCV")) or 88.0
  plt_check = parse_num(cbc_inputs.get("PLT")) or 250.0

  if hb_check < 12.0 and mcv_check < 80.0:
    def_rbc = (
        "Microcytic, hypochromic red cells with mild anisopoikilocytosis. Few"
        " pencil cells seen."
    )
    def_imp = (
        "Microcytic Hypochromic Anemia (Probable Iron Deficiency). Advised:"
        " Serum Ferritin."
    )
  else:
    def_rbc = (
        "Predominantly normocytic normochromic. Central pallor is normal. No"
        " inclusion bodies seen."
    )
    def_imp = (
        "Hematological parameters within normal limits. No specific pathology"
        " identified."
    )

  def_plt = (
      "Reduced on smear."
      if plt_check < 150
      else (
          "Adequate in number, seen singly and in small clumps. Normal"
          " morphology."
      )
  )

  gb_c1, gb_c2 = st.columns(2)
  with gb_c1:
    gbp_rbc = st.text_input("RBC Morphology", value=def_rbc)
    gbp_wbc = st.text_input(
        "WBC Morphology",
        value=(
            "Mature neutrophils and lymphocytes seen. No atypical cells or"
            " blasts."
        ),
    )
  with gb_c2:
    gbp_plt = st.text_input("Platelets on Smear", value=def_plt)
    gbp_imp = st.text_input("Diagnostic Impression", value=def_imp)


# SECTION: LFT (With Auto-Formulas)
lft_inputs = {}
if "Liver Function Test (LFT)" in selected_profiles:
  st.markdown("---")
  st.subheader("🧪 Liver Function Test (LFT)")
  lc1, lc2, lc3 = st.columns(3)
  with lc1:
    b_tot = st.text_input("Bilirubin Total (mg/dL)", value="", key="lft_btot")
    b_dir = st.text_input("Bilirubin Direct (mg/dL)", value="", key="lft_bdir")
    # Auto formula: Indirect = Total - Direct
    bt_val, bd_val = parse_num(b_tot), parse_num(b_dir)
    auto_indir = (
        f"{round(bt_val - bd_val, 2)}"
        if (bt_val is not None and bd_val is not None and bt_val >= bd_val)
        else ""
    )
    b_ind = st.text_input(
        "Bilirubin Indirect (Auto-Calculated)",
        value=auto_indir,
        key="lft_bind",
    )

  with lc2:
    sgot = st.text_input("SGOT / AST (U/L)", value="", key="lft_sgot")
    sgpt = st.text_input("SGPT / ALT (U/L)", value="", key="lft_sgpt")
    alp = st.text_input(
        "Alkaline Phosphatase - ALP (U/L)", value="", key="lft_alp"
    )
    # Auto formula: AST/ALT Ratio
    sgot_v, sgpt_v = parse_num(sgot), parse_num(sgpt)
    auto_deritis = (
        f"{round(sgot_v / sgpt_v, 2)}"
        if (sgot_v is not None and sgpt_v and sgpt_v > 0)
        else ""
    )
    ast_alt_ratio = st.text_input(
        "AST / ALT Ratio (De Ritis Ratio)",
        value=auto_deritis,
        key="lft_deritis",
    )

  with lc3:
    t_prot = st.text_input("Total Protein (g/dL)", value="", key="lft_prot")
    s_alb = st.text_input("Serum Albumin (g/dL)", value="", key="lft_alb")
    # Auto formulas: Globulin = Protein - Albumin, A:G Ratio = Albumin / Globulin
    tp_val, alb_val = parse_num(t_prot), parse_num(s_alb)
    auto_glob = (
        f"{round(tp_val - alb_val, 2)}"
        if (tp_val is not None and alb_val is not None and tp_val >= alb_val)
        else ""
    )
    s_glob = st.text_input(
        "Serum Globulin (Auto-Calculated)", value=auto_glob, key="lft_glob"
    )

    glob_val = parse_num(auto_glob)
    auto_ag = (
        f"{round(alb_val / glob_val, 2)}"
        if (alb_val is not None and glob_val and glob_val > 0)
        else ""
    )
    ag_ratio = st.text_input(
        "A : G Ratio (Auto-Calculated)", value=auto_ag, key="lft_ag"
    )

  # Fill dictionary
  lft_dict_raw = {
      "Bilirubin Total": b_tot,
      "Bilirubin Direct": b_dir,
      "Bilirubin Indirect": b_ind,
      "SGOT / AST": sgot,
      "SGPT / ALT": sgpt,
      "AST / ALT Ratio": ast_alt_ratio,
      "Alkaline Phosphatase (ALP)": alp,
      "Total Protein": t_prot,
      "Serum Albumin": s_alb,
      "Serum Globulin": s_glob,
      "A:G Ratio": ag_ratio,
  }
  lft_inputs = {k: v for k, v in lft_dict_raw.items() if str(v).strip()}


# SECTION: KFT (With Auto-Formulas)
kft_inputs = {}
if "Kidney Function Test (KFT / RFT)" in selected_profiles:
  st.markdown("---")
  st.subheader("🫘 Kidney Function Test (KFT / RFT)")
  kc1, kc2, kc3 = st.columns(3)
  with kc1:
    urea = st.text_input("Blood Urea (mg/dL)", value="", key="kft_urea")
    creat = st.text_input("Serum Creatinine (mg/dL)", value="", key="kft_creat")
    # Auto formula: BUN = Urea / 2.14
    u_val, cr_val = parse_num(urea), parse_num(creat)
    auto_bun = f"{round(u_val / 2.14, 2)}" if u_val is not None else ""
    bun = st.text_input(
        "Blood Urea Nitrogen - BUN (Auto)", value=auto_bun, key="kft_bun"
    )

    auto_uc_ratio = (
        f"{round(u_val / cr_val, 2)}"
        if (u_val is not None and cr_val and cr_val > 0)
        else ""
    )
    uc_ratio = st.text_input(
        "Urea / Creatinine Ratio (Auto)", value=auto_uc_ratio, key="kft_ucrat"
    )

  with kc2:
    uric = st.text_input("Serum Uric Acid (mg/dL)", value="", key="kft_uric")
    calcium = st.text_input("Serum Calcium (mg/dL)", value="", key="kft_ca")
  with kc3:
    sodium = st.text_input(
        "Serum Sodium - Na+ (mEq/L)", value="", key="kft_na"
    )
    potass = st.text_input(
        "Serum Potassium - K+ (mEq/L)", value="", key="kft_k"
    )

  kft_dict_raw = {
      "Blood Urea": urea,
      "Serum Creatinine": creat,
      "Blood Urea Nitrogen (BUN)": bun,
      "Urea / Creatinine Ratio": uc_ratio,
      "Serum Uric Acid": uric,
      "Serum Calcium": calcium,
      "Serum Sodium (Na+)": sodium,
      "Serum Potassium (K+)": potass,
  }
  kft_inputs = {k: v for k, v in kft_dict_raw.items() if str(v).strip()}


# SECTION: Lipid Profile (With Friedewald Equations)
lipid_inputs = {}
if "Lipid Profile" in selected_profiles:
  st.markdown("---")
  st.subheader("❤️ Lipid Profile (With Automatic Formulas)")
  lip1, lip2, lip3 = st.columns(3)
  with lip1:
    tc = st.text_input("Total Cholesterol (mg/dL)", value="", key="lip_tc")
    tg = st.text_input("Serum Triglycerides (mg/dL)", value="", key="lip_tg")
    hdl = st.text_input("HDL Cholesterol (mg/dL)", value="", key="lip_hdl")

  tc_v, tg_v, hdl_v = parse_num(tc), parse_num(tg), parse_num(hdl)
  # Formulas:
  # VLDL = Triglycerides / 5
  # LDL = Total Cholesterol - HDL - VLDL
  # Non-HDL = Total Cholesterol - HDL
  auto_vldl = f"{round(tg_v / 5, 2)}" if tg_v is not None else ""
  vldl_v = parse_num(auto_vldl)

  auto_ldl = (
      f"{round(tc_v - hdl_v - vldl_v, 2)}"
      if (tc_v is not None and hdl_v is not None and vldl_v is not None)
      else ""
  )
  ldl_v = parse_num(auto_ldl)

  auto_tc_hdl = (
      f"{round(tc_v / hdl_v, 2)}"
      if (tc_v is not None and hdl_v and hdl_v > 0)
      else ""
  )
  auto_ldl_hdl = (
      f"{round(ldl_v / hdl_v, 2)}"
      if (ldl_v is not None and hdl_v and hdl_v > 0)
      else ""
  )
  auto_non_hdl = (
      f"{round(tc_v - hdl_v, 2)}"
      if (tc_v is not None and hdl_v is not None)
      else ""
  )

  with lip2:
    vldl = st.text_input(
        "VLDL Cholesterol (Auto: TG/5)", value=auto_vldl, key="lip_vldl"
    )
    ldl = st.text_input(
        "LDL Cholesterol (Auto: TC - HDL - VLDL)",
        value=auto_ldl,
        key="lip_ldl",
    )
    non_hdl = st.text_input(
        "Non-HDL Cholesterol (Auto)", value=auto_non_hdl, key="lip_nonhdl"
    )

  with lip3:
    tc_hdl = st.text_input(
        "TC / HDL Ratio (Auto)", value=auto_tc_hdl, key="lip_tchdl"
    )
    ldl_hdl = st.text_input(
        "LDL / HDL Ratio (Auto)", value=auto_ldl_hdl, key="lip_ldlhdl"
    )

  lip_dict_raw = {
      "Total Cholesterol": tc,
      "Triglycerides": tg,
      "HDL Cholesterol": hdl,
      "LDL Cholesterol": ldl,
      "VLDL Cholesterol": vldl,
      "Non-HDL Cholesterol": non_hdl,
      "TC / HDL Ratio": tc_hdl,
      "LDL / HDL Ratio": ldl_hdl,
  }
  lipid_inputs = {k: v for k, v in lip_dict_raw.items() if str(v).strip()}


# SECTION: Serology / Rapid Tests
serology_inputs = {}
if "Widal Agglutination Test" in selected_profiles:
  st.markdown("---")
  st.subheader("🌡️ Widal Agglutination Test (Slide / Tube)")
  wc = st.columns(4)
  with wc[0]:
    w_o = st.selectbox(
        "S. typhi 'O'",
        ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"],
        index=0,
    )
  with wc[1]:
    w_h = st.selectbox(
        "S. typhi 'H'",
        ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"],
        index=0,
    )
  with wc[2]:
    w_ah = st.selectbox(
        "S. paratyphi 'AH'", ["Negative", "1:20", "1:40", "1:80"], index=0
    )
  with wc[3]:
    w_bh = st.selectbox(
        "S. paratyphi 'BH'", ["Negative", "1:20", "1:40", "1:80"], index=0
    )
  serology_inputs["Salmonella typhi 'O'"] = w_o
  serology_inputs["Salmonella typhi 'H'"] = w_h
  serology_inputs["Salmonella paratyphi 'AH'"] = w_ah
  serology_inputs["Salmonella paratyphi 'BH'"] = w_bh

if "Typhidot (IgM / IgG)" in selected_profiles:
  st.markdown("---")
  st.subheader("🧪 Typhidot Rapid Card")
  tc = st.columns(2)
  with tc[0]:
    t_igm = st.selectbox(
        "Typhidot IgM (Acute Infection)",
        ["Non-Reactive (Negative)", "Reactive (Positive)"],
    )
  with tc[1]:
    t_igg = st.selectbox(
        "Typhidot IgG (Past / Carrier)",
        ["Non-Reactive (Negative)", "Reactive (Positive)"],
    )
  serology_inputs["Typhidot IgM (Acute Infection)"] = t_igm
  serology_inputs["Typhidot IgG (Past / Carrier)"] = t_igg

if "Malaria Card & Smear (MP)" in selected_profiles:
  st.markdown("---")
  st.subheader("🦟 Malaria Examination")
  mc = st.columns(3)
  with mc[0]:
    m_smear = st.selectbox(
        "Peripheral Smear Examination",
        ["Not Seen", "P. vivax trophozoites seen", "P. falciparum rings seen"],
    )
  with mc[1]:
    m_pv = st.selectbox("P. vivax Antigen (Card)", ["Negative", "Positive"])
  with mc[2]:
    m_pf = st.selectbox(
        "P. falciparum Antigen (Card)", ["Negative", "Positive"]
    )
  serology_inputs["Malarial Parasite (Smear)"] = m_smear
  serology_inputs["P. vivax Antigen (Rapid Card)"] = m_pv
  serology_inputs["P. falciparum Antigen (Rapid Card)"] = m_pf

if "Blood Glucose" in selected_profiles:
  st.markdown("---")
  st.subheader("🍬 Blood Glucose")
  gc = st.columns(3)
  with gc[0]:
    g_f = st.text_input("Blood Glucose - Fasting (mg/dL)", value="")
    if g_f:
      serology_inputs["Blood Glucose (Fasting)"] = g_f
  with gc[1]:
    g_pp = st.text_input("Blood Glucose - Post Prandial (mg/dL)", value="")
    if g_pp:
      serology_inputs["Blood Glucose (PP)"] = g_pp
  with gc[2]:
    g_r = st.text_input("Blood Glucose - Random (mg/dL)", value="")
    if g_r:
      serology_inputs["Blood Glucose (Random)"] = g_r

# Universal Reference Range Database
MASTER_REFS = {
    # CBC
    "hgb": {"name": "Hemoglobin (Hb)", "unit": "g/dL", "ref": "13.0 - 17.0"},
    "rbc": {"name": "Total RBC Count", "unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "hct": {
        "name": "Packed Cell Volume (PCV/HCT)",
        "unit": "%",
        "ref": "40.0 - 50.0",
    },
    "mcv": {
        "name": "Mean Corpuscular Volume (MCV)",
        "unit": "fL",
        "ref": "80.0 - 100.0",
    },
    "mch": {
        "name": "Mean Corpuscular Hemoglobin (MCH)",
        "unit": "pg",
        "ref": "27.0 - 32.0",
    },
    "mchc": {
        "name": "Mean Corpuscular Hb Conc. (MCHC)",
        "unit": "g/dL",
        "ref": "31.5 - 35.5",
    },
    "rdwa": {"name": "RDW - SD (RDWa)", "unit": "fL", "ref": "39.0 - 46.0"},
    "rdw_percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "wbc": {
        "name": "Total Leukocyte Count (WBC/TLC)",
        "unit": "10^3/uL",
        "ref": "4.0 - 10.0",
    },
    "gran_percent": {
        "name": "Granulocytes / Neutrophils (%)",
        "unit": "%",
        "ref": "40.0 - 70.0",
    },
    "gran_absolute": {
        "name": "Granulocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "2.0 - 7.0",
    },
    "lym_percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "lym_absolute": {
        "name": "Lymphocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "1.0 - 3.0",
    },
    "mid_percent": {
        "name": "Mid Cells / Monocytes (%)",
        "unit": "%",
        "ref": "2.0 - 8.0",
    },
    "mid_absolute": {
        "name": "Mid Cells / Monocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "0.1 - 0.8",
    },
    "plt": {
        "name": "Platelet Count (PLT)",
        "unit": "10^3/uL",
        "ref": "150 - 450",
    },
    "mpv": {
        "name": "Mean Platelet Volume (MPV)",
        "unit": "fL",
        "ref": "7.5 - 11.5",
    },
    "pdw": {
        "name": "Platelet Distribution Width (PDW)",
        "unit": "%",
        "ref": "9.0 - 17.0",
    },
    "pct": {"name": "Plateletcrit (PCT)", "unit": "%", "ref": "0.10 - 0.50"},
    "lpcr": {
        "name": "Platelet Large Cell Ratio (P-LCR)",
        "unit": "%",
        "ref": "15.0 - 35.0",
    },
    # LFT
    "Bilirubin Total": {
        "name": "Serum Bilirubin Total",
        "unit": "mg/dL",
        "ref": "0.2 - 1.2",
    },
    "Bilirubin Direct": {
        "name": "Serum Bilirubin Direct",
        "unit": "mg/dL",
        "ref": "0.0 - 0.3",
    },
    "Bilirubin Indirect": {
        "name": "Serum Bilirubin Indirect",
        "unit": "mg/dL",
        "ref": "0.2 - 0.9",
    },
    "SGOT / AST": {"name": "SGOT / AST", "unit": "U/L", "ref": "5 - 40"},
    "SGPT / ALT": {"name": "SGPT / ALT", "unit": "U/L", "ref": "5 - 45"},
    "AST / ALT Ratio": {
        "name": "AST / ALT Ratio (De Ritis)",
        "unit": "Ratio",
        "ref": "0.8 - 1.5",
    },
    "Alkaline Phosphatase (ALP)": {
        "name": "Alkaline Phosphatase (ALP)",
        "unit": "U/L",
        "ref": "80 - 306",
    },
    "Total Protein": {
        "name": "Serum Total Protein",
        "unit": "g/dL",
        "ref": "6.4 - 8.3",
    },
    "Serum Albumin": {"name": "Serum Albumin", "unit": "g/dL", "ref": "3.5 - 5.2"},
    "Serum Globulin": {
        "name": "Serum Globulin",
        "unit": "g/dL",
        "ref": "2.0 - 3.5",
    },
    "A:G Ratio": {"name": "A : G Ratio", "unit": "Ratio", "ref": "1.2 - 2.2"},
    # KFT
    "Blood Urea": {"name": "Blood Urea", "unit": "mg/dL", "ref": "15 - 45"},
    "Serum Creatinine": {
        "name": "Serum Creatinine",
        "unit": "mg/dL",
        "ref": "0.6 - 1.4",
    },
    "Blood Urea Nitrogen (BUN)": {
        "name": "Blood Urea Nitrogen (BUN)",
        "unit": "mg/dL",
        "ref": "7 - 20",
    },
    "Urea / Creatinine Ratio": {
        "name": "Urea / Creatinine Ratio",
        "unit": "Ratio",
        "ref": "20 - 35",
    },
    "Serum Uric Acid": {
        "name": "Serum Uric Acid",
        "unit": "mg/dL",
        "ref": "3.5 - 7.2",
    },
    "Serum Calcium": {"name": "Serum Calcium", "unit": "mg/dL", "ref": "8.5 - 10.5"},
    "Serum Sodium (Na+)": {
        "name": "Serum Sodium (Na+)",
        "unit": "mEq/L",
        "ref": "135 - 145",
    },
    "Serum Potassium (K+)": {
        "name": "Serum Potassium (K+)",
        "unit": "mEq/L",
        "ref": "3.5 - 5.0",
    },
    # Lipid
    "Total Cholesterol": {
        "name": "Total Cholesterol",
        "unit": "mg/dL",
        "ref": "< 200 (Desirable)",
    },
    "Triglycerides": {
        "name": "Serum Triglycerides",
        "unit": "mg/dL",
        "ref": "< 150 (Normal)",
    },
    "HDL Cholesterol": {
        "name": "HDL Cholesterol (Good)",
        "unit": "mg/dL",
        "ref": "> 40 (Optimal)",
    },
    "LDL Cholesterol": {
        "name": "LDL Cholesterol (Bad)",
        "unit": "mg/dL",
        "ref": "< 100 (Optimal)",
    },
    "VLDL Cholesterol": {
        "name": "VLDL Cholesterol",
        "unit": "mg/dL",
        "ref": "5 - 30",
    },
    "Non-HDL Cholesterol": {
        "name": "Non-HDL Cholesterol",
        "unit": "mg/dL",
        "ref": "< 130",
    },
    "TC / HDL Ratio": {"name": "TC / HDL Ratio", "unit": "Ratio", "ref": "3.0 - 5.0"},
    "LDL / HDL Ratio": {
        "name": "LDL / HDL Ratio",
        "unit": "Ratio",
        "ref": "1.5 - 3.5",
    },
    # Glucose
    "Blood Glucose (Fasting)": {
        "name": "Blood Glucose (Fasting)",
        "unit": "mg/dL",
        "ref": "70 - 100",
    },
    "Blood Glucose (PP)": {
        "name": "Blood Glucose (Post Prandial)",
        "unit": "mg/dL",
        "ref": "70 - 140",
    },
    "Blood Glucose (Random)": {
        "name": "Blood Glucose (Random)",
        "unit": "mg/dL",
        "ref": "70 - 140",
    },
}


def lookup_any_ref(key):
  clean = key.strip().lower()
  if clean in MASTER_REFS:
    return MASTER_REFS[clean]
  for k, v in MASTER_REFS.items():
    if k.lower() == clean:
      return v
  return {"name": key, "unit": "-", "ref": "Clinical Correlation"}


# ----------------------------------------------------
# ReportLab Safe Multi-Page Engine
# ----------------------------------------------------
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
    self.c.drawString(
        32,
        self.height - 48,
        "ADVANCED PATHOLOGY & CLINICAL LABORATORY | ACCREDITED DIAGNOSTIC"
        " SERVICES",
    )
    self.c.drawRightString(
        self.width - 32, self.height - 35, f"Helpdesk: +91 {p_contact}"
    )

    self.c.setFillColor(colors.HexColor("#f8fafc"))
    self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
    self.c.roundRect(
        32, self.height - 116, self.width - 64, 48, 3, fill=True, stroke=True
    )

    self.c.setFillColor(colors.HexColor("#475569"))
    self.c.setFont("Helvetica-Bold", 7.5)
    self.c.drawString(42, self.height - 80, "Patient Name:")
    self.c.drawString(42, self.height - 93, "Age / Sex:")
    self.c.drawString(42, self.height - 106, "Referred By:")

    self.c.setFont("Helvetica", 7.5)
    self.c.drawString(108, self.height - 80, f"Mr./Ms. {p_name or '---'}")
    self.c.drawString(108, self.height - 93, f"{p_age or '--'} Yrs / {p_sex}")
    self.c.drawString(108, self.height - 106, f"Dr. {p_doctor or 'Self'}")

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
    if not items_dict:
      return
    needed_height = 28 + (len(items_dict) * 11)
    if self.current_y - needed_height < 65:
      self.draw_footer()
      self.c.showPage()
      self.draw_header()
      self.current_y = self.height - 128

    self.c.setFillColor(colors.HexColor(bar_color))
    self.c.rect(
        32, self.current_y - 12, self.width - 64, 12, fill=True, stroke=False
    )
    self.c.setFillColor(colors.white)
    self.c.setFont("Helvetica-Bold", 7)
    self.c.drawString(38, self.current_y - 9, title)

    self.c.setFillColor(colors.HexColor("#e2e8f0"))
    self.c.rect(
        32, self.current_y - 25, self.width - 64, 12, fill=True, stroke=False
    )
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
    self.c.rect(
        32, self.current_y - 10, self.width - 64, 11, fill=True, stroke=False
    )
    self.c.setFillColor(colors.white)
    self.c.setFont("Helvetica-Bold", 7)
    self.c.drawString(
        38, self.current_y - 7, "GENERAL BLOOD PICTURE (PERIPHERAL SMEAR FINDINGS)"
    )

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


st.markdown("---")
# Download PDF Action
if st.button("🖨️ Generate Comprehensive Pathology Report (PDF)"):
  valid_cbc = {k: v for k, v in cbc_inputs.items() if str(v).strip()}
  has_data = (
      valid_cbc or lft_inputs or kft_inputs or lipid_inputs or serology_inputs
  )

  if not has_data:
    st.error(
        "Kripya kam se kam ek test profile select karke uske parameters bharein!"
    )
  else:
    buf = io.BytesIO()
    doc = PathologyReportDoc(buf)

    # 1. CBC
    if "Complete Blood Count (CBC + GBP)" in selected_profiles and valid_cbc:
      doc.add_section(
          "COMPLETE BLOOD COUNT (AUTOMATED HEMATOLOGY)", valid_cbc, "#0f766e"
      )
      doc.add_gbp(gbp_rbc, gbp_wbc, gbp_plt, gbp_imp)

    # 2. LFT
    if "Liver Function Test (LFT)" in selected_profiles and lft_inputs:
      doc.add_section(
          "CLINICAL BIOCHEMISTRY - LIVER FUNCTION TEST (LFT)",
          lft_inputs,
          "#854d0e",
      )

    # 3. KFT
    if "Kidney Function Test (KFT / RFT)" in selected_profiles and kft_inputs:
      doc.add_section(
          "CLINICAL BIOCHEMISTRY - KIDNEY FUNCTION TEST (KFT)",
          kft_inputs,
          "#7c2d12",
      )

    # 4. Lipid Profile
    if "Lipid Profile" in selected_profiles and lipid_inputs:
      doc.add_section(
          "CLINICAL BIOCHEMISTRY - LIPID PROFILE", lipid_inputs, "#be123c"
      )

    # 5. Serology / Rapid
    if serology_inputs:
      doc.add_section(
          "SEROLOGY & CLINICAL IMMUNOLOGY", serology_inputs, "#4338ca"
      )

    doc.finish()
    buf.seek(0)

    st.download_button(
        label="📥 Download Complete Pathology PDF",
        data=buf,
        file_name=(
            f"{p_name.replace(' ', '_') or 'Patient'}_Pathology_Report.pdf"
        ),
        mime="application/pdf",
    )
