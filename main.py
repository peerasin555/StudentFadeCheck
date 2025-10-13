# app.py  — Improved UI with better UX
import os, io, json, html, time
from typing import Any, Dict
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ----------------- Page -----------------
st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

CSS = """
<style>
/* Base styles */
html, body, [class*="css"] { 
    font-size: 16px; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
div.block-container { 
    padding: 1rem 1rem 3rem;
    max-width: 600px;
    margin: 0 auto;
}

/* Header with gradient */
.header { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}
.header h1 { 
    font-size: 28px;
    margin: 0;
    color: white;
    font-weight: 800;
    letter-spacing: 0.5px;
}
.header p {
    color: rgba(255, 255, 255, 0.9);
    margin: 8px 0 0 0;
    font-size: 14px;
}

/* Camera container with better spacing */
.cam-box { 
    position: relative;
    margin-bottom: 1rem;
    background: #f8fafc;
    padding: 1rem;
    border-radius: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.cam-box [data-testid="stCameraInputLabel"] { 
    display: none;
}
.cam-box [data-testid="stCameraInput"] video,
.cam-box [data-testid="stCameraInput"] img { 
    border-radius: 16px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

/* Modern corner overlays */
.overlay { 
    pointer-events: none;
    position: absolute;
    inset: 24px;
    border-radius: 16px;
}
.corner { 
    position: absolute;
    width: 50px;
    height: 50px;
    border: 4px solid #667eea;
    opacity: 0.8;
    border-radius: 12px;
    transition: all 0.3s ease;
}
.corner.tl { left: 0; top: 0; border-bottom: none; border-right: none; }
.corner.tr { right: 0; top: 0; border-bottom: none; border-left: none; }
.corner.bl { left: 0; bottom: 0; border-top: none; border-right: none; }
.corner.br { right: 0; bottom: 0; border-top: none; border-left: none; }

/* Info card */
.info-card {
    background: linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%);
    padding: 1rem 1.25rem;
    border-radius: 16px;
    margin: 1rem 0;
    border: 2px solid #c7d2fe;
}
.info-card-title {
    font-weight: 700;
    color: #4c1d95;
    margin-bottom: 0.5rem;
    font-size: 15px;
}
.info-card-text {
    color: #5b21b6;
    font-size: 14px;
    line-height: 1.6;
}

/* Hint pill - improved */
.hint { 
    text-align: center;
    margin: 1rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff;
    padding: 12px 20px;
    border-radius: 16px;
    display: inline-block;
    font-weight: 600;
    font-size: 14px;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

/* Button container */
.button-container {
    display: flex;
    gap: 12px;
    margin: 1.5rem 0;
}

/* Buttons - modern design */
.stButton > button { 
    width: 100%;
    padding: 1rem 1.2rem;
    font-size: 16px;
    font-weight: 700;
    border-radius: 16px;
    border: none !important;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}
.stButton > button[kind="primary"] { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: #fff !important;
}
.stButton > button[kind="secondary"] { 
    background: #f1f5f9 !important;
    color: #334155 !important;
}

/* Result sheet - improved */
.sheet { 
    border-radius: 24px 24px 0 0;
    padding: 1.5rem;
    background: white;
    box-shadow: 0 -4px 24px rgba(0,0,0,0.12);
    border: 1px solid rgba(0,0,0,0.06);
    margin-top: 2rem;
}

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid #f1f5f9;
}

.result-title {
    font-weight: 800;
    font-size: 20px;
    color: #0f172a;
}

/* Badge - improved */
.badge { 
    display: inline-flex;
    align-items: center;
    padding: 8px 16px;
    border-radius: 12px;
    color: white;
    font-weight: 800;
    font-size: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.badge::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: white;
    margin-right: 8px;
}
.badge-ok { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.badge-no { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
.badge-unsure { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }

/* Result sections */
.result-section {
    background: #f8fafc;
    padding: 1rem 1.25rem;
    border-radius: 16px;
    margin: 1rem 0;
    border: 1px solid #e2e8f0;
}

.result-section-title {
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.75rem;
    font-size: 15px;
    display: flex;
    align-items: center;
}

.result-section-title::before {
    content: '•';
    color: #667eea;
    font-size: 24px;
    margin-right: 8px;
}

.result-list {
    margin: 0;
    padding-left: 1.5rem;
}

.result-list li {
    margin-bottom: 0.5rem;
    color: #334155;
    line-height: 1.6;
    font-size: 14px;
}

/* Confidence bar */
.confidence-bar {
    background: #e2e8f0;
    height: 8px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 999px;
    transition: width 0.5s ease;
}

/* Alert messages */
.stAlert {
    border-radius: 16px;
    padding: 1rem 1.25rem;
}

/* Progress bar */
.stProgress > div > div {
    border-radius: 999px;
}

/* Image preview */
.image-preview {
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    margin: 1.5rem 0;
}

/* Loading animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 1.5s ease-in-out infinite;
}

/* Responsive adjustments */
@media (max-width: 640px) {
    .header h1 { font-size: 24px; }
    .result-title { font-size: 18px; }
    .button-container { flex-direction: column; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------- Rules & schema -----------------
RULES = (
    "กฎระเบียบทรงผม (ชาย)\n"
    "1) รองทรงสูง ด้านข้าง/ด้านหลังสั้น\n"
    "2) ด้านบนยาวไม่เกิน 5 ซม.\n"
    "3) ห้ามย้อม/ดัด/ไว้หนวดเครา\n"
)
SCHEMA_HINT = (
    'จงตอบเป็น JSON เท่านั้น ตามสคีมา:\n'
    '{"verdict":"compliant | non_compliant | unsure","reasons":["string"],'
    '"violations":[{"code":"STRING","message":"STRING"}],"confidence":0.0,'
    '"meta":{"rule_set_id":"default-v1","timestamp":"AUTO"}}'
)

# ----------------- Helpers -----------------
def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)

def badge(verdict: str) -> str:
    m = {
        "compliant": ("✓ ผ่านระเบียบ", "badge-ok"),
        "non_compliant": ("✗ ไม่ผ่านระเบียบ", "badge-no"),
        "unsure": ("? ไม่แน่ใจ", "badge-unsure"),
    }
    label, cls = m.get(verdict, ("? ไม่แน่ใจ", "badge-unsure"))
    return f'<span class="badge {cls}">{label}</span>'

def compress(img: Image.Image, mime: str) -> bytes:
    img = img.copy()
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    if mime == "image/png":
        img.save(buf, "PNG", optimize=True)
    else:
        img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()

def parse_json_strict(text: str) -> Dict[str, Any]:
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[s:e+1])

# ----------------- Gemini -----------------
def call_gemini(image_bytes: bytes, mime: str, retries: int = 2) -> Dict[str, Any]:
    api_key = (getattr(st, "secrets", {}).get("GEMINI_API_KEY", None)
               if hasattr(st, "secrets") else None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set (Secrets/Env).")

    client = genai.Client(api_key=api_key)
    prompt = f"""SYSTEM:
คุณเป็นผู้ช่วยตรวจทรงผมนักเรียน ให้ตอบเป็น JSON เท่านั้น
USER (ไทย):
ตรวจรูปนี้ตามกฎ:
{RULES}

{SCHEMA_HINT}
- ถ้ารูปไม่ชัด ให้ verdict="unsure" พร้อมเหตุผล
"""

    last_err = None
    for i in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": image_bytes}}
                ]}],
            )
            return parse_json_strict((resp.text or "").strip())
        except errors.ServerError as e:
            last_err = e
            if "503" in str(e) and i < retries - 1:
                st.info("🔄 ระบบหนาแน่น กำลังลองใหม่...")
                time.sleep(2 * (i + 1))
                continue
            break
        except Exception as e:
            last_err = e
            break

    return {
        "verdict": "unsure",
        "reasons": [f"เกิดข้อผิดพลาด: {last_err}"],
        "violations": [],
        "confidence": 0.0,
        "meta": {"rule_set_id": "default-v1"},
    }

# ----------------- Header -----------------
st.markdown('''
<div class="header">
    <h1>✂️ Hair Check</h1>
    <p>ระบบตรวจสอบทรงผมนักเรียนอัตโนมัติ</p>
</div>
''', unsafe_allow_html=True)

# Info card
st.markdown('''
<div class="info-card">
    <div class="info-card-title">📋 วิธีใช้งาน</div>
    <div class="info-card-text">
        1. กดปุ่ม "Take Photo" เพื่อถ่ายภาพ<br>
        2. ตรวจสอบภาพที่ถ่ายให้ชัดเจน<br>
        3. กดปุ่ม "🔎 ตรวจสอบ" เพื่อวิเคราะห์ทรงผม
    </div>
</div>
''', unsafe_allow_html=True)

# ----------------- Camera -----------------
st.markdown('<div class="cam-box">', unsafe_allow_html=True)
photo = st.camera_input("📸 ถ่ายภาพทรงผม")
st.markdown("""
<div class="overlay">
    <div class="corner tl"></div>
    <div class="corner tr"></div>
    <div class="corner bl"></div>
    <div class="corner br"></div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Hint
st.markdown('<div style="text-align:center;"><span class="hint">💡 วางตำแหน่งใบหน้าให้อยู่ในกรอบสี่เหลี่ยม</span></div>', unsafe_allow_html=True)

# Buttons
st.markdown('<div class="button-container">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    do_analyze = st.button("🔎 ตรวจสอบ", type="primary", use_container_width=True)
with col2:
    clear = st.button("↺ ถ่ายใหม่", type="secondary", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if clear:
    if "result" in st.session_state:
        del st.session_state["result"]
    st.rerun()

# ----------------- Analyze -----------------
if do_analyze:
    if not photo:
        st.warning("⚠️ กรุณาถ่ายภาพก่อนกดตรวจสอบ")
    else:
        try:
            img = Image.open(photo).convert("RGB")
            mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
            
            # Show preview
            st.markdown('<div class="image-preview">', unsafe_allow_html=True)
            st.image(img, caption="📷 ภาพที่ถ่าย", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Progress
            prog = st.progress(0, text="⏳ กำลังเตรียมภาพ...")
            data = compress(img, mime)
            prog.progress(35, text="📤 กำลังส่งไปตรวจ...")

            with st.spinner("🤖 ระบบ AI กำลังวิเคราะห์..."):
                result = call_gemini(data, mime)
            
            prog.progress(100, text="✅ เสร็จสิ้น")
            time.sleep(0.5)
            prog.empty()
            
            st.success("✅ ตรวจสอบเสร็จสิ้น!")
            st.session_state["result"] = result
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

# ----------------- Result -----------------
res = st.session_state.get("result")
if res:
    verdict = res.get("verdict", "unsure")
    reasons = res.get("reasons", []) or []
    violations = res.get("violations", []) or []
    conf = res.get("confidence", 0.0)

    st.markdown('<div class="sheet">', unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="result-header">
        <div class="result-title">📊 ผลการตรวจสอบ</div>
        {badge(verdict)}
    </div>
    """, unsafe_allow_html=True)
    
    # Confidence
    st.markdown(f"""
    <div class="result-section">
        <div class="result-section-title">🎯 ความมั่นใจของระบบ</div>
        <div style="font-size: 24px; font-weight: 800; color: #667eea;">{conf:.1%}</div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: {conf*100}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Reasons
    if reasons:
        st.markdown(f"""
        <div class="result-section">
            <div class="result-section-title">💭 เหตุผลสรุป</div>
            <ul class="result-list">
                {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Violations
    if violations:
        st.markdown(f"""
        <div class="result-section">
            <div class="result-section-title">⚠️ จุดที่ไม่ตรงกับระเบียบ</div>
            <ul class="result-list">
                {''.join(f'<li><b>{esc(v.get("code", "N/A"))}</b>: {esc(v.get("message", ""))}</li>' for v in violations)}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
