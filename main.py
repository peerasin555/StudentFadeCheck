# app.py
import os, io, json, html, time
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ===================== Page setup =====================
st.set_page_config(page_title="Student Hair Check", page_icon="✂️", layout="wide")

# ---- CSS (Lens-like, minimal, mobile-first) ----
CSS = """
<style>
/* Base */
html, body, [class*="css"] { font-size: 18px; }
div.block-container { padding-top: .4rem; padding-bottom: 2rem; }

/* Top bar */
.topbar { display:flex; align-items:center; justify-content:space-between;
  gap:12px; padding:.4rem .2rem .6rem .2rem; }
.brand { font-weight:800; font-size:1.2rem; letter-spacing:.2px; }
.gear-wrap { display:flex; gap:8px; align-items:center; }

/* Gear button */
.stButton > button.gear {
  width:auto; padding:.55rem .7rem; border-radius:12px; font-size:1.05rem;
  background:#f1f5f9 !important; color:#0f172a !important; border:none !important;
}
.stButton > button.gear:hover { background:#e2e8f0 !important; }

/* Primary / Secondary buttons */
.stButton > button.primary {
  width:100%; padding:1.0rem 1.1rem; font-size:1.12rem; font-weight:700;
  border-radius:14px; background:#2563eb !important; color:#fff !important; border:none !important;
}
.stButton > button.primary:hover { background:#1e40af !important; }
.stButton > button.secondary {
  width:100%; padding:1.0rem 1.1rem; font-size:1.02rem; font-weight:700;
  border-radius:14px; background:#e2e8f0 !important; color:#0f172a !important; border:none !important;
}
.stButton > button.secondary:hover { background:#cbd5e1 !important; }

/* Camera label */
[data-testid="stCameraInputLabel"] { font-size:1.05rem; }

/* Result card */
.result-card {
  border-radius:16px; padding:1rem 1.1rem; margin-top:.6rem;
  border:1px solid rgba(0,0,0,.08); box-shadow:0 2px 10px rgba(0,0,0,.06);
  background:#fff;
}
/* enforce readable text even in dark theme */
.result-card, .result-card * { color:#0f172a !important; }
.result-card hr { border-color: rgba(0,0,0,.12) !important; }

/* Badge */
.badge {
  display:inline-block; padding:.35rem .9rem; border-radius:999px;
  font-weight:800; font-size:1rem; color:#fff; border:2px solid #fff;
  box-shadow:0 2px 4px rgba(0,0,0,.15);
}
.badge-ok { background:#22c55e; }
.badge-no { background:#ef4444; }
.badge-unsure { background:#f59e0b; }

/* List */
.result-list { margin:.4rem 0 0 1.1rem; }
.result-list li { margin-bottom:.2rem; }

/* Settings panel mimic (Lens-like sheet) */
.panel {
  border:1px solid #e2e8f0; border-radius:16px; background:#f8fafc;
  padding:12px 14px; margin-bottom:.4rem;
}
.panel h4 { margin:.2rem 0 .6rem 0; font-size:1.05rem; }
textarea, input, .stTextInput input, .stSelectbox div, .stSlider { font-size:1rem !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ===================== Defaults & schema hint =====================
DEFAULT_RULES = """\
กฎระเบียบทรงผม (ชาย)
1) รองทรงสูง ด้านข้าง/ด้านหลังสั้น
2) ด้านบนยาวไม่เกิน 5 ซม.
3) ห้ามย้อม/ดัด/ไว้หนวดเครา
"""

SCHEMA_HINT = """\
จงตอบเป็น JSON เท่านั้น ตามสคีมา:
{
  "verdict": "compliant | non_compliant | unsure",
  "reasons": ["string"],
  "violations": [{"code":"STRING","message":"STRING"}],
  "confidence": 0.0,
  "meta": {"rule_set_id":"default-v1","timestamp":"AUTO"}
}
"""

# ===================== Helpers =====================
def esc(s: object) -> str:
    return html.escape(str(s), quote=True)

def verdict_badge(verdict: str) -> str:
    mp = {
        "compliant": ("ผ่านระเบียบ", "badge-ok"),
        "non_compliant": ("ไม่ผ่านระเบียบ", "badge-no"),
        "unsure": ("ไม่แน่ใจ", "badge-unsure"),
    }
    label, css = mp.get(verdict, ("ไม่แน่ใจ", "badge-unsure"))
    return f'<span class="badge {css}">{label}</span>'

def compress_image(img: Image.Image, mime: str, max_side: int = 1024, jpeg_q: int = 85) -> bytes:
    """Resize down + compress for mobile networks"""
    img = img.copy()
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    if mime == "image/png":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=jpeg_q, optimize=True)
    return buf.getvalue()

# ===================== Gemini call =====================
def call_gemini(image_bytes: bytes, mime: str, rules: str, model_name: str, retries: int = 2):
    # API key: secrets -> env
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY (Secrets/Env).")

    client = genai.Client(api_key=api_key)

    prompt = f"""
SYSTEM:
คุณเป็นผู้ช่วยตรวจทรงผมนักเรียน ให้ตอบเป็น JSON เท่านั้น

USER (ไทย):
ตรวจรูปนี้ตามกฎ:
{rules}

{SCHEMA_HINT}

เงื่อนไข:
- ถ้ารูปไม่ชัด/ไม่เห็นทรงผมพอ ให้ verdict="unsure" และบอกเหตุผล
- เหตุผลควรกระชับ เข้าใจง่าย
- meta.rule_set_id = "default-v1"
"""

    last_err = None
    for i in range(retries):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=[{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": image_bytes}}
                    ]
                }],
            )
            text = (resp.text or "").strip()
            s, e = text.find("{"), text.rfind("}")
            return json.loads(text[s:e+1])
        except errors.ServerError as e:
            last_err = e
            if "503" in str(e) and i < retries - 1:
                st.toast("ระบบหนาแน่น กำลังลองใหม่…", icon="⏳")
                time.sleep(2 * (i + 1))
                continue
            break
        except Exception as e:
            last_err = e
            break

    return {
        "verdict": "unsure",
        "reasons": [f"เกิดข้อผิดพลาดระหว่างเรียกโมเดล: {last_err}"],
        "violations": [],
        "confidence": 0.0,
        "meta": {"rule_set_id": "default-v1"}
    }

# ===================== State init =====================
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "rules_cache" not in st.session_state:
    st.session_state.rules_cache = DEFAULT_RULES
if "auto_analyze" not in st.session_state:
    st.session_state.auto_analyze = True
if "model_name" not in st.session_state:
    st.session_state.model_name = "gemini-2.5-flash"
if "max_side" not in st.session_state:
    st.session_state.max_side = 1024
if "jpeg_q" not in st.session_state:
    st.session_state.jpeg_q = 85
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# ===================== Top bar (brand + gear) =====================
c1, c2 = st.columns([6, 1])
with c1:
    st.markdown('<div class="topbar"><div class="brand">Hair Check</div></div>', unsafe_allow_html=True)
with c2:
    if st.button("⚙️", key="gear", help="ตั้งค่า", type="secondary", use_container_width=True):
        st.session_state.show_settings = not st.session_state.show_settings
# mimic Lens: gear toggles a compact panel below

# ===================== Settings Panel =====================
if st.session_state.show_settings:
    with st.container():
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("#### การตั้งค่า")
        st.session_state.model_name = st.selectbox(
            "โมเดล", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0
        )
        st.session_state.auto_analyze = st.toggle("วิเคราะห์อัตโนมัติหลังถ่าย", value=st.session_state.auto_analyze)
        st.session_state.max_side = st.slider("จำกัดด้านยาวภาพ (px)", 640, 2048, st.session_state.max_side, step=64)
        st.session_state.jpeg_q = st.slider("คุณภาพ JPEG (%)", 50, 95, st.session_state.jpeg_q, step=5)
        rules = st.text_area("กฎระเบียบ (ปรับได้)", st.session_state.rules_cache, height=120)
        st.session_state.rules_cache = rules or DEFAULT_RULES
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== Main capture area =====================
st.caption("ถ่ายภาพให้เห็นทรงผมชัดเจน แล้วกดตรวจ")
photo = st.camera_input("ถ่ายภาพ", key="cam")

# Auto analyze once after capture
trigger_auto = st.session_state.auto_analyze and photo is not None and st.session_state.last_result is None

# Action buttons
colA, colB = st.columns(2)
with colA:
    analyze_clicked = st.button("🔎 ตรวจทันที", type="primary", use_container_width=True)
with colB:
    clear_clicked = st.button("↺ ถ่ายใหม่", type="secondary", use_container_width=True)

if clear_clicked:
    st.session_state.last_result = None
    st.rerun()

# ===================== Run analysis =====================
if photo and (analyze_clicked or trigger_auto):
    try:
        img = Image.open(photo).convert("RGB")
        mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
        st.image(img, caption="ภาพที่ถ่าย", use_container_width=True)

        prog = st.progress(0, text="เตรียมภาพ…")
        image_bytes = compress_image(img, mime, max_side=st.session_state.max_side, jpeg_q=st.session_state.jpeg_q)
        prog.progress(35, text="กำลังส่งไปตรวจ…")

        with st.spinner("ระบบกำลังตรวจ…"):
            result = call_gemini(
                image_bytes=image_bytes,
                mime=mime,
                rules=st.session_state.rules_cache,
                model_name=st.session_state.model_name,
            )
        prog.progress(100, text="เสร็จสิ้น")
        st.toast("ตรวจเสร็จแล้ว", icon="✅")

        st.session_state.last_result = result
    except Exception as e:
        st.error(f"ไม่สามารถวิเคราะห์ได้: {e}")

# ===================== Result card =====================
if st.session_state.last_result:
    r = st.session_state.last_result
    verdict = r.get("verdict", "unsure")
    reasons = r.get("reasons", []) or []
    violations = r.get("violations", []) or []
    conf = r.get("confidence", 0.0)
    meta = r.get("meta", {}) or {}

    st.markdown(
        f"""
        <div class="result-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
            <div style="font-weight:800;font-size:1.06rem;">ผลการตรวจ</div>
            <div>{verdict_badge(verdict)}</div>
          </div>
          <div style="margin-top:6px;color:#475569;">ความมั่นใจของระบบ: <b>{conf:.2f}</b></div>
          <hr style="opacity:.12;margin:12px 0;">
          <div style="font-weight:700;margin-bottom:6px;">เหตุผลสรุป</div>
          <ul class="result-list">
            {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
          </ul>
          {"<div style='font-weight:700;margin-top:10px;'>ข้อที่ไม่ตรงระเบียบ</div><ul class='result-list'>" + ''.join(f"<li>{esc(v.get('message',''))}</li>" for v in violations) + "</ul>" if violations else ""}
        </div>
        """,
        unsafe_allow_html=True
    )
