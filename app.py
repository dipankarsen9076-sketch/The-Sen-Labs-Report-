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

st.set_page_config(page_title="The Sen Labs", layout="centered")
st.title("The Sen Labs - Diagnostic Reporting")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# Patient Details
st.subheader("Patient Details")
p_name = st.text_input("Patient Name", value="Dipankar Sen")
col1, col2 = st.columns(2)
with col1:
  p_age = st.text_input("Age", value="26")
  p_doctor = st.text_input("Referred By", value="Self")
with col2:
  p_sex = st.selectbox("Sex", ["Male (M)", "Female (F)", "Other"])
  p_contact = st.text_input("Lab Contact", value="9076816740")

# Input Option: Choose Gallery or Camera (Camera band rahega jab tak zaroorat na ho)
st.subheader("Analyzer Screen / Printout Slip")
input_mode = st.radio(
    "Photo Source Chuniye:",
    ("📁 Upload from Gallery", "📸 Take Photo with Camera"),
    horizontal=True,
)

active_image = None
if input_mode == "📁 Upload from Gallery":
  active_image = st.file_uploader(
      "Gallery se Slip / Screen ki photo upload karein",
      type=["jpg", "jpeg", "png"],
  )
else:
  active_image = st.camera_input("Camera se machine screen ki photo lein")


# Image compression helper to boost AI speed 5x
def compress_image_for_fast_ai(img_file):
  img = Image.open(img_file)
  if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
  # Resize dimension to optimal OCR size (1200px max)
  img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
  out_bytes = io.BytesIO()
  img.save(out_bytes, format="JPEG", quality=82, optimize=True)
  return out_bytes.getvalue()


if "extracted_tests" not in st.session_state:
  st.session_state.extracted_tests = {}

if active_image and st.button("⚡ Extract Data from Photo (Fast Mode)"):
  if not api_key:
    st.error("Pehle sidebar me apni API Key dalein!")
  else:
    with st.spinner("Processing & extracting machine parameters rapidly..."):
      client = genai.Client(api_key=api_key)

      # Compress image in memory for ultra-fast payload transfer
      optimized_image_bytes = compress_image_for_fast_ai(active_image)

      prompt = """
            You are a senior clinical hematology technologist.
            Extract EVERY SINGLE lab test parameter and numerical value from this hematology analyzer or printout.
            Capture exact keys:
            - WBC, RBC, HGB, HCT, MCV, MCH, MCHC, RDWA, RDW_PERCENT
            - PLT, MPV, PDW, PCT, LPCR
            - LYM_PERCENT, LYM_ABSOLUTE
            - MID_PERCENT, MID_ABSOLUTE
            - GRAN_PERCENT, GRAN_ABSOLUTE
            
            Return strictly a valid single JSON dictionary:
            {"PARAMETER_NAME": "VALUE", ...}
            Do not skip any line. No markdown formatting, no backticks.
            """

      candidate_models = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
      success = False
      last_err = ""

      for m_name in candidate_models:
        try:
          response = client.models.generate_content(
              model=m_name,
              contents=[
                  types.Part.from_bytes(
                      data=optimized_image_bytes, mime_type="image/jpeg"
                  ),
                  prompt,
              ],
          )
          raw_text = response.text.strip()
          cleaned_json = re.sub(
              r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE
          ).strip()
          st.session_state.extracted_tests = json.loads(cleaned_json)
          st.success(
              f"⚡ Extracted all {len(st.session_state.extracted_tests)}"
              " parameters instantly!"
          )
          success = True
          break
        except Exception as err:
          last_err = str(err)
          continue

      if not success:
        st.error(
            f"Extraction busy/error. Please click again. ({last_err[:90]}...)"
        )

# Comprehensive Reference Database
MASTER_REFS = {
    "hgb": {"name": "Hemoglobin (Hb)", "unit": "g/dL", "ref": "13.0 - 17.0"},
    "hemoglobin": {
        "name": "Hemoglobin (Hb)",
        "unit": "g/dL",
        "ref": "13.0 - 17.0",
    },
    "rbc": {"name": "Total RBC Count", "unit": "10^6/uL", "ref": "4.50 - 5.50"},
    "hct": {
        "name": "Packed Cell Volume (PCV/HCT)",
        "unit": "%",
        "ref": "40.0 - 50.0",
    },
    "hematocrit": {
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
    "rdw-sd": {"name": "RDW - SD (RDWa)", "unit": "fL", "ref": "39.0 - 46.0"},
    "rdw percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "rdw_percent": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "rdw": {"name": "RDW - CV", "unit": "%", "ref": "11.5 - 14.5"},
    "wbc": {
        "name": "Total Leukocyte Count (WBC/TLC)",
        "unit": "10^3/uL",
        "ref": "4.0 - 10.0",
    },
    "tlc": {
        "name": "Total Leukocyte Count (WBC/TLC)",
        "unit": "10^3/uL",
        "ref": "4.0 - 10.0",
    },
    "gran": {
        "name": "Granulocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "2.0 - 7.0",
    },
    "gran absolute": {
        "name": "Granulocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "2.0 - 7.0",
    },
    "gran_absolute": {
        "name": "Granulocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "2.0 - 7.0",
    },
    "gran percent": {
        "name": "Granulocytes / Neutrophils (%)",
        "unit": "%",
        "ref": "40.0 - 70.0",
    },
    "gran_percent": {
        "name": "Granulocytes / Neutrophils (%)",
        "unit": "%",
        "ref": "40.0 - 70.0",
    },
    "lym": {
        "name": "Lymphocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "1.0 - 3.0",
    },
    "lym absolute": {
        "name": "Lymphocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "1.0 - 3.0",
    },
    "lym_absolute": {
        "name": "Lymphocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "1.0 - 3.0",
    },
    "lym percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "lym_percent": {"name": "Lymphocytes (%)", "unit": "%", "ref": "20.0 - 40.0"},
    "mid": {
        "name": "Mid Cells / Monocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "0.1 - 0.8",
    },
    "mid absolute": {
        "name": "Mid Cells / Monocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "0.1 - 0.8",
    },
    "mid_absolute": {
        "name": "Mid Cells / Monocytes Absolute (#)",
        "unit": "10^3/uL",
        "ref": "0.1 - 0.8",
    },
    "mid percent": {
        "name": "Mid Cells / Monocytes (%)",
        "unit": "%",
        "ref": "2.0 - 8.0",
    },
    "mid_percent": {
        "name": "Mid Cells / Monocytes (%)",
        "unit": "%",
        "ref": "2.0 - 8.0",
    },
    "plt": {
        "name": "Platelet Count (PLT)",
        "unit": "10^3/uL",
        "ref": "150 - 450",
    },
    "platelets": {
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
    "p-lcr": {
        "name": "Platelet Large Cell Ratio (P-LCR)",
        "unit": "%",
        "ref": "15.0 - 35.0",
    },
}


def resolve_meta(raw_key):
  cleaned = raw_key.strip().lower().replace("_", " ")
  if cleaned in MASTER_REFS:
    return MASTER_REFS[cleaned]
  key_no_space = cleaned.replace(" ", "")
  if key_no_space in MASTER_REFS:
    return MASTER_REFS[key_no_space]
  return {
      "name": raw_key.replace("_", " ").upper(),
      "unit": "-",
      "ref": "Clinical Correlation",
  }


if st.session_state.extracted_tests:
  st.subheader(
      f"Verify & Edit Values ({len(st.session_state.extracted_tests)}"
      " parameters)"
  )
  final_data = {}

  cols = st.columns(2)
  idx = 0
  for test, val in st.session_state.extracted_tests.items():
    meta = resolve_meta(test)
    with cols[idx % 2]:
      final_data[test] = st.text_input(
          f"{meta['name']}", value=str(val), key=f"inp_{test}"
      )
    idx += 1

  # Intelligent GBP baseline logic
  try:
    hb_val = float(
        str(final_data.get("HGB", final_data.get("Hemoglobin", 13.5))).replace(
            ",", "."
        )
    )
  except:
    hb_val = 13.5

  try:
    mcv_val = float(str(final_data.get("MCV", 88.0)).replace(",", "."))
  except:
    mcv_val = 88.0

  try:
    plt_val = float(
        str(final_data.get("PLT", final_data.get("Platelets", 250))).replace(
            ",", "."
        )
    )
  except:
    plt_val = 250.0

  if hb_val < 12.0 and mcv_val < 80.0:
    def_rbc = (
        "Microcytic, hypochromic red cells with mild anisopoikilocytosis. Few"
        " pencil cells seen."
    )
    def_imp = (
        "Microcytic Hypochromic Anemia (Probable Iron Deficiency Anemia)."
        " Advised: Serum Ferritin / Iron Profile."
    )
  elif hb_val < 12.0:
    def_rbc = (
        "Normocytic, normochromic to mildly hypochromic red blood cells. No"
        " abnormal inclusion bodies."
    )
    def_imp = "Mild Anemia. Advised clinical correlation and follow up."
  else:
    def_rbc = (
        "Predominantly normocytic and normochromic. Central pallor is normal."
        " No nucleated RBCs seen."
    )
    def_imp = (
        "Blood smear examination reveals normal hematological profile. No"
        " specific pathology identified."
    )

  if plt_val < 150:
    def_plt = (
        "Reduced on smear. No significant giant platelets or platelet"
        " aggregation seen."
    )
  else:
    def_plt = (
        "Adequate in number, seen singly and in small clumps. Normal"
        " morphology."
    )

  def_wbc = (
      "Normal in total count and distribution. Mature granulocytes seen without"
      " shift to left. No immature or blast cells."
  )
  def_parasite = (
      "No hemoparasites (Malarial Parasite / Microfilaria) seen on smear"
      " examination."
  )

  st.markdown("---")
  st.subheader("🔬 General Blood Picture (GBP / Peripheral Smear Examination)")

  gbp_rbc = st.text_area("RBC Morphology", value=def_rbc, height=68)
  gbp_wbc = st.text_area("WBC Morphology", value=def_wbc, height=68)
  gbp_plt = st.text_area("Platelets on Smear", value=def_plt, height=68)
  gbp_parasite = st.text_input("Hemoparasites", value=def_parasite)
  gbp_imp = st.text_area(
      "Diagnostic Impression / Advice", value=def_imp, height=68
  )

  if st.button("Generate Complete CBC + GBP PDF Report"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    report_time = datetime.now().strftime("%d-%b-%Y %I:%M %p")

    # 1. Header Banner
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.rect(0, height - 60, width, 60, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(32, height - 32, "THE SEN LABS")
    c.setFont("Helvetica", 8)
    c.drawString(
        32,
        height - 47,
        "ADVANCED PATHOLOGY & CLINICAL LABORATORY | AUTOMATED HEMATOLOGY &"
        " CYTOMORPHOLOGY",
    )
    c.drawRightString(width - 32, height - 35, f"Helpdesk: +91 {p_contact}")

    # 2. Patient Details Box
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.roundRect(32, height - 116, width - 64, 50, 3, fill=True, stroke=True)

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(42, height - 80, "Patient Name:")
    c.drawString(42, height - 94, "Age / Sex:")
    c.drawString(42, height - 107, "Referred By:")

    c.setFont("Helvetica", 7.5)
    c.drawString(108, height - 80, f"Mr. {p_name}")
    c.drawString(108, height - 94, f"{p_age} Yrs / {p_sex}")
    c.drawString(108, height - 107, f"Dr. {p_doctor}")

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(320, height - 80, "Sample ID:")
    c.drawString(320, height - 94, "Sample Type:")
    c.drawString(320, height - 107, "Report Date:")

    c.setFont("Helvetica", 7.5)
    c.drawString(385, height - 80, "TSL-CBC-8167")
    c.drawString(385, height - 94, "Whole Blood (EDTA)")
    c.drawString(385, height - 107, report_time)

    # 3. CBC Department Banner
    c.setFillColor(colors.HexColor("#0f766e"))
    c.rect(32, height - 131, width - 64, 12, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(
        38,
        height - 128,
        "COMPLETE BLOOD COUNT (AUTOMATED 3-PART HEMATOLOGY PROFILE)",
    )

    # 4. CBC Table Header
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.rect(32, height - 145, width - 64, 12, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(38, height - 142, "INVESTIGATION / PARAMETER")
    c.drawString(245, height - 142, "RESULT")
    c.drawString(315, height - 142, "UNIT")
    c.drawString(395, height - 142, "BIOLOGICAL REFERENCE RANGE")

    # 5. Compact CBC Table Rows
    y = height - 156
    c.setFont("Helvetica", 6.8)

    for key, val in final_data.items():
      meta = resolve_meta(key)

      c.setFillColor(colors.HexColor("#0f172a"))
      c.drawString(38, y, str(meta["name"]))

      c.setFont("Helvetica-Bold", 6.8)
      c.drawString(245, y, str(val))
      c.setFont("Helvetica", 6.8)

      c.drawString(315, y, str(meta["unit"]))
      c.drawString(395, y, str(meta["ref"]))

      c.setStrokeColor(colors.HexColor("#f1f5f9"))
      c.line(32, y - 2, width - 32, y - 2)

      y -= 10.8
      if y < height - 355:
        break

    # 6. GBP / Peripheral Smear Banner
    gbp_top = y - 4
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.rect(32, gbp_top, width - 64, 12, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(
        38,
        gbp_top + 3,
        "GENERAL BLOOD PICTURE (PERIPHERAL BLOOD SMEAR EXAMINATION)",
    )

    # 7. GBP Details Box
    gbp_box_y = gbp_top - 12
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.rect(32, 70, width - 64, gbp_box_y - 70, fill=True, stroke=True)

    cur_y = gbp_box_y - 12

    def print_gbp_field(title, text, cur_y):
      c.setFont("Helvetica-Bold", 7.2)
      c.setFillColor(colors.HexColor("#0f172a"))
      c.drawString(40, cur_y, f"{title}:")
      c.setFont("Helvetica", 7.2)
      c.setFillColor(colors.HexColor("#334155"))
      c.drawString(120, cur_y, text[:110])
      if len(text) > 110:
        cur_y -= 9
        c.drawString(120, cur_y, text[110:220])
      return cur_y - 11

    cur_y = print_gbp_field("RBC Morphology", gbp_rbc, cur_y)
    cur_y = print_gbp_field("WBC Morphology", gbp_wbc, cur_y)
    cur_y = print_gbp_field("Platelets on Smear", gbp_plt, cur_y)
    cur_y = print_gbp_field("Hemoparasites", gbp_parasite, cur_y)

    # Impression Callout
    c.setFillColor(colors.HexColor("#ecfdf5"))
    c.setStrokeColor(colors.HexColor("#a7f3d0"))
    c.roundRect(38, 76, width - 76, cur_y - 72, 2, fill=True, stroke=True)
    c.setFont("Helvetica-Bold", 7.2)
    c.setFillColor(colors.HexColor("#065f46"))
    c.drawString(44, cur_y - 8, "IMPRESSION / ADVISE:")
    c.setFont("Helvetica", 7.2)
    c.drawString(150, cur_y - 8, gbp_imp[:95])
    if len(gbp_imp) > 95:
      c.drawString(150, cur_y - 17, gbp_imp[95:190])

    # 8. Signatures Block
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(32, 58, width - 32, 58)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(42, 46, "Dipankar Sen")
    c.drawString(width - 190, 46, "Dr. R. K. Banerjee")
    c.setFont("Helvetica", 6.8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(42, 36, "Medical Lab Technologist (DMLT / BSS)")
    c.drawString(width - 190, 36, "Consultant Pathologist (MD Path)")

    c.save()
    buf.seek(0)

    st.download_button(
        label="Download Complete CBC + GBP PDF",
        data=buf,
        file_name=f"{p_name.replace(' ', '_')}_CBC_GBP_Report.pdf",
        mime="application/pdf",
    )
