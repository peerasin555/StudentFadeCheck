# app.py — Bottom nav switches tabs instantly (no page reload)
import os, io, json, html, time
from typing import Any, Dict, List, Optional
from PIL import Image, UnidentifiedImageError
import streamlit as st
from google import genai
from google.genai import errors

st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
:root{
  --bg:#f6f7fb; --card:#ffffff; --ink:#0f172a; --muted:#64748b; --br:#e5e7eb;
  --ok:#10b981; --no:#ef4444; --unsure:#f59e0b;
  --b1:#667eea; --b2:#764ba2; --active:#4f46e5;
}
html,body,[class*="css"]{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,system-ui;
  color:var(--ink); font-size:16px;}
div.block-container{max-width:720px; padding:1rem 1rem 5.5rem; background:var(--bg);}

/* Appbar */
.appbar{position:sticky; top:0; z-index:5; background:linear-gradient(135deg,var(--b1),var(--b2));
  padding:14px 16px; border-radius:16px; color:#fff; display:flex; align-items:center; gap:10px;
  box-shadow:0 6px 28px rgba(102,126,234,.25); margin-bottom:14px}
.appbar h1{font-size:20px; margin:0; font-weight:900; letter-spacing:.3px}

/* Cards */
.card{background:var(--card); border:1px solid var(--br); border-radius:16px; padding:14px; box-shadow:0 2px 12px rgba(0,0,0,.05);}
.meta{color:var(--muted); font-size:13px}

/* Bottom nav */
.navbar{position:fixed; left:0; right:0; bottom:0; background:#fff; border-top:1px solid var(--br);
  display:flex; justify-content:space-around; padding:8px 4px; z-index:10;}
.navbtn{background:none; border:none; display:flex; flex-direction:column; align-items:center; gap:2px;
  font-size:12px; color:#0f172a; cursor:pointer; border-radius:10px;}
.navbtn.active{color:var(--active); font-weight:900; background:rgba(79,70,229,.08);}
.navbtn svg{width:22px; height:22px;}
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
if "tab" not in st.session_state: st.session_state.tab = "Home"
if "rules_text" not in st.session_state:
    st.session_state.rules_text = "กฎระเบียบทรงผม (ชาย)\n1) รองทรงสูง ด้านข้าง/หลังสั้น\n2) ด้านบนยาวไม่เกิน 5 ซม.\n3) ห้ามย้อม/ดัด/ไว้หนวดเครา"
if "history" not in st.session_state: st.session_state.history = []

# ---------- Utils ----------
def goto(tab: str):
    st.session_state.tab = tab
    st.rerun()

def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)

def badge(verdict: str) -> str:
    m = {"compliant":("ผ่านระเบียบ","ok"), "non_compliant":("ไม่ผ่านระเบียบ","no"), "unsure":("ไม่แน่ใจ","unsure")}
    t, c = m.get(verdict, ("ไม่แน่ใจ","unsure"))
    return f'<span style="background:var(--{c});color:#fff;padding:4px 10px;border-radius:999px;font-weight:800">{t}</span>'

# ---------- Pages ----------
def page_home():
    st.markdown('<div class="card"><b>ตรวจทรงผมนักเรียน</b><div class="meta">เปิดกล้องและวิเคราะห์อัตโนมัติ</div></div>', unsafe_allow_html=True)
    if st.button("เริ่มตรวจ", use_container_width=True): goto("Check")
    st.markdown("")
    if st.button("เปิดดูประวัติ", use_container_width=True): goto("History")

def page_check():
    st.write("📷 **ถ่ายภาพทรงผมเพื่อวิเคราะห์**")
    photo = st.camera_input("ถ่ายภาพ")
    if photo:
        st.info("ระบบตัวอย่าง: จำลองผลลัพธ์")
        res = {"verdict":"compliant","confidence":0.95,"reasons":["รองทรงถูกต้อง"],"violations":[]}
        st.session_state.history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M"), "result": res})
        st.markdown(badge(res["verdict"]), unsafe_allow_html=True)
        st.write("ความมั่นใจ:", f"{res['confidence']*100:.1f}%")

def page_history():
    if not st.session_state.history:
        st.info("ยังไม่มีประวัติการตรวจ")
        return
    for h in st.session_state.history[:10]:
        st.markdown(f"<div class='card'><b>{h['time']}</b> {badge(h['result']['verdict'])}</div>", unsafe_allow_html=True)

def page_settings():
    st.markdown('<div class="card"><b>กฎระเบียบทรงผม</b></div>', unsafe_allow_html=True)
    st.text_area("แก้ไขข้อความกฎ", st.session_state.rules_text, key="rules_text")

# ---------- Router ----------
tab = st.session_state.tab
st.markdown(f'<div class="appbar"><h1>{tab}</h1></div>', unsafe_allow_html=True)

if tab == "Home": page_home()
elif tab == "Check": page_check()
elif tab == "History": page_history()
else: page_settings()

# ---------- Bottom Nav ----------
st.markdown('<div class="navbar">', unsafe_allow_html=True)
cols = st.columns(4)
tabs = [("Home","M3 9.5 12 3l9 6.5V21a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.5z"),
        ("Check","M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm0 2c-4.33 0-8 2.17-8 5v1h16v-1c0-2.83-3.67-5-8-5Z"),
        ("History","M3 5h18M3 12h18M3 19h18"),
        ("Settings","M12 15.5a3.5 3.5 0 1 0-3.5-3.5 ... 1.56Z")]
for i, (name, path) in enumerate(tabs):
    active = " active" if tab == name else ""
    with cols[i]:
        if st.button("", key=f"nav_{name}", help=name):
            goto(name)
        st.markdown(f"""
        <div class="navbtn{active}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="{path}" stroke-width="1.7"/></svg>
          {name}
        </div>
        """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
