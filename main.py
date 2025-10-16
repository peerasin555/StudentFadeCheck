# app.py — Hair Check • Pet-sit–style UI
import os, io, json, html, time
from typing import Any, Dict, List
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# -------------------- Page --------------------
st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# -------------------- Theme / CSS --------------------
st.markdown("""
<style>
:root{
  --bg:#f6f7fb; --card:#ffffff; --ink:#0f172a; --muted:#64748b;
  --ok:#10b981; --no:#ef4444; --unsure:#f59e0b; --brand1:#6b7cff; --brand2:#8b5cf6;
}
html,body,[class*="css"]{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,system-ui;
  color:var(--ink); font-size:16px;}
div.block-container{max-width:720px; padding:1rem 1rem 5.5rem; background:var(--bg);}
a{color:inherit; text-decoration:none}

/* Top app bar */
.appbar{position:sticky; top:0; z-index:5; background:linear-gradient(135deg,var(--brand1),var(--brand2));
  padding:14px 16px; border-radius:16px; color:#fff; display:flex; align-items:center; gap:10px;
  box-shadow:0 6px 28px rgba(139,92,246,.25); margin-bottom:14px}
.appbar h1{font-size:20px; margin:0; font-weight:900; letter-spacing:.3px}

/* Big CTA buttons (Home) */
.bigbtn{display:block; background:var(--card); border-radius:16px; padding:18px; border:1px solid #e5e7eb;
  box-shadow:0 2px 12px rgba(0,0,0,.05); font-weight:800; text-align:left}
.bigbtn small{display:block; color:var(--muted); font-weight:600}

/* Cards / lists */
.card{background:var(--card); border:1px solid #e5e7eb; border-radius:16px; padding:14px 14px; box-shadow:0 2px 12px rgba(0,0,0,.05);}
.row{display:flex; gap:12px; align-items:center}
.avatar{width:48px; height:48px; border-radius:12px; background:#e5e7eb}
.meta{color:var(--muted); font-size:13px}

/* Chips */
.chips{display:flex; gap:8px; flex-wrap:wrap}
.chip{padding:6px 10px; border-radius:999px; background:#eef2ff; color:#3730a3; font-weight:700; font-size:12px; border:1px solid #e0e7ff}

/* Camera */
[data-testid="stCameraInput"]{position:relative; display:inline-block; width:100%}
[data-testid="stCameraInput"] video, [data-testid="stCameraInput"] img{width:100%; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08)}
.overlay{pointer-events:none; position:relative; margin-top:-56px; height:0}
.corner{position:absolute; width:48px; height:48px; border:3px solid #fff; opacity:.95; border-radius:12px}
.tl{left:18px; top:-290px; border-right:none;border-bottom:none}
.tr{right:18px; top:-290px; border-left:none;border-bottom:none}
.bl{left:18px; top:-56px; border-right:none;border-top:none}
.br{right:18px; top:-56px; border-left:none;border-top:none}

/* Buttons */
.stButton > button{width:100%; padding:14px 16px; border-radius:14px; font-weight:800; box-shadow:0 2px 12px rgba(0,0,0,.08)}
.btn-primary{background:linear-gradient(135deg,var(--brand1),var(--brand2)) !important; color:#fff !important; border:none !important}
.btn-muted{background:#e5e7eb !important; color:#111827 !important; border:none !important}

/* Result card */
.badge{display:inline-flex;align-items:center;gap:8px; padding:6px 12px; border-radius:999px; color:#fff; font-weight:900}
.badge.ok{background:var(--ok)} .badge.no{background:var(--no)} .badge.unsure{background:var(--unsure)}
.result{background:var(--card); border:1px solid #e5e7eb; border-radius:16px; padding:14px; box-shadow:0 2px 12px rgba(0,0,0,.05)}
.result h3{margin:.2rem 0 .3rem 0}

/* Bottom nav */
.nav{position:fixed; left:0; right:0; bottom:0; background:#fff; border-top:1px solid #e5e7eb;
  display:flex; justify-content:space-around; padding:10px 8px; z-index:10}
.nav a{display:flex; flex-direction:column; align-items:center; gap:4px; font-size:12px; color:#0f172a}
.nav .active{color:#4f46e5; font-weight:900}
.nav .icon{font-size:18px}
</style>
""", unsafe_allow_html=True)

# -------------------- Shared texts / rules --------------------
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

# -------------------- Utils --------------------
def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)

def compress(img: Image.Image, mime: str) -> bytes:
    img = img.copy(); img.thumbnail((1024,1024))
    buf = io.BytesIO()
    if mime == "image/png": img.save(buf,"PNG",optimize=True)
    else: img.save(buf,"JPEG",quality=85, optimize=True)
    return buf.getvalue()

def badge(verdict: str) -> str:
    m = {"compliant":("ผ่านระเบียบ","ok"), "non_compliant":("ไม่ผ่านระเบียบ","no"), "unsure":("ไม่แน่ใจ","unsure")}
    label, cls = m.get(verdict, ("ไม่แน่ใจ","unsure"))
    return f'<span class="badge {cls}">● {label}</span>'

def parse_json_strict(text: str) -> Dict[str, Any]:
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[s:e+1])

# -------------------- Gemini --------------------
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
    last = None
    for i in range(retries):
        try:
            r = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role":"user","parts":[
                    {"text":prompt},
                    {"inline_data":{"mime_type":mime,"data":image_bytes}}
                ]}],
            )
            raw = (r.text or "").strip()
            try:
                return parse_json_strict(raw)
            except Exception as pe:
                return {"verdict":"unsure","reasons":[f"ผลไม่ใช่ JSON ล้วน: {pe}", raw[:200]],
                        "violations":[], "confidence":0.0, "meta":{"rule_set_id":"default-v1"}}
        except errors.ServerError as e:
            last = e
            if "503" in str(e) and i < retries-1:
                st.info("ระบบหนาแน่น กำลังลองใหม่…"); time.sleep(2*(i+1)); continue
            break
        except Exception as e:
            last = e; break
    return {"verdict":"unsure","reasons":[f"เกิดข้อผิดพลาด: {last}"],"violations":[],
            "confidence":0.0, "meta":{"rule_set_id":"default-v1"}}

# -------------------- Nav state --------------------
if "tab" not in st.session_state: st.session_state.tab = "Home"
if "history" not in st.session_state: st.session_state.history: List[Dict[str,Any]] = []
def nav_to(t): st.session_state.tab = t; st.rerun()

# -------------------- AppBar --------------------
st.markdown('<div class="appbar"><h1>Pet-style Hair Check</h1></div>', unsafe_allow_html=True)

# -------------------- Pages --------------------
def page_home():
    st.markdown('<a class="bigbtn" href="#" onclick="return false;">🧑‍🎓 ตรวจทรงผมของนักเรียน<small>เปิดกล้องและวิเคราะห์อัตโนมัติ</small></a>', unsafe_allow_html=True)
    st.markdown("")
    st.markdown('<a class="bigbtn" href="#" onclick="return false;">🗂️ ดูประวัติการตรวจ<small>ผลล่าสุดและรายละเอียด</small></a>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("เริ่มตรวจตอนนี้", key="cta1", use_container_width=True):
            nav_to("Check")
    with c2:
        if st.button("เปิดดูประวัติ", key="cta2", use_container_width=True):
            nav_to("History")

def page_check():
    st.text_input("ค้นหาสถานที่/ห้องเรียน (ตัวอย่างการวางตำแหน่ง UI)", placeholder="เช่น อาคาร A ห้อง 201")
    st.markdown('<div class="chips">'+
                ''.join([f'<span class="chip">{x}</span>' for x in ["แสงเพียงพอ","เห็นหู","ไม่ย้อนแสง","ถือให้มั่นคง"]])+
                '</div>', unsafe_allow_html=True)

    photo = st.camera_input("ถ่ายภาพทรงผม")
    st.markdown('<div class="overlay"><span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div>', unsafe_allow_html=True)

    if photo:
        img = Image.open(photo).convert("RGB")
        mime = photo.type if photo.type in ("image/png","image/jpeg") else "image/jpeg"
        st.image(img, caption="ภาพที่ถ่าย", use_container_width=True)

        data = compress(img, mime)
        if len(data) > 5*1024*1024:
            img2 = img.copy(); img2.thumbnail((800,800)); data = compress(img2, mime)

        with st.spinner("กำลังวิเคราะห์…"):
            res = call_gemini(data, mime)

        # Save history
        item = {"time": time.strftime("%Y-%m-%d %H:%M"), "result": res}
        st.session_state.history.insert(0, item)

        # Result card (detail)
        verdict = res.get("verdict","unsure")
        reasons = res.get("reasons",[]) or []
        violations = res.get("violations",[]) or []
        conf = res.get("confidence",0.0)

        st.markdown('<div class="result">', unsafe_allow_html=True)
        st.markdown(f'<div class="row" style="justify-content:space-between;"><h3>ผลการตรวจ</h3>{badge(verdict)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta">ความมั่นใจ: <b>{conf:.1%}</b></div>', unsafe_allow_html=True)
        if reasons:
            st.markdown('<div style="margin:.6rem 0 .2rem;font-weight:800;">เหตุผล</div>', unsafe_allow_html=True)
            st.markdown('<ul>'+''.join(f'<li>{esc(x)}</li>' for x in reasons) +'</ul>', unsafe_allow_html=True)
        if violations:
            st.markdown('<div style="margin:.6rem 0 .2rem;font-weight:800;">จุดที่ไม่ตรงระเบียบ</div>', unsafe_allow_html=True)
            st.markdown('<ul>'+''.join(f'<li>{esc(v.get("message",""))}</li>' for v in violations) +'</ul>', unsafe_allow_html=True)
        st.download_button("⬇️ ดาวน์โหลดผลลัพธ์ (JSON)", data=json.dumps(res,ensure_ascii=False,indent=2),
                           file_name="haircheck_result.json", mime="application/json", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def page_history():
    st.markdown('<div class="card"><div class="row"><div class="avatar"></div><div><b>Top rated</b><div class="meta">ผลที่เชื่อถือได้มากสุดล่าสุด</div></div></div></div>', unsafe_allow_html=True)
    st.write("")
    if not st.session_state.history:
        st.info("ยังไม่มีประวัติการตรวจ")
        return
    for i, h in enumerate(st.session_state.history[:12], start=1):
        r = h["result"]; v = r.get("verdict","unsure"); conf = r.get("confidence",0.0)
        st.markdown(f"""
        <div class="card" style="margin-bottom:10px;">
          <div class="row" style="justify-content:space-between;">
            <div><b>ผล #{i}</b><div class="meta">{esc(h['time'])}</div></div>
            {badge(v)}
          </div>
          <div class="meta" style="margin-top:6px;">ความมั่นใจ {conf:.1%}</div>
        </div>
        """, unsafe_allow_html=True)

def page_settings():
    st.markdown('<div class="card"><b>กฎระเบียบทรงผม</b><div class="meta">ปรับข้อความกฎตามสถานศึกษา</div></div>', unsafe_allow_html=True)
    rules = st.text_area("RULES", RULES, height=120)
    st.caption("ระบบจะใช้กฎนี้ในการประเมินผลครั้งถัดไป (หน้านี้เป็นตัวอย่าง UI แบบการตั้งค่า)")
    st.info("สำหรับการใช้งานจริง: ใส่ GEMINI_API_KEY ใน Secrets หรือ environment variable ชื่อเดียวกัน")

# -------------------- Router --------------------
tab = st.session_state.tab
if tab == "Home": page_home()
elif tab == "Check": page_check()
elif tab == "History": page_history()
else: page_settings()

# -------------------- Bottom Nav --------------------
def nav_item(name, icon, target):
    active = "active" if tab == target else ""
    return f'<a class="{active}" href="#" onclick="return false;"><span class="icon">{icon}</span>{name}</a>'

st.markdown(f"""
<div class="nav">
  {nav_item("Home","🏠","Home")}
  {nav_item("Check","🐾","Check")}
  {nav_item("History","🗂️","History")}
  {nav_item("Settings","⚙️","Settings")}
</div>
<script>
const labels = Array.from(window.parent.document.querySelectorAll('div.nav a'));
labels.forEach((el, i) => el.addEventListener('click', () => {{
  const py = [{repr("Home")},{repr("Check")},{repr("History")},{repr("Settings")}][i];
  fetch(window.location.href, {{method:'POST', headers:{{'X-Requested-With':'XMLHttpRequest'}}, body:py}});
}}));
</script>
""", unsafe_allow_html=True)

# Soft router via empty forms (no page reload hard links)
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button(" ", key="nav_home"): st.session_state.tab="Home"; st.experimental_rerun()
with c2:
    if st.button(" ", key="nav_check"): st.session_state.tab="Check"; st.experimental_rerun()
with c3:
    if st.button(" ", key="nav_hist"): st.session_state.tab="History"; st.experimental_rerun()
with c4:
    if st.button(" ", key="nav_settings"): st.session_state.tab="Settings"; st.experimental_rerun()
