# app.py  — Lens-like, minimal & mobile-first
import os, io, json, html, time
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# ========= CSS: Google Lens–like =========
st.markdown("""
<style>
/* Base */
html, body, [class*="css"] { font-size: 18px; }
div.block-container { padding: 0; }

/* Top bar */
.topbar { position: sticky; top:0; z-index:5; backdrop-filter: blur(6px);
  display:flex; align-items:center; justify-content:center; height:54px;
  border-bottom: 1px solid rgba(0,0,0,.06); }
.brand { font-weight:800; font-size: 20px; letter-spacing:.2px; }

/* Camera wrap */
.cam-wrap { position: relative; padding: 0 0 72px 0; } /* leave space for shutter */
.cam-inner { position: relative; }
.cam-inner [data-testid="stCameraInputLabel"] { display:none; }
.cam-inner [data-testid="stCameraInput"] video,
.cam-inner [data-testid="stCameraInput"] img { border-radius: 18px; }

/* Overlay: 4 corner arcs */
.overlay { pointer-events: none; position:absolute; inset: 12px; border-radius: 18px; }
.corner { position:absolute; width: 64px; height: 64px; border-radius: 14px; border: 3px solid #fff; opacity:.92; }
.corner.tl { left:0; top:0; border-right:none; border-bottom:none; }
.corner.tr { right:0; top:0; border-left:none; border-bottom:none; }
.corner.bl { left:0; bottom:0; border-right:none; border-top:none; }
.corner.br { right:0; bottom:0; border-left:none; border-top:none; }

/* Hint pill */
.hint { position:absolute; left:50%; transform: translateX(-50%);
  bottom: 94px; background: rgba(30,41,59,.88); color:#fff; padding: 10px 16px;
  border-radius: 999px; font-weight:700; font-size: 15px; box-shadow:0 4px 16px rgba(0,0,0,.25);
}

/* Shutter area */
.shutter-bar { position: fixed; left:0; right:0; bottom: 12px; z-index: 10;
  display:flex; align-items:center; justify-content:center; gap:16px; }
button.shutter { width: 74px; height: 74px; border-radius: 999px; border: 6px solid #fff !important;
  background: #0ea5e9 !important; color:#fff !important; font-size: 0; box-shadow:0 6px 18px rgba(14,165,233,.45); }
button.shutter:hover { background:#0284c7 !important; }

/* Result sheet */
.sheet { position: sticky; bottom:0; background:#fff; border-top-left-radius:18px; border-top-right-radius:18px;
  padding: 14px 16px 20px; box-shadow: 0 -10px 30px rgba(0,0,0,.12); border-top:1px solid rgba(0,0,0,.06); }
.result-card, .sheet * { color:#0f172a !important; }
.badge { display:inline-block; padding:.35rem .9rem; border-radius:999px; color:#fff; font-weight:800; }
.badge-ok{background:#22c55e;} .badge-no{background:#ef4444;} .badge-unsure{background:#f59e0b;}
.result-list { margin:.4rem 0 0 1.1rem; }
</style>
""", unsafe_allow_html=True)

# ========= constants (rules kept internal, no UI editor) =========
RULES = """กฎระเบียบทรงผม (ชาย)
1) รองทรงสูง ด้านข้าง/ด้านหลังสั้น
2) ด้านบนยาวไม่เกิน 5 ซม.
3) ห้ามย้อม/ดัด/ไว้หนวดเครา
"""
SCHEMA_HINT = """จงตอบเป็น JSON เท่านั้น ตามสคีมา:
{"verdict":"compliant | non_compliant | unsure","reasons":["string"],
"violations":[{"code":"STRING","message":"STRING"}],"confidence":0.0,
"meta":{"rule_set_id":"default-v1","timestamp":"AUTO"}}"""

# ========= helpers =========
def esc(x): return html.escape(str(x), quote=True)

def badge(verdict:str)->str:
    m={"compliant":("ผ่านระเบียบ","badge-ok"),
       "non_compliant":("ไม่ผ่านระเบียบ","badge-no"),
       "unsure":("ไม่แน่ใจ","badge-unsure")}
    label, cls = m.get(verdict, ("ไม่แน่ใจ","badge-unsure"))
    return f'<span class="badge {cls}">{label}</span>'

def compress(img: Image.Image, mime: str)->bytes:
    img=img.copy(); img.thumbnail((1024,1024))
    buf=io.BytesIO()
    if mime=="image/png": img.save(buf,"PNG",optimize=True)
    else: img.save(buf,"JPEG",quality=85,optimize=True)
    return buf.getvalue()

def call_gemini(image_bytes:bytes, mime:str, retries:int=2):
    api_key = (st.secrets.get("GEMINI_API_KEY") if hasattr(st,"secrets") else None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set (Secrets/Env).")
    client = genai.Client(api_key=api_key)
    prompt = f"""SYSTEM:
คุณเป็นผู้ช่วยตรวจทรงผมนักเรียน ให้ตอบเป็น JSON เท่านั้น
USER (ไทย):
ตรวจรูปนี้ตามกฎ:
{RULES}

{SCHEMA_HINT}
- ถ้ารูปไม่ชัด ให้ verdict="unsure" พร้อมเหตุผล"""
    last=None
    for i in range(retries):
        try:
            r=client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role":"user","parts":[
                    {"text":prompt},
                    {"inline_data":{"mime_type":mime,"data":image_bytes}}
                ]}]
            )
            t=(r.text or "").strip(); s,e=t.find("{"), t.rfind("}")
            return json.loads(t[s:e+1])
        except errors.ServerError as e:
            last=e
            if "503" in str(e) and i<retries-1:
                st.toast("ระบบหนาแน่น กำลังลองใหม่…", icon="⏳"); time.sleep(2*(i+1)); continue
            break
        except Exception as e:
            last=e; break
    return {"verdict":"unsure","reasons":[f"ผิดพลาด: {last}"],"violations":[],"confidence":0.0,"meta":{"rule_set_id":"default-v1"}}

# ========= state =========
if "result" not in st.session_state: st.session_state.result=None

# ========= UI =========
st.markdown('<div class="topbar"><div class="brand">Hair Check</div></div>', unsafe_allow_html=True)

# Camera block (Lens-like)
st.markdown('<div class="cam-wrap">', unsafe_allow_html=True)
cam_col = st.container()
with cam_col:
    st.markdown('<div class="cam-inner">', unsafe_allow_html=True)
    photo = st.camera_input(" ", key="cam")  # label hidden via CSS
    st.markdown("""
    <div class="overlay">
      <div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <div class="hint">แตะปุ่มชัตเตอร์เพื่อ “ตรวจ”</div>
    </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Shutter (analyze) button
cols = st.columns([1,1,1])
with cols[1]:
    fire = st.button(" ", key="shutter", type="primary", help="ตรวจ", use_container_width=False)
    st.markdown("<script></script>", unsafe_allow_html=True)
    # apply shutter style
    st.markdown("""
        <style>
        div.stButton > button[kind="secondary"]{display:none;}
        </style>
    """, unsafe_allow_html=True)
    # attach shutter class
    st.markdown("""
        <script>
        const btns = parent.document.querySelectorAll('button');
        [...btns].forEach(b=>{ if(b.innerText===''){ b.classList.add('shutter'); }});
        </script>
    """, unsafe_allow_html=True)

# Run analyze when: have photo AND user taps shutter
if photo and fire:
    try:
        img = Image.open(photo).convert("RGB")
        mime = photo.type if photo.type in ("image/png","image/jpeg") else "image/jpeg"
        b = compress(img, mime)
        with st.spinner("กำลังตรวจ…"):
            st.session_state.result = call_gemini(b, mime)
        st.toast("เสร็จแล้ว", icon="✅")
    except Exception as e:
        st.error(f"วิเคราะห์ไม่ได้: {e}")

# Result sheet (slides up feel)
if st.session_state.result:
    r=st.session_state.result
    verdict=r.get("verdict","unsure"); reasons=r.get("reasons",[]) or []
    violations=r.get("violations",[]) or []; conf=r.get("confidence",0.0)

    st.markdown('<div class="sheet">', unsafe_allow_html=True)
    st.markdown(f"""
      <div class="result-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div style="font-weight:900;font-size:1.08rem;">ผลการตรวจ</div>
          <div>{badge(verdict)}</div>
        </div>
        <div style="margin-top:6px;opacity:.8;">ความมั่นใจ: <b>{conf:.2f}</b></div>
        <hr style="opacity:.12;margin:12px 0;">
        <div style="font-weight:800;margin-bottom:6px;">เหตุผล</div>
        <ul class="result-list">
          {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
        </ul>
        {"<div style='font-weight:800;margin-top:10px;'>ข้อที่ไม่ตรงระเบียบ</div><ul class='result-list'>" + ''.join(f"<li>{esc(v.get('message',''))}</li>" for v in violations) + "</ul>" if violations else ""}
      </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
