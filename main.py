import os, io, json, html, time
from typing import Any, Dict, List
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
:root{
  --bg:#f6f7fb; --card:#fff; --ink:#0f172a; --muted:#64748b; --br:#e5e7eb;
  --ok:#10b981; --no:#ef4444; --unsure:#f59e0b;
  --b1:#667eea; --b2:#764ba2; --active:#4f46e5;
}
html,body,[class*="css"]{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,system-ui;
  color:var(--ink); font-size:16px;
}
div.block-container{max-width:720px;padding:1rem 1rem 5.5rem;background:var(--bg);}
a{color:inherit;text-decoration:none}

/* Top bar */
.appbar{position:sticky;top:0;z-index:5;background:linear-gradient(135deg,var(--b1),var(--b2));
  padding:14px 16px;border-radius:16px;color:#fff;display:flex;align-items:center;gap:10px;
  box-shadow:0 6px 28px rgba(102,126,234,.25);margin-bottom:14px}
.appbar h1{font-size:20px;margin:0;font-weight:900;letter-spacing:.3px}

/* Card & Result */
.card,.result{background:var(--card);border:1px solid var(--br);border-radius:16px;
  box-shadow:0 2px 12px rgba(0,0,0,.05);padding:14px;margin-bottom:10px;}
.badge{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;
  color:#fff;font-weight:900;font-size:13px;}
.badge.ok{background:var(--ok)}.badge.no{background:var(--no)}.badge.unsure{background:var(--unsure)}
.nav{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--br);
  display:flex;justify-content:space-around;padding:8px 4px;z-index:10}
.nav button{background:none;border:none;padding:6px 10px;display:flex;flex-direction:column;
  align-items:center;gap:2px;color:#0f172a;font-size:12px;cursor:pointer;border-radius:10px;}
.nav button.active{color:var(--active);font-weight:900;background:rgba(79,70,229,.08);}
.nav svg{width:22px;height:22px;display:block}
form[data-testid="stForm"] button{
  display:none !important;
  visibility:hidden !important;
  height:0 !important;
  width:0 !important;
  padding:0 !important;
  margin:0 !important;
  border:none !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Shared content ----------
RULES = (
    "กฎระเบียบทรงผม (ชาย)\n"
    "1) รองทรงสูง ด้านข้าง/ด้านหลังสั้น\n"
    "2) ด้านบนยาวไม่เกิน 5 ซม.\n"
    "3) ห้ามย้อม/ดัด/ไว้หนวดเครา\n"
)
SCHEMA_HINT = (
    '{"verdict":"compliant | non_compliant | unsure","reasons":["string"],'
    '"violations":[{"code":"STRING","message":"STRING"}],"confidence":0.0,'
    '"meta":{"rule_set_id":"default-v1","timestamp":"AUTO"}}'
)

def esc(x): return html.escape(str(x), quote=True)
def badge_view(v):
    mp={"compliant":("ผ่านระเบียบ","ok"),"non_compliant":("ไม่ผ่านระเบียบ","no"),"unsure":("ไม่แน่ใจ","unsure")}
    t,c=mp.get(v,("ไม่แน่ใจ","unsure"))
    return f'<span class="badge {c}">● {t}</span>'

# ---------- Gemini ----------
def call_gemini(image_bytes: bytes, mime: str):
    api_key = (getattr(st,"secrets",{}).get("GEMINI_API_KEY") if hasattr(st,"secrets") else None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"verdict":"unsure","reasons":["ยังไม่ได้ตั้งค่า GEMINI_API_KEY"],"violations":[],"confidence":0.0}
    client = genai.Client(api_key=api_key)
    prompt = f"คุณเป็นผู้ช่วยตรวจทรงผม ตอบเป็น JSON เท่านั้น\n\n{RULES}\n{SCHEMA_HINT}"
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role":"user","parts":[{"text":prompt},{"inline_data":{"mime_type":mime,"data":image_bytes}}]}],
        )
        txt=(resp.text or "").strip()
        s,e=txt.find("{"),txt.rfind("}")
        return json.loads(txt[s:e+1])
    except Exception as e:
        return {"verdict":"unsure","reasons":[str(e)],"violations":[],"confidence":0.0}

# ---------- State ----------
if "tab" not in st.session_state: st.session_state.tab="Home"
if "history" not in st.session_state: st.session_state.history=[]

# ---------- Pages ----------
def page_home():
    st.markdown('<div class="card"><b>เริ่มต้น</b><br>ตรวจทรงผมของนักเรียนโดยใช้กล้องมือถือ</div>', unsafe_allow_html=True)
    if st.button("เริ่มตรวจ", use_container_width=True):
        st.session_state.tab="Check"; st.rerun()

def page_check():
    st.caption("ถ่ายภาพให้เห็นทรงผมชัดเจน / แสงเพียงพอ")
    photo=st.camera_input("ถ่ายภาพ")
    if not photo: return
    img=Image.open(photo).convert("RGB")
    mime=photo.type if photo.type in ("image/png","image/jpeg") else "image/jpeg"
    buf=io.BytesIO(); img.save(buf,"JPEG",quality=85)
    res=call_gemini(buf.getvalue(),mime)
    st.session_state.history.insert(0,{"time":time.strftime("%Y-%m-%d %H:%M"),"result":res})
    st.image(img,use_container_width=True)
    st.markdown(f"<div class='result'><b>ผลการตรวจ:</b> {badge_view(res.get('verdict'))}<br>"
                f"ความมั่นใจ: {res.get('confidence',0):.1%}<br>"
                f"{'<br>'.join(esc(x) for x in res.get('reasons',[]))}</div>",unsafe_allow_html=True)

def page_history():
    if not st.session_state.history:
        st.info("ยังไม่มีประวัติการตรวจ")
        return
    for i,h in enumerate(st.session_state.history[:10],1):
        r=h["result"]
        st.markdown(f"<div class='card'><b>#{i}</b> {badge_view(r.get('verdict'))}<br>"
                    f"เวลา: {h['time']}<br>ความมั่นใจ: {r.get('confidence',0):.1%}</div>",unsafe_allow_html=True)

def page_settings():
    st.text_area("แก้ไขกฎระเบียบ", RULES, height=120, key="rules_text")
    st.caption("เพิ่ม GEMINI_API_KEY ใน Secrets ก่อนใช้งานจริง")

# ---------- Router ----------
tab=st.session_state.tab
if tab=="Home": page_home()
elif tab=="Check": page_check()
elif tab=="History": page_history()
else: page_settings()

# ---------- Bottom Nav ----------
st.markdown(f"""
<div class="nav" id="navbar">
  <button id="nav-home" class="{ 'active' if tab=='Home' else '' }">
    <svg viewBox="0 0 24 24"><path d="M3 9.5 12 3l9 6.5V21a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.5z" stroke="currentColor" stroke-width="1.7" fill="none"/></svg>
    Home
  </button>
  <button id="nav-check" class="{ 'active' if tab=='Check' else '' }">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="5" stroke="currentColor" stroke-width="1.7" fill="none"/><path d="M4 21c0-3 4-5 8-5s8 2 8 5" stroke="currentColor" stroke-width="1.7"/></svg>
    Check
  </button>
  <button id="nav-history" class="{ 'active' if tab=='History' else '' }">
    <svg viewBox="0 0 24 24"><path d="M3 5h18M3 12h18M3 19h18" stroke="currentColor" stroke-width="1.7" fill="none"/></svg>
    History
  </button>
  <button id="nav-settings" class="{ 'active' if tab=='Settings' else '' }">
    <svg viewBox="0 0 24 24"><path d="M12 15.5a3.5 3.5 0 1 0-3.5-3.5 3.5 3.5 0 0 0 3.5 3.5Z" stroke="currentColor" stroke-width="1.5" fill="none"/><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>
    Settings
  </button>
</div>
<div id="nav-form-anchor"></div>
""", unsafe_allow_html=True)

# hidden buttons (keys unique)
with st.form("nav_form_final", clear_on_submit=False):
    c1,c2,c3,c4=st.columns(4)
    go_home=c1.form_submit_button("", key="nav_home_btn")
    go_chk=c2.form_submit_button("", key="nav_chk_btn")
    go_his=c3.form_submit_button("", key="nav_his_btn")
    go_set=c4.form_submit_button("", key="nav_set_btn")

st.markdown("""
<script>
function linkNav(){
  const ids=["nav-home","nav-check","nav-history","nav-settings"];
  const form=document.querySelector('form[data-testid="stForm"]');
  if(!form) return;
  const btns=form.querySelectorAll('button');
  ids.forEach((id,i)=>{
    const el=document.getElementById(id);
    if(!el) return;
    el.addEventListener('click', e=>{
      e.preventDefault();
      if(btns[i]) btns[i].click();
    });
  });
}
setTimeout(linkNav,500);
</script>
""", unsafe_allow_html=True)

# handle clicks
if go_home: st.session_state.tab="Home"; st.rerun()
if go_chk:  st.session_state.tab="Check"; st.rerun()
if go_his:  st.session_state.tab="History"; st.rerun()
if go_set:  st.session_state.tab="Settings"; st.rerun()
