# app.py — Mobile-first HTML/CSS UI + Streamlit camera + Gemini backend + Icon bottom nav
import os, io, json, html, time
from typing import Any, Dict, List
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ---------- Page ----------
st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# ---------- CSS (HTML-first UI) ----------
st.markdown("""
<style>
:root{
  --bg:#f6f7fb; --card:#ffffff; --ink:#0f172a; --muted:#64748b; --br:#e5e7eb;
  --ok:#10b981; --no:#ef4444; --unsure:#f59e0b; --b1:#667eea; --b2:#764ba2;
}
html,body,[class*="css"]{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,system-ui;
  color:var(--ink); font-size:16px;}
div.block-container{max-width:720px; padding:1rem 1rem 5.5rem; background:var(--bg);}
a{color:inherit; text-decoration:none}

/* Top app bar */
.appbar{position:sticky; top:0; z-index:5; background:linear-gradient(135deg,var(--b1),var(--b2));
  padding:14px 16px; border-radius:16px; color:#fff; display:flex; align-items:center; gap:10px;
  box-shadow:0 6px 28px rgba(102,126,234,.25); margin-bottom:14px}
.appbar h1{font-size:20px; margin:0; font-weight:900; letter-spacing:.3px}

/* Big cards on Home */
.bigbtn{display:block; background:var(--card); border-radius:16px; padding:18px; border:1px solid var(--br);
  box-shadow:0 2px 12px rgba(0,0,0,.05); font-weight:800; text-align:left}
.bigbtn small{display:block; color:var(--muted); font-weight:600}

/* Cards / lists */
.card{background:var(--card); border:1px solid var(--br); border-radius:16px; padding:14px 14px; box-shadow:0 2px 12px rgba(0,0,0,.05);}
.row{display:flex; gap:12px; align-items:center}
.avatar{width:48px; height:48px; border-radius:12px; background:#e5e7eb}
.meta{color:var(--muted); font-size:13px}

/* Chips */
.chips{display:flex; gap:8px; flex-wrap:wrap}
.chip{padding:6px 10px; border-radius:999px; background:#eef2ff; color:#3730a3; font-weight:700; font-size:12px; border:1px solid #e0e7ff}

/* Camera (streamlit widget) */
[data-testid="stCameraInput"]{position:relative; display:inline-block; width:100%}
[data-testid="stCameraInput"] video, [data-testid="stCameraInput"] img{width:100%; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08)}

/* Overlay corners */
.overlay{pointer-events:none; position:relative; margin-top:-56px; height:0}
.corner{position:absolute; width:48px; height:48px; border:3px solid #fff; opacity:.95; border-radius:12px}
.tl{left:18px; top:-290px; border-right:none;border-bottom:none}
.tr{right:18px; top:-290px; border-left:none;border-bottom:none}
.bl{left:18px; top:-56px; border-right:none;border-top:none}
.br{right:18px; top:-56px; border-left:none;border-top:none}

/* Buttons */
.stButton > button{width:100%; padding:14px 16px; border-radius:14px; font-weight:800; box-shadow:0 2px 12px rgba(0,0,0,.08)}
.btn-primary{background:linear-gradient(135deg,var(--b1),var(--b2)) !important; color:#fff !important; border:none !important}
.btn-muted{background:#e5e7eb !important; color:#111827 !important; border:none !important}

/* Result card */
.badge{display:inline-flex;align-items:center;gap:8px; padding:6px 12px; border-radius:999px; color:#fff; font-weight:900}
.badge.ok{background:var(--ok)} .badge.no{background:var(--no)} .badge.unsure{background:var(--unsure)}
.result{background:var(--card); border:1px solid var(--br); border-radius:16px; padding:14px; box-shadow:0 2px 12px rgba(0,0,0,.05)}
.result h3{margin:.2rem 0 .3rem 0}

/* --- Bottom nav (icon only) --- */
.nav{
  position:fixed; left:0; right:0; bottom:0;
  background:#fff; border-top:1px solid var(--br);
  display:flex; justify-content:space-around; padding:10px 8px; z-index:10
}
.nav a{
  display:flex; flex-direction:column; align-items:center; gap:6px;
  font-size:11px; color:#0f172a; text-decoration:none
}
.nav a .icon{ width:24px; height:24px; display:block; }
.nav a .icon svg{ width:24px; height:24px; stroke:#0f172a; stroke-width:2; fill:none; }
.nav a.active .icon svg{ stroke:#4f46e5; }
.nav a.active{ color:#4f46e5; font-weight:900; }
</style>
""", unsafe_allow_html=True)

# ---------- Shared texts/rules ----------
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

# ---------- Utils ----------
def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)

def compress(img: Image.Image, mime: str) -> bytes:
    img = img.copy(); img.thumbnail((1024,1024))
    buf = io.BytesIO()
    if mime == "image/png": img.save(buf,"PNG",optimize=True)
    else: img.save(buf,"JPEG",quality=85, optimize=True)
    return buf.getvalue()

def badge_view(verdict: str) -> str:
    mapping = {"compliant":("ผ่านระเบียบ","ok"), "non_compliant":("ไม่ผ่านระเบียบ","no"), "unsure":("ไม่แน่ใจ","unsure")}
    label, cls = mapping.get(verdict, ("ไม่แน่ใจ","unsure"))
    return f'<span class="badge {cls}">● {label}</span>'

def parse_json_strict(text: str) -> Dict[str, Any]:
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[s:e+1])

# ---------- Gemini ----------
def call_gemini(image_bytes: bytes, mime: str, retries: int = 2) -> Dict[str, Any]:
    api_key = (getattr(st, "secrets", {}).get("GEMINI_API_KEY", None)
               if hasattr(st, "secrets") else None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"verdict":"unsure","reasons":["ยังไม่ได้ตั้งค่า GEMINI_API_KEY"],"violations":[],"confidence":0.0,"meta":{"rule_set_id":"default-v1"}}

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
            raw = (resp.text or "").strip()
            try:
                return parse_json_strict(raw)
            except Exception as pe:
                return {"verdict":"unsure","reasons":[f"ผลไม่ใช่ JSON ล้วน: {pe}", raw[:200]],"violations":[],
                        "confidence":0.0,"meta":{"rule_set_id":"default-v1"}}
        except errors.ServerError as e:
            last_err = e
            if "503" in str(e) and i < retries-1:
                st.info("🔄 ระบบหนาแน่น กำลังลองใหม่…"); time.sleep(2*(i+1)); continue
            break
        except Exception as e:
            last_err = e; break
    return {"verdict":"unsure","reasons":[f"เกิดข้อผิดพลาด: {last_err}"],"violations":[],"confidence":0.0,"meta":{"rule_set_id":"default-v1"}}

# ---------- Query param helpers (compatible with older Streamlit) ----------
def get_tab() -> str:
    try:
        qp = st.query_params
        return qp.get("tab", "Home")
    except Exception:
        q = st.experimental_get_query_params()
        return (q.get("tab", ["Home"]) or ["Home"])[0]

def set_tab(name: str):
    try:
        st.query_params.update({"tab": name})
    except Exception:
        st.experimental_set_query_params(tab=name)

tab = get_tab()

# ---------- AppBar ----------
st.markdown('<div class="appbar"><h1>Pet-style Hair Check</h1></div>', unsafe_allow_html=True)

# ---------- State ----------
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str,Any]] = []

# ---------- Pages ----------
def page_home():
    st.markdown('<a class="bigbtn" href="?tab=Check">🧑‍🎓 ตรวจทรงผมของนักเรียน<small>เปิดกล้องและวิเคราะห์อัตโนมัติ</small></a>', unsafe_allow_html=True)
    st.markdown("")
    st.markdown('<a class="bigbtn" href="?tab=History">🗂️ ดูประวัติการตรวจ<small>ผลล่าสุดและรายละเอียด</small></a>', unsafe_allow_html=True)

def page_check():
    st.text_input("ค้นหาสถานที่/ห้องเรียน (ตัวอย่าง UI เท่านั้น)", placeholder="เช่น อาคาร A ห้อง 201")
    st.markdown('<div class="chips">'+ ''.join(f'<span class="chip">{x}</span>' for x in ["แสงเพียงพอ","เห็นหู","ไม่ย้อนแสง","ถือให้มั่นคง"]) +'</div>', unsafe_allow_html=True)

    photo = st.camera_input("ถ่ายภาพทรงผม")
    st.markdown('<div class="overlay"><span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div>', unsafe_allow_html=True)

    if photo is None:
        st.info("ℹ️ หากกล้องไม่ขึ้น: ใช้ HTTPS หรือ localhost และอนุญาตสิทธิ์กล้องในเบราว์เซอร์")
        return

    img = Image.open(photo).convert("RGB")
    mime = photo.type if photo.type in ("image/png","image/jpeg") else "image/jpeg"
    st.image(img, caption="ภาพที่ถ่าย", use_container_width=True)

    data = compress(img, mime)
    if len(data) > 5*1024*1024:
        img2 = img.copy(); img2.thumbnail((800,800)); data = compress(img2, mime)

    with st.spinner("🤖 กำลังวิเคราะห์…"):
        res = call_gemini(data, mime)

    # เก็บประวัติ
    st.session_state.history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M"), "result": res})

    # แสดงผล
    v = res.get("verdict","unsure")
    reasons = res.get("reasons",[]) or []
    violations = res.get("violations",[]) or []
    conf = res.get("confidence",0.0)

    st.markdown('<div class="result">', unsafe_allow_html=True)
    st.markdown(f'<div class="row" style="justify-content:space-between;"><h3>ผลการตรวจ</h3>{badge_view(v)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta">ความมั่นใจ: <b>{conf:.1%}</b></div>', unsafe_allow_html=True)
    if reasons:
        st.markdown('<div style="margin:.6rem 0 .2rem;font-weight:800;">เหตุผล</div>', unsafe_allow_html=True)
        st.markdown('<ul>'+ ''.join(f'<li>{esc(x)}</li>' for x in reasons) +'</ul>', unsafe_allow_html=True)
    if violations:
        st.markdown('<div style="margin:.6rem 0 .2rem;font-weight:800;">จุดที่ไม่ตรงระเบียบ</div>', unsafe_allow_html=True)
        st.markdown('<ul>'+ ''.join(f'<li>{esc(v.get("message",""))}</li>' for v in violations) +'</ul>', unsafe_allow_html=True)
    st.download_button("⬇️ ดาวน์โหลดผลลัพธ์ (JSON)", data=json.dumps(res, ensure_ascii=False, indent=2),
                       file_name="haircheck_result.json", mime="application/json", use_container_width=True)
    st.button("↺ ลบและถ่ายใหม่", type="secondary", use_container_width=True, on_click=lambda: set_tab("Check"))

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
            {badge_view(v)}
          </div>
          <div class="meta" style="margin-top:6px;">ความมั่นใจ {conf:.1%}</div>
        </div>
        """, unsafe_allow_html=True)

def page_settings():
    st.markdown('<div class="card"><b>กฎระเบียบทรงผม</b><div class="meta">ปรับข้อความกฎตามสถานศึกษา</div></div>', unsafe_allow_html=True)
    st.text_area("RULES (ตัวอย่างค่าเริ่มต้น)", RULES, height=120, key="rules_text")
    st.caption("ใส่ GEMINI_API_KEY ใน Secrets หรือ environment เพื่อใช้งานจริง")

# ---------- Router ----------
if tab == "Home": page_home()
elif tab == "Check": page_check()
elif tab == "History": page_history()
else: page_settings()

# ---------- Bottom Nav (icon + in-place switching) ----------
def nav_bar(active: str):
    ICONS = {
        "Home": """
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 10.5 12 3l9 7.5" />
              <path d="M5 10v10h14V10" />
            </svg>
        """,
        "Check": """
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="3" width="18" height="18" rx="4" />
              <path d="M8 12h8M12 8v8" />
            </svg>
        """,
        "History": """
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 13a9 9 0 1 0 3-7.4l-3 3.4" />
              <path d="M3 3v6h6" />
              <path d="M12 7v5l3 3" />
            </svg>
        """,
        "Settings": """
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
              <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.03.03a2 2 0 1 1-2.83 2.83l-.03-.03A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .31 1.8 1.8 0 0 0-.9 1.56v.06a2 2 0 1 1-4 0v-.06A1.8 1.8 0 0 0 7 19.4a1.8 1.8 0 0 0-1.96-.36l-.03.03a2 2 0 1 1-2.83-2.83l.03-.03A1.8 1.8 0 0 0 4.6 15 1.8 1.8 0 0 0 4.29 14a1.8 1.8 0 0 0-1.56-.9H2.67a2 2 0 1 1 0-4h.06A1.8 1.8 0 0 0 4.29 8a1.8 1.8 0 0 0 .31-1 1.8 1.8 0 0 0-.36-1.96l-.03-.03A2 2 0 1 1 7.04 1.18l.03.03A1.8 1.8 0 0 0 8 4.6c.3 0 .68-.1 1-.31.3-.2.7-.29 1.06-.3h.06a2 2 0 1 1 4 0h.06c.36.01.76.1 1.06.3.32.21.7.31 1 .31A1.8 1.8 0 0 0 19.4 5l.03-.03a2 2 0 1 1 2.83 2.83L22.2 7.83A1.8 1.8 0 0 0 19.4 9c0 .3.1.68.31 1 .2.3.29.7.3 1.06v.06Z" />
            </svg>
        """,
    }
    def item(name: str) -> str:
        cls = "active" if active == name else ""
        return f'''
          <a href="#" class="{cls}" data-tab="{name}">
            <span class="icon">{ICONS[name]}</span>
            <span>{name}</span>
          </a>
        '''
    st.markdown(f"""
    <div class="nav" id="bottom-nav">
      {item("Home")}
      {item("Check")}
      {item("History")}
      {item("Settings")}
    </div>
    <script>
      (function() {{
        const nav = document.getElementById('bottom-nav');
        if (!nav) return;
        nav.querySelectorAll('a[data-tab]').forEach(a => {{
          a.addEventListener('click', (ev) => {{
            ev.preventDefault();
            const tab = a.getAttribute('data-tab');
            const url = new URL(window.location.href);
            url.searchParams.set('tab', tab);
            window.history.replaceState(null, '', url.toString());
            window.location.reload(); // สลับหน้าในแท็บเดิม
          }});
        }});
      }})();
    </script>
    """, unsafe_allow_html=True)

nav_bar(tab)
