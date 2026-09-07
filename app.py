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

st.set_page_config(page_title="The Sen Labs - Diagnostic Reporting", layout="wide")
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
    sample_id = st.text_input("Sample ID / Lab No.", value=f"TSL-{datetime.now().strftime('%y%m%d%H%M')}")

# 2. Multi-Test Profile Selector
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
        "Blood Glucose"
    ],
    default=[]
)

# 3. Layout Preference
st.subheader("3. PDF Layout Preference")
layout_choice = st.radio(
    "Report Formatting Mode:",
    ("📄 Har Test Profile Alag Page Par (CBC+GBP Page 1 par ek sath, baki sab alag pages par)", 
     "📑 Ek Sath Compact Flow (Sabhi Test Continuous Flow Mein)"),
    index=0,
    horizontal=True
)
separate_pages = "Har Test Profile Alag Page Par" in layout_choice

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

# ----------------- SECTION 1: CBC + GBP (WITH AUTO ABSOLUTE COUNTS) -----------------
if "Complete Blood Count (CBC + GBP)" in selected_profiles:
    st.markdown("---")
    st.subheader("🩸 Complete Blood Count (CBC) with Auto Absolute Calculations")
    
    cbc_source = st.radio("Choose Photo Source for CBC Analyzer:", ("📁 Upload Image / Slip", "📸 Live Camera"), horizontal=True)
    cbc_img = st.file_uploader("Upload machine screen or slip", type=["jpg", "jpeg", "png"], key="cbc_file") if cbc_source == "📁 Upload Image / Slip" else st.camera_input("Capture machine display", key="cbc_live")
    
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
                                contents=[types.Part.from_bytes(data=optimized, mime_type="image/jpeg"), prompt]
                            )
                            cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.text.strip(), flags=re.M).strip()
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
        hgb = st.text_input("Hemoglobin (Hb)", value=str(c_raw.get("HGB", c_raw.get("Hemoglobin", ""))))
        rbc = st.text_input("Total RBC Count", value=str(c_raw.get("RBC", "")))
        hct = st.text_input("Hematocrit (PCV)", value=str(c_raw.get("HCT", c_raw.get("PCV", ""))))
        
        # RBC Indices Formulas: MCV=(HCT*10)/RBC, MCH=(Hb*10)/RBC, MCHC=(Hb*100)/HCT
        hgb_f, rbc_f, hct_f = safe_float(hgb), safe_float(rbc), safe_float(hct)
        calc_mcv = str(c_raw.get("MCV", ""))
        calc_mch = str(c_raw.get("MCH", ""))
        calc_mchc = str(c_raw.get("MCHC", ""))
        if not calc_mcv and hct_f and rbc_f and rbc_f > 0: calc_mcv = f"{(hct_f * 10) / rbc_f:.1f}"
        if not calc_mch and hgb_f and rbc_f and rbc_f > 0: calc_mch = f"{(hgb_f * 10) / rbc_f:.1f}"
        if not calc_mchc and hgb_f and hct_f and hct_f > 0: calc_mchc = f"{(hgb_f * 100) / hct_f:.1f}"
        
        mcv = st.text_input("MCV", value=calc_mcv)
        mch = st.text_input("MCH", value=calc_mch)
        mchc = st.text_input("MCHC", value=calc_mchc)

    with cbc_cols[1]:
        wbc = st.text_input("Total WBC / TLC", value=str(c_raw.get("WBC", c_raw.get("TLC", ""))))
        gran_p = st.text_input("Neutrophils / Gran (%)", value=str(c_raw.get("GRAN_PERCENT", "")))
        lym_p = st.text_input("Lymphocytes (%)", value=str(c_raw.get("LYM_PERCENT", "")))
        mid_p = st.text_input("Monocytes / Mid (%)", value=str(c_raw.get("MID_PERCENT", "")))

        # ABSOLUTE COUNT CALCULATION FORMULAS: (TLC * Percentage) / 100
        wbc_f = safe_float(wbc)
        gran_p_f = safe_float(gran_p)
        lym_p_f = safe_float(lym_p)
        mid_p_f = safe_float(mid_p)

        # Machine OCR check or Auto Math Calculation
        calc_gran_abs = str(c_raw.get("GRAN_ABSOLUTE", c_raw.get("GRAN", "")))
        if not calc_gran_abs and wbc_f and gran_p_f is not None:
            calc_gran_abs = f"{(wbc_f * gran_p_f) / 100.0:.2f}"

        calc_lym_abs = str(c_raw.get("LYM_ABSOLUTE", c_raw.get("LYM", "")))
        if not calc_lym_abs and wbc_f and lym_p_f is not None:
            calc_lym_abs = f"{(wbc_f * lym_p_f) / 100.0:.2f}"

        calc_mid_abs = str(c_raw.get("MID_ABSOLUTE", c_raw.get("MID", "")))
        if not calc_mid_abs and wbc_f and mid_p_f is not None:
            calc_mid_abs = f"{(wbc_f * mid_p_f) / 100.0:.2f}"

    with cbc_cols[2]:
        gran_abs = st.text_input("Absolute Neutrophil Count (#)", value=calc_gran_abs)
        lym_abs = st.text_input("Absolute Lymphocyte Count (#)", value=calc_lym_abs)
        mid_abs = st.text_input("Absolute Monocyte/Mid Count (#)", value=calc_mid_abs)
        st.info("✨ Absolute Counts calculated automatically using (WBC x %) / 100")

    with cbc_cols[3]:
        plt = st.text_input("Platelet Count (PLT)", value=str(c_raw.get("PLT", c_raw.get("Platelets", ""))))
        mpv = st.text_input("MPV", value=str(c_raw.get("MPV", "")))
        pdw = st.text_input("PDW", value=str(c_raw.get("PDW", "")))
        pct = st.text_input("Plateletcrit (PCT)", value=str(c_raw.get("PCT", "")))
        lpcr = st.text_input("P-LCR", value=str(c_raw.get("LPCR", "")))
        rdwa = st.text_input("RDW - SD (RDWa)", value=str(c_raw.get("RDWA", "")))
        rdw_cv = st.text_input("RDW - CV (%)", value=str(c_raw.get("RDW_PERCENT", "")))

    st.markdown("##### 🔬 GBP / Peripheral Smear Findings")
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        gbp_rbc = st.text_input("RBC Morphology", value="Normocytic normochromic red cells with normal central pallor.")
        gbp_wbc = st.text_input("WBC Morphology", value="Mature neutrophils & lymphocytes seen. No atypical or blast cells.")
    with g_col2:
        gbp_plt = st.text_input("Platelets on Smear", value="Adequate on smear, seen singly and in small aggregates.")
        gbp_imp = st.text_input("Diagnostic Impression", value="Complete hemogram within biological reference intervals.")

    final_report_sections["CBC"] = {
        "items": {
            "Hemoglobin (Hb)": (hgb, "SLS Method", "g/dL", "13.0 - 17.0", 13.0, 17.0),
            "Total RBC Count": (rbc, "Electrical Impedance", "10^6/uL", "4.50 - 5.50", 4.50, 5.50),
            "Packed Cell Volume (PCV)": (hct, "Calculated", "%", "40.0 - 50.0", 40.0, 50.0),
            "Mean Corpuscular Volume (MCV)": (mcv, "Calculated", "fL", "80.0 - 100.0", 80.0, 100.0),
            "Mean Corpuscular Hb (MCH)": (mch, "Calculated", "pg", "27.0 - 32.0", 27.0, 32.0),
            "Mean Corpuscular Hb Conc (MCHC)": (mchc, "Calculated", "g/dL", "31.5 - 35.5", 31.5, 35.5),
            "RDW - SD (RDWa)": (rdwa, "Volume Histogram", "fL", "39.0 - 46.0", 39.0, 46.0),
            "RDW - CV": (rdw_cv, "Calculated", "%", "11.5 - 14.5", 11.5, 14.5),
            "Total Leukocyte Count (TLC)": (wbc, "Electrical Impedance", "10^3/uL", "4.0 - 10.0", 4.0, 10.0),
            "Granulocytes / Neutrophils (%)": (gran_p, "Impedance / Flow", "%", "40.0 - 70.0", 40.0, 70.0),
            "Absolute Neutrophil Count (#)": (gran_abs, "Calculated (TLC x %)", "10^3/uL", "2.00 - 7.00", 2.00, 7.00),
            "Lymphocytes (%)": (lym_p, "Impedance / Flow", "%", "20.0 - 40.0", 20.0, 40.0),
            "Absolute Lymphocyte Count (#)": (lym_abs, "Calculated (TLC x %)", "10^3/uL", "1.00 - 3.00", 1.00, 3.00),
            "Mid Cells / Monocytes (%)": (mid_p, "Impedance / Flow", "%", "2.0 - 8.0", 2.0, 8.0),
            "Absolute Monocyte / Mid Count (#)": (mid_abs, "Calculated (TLC x %)", "10^3/uL", "0.10 - 0.80", 0.10, 0.80),
            "Platelet Count (PLT)": (plt, "Electrical Impedance", "10^3/uL", "150 - 450", 150.0, 450.0),
            "Mean Platelet Volume (MPV)": (mpv, "Calculated", "fL", "7.5 - 11.5", 7.5, 11.5),
            "Platelet Distribution Width (PDW)": (pdw, "Calculated", "%", "9.0 - 17.0", 9.0, 17.0),
            "Plateletcrit (PCT)": (pct, "Calculated", "%", "0.10 - 0.50", 0.10, 0.50),
            "Platelet Large Cell Ratio (P-LCR)": (lpcr, "Calculated", "%", "15.0 - 35.0", 15.0, 35.0)
        },
        "gbp": {"rbc": gbp_rbc, "wbc": gbp_wbc, "plt": gbp_plt, "imp": gbp_imp}
    }

# ----------------- SECTION 2: LFT -----------------
if "Liver Function Test (LFT)" in selected_profiles:
    st.markdown("---")
    st.subheader("🧪 Liver Function Test (LFT) - Self Calculating")
    l_c1, l_c2, l_c3 = st.columns(3)
    with l_c1:
        b_tot = st.text_input("Bilirubin Total (mg/dL)", value="")
        b_dir = st.text_input("Bilirubin Direct (mg/dL)", value="")
        bt_f, bd_f = safe_float(b_tot), safe_float(b_dir)
        b_ind = f"{max(0.0, bt_f - bd_f):.2f}" if (bt_f is not None and bd_f is not None) else ""
        st.info(f"✨ Auto Indirect Bilirubin: {b_ind or '--'} mg/dL")
    with l_c2:
        sgot = st.text_input("SGOT / AST (U/L)", value="")
        sgpt = st.text_input("SGPT / ALT (U/L)", value="")
        alp = st.text_input("Alkaline Phosphatase (ALP) (U/L)", value="")
        sgot_f, sgpt_f = safe_float(sgot), safe_float(sgpt)
        de_ritis = f"{(sgot_f / sgpt_f):.2f}" if (sgot_f and sgpt_f and sgpt_f > 0) else ""
    with l_c3:
        t_prot = st.text_input("Total Protein (g/dL)", value="")
        alb = st.text_input("Serum Albumin (g/dL)", value="")
        tp_f, alb_f = safe_float(t_prot), safe_float(alb)
        glob = f"{max(0.0, tp_f - alb_f):.2f}" if (tp_f is not None and alb_f is not None) else ""
        glob_f = safe_float(glob)
        ag_ratio = f"{(alb_f / glob_f):.2f}" if (alb_f and glob_f and glob_f > 0) else ""
        st.info(f"✨ Auto Globulin: {glob or '--'} | A:G Ratio: {ag_ratio or '--'}")

    final_report_sections["LFT"] = {
        "Serum Bilirubin Total": (b_tot, "Diazo Method", "mg/dL", "0.2 - 1.2", 0.2, 1.2),
        "Serum Bilirubin Direct": (b_dir, "Diazo Coupling", "mg/dL", "0.0 - 0.3", 0.0, 0.3),
        "Serum Bilirubin Indirect": (b_ind, "Calculated", "mg/dL", "0.2 - 0.9", 0.2, 0.9),
        "SGOT / AST": (sgot, "IFCC Kinetic", "U/L", "5 - 40", 5.0, 40.0),
        "SGPT / ALT": (sgpt, "IFCC Kinetic", "U/L", "5 - 45", 5.0, 45.0),
        "AST : ALT (De Ritis) Ratio": (de_ritis, "Calculated", "Ratio", "0.8 - 1.5", 0.8, 1.5),
        "Alkaline Phosphatase (ALP)": (alp, "p-NPP Kinetic", "U/L", "80 - 306", 80.0, 306.0),
        "Serum Total Protein": (t_prot, "Biuret Method", "g/dL", "6.4 - 8.3", 6.4, 8.3),
        "Serum Albumin": (alb, "Bromocresol Green", "g/dL", "3.5 - 5.2", 3.5, 5.2),
        "Serum Globulin": (glob, "Calculated", "g/dL", "2.0 - 3.5", 2.0, 3.5),
        "A : G Ratio": (ag_ratio, "Calculated", "Ratio", "1.2 - 2.2", 1.2, 2.2)
    }

# ----------------- SECTION 3: KFT -----------------
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
        "Blood Urea": (urea, "GLDH Urease Kinetic", "mg/dL", "15.0 - 45.0", 15.0, 45.0),
        "Serum Creatinine": (creat, "Modified Jaffe's", "mg/dL", "0.6 - 1.4", 0.6, 1.4),
        "Blood Urea Nitrogen (BUN)": (bun, "Calculated", "mg/dL", "7.0 - 20.0", 7.0, 20.0),
        "Urea / Creatinine Ratio": (u_cr_ratio, "Calculated", "Ratio", "20.0 - 35.0", 20.0, 35.0),
        "Serum Uric Acid": (uric, "Uricase / POD", "mg/dL", "3.5 - 7.2", 3.5, 7.2),
        "Serum Calcium": (calcium, "Arsenazo III", "mg/dL", "8.5 - 10.5", 8.5, 10.5),
        "Serum Sodium (Na+)": (sod, "ISE Direct", "mEq/L", "135 - 145", 135.0, 145.0),
        "Serum Potassium (K+)": (pot, "ISE Direct", "mEq/L", "3.5 - 5.0", 3.5, 5.0),
        "Serum Chloride (Cl-)": (chlor, "ISE Direct", "mEq/L", "96 - 106", 96.0, 106.0)
    }

# ----------------- SECTION 4: LIPID PROFILE -----------------
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
        ldl = f"{(ch_f - hd_f - vldl_f):.1f}" if (ch_f and hd_f and vldl_f) else ""
        tc_hdl = f"{(ch_f / hd_f):.2f}" if (ch_f and hd_f and hd_f > 0) else ""
        non_hdl = f"{(ch_f - hd_f):.1f}" if (ch_f and hd_f) else ""
        st.info(f"✨ Auto VLDL: {vldl or '--'} | Auto LDL: {ldl or '--'} | TC/HDL Ratio: {tc_hdl or '--'}")

    final_report_sections["LIPID"] = {
        "Total Cholesterol": (chol, "CHOD - PAP", "mg/dL", "< 200 (Desirable)", 0.0, 200.0),
        "Serum Triglycerides": (trig, "GPO - PAP", "mg/dL", "< 150 (Normal)", 0.0, 150.0),
        "HDL Cholesterol (Good)": (hdl, "Direct Clearance", "mg/dL", "> 40 (Optimal)", 40.0, 999.0),
        "LDL Cholesterol (Bad)": (ldl, "Friedewald Formula", "mg/dL", "< 100 (Optimal)", 0.0, 100.0),
        "VLDL Cholesterol": (vldl, "Calculated", "mg/dL", "5.0 - 30.0", 5.0, 30.0),
        "Non-HDL Cholesterol": (non_hdl, "Calculated", "mg/dL", "< 130", 0.0, 130.0),
        "Total Chol / HDL Ratio": (tc_hdl, "Calculated", "Ratio", "3.0 - 5.0", 3.0, 5.0)
    }

# ----------------- SEPARATE INDEPENDENT RAPID & SEROLOGY SECTIONS -----------------
if "Widal Agglutination Test" in selected_profiles:
    st.markdown("---")
    st.subheader("🌡️ Widal Agglutination Slide / Tube Test")
    w1, w2, w3, w4 = st.columns(4)
    with w1: wo = st.selectbox("S. typhi 'O'", ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"], key="w_o")
    with w2: wh = st.selectbox("S. typhi 'H'", ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320"], key="w_h")
    with w3: wah = st.selectbox("S. paratyphi 'AH'", ["Negative", "1:20", "1:40", "1:80"], key="w_ah")
    with w4: wbh = st.selectbox("S. paratyphi 'BH'", ["Negative", "1:20", "1:40", "1:80"], key="w_bh")
    final_report_sections["WIDAL"] = {
        "Salmonella typhi 'O'": (wo, "Slide Agglutination", "Titer", "Significant >= 1:80", None, None),
        "Salmonella typhi 'H'": (wh, "Slide Agglutination", "Titer", "Significant >= 1:160", None, None),
        "Salmonella paratyphi 'AH'": (wah, "Slide Agglutination", "Titer", "Negative / Non-significant", None, None),
        "Salmonella paratyphi 'BH'": (wbh, "Slide Agglutination", "Titer", "Negative / Non-significant", None, None)
    }

if "Typhidot (IgM / IgG)" in selected_profiles:
    st.markdown("---")
    st.subheader("🧪 Typhidot Rapid Card Test")
    t1, t2 = st.columns(2)
    with t1: ty_m = st.selectbox("Typhidot IgM (Acute Phase)", ["Non-Reactive (Negative)", "Reactive (Positive)"], key="ty_m")
    with t2: ty_g = st.selectbox("Typhidot IgG (Convalescent/Carrier)", ["Non-Reactive (Negative)", "Reactive (Positive)"], key="ty_g")
    final_report_sections["TYPHIDOT"] = {
        "Typhidot IgM Antibody": (ty_m, "Immunochromatography", "Qualitative", "Non-Reactive", None, None),
        "Typhidot IgG Antibody": (ty_g, "Immunochromatography", "Qualitative", "Non-Reactive", None, None)
    }

if "Malaria Card & Smear (MP)" in selected_profiles:
    st.markdown("---")
    st.subheader("🦟 Malaria Diagnostic Profile")
    m1, m2, m3 = st.columns(3)
    with m1: mp_smear = st.selectbox("Peripheral Smear for MP", ["Not Seen", "P. vivax trophozoites seen", "P. falciparum ring forms seen"], key="mp_smear")
    with m2: mp_pv = st.selectbox("P. vivax Antigen (Rapid)", ["Negative", "Positive"], key="mp_pv")
    with m3: mp_pf = st.selectbox("P. falciparum Antigen (Rapid)", ["Negative", "Positive"], key="mp_pf")
    final_report_sections["MALARIA"] = {
        "Malarial Parasite (Smear)": (mp_smear, "Microscopy (Leishman)", "Smear", "No Parasites Seen", None, None),
        "P. vivax Antigen": (mp_pv, "Immunochromatography", "Card", "Negative", None, None),
        "P. falciparum Antigen": (mp_pf, "Immunochromatography", "Card", "Negative", None, None)
    }

if "Blood Glucose" in selected_profiles:
    st.markdown("---")
    st.subheader("🍬 Blood Glucose Profile")
    g1, g2, g3 = st.columns(3)
    with g1: glu_f = st.text_input("Fasting Blood Sugar (FBS)", value="", key="glu_f")
    with g2: glu_pp = st.text_input("Post Prandial Blood Sugar (PPBS)", value="", key="glu_pp")
    with g3: glu_r = st.text_input("Random Blood Sugar (RBS)", value="", key="glu_r")
    glu_dict = {}
    if glu_f: glu_dict["Blood Glucose (Fasting)"] = (glu_f, "GOD - POD Method", "mg/dL", "70.0 - 100.0", 70.0, 100.0)
    if glu_pp: glu_dict["Blood Glucose (PP)"] = (glu_pp, "GOD - POD Method", "mg/dL", "70.0 - 140.0", 70.0, 140.0)
    if glu_r: glu_dict["Blood Glucose (Random)"] = (glu_r, "GOD - POD Method", "mg/dL", "70.0 - 140.0", 70.0, 140.0)
    if glu_dict:
        final_report_sections["GLUCOSE"] = glu_dict

# ----------------- KNOWLEDGE BASE -----------------
KNOWLEDGE_BASE = {
    "CBC": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: HEMATOLOGY PROFILE",
        "significance": "Complete Blood Count (CBC) evaluates erythrocytes, leukocytes, and thrombocytes. Absolute counts provide the exact quantitative load of specific white cells in peripheral blood, offering superior clinical diagnostic accuracy over percentage values.",
        "elevated": "ELEVATED (HIGH): Absolute Neutrophilia (ANC > 7.0x10^3/uL) indicates acute bacterial infections, tissue necrosis, or severe physiological stress. Absolute Lymphocytosis (ALC > 3.0x10^3/uL) suggests viral infections (EBV, CMV), pertussis, or chronic lymphocytic leukemia (CLL).",
        "decreased": "DECREASED (LOW): Absolute Neutropenia (ANC < 2.0x10^3/uL; severe < 0.5x10^3/uL) significantly predisposes to opportunistic infections, often seen after chemotherapy, septic shock, or autoimmune disease. Absolute Lymphopenia (< 1.0x10^3/uL) is noted in viral sepsis, immunodeficiency, or corticosteroid therapy.",
        "guidance": "RECOMMENDED ACTION: In severe neutropenia (ANC < 1.0x10^3/uL), implement neutropenic precautions and evaluate bone marrow if persistent. In thrombocytopenia (<50x10^3/uL), screen for Dengue NS1/IgM and avoid intramuscular injections.",
        "notes": "NOTE: Automated counts must be correlated with microscopic smear examination (GBP)."
    },
    "LFT": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: LIVER FUNCTION PROFILE",
        "significance": "Liver Function Tests (LFT) assess hepatic excretory function (Bilirubin), synthetic capability (Albumin, Total Protein), and hepatocellular integrity (Transaminases: AST/ALT, ALP).",
        "elevated": "ELEVATED (HIGH): Hyperbilirubinemia occurs in hemolytic jaundice, acute hepatitis, and extrahepatic biliary obstruction. Markedly elevated SGOT & SGPT indicates acute viral or drug-induced liver injury.",
        "decreased": "DECREASED (LOW): Hypoalbuminemia (<3.5 g/dL) is characteristic of chronic cirrhosis, severe malnutrition, or nephrotic protein loss. Inverted A:G ratio (<1.0) correlates with hepatic parenchymal disease.",
        "guidance": "RECOMMENDED ACTION: For elevated transaminases, screen for Hepatitis B & C (HBsAg, Anti-HCV) and obtain USG Abdomen. Avoid alcohol and hepatotoxic medications.",
        "notes": "NOTE: Mild transient elevations can occur following strenuous exercise or heavy lipid meals."
    },
    "KFT": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: RENAL FUNCTION PROFILE",
        "significance": "Kidney Function Tests evaluate glomerular filtration efficiency, renal tubular reabsorption, and systemic fluid-electrolyte balance.",
        "elevated": "ELEVATED (HIGH): Elevated Urea and Creatinine indicate acute kidney injury (AKI) or chronic kidney disease (CKD). High BUN-to-Creatinine ratio (>20:1) suggests pre-renal azotemia or dehydration. Hyperkalemia (>5.0 mEq/L) pre-disposes to cardiac arrhythmias.",
        "decreased": "DECREASED (LOW): Hyponatremia (<135 mEq/L) causes neurological symptoms, seen in diuretic therapy or fluid overload. Hypokalemia (<3.5 mEq/L) leads to muscle weakness and cardiac arrhythmias.",
        "guidance": "RECOMMENDED ACTION: Ensure adequate hydration, check 24-hr urinary protein, and obtain USG KUB. For Hyperkalemia (>5.5 mEq/L), obtain an urgent 12-lead ECG and consult Nephrologist.",
        "notes": "NOTE: Serum Creatinine levels reflect muscle mass; correlate with clinical status."
    },
    "LIPID": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: LIPID PROFILE",
        "significance": "Lipid Profile assesses circulating atherogenic and protective lipoproteins to estimate 10-year risk of Atherosclerotic Cardiovascular Disease (ASCVD), CAD, and stroke.",
        "elevated": "ELEVATED (HIGH): Elevated LDL-C and Total Cholesterol accelerate coronary plaque formation. High Triglycerides (>150 mg/dL, especially >500 mg/dL) heighten risks of acute pancreatitis.",
        "decreased": "DECREASED (LOW): Low HDL-C (<40 mg/dL) represents an independent risk factor for premature coronary artery disease due to compromised reverse cholesterol transport.",
        "guidance": "RECOMMENDED ACTION: Adopt Therapeutic Lifestyle Changes (TLC) — reduce dietary saturated fats, 150 min/week moderate aerobic exercise. Consider statin therapy if indicated.",
        "notes": "NOTE: Requires strict 10-12 hours overnight fasting. Friedewald LDL valid only when TG < 400 mg/dL."
    },
    "WIDAL": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: WIDAL AGGLUTINATION PROFILE",
        "significance": "Widal test measures circulating agglutinating antibodies against Lipopolysaccharide O and Flagellar H antigens of Salmonella enterica serotypes Typhi and Paratyphi.",
        "elevated": "INTERPRETATION: Titers >= 1:80 for 'O' antigen and >= 1:160 for 'H' antigen are considered clinically significant for active Enteric (Typhoid) fever in endemic regions.",
        "decreased": "LIMITATIONS: Low baseline titers (1:20, 1:40) are common in healthy individuals in endemic zones. A negative test does not rule out typhoid if tested in early bacteremic stage.",
        "guidance": "RECOMMENDED ACTION: Blood culture is the gold standard diagnostic method during 1st week of fever. Initiate targeted antibiotic therapy as per clinician advice.",
        "notes": "NOTE: Previous TAB vaccination or past infection can cause anamnestic false-positive H titers."
    },
    "TYPHIDOT": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: TYPHIDOT (IgM / IgG) RAPID TEST",
        "significance": "Typhidot detects specific IgM and IgG antibodies against outer membrane protein (OMP) of Salmonella typhi, enabling differential identification of acute vs past/carrier infection.",
        "elevated": "INTERPRETATION: Positive IgM indicates early, acute typhoid infection (detectable from day 2-3 of fever). Positive IgG alone indicates past infection or carrier state.",
        "decreased": "LIMITATIONS: Non-reactive result in early fever does not completely rule out enteric fever; repeat testing advised after 48-72 hours if symptoms persist.",
        "guidance": "RECOMMENDED ACTION: Positive IgM indicates acute enteric fever. Correlate with CBC (leukopenia/neutropenia is common). Follow physician's antibiotic protocol.",
        "notes": "NOTE: Higher sensitivity and specificity than conventional slide Widal in early fever."
    },
    "MALARIA": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: MALARIA EXAMINATION PROFILE",
        "significance": "Combines high-resolution Romanowsky (Leishman/Giemsa) microscopy with qualitative immunochromatographic detection of histidine-rich protein II (HRP-2) and plasmodium lactate dehydrogenase (pLDH).",
        "elevated": "INTERPRETATION: Demonstration of trophozoites, schizonts, or gametocytes confirms active Malaria. Differentiation between Plasmodium vivax and Plasmodium falciparum is critical for treatment.",
        "decreased": "LIMITATIONS: Low parasitemia (<50 parasites/uL) may be missed on a single smear. Repeated thick & thin smear examination at 12-hour intervals during pyrexia spike is recommended.",
        "guidance": "RECOMMENDED ACTION: Immediate species-specific therapy: ACT for P. falciparum; Chloroquine + Primaquine for P. vivax. Monitor platelet count closely.",
        "notes": "NOTE: P. falciparum can progress rapidly to complicated/cerebral malaria; treat urgently."
    },
    "GLUCOSE": {
        "title": "CLINICAL SIGNIFICANCE & INTERPRETATION: BLOOD GLUCOSE PROFILE",
        "significance": "Evaluates carbohydrate metabolism and pancreatic endocrine function. Diagnoses impaired glucose tolerance, Type 1 & 2 Diabetes Mellitus, and hypoglycemia.",
        "elevated": "INTERPRETATION: Fasting Blood Sugar >= 126 mg/dL or Post Prandial / Random >= 200 mg/dL on repeated testing meets diagnostic criteria for Diabetes Mellitus.",
        "decreased": "HYPOGLYCEMIA: Values < 70 mg/dL indicate hypoglycemia, which requires immediate corrective glucose intake to avoid neuroglycopenic symptoms.",
        "guidance": "RECOMMENDED ACTION: Obtain Glycated Hemoglobin (HbA1c) to evaluate 3-month average glycemic control. Advise dietary modifications and lifestyle intervention.",
        "notes": "NOTE: Fasting requires 8-10 hours without caloric intake. PPBS requires sample collection exactly 2 hours after meal."
    }
}

# ----------------- SAFE MULTI-PAGE REPORT MANAGER CLASS -----------------
class PDFReportManager:
    def __init__(self, buffer, p_dict, separate_pages_mode=True):
        self.c = canvas.Canvas(buffer, pagesize=letter)
        self.width, self.height = letter
        self.p = p_dict
        self.separate_pages_mode = separate_pages_mode
        self.curr_y = self.height - 134
        self.page_number = 1
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
        self.c.drawString(32, self.height - 46, "ADVANCED PATHOLOGY & CLINICAL BIOCHEMISTRY | AUTOMATED DIAGNOSTICS")
        self.c.drawRightString(self.width - 32, self.height - 34, f"Helpdesk: +91 {self.p['contact']}")
        
        self.c.setFillColor(colors.HexColor("#f8fafc"))
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.roundRect(32, self.height - 122, self.width - 64, 56, 3, fill=True, stroke=True)
        
        self.c.setFillColor(colors.HexColor("#475569"))
        self.c.setFont("Helvetica-Bold", 7.5)
        self.c.drawString(42, self.height - 80, "Patient Name:")
        self.c.drawString(42, self.height - 94, "Age / Sex:")
        self.c.drawString(42, self.height - 108, "Referred By:")
        
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(108, self.height - 80, f"Mr./Ms. {self.p['name']}")
        self.c.drawString(108, self.height - 94, f"{self.p['age']} Yrs / {self.p['sex']}")
        self.c.drawString(108, self.height - 108, f"Dr. {self.p['doctor']}")
        
        self.c.setFont("Helvetica-Bold", 7.5)
        self.c.drawString(310, self.height - 80, "Sample ID:")
        self.c.drawString(310, self.height - 94, "Collection Time:")
        self.c.drawString(310, self.height - 108, "Reporting Date & Time:")
        
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(405, self.height - 80, self.p['sample_id'])
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
        self.c.drawRightString(self.width / 2 + 15, 32, f"Page {self.page_number}")

    def new_page(self):
        self.draw_footer()
        self.c.showPage()
        self.page_number += 1
        self.draw_header()
        self.curr_y = self.height - 134

    def print_wrapped_text(self, prefix, text, start_y, max_width=530):
        self.c.setFont("Helvetica-Bold", 6.2)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.drawString(42, start_y, prefix)
        
        p_w = self.c.stringWidth(prefix, "Helvetica-Bold", 6.2) + 4
        self.c.setFont("Helvetica", 6.0)
        self.c.setFillColor(colors.HexColor("#334155"))
        
        words = text.split(" ")
        line = ""
        y = start_y
        first_line = True
        
        for word in words:
            test_line = line + (" " if line else "") + word
            limit = (max_width - p_w) if first_line else max_width
            if self.c.stringWidth(test_line, "Helvetica", 6.0) < limit:
                line = test_line
            else:
                self.c.drawString(42 + (p_w if first_line else 0), y, line)
                y -= 8.0
                line = word
                first_line = False
        if line:
            self.c.drawString(42 + (p_w if first_line else 0), y, line)
            y -= 8.0
            
        return y

    def print_knowledge_box(self, section_key):
        if section_key not in KNOWLEDGE_BASE:
            return
            
        kb = KNOWLEDGE_BASE[section_key]
        box_top = self.curr_y - 4
        box_height = box_top - 64
        if box_height < 45:
            return

        self.c.setFillColor(colors.HexColor("#f8fafc"))
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.roundRect(32, 64, self.width - 64, box_height, 3, fill=True, stroke=True)

        self.c.setFillColor(colors.HexColor("#e2e8f0"))
        self.c.rect(32, box_top - 11, self.width - 64, 11, fill=True, stroke=False)
        self.c.setFillColor(colors.HexColor("#1e3a8a"))
        self.c.setFont("Helvetica-Bold", 6.5)
        self.c.drawString(40, box_top - 8.5, kb["title"])

        y = box_top - 18
        y = self.print_wrapped_text("Clinical Significance: ", kb["significance"], y)
        y -= 1.0
        
        if y > 110:
            y = self.print_wrapped_text("High Findings (Elevated): ", kb["elevated"], y)
            y -= 1.0
            
        if y > 95:
            y = self.print_wrapped_text("Low Findings (Decreased): ", kb["decreased"], y)
            y -= 1.0
            
        if y > 80:
            y = self.print_wrapped_text("Recommended Action: ", kb["guidance"], y)
            y -= 1.0
            
        if y > 70:
            self.c.setFont("Helvetica-Oblique", 5.6)
            self.c.setFillColor(colors.HexColor("#64748b"))
            self.c.drawString(42, y, kb["notes"][:140])

        self.curr_y = 62

    # CBC + GBP TOGETHER ON PAGE 1
    def print_cbc_and_gbp_together(self, cbc_items, gbp_data):
        active_rows = {k: v for k, v in cbc_items.items() if str(v[0]).strip() != ""}
        
        # Dept Banner
        self.c.setFillColor(colors.HexColor("#0f766e"))
        self.c.rect(32, self.curr_y - 12, self.width - 64, 12, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(38, self.curr_y - 9, "COMPLETE BLOOD COUNT (AUTOMATED HEMATOLOGY WITH ABSOLUTE INDICES)")

        # Table Header
        self.c.setFillColor(colors.HexColor("#e2e8f0"))
        self.c.rect(32, self.curr_y - 23, self.width - 64, 11, fill=True, stroke=False)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.setFont("Helvetica-Bold", 6.4)
        self.c.drawString(38, self.curr_y - 20, "TEST / INVESTIGATION")
        self.c.drawString(195, self.curr_y - 20, "TEST METHOD")
        self.c.drawString(315, self.curr_y - 20, "RESULT")
        self.c.drawString(410, self.curr_y - 20, "UNIT")
        self.c.drawString(455, self.curr_y - 20, "REFERENCE INTERVAL")

        y = self.curr_y - 32
        # Calibrated 9.4pt row height so all 20 parameters fit cleanly in top half
        for param, (val, method, unit, ref, low_val, high_val) in active_rows.items():
            val_str = str(val).strip()
            v_num = safe_float(val_str)
            is_abnormal = False
            flag_suffix = ""

            if v_num is not None:
                if low_val is not None and v_num < low_val:
                    is_abnormal = True
                    flag_suffix = " (L) ▼"
                elif high_val is not None and v_num > high_val:
                    is_abnormal = True
                    flag_suffix = " (H) ▲"

            self.c.setFont("Helvetica", 6.2)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(38, y, str(param)[:34])
            
            self.c.setFont("Helvetica-Oblique", 5.6)
            self.c.setFillColor(colors.HexColor("#64748b"))
            self.c.drawString(195, y, str(method)[:24])

            if is_abnormal:
                self.c.setFont("Helvetica-Bold", 6.4)
                self.c.setFillColor(colors.HexColor("#b91c1c"))
                self.c.drawString(315, y, f"{val_str[:20]}{flag_suffix}")
            else:
                self.c.setFont("Helvetica", 6.2)
                self.c.setFillColor(colors.HexColor("#0f172a"))
                self.c.drawString(315, y, str(val_str)[:20])

            self.c.setFont("Helvetica", 6.2)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(410, y, str(unit)[:8])
            self.c.drawString(455, y, str(ref)[:25])

            self.c.setStrokeColor(colors.HexColor("#f1f5f9"))
            self.c.line(32, y - 1.5, self.width - 32, y - 1.5)
            y -= 9.4

        # GBP Section on SAME PAGE directly under CBC table
        gbp_top = y - 3
        self.c.setFillColor(colors.HexColor("#1e3a8a"))
        self.c.rect(32, gbp_top, self.width - 64, 10, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 6.5)
        self.c.drawString(38, gbp_top + 2.5, "GENERAL BLOOD PICTURE (PERIPHERAL BLOOD SMEAR EXAMINATION)")

        box_top = gbp_top - 1
        self.c.setFillColor(colors.HexColor("#f8fafc"))
        self.c.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.c.rect(32, box_top - 36, self.width - 64, 36, fill=True, stroke=True)

        gy = box_top - 7.5
        for label, txt in [("RBC Morphology", gbp_data["rbc"]), ("WBC Morphology", gbp_data["wbc"]), ("Platelets on Smear", gbp_data["plt"]), ("Smear Impression", gbp_data["imp"])]:
            self.c.setFont("Helvetica-Bold", 6.0)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(38, gy, f"{label}:")
            self.c.setFont("Helvetica", 6.0)
            self.c.setFillColor(colors.HexColor("#334155"))
            self.c.drawString(125, gy, txt[:105])
            gy -= 8.2
            
        self.curr_y = box_top - 41
        
        # Clinical Guidance Box filling bottom area on same page
        self.print_knowledge_box("CBC")

    def print_section(self, section_key, title, data_dict, bar_hex, is_first_on_page=False):
        active_rows = {k: v for k, v in data_dict.items() if str(v[0]).strip() != ""}
        if not active_rows:
            return

        if self.separate_pages_mode and not is_first_on_page:
            self.new_page()
        else:
            needed = 34 + (len(active_rows) * 11)
            if self.curr_y - needed < 65:
                self.new_page()

        # Department Banner
        self.c.setFillColor(colors.HexColor(bar_hex))
        self.c.rect(32, self.curr_y - 12, self.width - 64, 12, fill=True, stroke=False)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(38, self.curr_y - 9, title)

        # Table Header
        self.c.setFillColor(colors.HexColor("#e2e8f0"))
        self.c.rect(32, self.curr_y - 25, self.width - 64, 12, fill=True, stroke=False)
        self.c.setFillColor(colors.HexColor("#0f172a"))
        self.c.setFont("Helvetica-Bold", 6.5)
        self.c.drawString(38, self.curr_y - 22, "TEST / INVESTIGATION")
        self.c.drawString(195, self.curr_y - 22, "TEST METHOD")
        self.c.drawString(315, self.curr_y - 22, "RESULT")
        self.c.drawString(410, self.curr_y - 22, "UNIT")
        self.c.drawString(455, self.curr_y - 22, "REFERENCE INTERVAL")

        y = self.curr_y - 36
        for param, (val, method, unit, ref, low_val, high_val) in active_rows.items():
            val_str = str(val).strip()
            v_num = safe_float(val_str)
            is_abnormal = False
            flag_suffix = ""

            if v_num is not None:
                if low_val is not None and v_num < low_val:
                    is_abnormal = True
                    flag_suffix = " (L) ▼"
                elif high_val is not None and v_num > high_val:
                    is_abnormal = True
                    flag_suffix = " (H) ▲"
            elif any(x in val_str.lower() for x in ["positive", "reactive", "seen", "1:160", "1:320"]):
                is_abnormal = True
                flag_suffix = " *"

            self.c.setFont("Helvetica", 6.8)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(38, y, str(param)[:32])
            
            self.c.setFont("Helvetica-Oblique", 6.2)
            self.c.setFillColor(colors.HexColor("#64748b"))
            self.c.drawString(195, y, str(method)[:24])

            if is_abnormal:
                self.c.setFont("Helvetica-Bold", 6.8)
                self.c.setFillColor(colors.HexColor("#b91c1c"))
                self.c.drawString(315, y, f"{val_str[:22]}{flag_suffix}")
            else:
                self.c.setFont("Helvetica", 6.8)
                self.c.setFillColor(colors.HexColor("#0f172a"))
                self.c.drawString(315, y, str(val_str)[:24])

            self.c.setFont("Helvetica", 6.8)
            self.c.setFillColor(colors.HexColor("#0f172a"))
            self.c.drawString(410, y, str(unit)[:8])
            self.c.drawString(455, y, str(ref)[:25])

            self.c.setStrokeColor(colors.HexColor("#f1f5f9"))
            self.c.line(32, y - 2, self.width - 32, y - 2)
            y -= 10.8

        self.curr_y = y - 8

        if self.separate_pages_mode:
            self.print_knowledge_box(section_key)

    def finish(self):
        self.draw_footer()
        self.c.save()

# ----------------- REPORT ACTION -----------------
st.markdown("---")
if not selected_profiles:
    st.info("👆 Kripya Section 2 me se kam se kam ek test profile select karein.")
else:
    if st.button("🖨️ Generate Professional Pathology Report (PDF)"):
        buf = io.BytesIO()
        p_info = {
            "name": p_name or "Anonymous",
            "age": p_age or "--",
            "sex": p_sex,
            "doctor": p_doctor or "Self",
            "contact": p_contact or "9076816740",
            "sample_id": sample_id
        }
        
        doc = PDFReportManager(buf, p_info, separate_pages_mode=separate_pages)
        first_section = True
        
        # 1. CBC + GBP (ALWAYS TOGETHER ON PAGE 1)
        if "CBC" in final_report_sections:
            doc.print_cbc_and_gbp_together(final_report_sections["CBC"]["items"], final_report_sections["CBC"]["gbp"])
            first_section = False
            
        # 2. LFT
        if "LFT" in final_report_sections:
            doc.print_section("LFT", "CLINICAL BIOCHEMISTRY - LIVER FUNCTION TEST (LFT)", final_report_sections["LFT"], "#854d0e", is_first_on_page=first_section)
            first_section = False
            
        # 3. KFT
        if "KFT" in final_report_sections:
            doc.print_section("KFT", "CLINICAL BIOCHEMISTRY - KIDNEY FUNCTION TEST (KFT)", final_report_sections["KFT"], "#7c2d12", is_first_on_page=first_section)
            first_section = False
            
        # 4. Lipid
        if "LIPID" in final_report_sections:
            doc.print_section("LIPID", "CLINICAL BIOCHEMISTRY - LIPID PROFILE", final_report_sections["LIPID"], "#be123c", is_first_on_page=first_section)
            first_section = False

        # 5. Distinct Independent Serology Profiles (Widal, Typhidot, Malaria)
        if "WIDAL" in final_report_sections:
            doc.print_section("WIDAL", "SEROLOGY - WIDAL AGGLUTINATION PROFILE", final_report_sections["WIDAL"], "#4338ca", is_first_on_page=first_section)
            first_section = False

        if "TYPHIDOT" in final_report_sections:
            doc.print_section("TYPHIDOT", "RAPID SEROLOGY - TYPHIDOT (IgM / IgG) ANTIBODY PROFILE", final_report_sections["TYPHIDOT"], "#6b21a8", is_first_on_page=first_section)
            first_section = False

        if "MALARIA" in final_report_sections:
            doc.print_section("MALARIA", "PARASITOLOGY - MALARIA RAPID & MICROSCOPY PROFILE", final_report_sections["MALARIA"], "#0e7490", is_first_on_page=first_section)
            first_section = False

        if "GLUCOSE" in final_report_sections:
            doc.print_section("GLUCOSE", "BIOCHEMISTRY - BLOOD GLUCOSE MONITORING", final_report_sections["GLUCOSE"], "#1e3a8a", is_first_on_page=first_section)
            first_section = False
            
        doc.finish()
        buf.seek(0)
        
        st.download_button(
            label="📥 Download Clinical Diagnostic Report (PDF)",
            data=buf,
            file_name=f"{p_name or 'Patient'}_Pathology_Report.pdf",
            mime="application/pdf"
        )
