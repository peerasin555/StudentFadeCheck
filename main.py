# app.py  — Google Lens-inspired UI
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
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Sarabun:wght@400;500;600;700&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body, [class*="css"] { 
    font-size: 16px; 
    font-family: 'Sarabun', 'Google Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #fff;
}

div.block-container { 
    padding: 0 !important;
    max-width: 100% !important;
}

/* Google Lens-style header */
.lens-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #fff;
    border-bottom: 1px solid #e8eaed;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.lens-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 20px;
    font-weight: 500;
    color: #202124;
}

.lens-logo-icon {
    width: 24px;
    height: 24px;
    background: linear-gradient(135deg, #4285f4, #34a853, #fbbc05, #ea4335);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 14px;
}

/* Camera viewfinder - full screen style */
.camera-container {
    position: relative;
    width: 100%;
    height: 70vh;
    max-height: 600px;
    background: #000;
    overflow: hidden;
}

.camera-container [data-testid="stCameraInputLabel"] { 
    display: none; 
}

.camera-container [data-testid="stCameraInput"] {
    height: 100%;
}

.camera-container [data-testid="stCameraInput"] video,
.camera-container [data-testid="stCameraInput"] img { 
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 0;
}

/* Lens-style scanning overlay */
.scan-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    display: flex;
    align-items: center;
    justify-content: center;
}

.scan-frame {
    width: 280px;
    height: 280px;
    position: relative;
}

.scan-corner {
    position: absolute;
    width: 48px;
    height: 48px;
    border: 3px solid #fff;
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
}

.scan-corner.tl { top: 0; left: 0; border-bottom: none; border-right: none; border-radius: 8px 0 0 0; }
.scan-corner.tr { top: 0; right: 0; border-bottom: none; border-left: none; border-radius: 0 8px 0 0; }
.scan-corner.bl { bottom: 0; left: 0; border-top: none; border-right: none; border-radius: 0 0 0 8px; }
.scan-corner.br { bottom: 0; right: 0; border-top: none; border-left: none; border-radius: 0 0 8px 0; }

.scan-line {
    position: absolute;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, #4285f4, transparent);
    animation: scanline 2s ease-in-out infinite;
}

@keyframes scanline {
    0%, 100% { top: 0; opacity: 0; }
    50% { top: 50%; opacity: 1; }
}

/* Camera hint */
.camera-hint {
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(32, 33, 36, 0.9);
    backdrop-filter: blur(10px);
    color: white;
    padding: 12px 24px;
    border-radius: 24px;
    font-size: 14px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

/* Bottom action bar */
.action-bar {
    background: #fff;
    padding: 16px;
    display: flex;
    gap: 12px;
    border-top: 1px solid #e8eaed;
}

/* Google Material buttons */
.stButton > button {
    width: 100%;
    height: 48px;
    border-radius: 24px;
    font-size: 15px;
    font-weight: 500;
    border: none;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    font-family: 'Sarabun', 'Google Sans', sans-serif !important;
    box-shadow: none;
}

.stButton > button[kind="primary"] {
    background: #1a73e8 !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    background: #1765cc !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24) !important;
}

.stButton > button[kind="secondary"] {
    background: #f1f3f4 !important;
    color: #3c4043 !important;
}

.stButton > button[kind="secondary"]:hover {
    background: #e8eaed !important;
}

/* Results bottom sheet - Google style */
.results-sheet {
    background: #fff;
    border-radius: 28px 28px 0 0;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    margin-top: -28px;
    position: relative;
    z-index: 10;
}

.sheet-handle {
    width: 32px;
    height: 4px;
    background: #dadce0;
    border-radius: 2px;
    margin: 12px auto;
}

.sheet-content {
    padding: 0 16px 24px;
}

/* Result card - Material Design */
.result-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 16px;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 16px;
}

.result-chip.success {
    background: #e6f4ea;
    color: #137333;
}

.result-chip.error {
    background: #fce8e6;
    color: #c5221f;
}

.result-chip.warning {
    background: #fef7e0;
    color: #ea8600;
}

.result-section {
    margin-bottom: 24px;
}

.result-title {
    font-size: 14px;
    font-weight: 500;
    color: #5f6368;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

.result-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
}

.result-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 8px 0;
    color: #3c4043;
    line-height: 1.5;
}

.result-icon {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    margin-top: 2px;
}

/* Confidence meter - Material style */
.confidence-container {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
}

.confidence-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 14px;
}

.confidence-label-text {
    color: #5f6368;
    font-weight: 500;
}

.confidence-value {
    color: #1a73e8;
    font-weight: 700;
}

.confidence-bar-bg {
    height: 4px;
    background: #e8eaed;
    border-radius: 2px;
    overflow: hidden;
}

.confidence-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #1a73e8, #4285f4);
    border-radius: 2px;
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Info card - Material */
.info-card {
    border: 1px solid #e8eaed;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    background: #fff;
}

.info-card-title {
    font-size: 16px;
    font-weight: 500;
    color: #202124;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.info-list {
    list-style: none;
    padding: 0;
}

.info-list li {
    padding: 6px 0;
    padding-left: 24px;
    position: relative;
    color: #5f6368;
    line-height: 1.5;
}

.info-list li:before {
    content: "•";
    position: absolute;
    left: 8px;
    color: #1a73e8;
    font-weight: bold;
}

/* Hide Streamlit elements */
.stCameraInput button {
    background: transparent !important;
    border: none !important;
}

.stAlert {
    border-radius: 12px !important;
    border: none !important;
    font-size: 14px !important;
}

/* Progress bar override */
.stProgress > div > div {
    background: #1a73e8 !important;
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

def result_chip(verdict: str) -> str:
    m = {
        "compliant": ("✓ ผ่านระเบียบ", "success"),
        "non_compliant": ("✗ ไม่ผ่าน", "error"),
        "unsure": ("? ไม่แน่ใจ", "warning"),
    }
    label, cls = m.get(verdict, ("? ไม่แน่ใจ", "warning"))
    return f'<div class="result-chip {cls}">{label}</div>'

def compress(img: Image.Image, mime: str) -> bytes:
    img = img.copy(); img.thumbnail((1024,1024))
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
                st.info("กำลังลองใหม่...")
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

# ----------------- Header (Google Lens style) -----------------
st.markdown("""
<div class="lens-header">
    <div class="lens-logo">
        <div class="lens-logo-icon">✂</div>
        <span>Hair Check</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Camera (Full-screen viewfinder) -----------------
st.markdown('<div class="camera-container">', unsafe_allow_html=True)
photo = st.camera_input(" ")

st.markdown("""
<div class="scan-overlay">
    <div class="scan-frame">
        <div class="scan-corner tl"></div>
        <div class="scan-corner tr"></div>
        <div class="scan-corner bl"></div>
        <div class="scan-corner br"></div>
        <div class="scan-line"></div>
    </div>
</div>
<div class="camera-hint">
    📷 จัดมุมกล้องให้เห็นทรงผมชัดเจน
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ----------------- Action Buttons -----------------
st.markdown('<div class="action-bar">', unsafe_allow_html=True)
col1, col2 = st.columns([2, 1])
with col1:
    do_analyze = st.button("🔍 ตรวจสอบ", type="primary", use_container_width=True)
with col2:
    clear = st.button("↻ ใหม่", type="secondary", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if clear:
    st.session_state.pop("result", None)
    st.rerun()

# ----------------- Analyze -----------------
if do_analyze:
    if not photo:
        st.warning("กรุณาถ่ายภาพก่อน")
    else:
        try:
            img = Image.open(photo).convert("RGB")
            mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
            
            prog = st.progress(0, text="กำลังประมวลผล...")
            data = compress(img, mime)
            prog.progress(35, text="กำลังวิเคราะห์...")

            with st.spinner(""):
                result = call_gemini(data, mime)
            
            prog.progress(100, text="เสร็จสิ้น")
            st.success("วิเคราะห์เสร็จแล้ว")
            st.session_state["result"] = result
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# ----------------- Results (Bottom Sheet) -----------------
res = st.session_state.get("result")
if res:
    verdict = res.get("verdict", "unsure")
    reasons = res.get("reasons", []) or []
    violations = res.get("violations", []) or []
    conf = res.get("confidence", 0.0)

    st.markdown('<div class="results-sheet">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-handle"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sheet-content">', unsafe_allow_html=True)
    
    # Result chip
    st.markdown(result_chip(verdict), unsafe_allow_html=True)
    
    # Confidence
    st.markdown(f"""
    <div class="confidence-container">
        <div class="confidence-label">
            <span class="confidence-label-text">ความเชื่อมั่น</span>
            <span class="confidence-value">{conf:.0%}</span>
        </div>
        <div class="confidence-bar-bg">
            <div class="confidence-bar-fill" style="width:{conf*100}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Reasons
    if reasons:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown('<div class="result-title">รายละเอียด</div>', unsafe_allow_html=True)
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        for reason in reasons:
            st.markdown(f"""
            <div class="result-item">
                <div class="result-icon">💬</div>
                <div>{esc(reason)}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    # Violations
    if violations:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown('<div class="result-title">ข้อที่ไม่ผ่าน</div>', unsafe_allow_html=True)
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        for v in violations:
            st.markdown(f"""
            <div class="result-item">
                <div class="result-icon">⚠️</div>
                <div>{esc(v.get('message', ''))}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    # Info card
    st.markdown("""
    <div class="info-card">
        <div class="info-card-title">💡 คำแนะนำ</div>
        <ul class="info-list">
            <li>ผลนี้เป็นข้อมูลเบื้องต้นจาก AI</li>
            <li>ควรให้ครูตรวจสอบอีกครั้ง</li>
            <li>ถ่ายในที่แสงสว่างเพื่อความแม่นยำ</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)

# Info section (before taking photo)
if not res:
    st.markdown("""
    <div style="padding: 16px;">
        <div class="info-card">
            <div class="info-card-title">📋 กฎระเบียบทรงผม</div>
            <ul class="info-list">
                <li>รองทรงสูง ด้านข้างและหลังสั้น</li>
                <li>ด้านบนยาวไม่เกิน 5 ซม.</li>
                <li>ห้ามย้อมสี ดัด หรือไว้หนวดเครา</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)
