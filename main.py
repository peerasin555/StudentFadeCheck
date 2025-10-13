# app.py  — Friendly, mobile-first UI
import os, io, json, html, time
from typing import Any, Dict
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ----------------- Page -----------------
st.set_page_config(page_title="Hair Check ✨", page_icon="✂️", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { 
    font-size: 18px; 
    font-family: 'Sarabun', sans-serif !important;
}
div.block-container { padding: 0.4rem 0.6rem 2rem; }

/* Gradient background */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Title bar with gradient */
.header { 
    display:flex; 
    justify-content:center; 
    align-items:center; 
    padding: 16px 0;
    margin-bottom: 12px;
}
.header h1 { 
    font-size: 28px; 
    margin: 0; 
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Welcome card */
.welcome-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    color: white;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
}
.welcome-card h2 {
    font-size: 22px;
    font-weight: 800;
    margin: 0 0 8px 0;
    color: white !important;
}
.welcome-card p {
    font-size: 16px;
    margin: 0;
    opacity: 0.95;
    color: white !important;
}

/* Camera container with playful design */
.cam-box { 
    position: relative; 
    margin-bottom: 16px;
    background: white;
    border-radius: 24px;
    padding: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.cam-box [data-testid="stCameraInputLabel"] { display:none; }
.cam-box [data-testid="stCameraInput"] video,
.cam-box [data-testid="stCameraInput"] img { 
    border-radius: 18px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

/* Animated corner arcs */
.overlay { pointer-events:none; position:absolute; inset:22px; border-radius: 18px; }
.corner { 
    position:absolute; 
    width:64px; 
    height:64px; 
    border:3px solid #667eea; 
    opacity:.9; 
    border-radius:14px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}
.corner.tl{left:0;top:0;border-bottom:none;border-right:none}
.corner.tr{right:0;top:0;border-bottom:none;border-left:none}
.corner.bl{left:0;bottom:0;border-top:none;border-right:none}
.corner.br{right:0;bottom:0;border-top:none;border-left:none}

/* Friendly hint pill */
.hint { 
    text-align:center; 
    margin:10px 0 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color:#fff; 
    padding:12px 20px;
    border-radius:999px; 
    display:inline-block;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
}

/* Enhanced buttons */
.stButton > button { 
    width:100%; 
    padding:1.1rem 1.2rem; 
    font-size:1.12rem; 
    font-weight:700; 
    border-radius:16px;
    transition: all 0.3s ease;
    font-family: 'Sarabun', sans-serif !important;
}
.stButton > button.primary { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color:#fff !important; 
    border:none !important;
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}
.stButton > button.primary:hover { 
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
}
.stButton > button.secondary { 
    background:#f1f5f9 !important; 
    color:#475569 !important; 
    border:2px solid #e2e8f0 !important;
}
.stButton > button.secondary:hover { 
    background:#e2e8f0 !important;
    transform: translateY(-2px);
}

/* Beautiful result sheet */
.sheet { 
    border-radius:24px 24px 0 0;
    padding: 20px 18px 24px; 
    background: linear-gradient(to bottom, #ffffff 0%, #f8fafc 100%);
    box-shadow:0 -12px 40px rgba(0,0,0,.15);
    border:none;
    margin-top: 16px;
}

.result-card { 
    border-radius:20px; 
    padding:1.2rem 1.3rem; 
    border:none;
    box-shadow:0 4px 20px rgba(0,0,0,.08); 
    background:#fff;
    margin-bottom: 12px;
}

.result-header {
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom: 16px;
}

.result-title {
    font-weight:900;
    font-size:1.2rem;
    color:#1e293b;
}

.result-list { 
    margin:.6rem 0 0 1.2rem;
    line-height: 1.6;
}
.result-list li { 
    margin-bottom:.4rem;
    color: #475569;
}

/* Enhanced badges with icons */
.badge { 
    display:inline-flex;
    align-items: center;
    gap: 6px;
    padding:.45rem 1rem; 
    border-radius:999px; 
    color:#fff; 
    font-weight:800;
    font-size: 0.95rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.badge-ok { 
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}
.badge-no { 
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}
.badge-unsure { 
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

/* Info cards */
.info-card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin: 12px 0;
    border: 2px solid #e2e8f0;
}

.info-card h3 {
    font-size: 18px;
    font-weight: 800;
    color: #1e293b;
    margin: 0 0 8px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.info-card ul {
    margin: 8px 0 0 20px;
    line-height: 1.8;
}

.info-card li {
    color: #475569;
    margin-bottom: 4px;
}

/* Confidence meter */
.confidence-meter {
    background: #f1f5f9;
    border-radius: 12px;
    padding: 12px;
    margin: 12px 0;
}

.confidence-bar {
    height: 8px;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 4px;
    transition: width 0.5s ease;
}

/* Success/Warning/Error messages */
.stAlert {
    border-radius: 16px !important;
    border: none !important;
    font-weight: 600 !important;
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
                st.info("⏳ ระบบหนาแน่น กำลังลองใหม่...")
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
        "meta": {"rule_set_id": "default-v1"},
    }

# ----------------- Header -----------------
st.markdown('<div class="header"><h1>✂️ Hair Check</h1></div>', unsafe_allow_html=True)

# ----------------- Welcome Card -----------------
st.markdown("""
<div class="welcome-card">
    <h2>👋 ยินดีต้อนรับ!</h2>
    <p>ระบบตรวจสอบทรงผมนักเรียนอัตโนมัติ ใช้งานง่าย รวดเร็ว แม่นยำ</p>
</div>
""", unsafe_allow_html=True)

# ----------------- Rules Info -----------------
st.markdown("""
<div class="info-card">
    <h3>📋 กฎระเบียบทรงผม</h3>
    <ul>
        <li>รองทรงสูง ด้านข้างและด้านหลังสั้น</li>
        <li>ด้านบนยาวไม่เกิน 5 ซม.</li>
        <li>ห้ามย้อมสี ดัดผม หรือไว้หนวดเครา</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# ----------------- Camera -----------------
st.markdown('<div class="cam-box">', unsafe_allow_html=True)
photo = st.camera_input(" ")
st.markdown("""
<div class="overlay">
  <div class="corner tl"></div><div class="corner tr"></div>
  <div class="corner bl"></div><div class="corner br"></div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center;"><span class="hint">📸 จัดท่าถ่ายให้เห็นทรงผมชัดเจน แล้วกดปุ่มตรวจ</span></div>', unsafe_allow_html=True)

colA, colB = st.columns(2)
with colA:
    do_analyze = st.button("🔍 ตรวจทรงผม", type="primary")
with colB:
    clear = st.button("🔄 ถ่ายใหม่", type="secondary")

if clear:
    st.session_state.pop("result", None)
    st.rerun()

# ----------------- Analyze -----------------
if do_analyze:
    if not photo:
        st.warning("⚠️ กรุณาถ่ายภาพก่อนกดตรวจ")
    else:
        try:
            img = Image.open(photo).convert("RGB")
            mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
            
            prog = st.progress(0, text="⚙️ กำลังเตรียมภาพ...")
            data = compress(img, mime)
            prog.progress(35, text="📤 กำลังส่งไปตรวจ...")

            with st.spinner("🤖 AI กำลังวิเคราะห์..."):
                result = call_gemini(data, mime)
            
            prog.progress(100, text="✅ เสร็จสิ้น")
            st.success("🎉 ตรวจเสร็จแล้ว!")

            st.session_state["result"] = result
        except Exception as e:
            st.error(f"❌ ไม่สามารถวิเคราะห์ได้: {e}")

# ----------------- Result -----------------
res = st.session_state.get("result")
if res:
    verdict = res.get("verdict", "unsure")
    reasons = res.get("reasons", []) or []
    violations = res.get("violations", []) or []
    conf = res.get("confidence", 0.0)

    st.markdown('<div class="sheet">', unsafe_allow_html=True)
    
    # Main result card
    st.markdown(f"""
    <div class="result-card">
      <div class="result-header">
        <div class="result-title">🎯 ผลการตรวจ</div>
        <div>{badge(verdict)}</div>
      </div>
      
      <div class="confidence-meter">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-weight:600;color:#64748b;">ความมั่นใจของระบบ</span>
          <span style="font-weight:800;color:#667eea;">{conf:.0%}</span>
        </div>
        <div style="background:#e2e8f0;border-radius:4px;height:8px;overflow:hidden;">
          <div class="confidence-bar" style="width:{conf*100}%;"></div>
        </div>
      </div>
      
      <div style="margin-top:16px;">
        <div style="font-weight:800;margin-bottom:8px;color:#1e293b;font-size:1.05rem;">💭 เหตุผลการตัดสิน</div>
        <ul class="result-list">
          {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
        </ul>
      </div>
      
      {f'''
      <div style="margin-top:16px;padding-top:16px;border-top:2px solid #f1f5f9;">
        <div style="font-weight:800;margin-bottom:8px;color:#dc2626;font-size:1.05rem;">⚠️ ข้อที่ไม่ตรงระเบียบ</div>
        <ul class="result-list">
          {"".join(f"<li style='color:#dc2626;'>{esc(v.get('message',''))}</li>" for v in violations)}
        </ul>
      </div>
      ''' if violations else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Additional info card
    st.markdown("""
    <div class="info-card" style="margin-top:16px;">
        <h3>💡 คำแนะนำ</h3>
        <ul>
            <li>ผลการตรวจเป็นเพียงข้อมูลเบื้องต้น</li>
            <li>ควรให้ครูหรือผู้รับผิดชอบตรวจสอบอีกครั้ง</li>
            <li>หากผลไม่แม่นยำ ลองถ่ายภาพใหม่ในที่ที่มีแสงสว่างเพียงพอ</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
