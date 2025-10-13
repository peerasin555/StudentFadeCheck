# app.py  — Stable, no-JS, mobile-first
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
html, body, [class*="css"] { font-size: 18px; }
div.block-container { padding: 0.4rem 0.6rem 2rem; }

/* Title bar */
.header { display:flex; justify-content:center; align-items:center; height:56px; }
.header h1 { font-size:20px; margin:0; letter-spacing:.2px; }

/* Camera container */
.cam-box { position: relative; margin-bottom: 12px; }
.cam-box [data-testid="stCameraInputLabel"] { display:none; }
.cam-box [data-testid="stCameraInput"] video,
.cam-box [data-testid="stCameraInput"] img { border-radius: 18px; }

/* 4 corner arcs */
.overlay { pointer-events:none; position:absolute; inset:10px; border-radius: 18px; }
.corner { position:absolute; width:64px; height:64px; border:3px solid #fff; opacity:.92; border-radius:14px; }
.corner.tl{left:0;top:0;border-bottom:none;border-right:none}
.corner.tr{right:0;top:0;border-bottom:none;border-left:none}
.corner.bl{left:0;bottom:0;border-top:none;border-right:none}
.corner.br{right:0;bottom:0;border-top:none;border-left:none}

/* Hint pill */
.hint { text-align:center; margin:10px 0 6px;
  background: rgba(30,41,59,.88); color:#fff; padding:10px 16px;
  border-radius:999px; display:inline-block; }

/* Primary/secondary buttons */
.stButton > button { width:100%; padding:1.0rem 1.1rem; font-size:1.12rem; font-weight:700; border-radius:14px; }
.stButton > button.primary { background:#2563eb !important; color:#fff !important; border:none !important; }
.stButton > button.primary:hover { background:#1e40af !important; }
.stButton > button.secondary { background:#e2e8f0 !important; color:#0f172a !important; border:none !important; }
.stButton > button.secondary:hover { background:#cbd5e1 !important; }

/* Result sheet */
.sheet { border-top-left-radius:18px; border-top-right-radius:18px;
  padding: 14px 16px 20px; background:#fff; box-shadow:0 -10px 30px rgba(0,0,0,.12);
  border:1px solid rgba(0,0,0,.06); }
.result-card, .sheet * { color:#0f172a !important; }
.result-card { border-radius:16px; padding:1rem 1.1rem; border:1px solid rgba(0,0,0,.08);
  box-shadow:0 2px 10px rgba(0,0,0,.06); background:#fff; }
.result-list { margin:.4rem 0 0 1.1rem; }
.result-list li { margin-bottom:.2rem; }

/* Badge */
.badge { display:inline-block; padding:.35rem .9rem; border-radius:999px; color:#fff; font-weight:800; }
.badge-ok { background:#22c55e; }
.badge-no { background:#ef4444; }
.badge-unsure { background:#f59e0b; }
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
        "compliant": ("ผ่านระเบียบ", "badge-ok"),
        "non_compliant": ("ไม่ผ่านระเบียบ", "badge-no"),
        "unsure": ("ไม่แน่ใจ", "badge-unsure"),
    }
    label, cls = m.get(verdict, ("ไม่แน่ใจ", "badge-unsure"))
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
                st.info("ระบบหนาแน่น (503) กำลังลองใหม่…")
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
st.markdown('<div class="header"><h1>Hair Check</h1></div>', unsafe_allow_html=True)

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

st.markdown('<div style="text-align:center;"><span class="hint">แตะ “ตรวจ” เพื่อประเมินทรงผม</span></div>', unsafe_allow_html=True)

colA, colB = st.columns(2)
with colA:
    do_analyze = st.button("🔎 ตรวจ", type="primary")
with colB:
    clear = st.button("↺ ถ่ายใหม่", type="secondary")

if clear:
    st.experimental_rerun()

# ----------------- Analyze -----------------
if do_analyze:
    if not photo:
        st.warning("กรุณาถ่ายภาพก่อนกด “ตรวจ”")
    else:
        try:
            img = Image.open(photo).convert("RGB")
            mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
            st.image(img, caption="ภาพที่ถ่าย", use_container_width=True)

            prog = st.progress(0, text="กำลังเตรียมภาพ…")
            data = compress(img, mime); prog.progress(35, text="กำลังส่งไปตรวจ…")

            with st.spinner("ระบบกำลังตรวจ…"):
                result = call_gemini(data, mime)
            prog.progress(100, text="เสร็จสิ้น")
            st.success("ตรวจเสร็จแล้ว")

            st.session_state["result"] = result
        except Exception as e:
            st.error(f"ไม่สามารถวิเคราะห์ได้: {e}")

# ----------------- Result -----------------
res = st.session_state.get("result")
if res:
    verdict = res.get("verdict", "unsure")
    reasons = res.get("reasons", []) or []
    violations = res.get("violations", []) or []
    conf = res.get("confidence", 0.0)

    st.markdown('<div class="sheet">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="result-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-weight:900;font-size:1.06rem;">ผลการตรวจ</div>
        <div>{badge(verdict)}</div>
      </div>
      <div style="margin-top:6px;opacity:.8;">ความมั่นใจของระบบ: <b>{conf:.2f}</b></div>
      <hr style="opacity:.12;margin:12px 0;">
      <div style="font-weight:800;margin-bottom:6px;">เหตุผลสรุป</div>
      <ul class="result-list">
        {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
      </ul>
      {"<div style='font-weight:800;margin-top:10px;'>ข้อที่ไม่ตรงระเบียบ</div><ul class=\"result-list\">" + ''.join(f"<li>{esc(v.get('message',''))}</li>" for v in violations) + "</ul>" if violations else ""}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
