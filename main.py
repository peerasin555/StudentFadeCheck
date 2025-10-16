import streamlit as st
import streamlit.components.v1 as components

# ตั้งค่าหน้า
st.set_page_config(page_title="Hair Check", page_icon="✂️", layout="wide")

# -------- CSS --------
st.markdown("""
<style>
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f9fafb;
  margin: 0;
}
.main {
  padding-bottom: 80px; /* space for bottom nav */
}

/* Bottom Navigation */
.nav {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px 0;
  z-index: 999;
}
.nav a {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  text-decoration: none;
  color: #334155;
  transition: color 0.2s ease;
}
.nav a.active {
  color: #4f46e5;
  font-weight: 700;
}
.nav a .icon svg {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}
</style>
""", unsafe_allow_html=True)

# -------- Router (จำลองระบบหลายหน้า) --------
query_params = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
tab = query_params.get("tab", ["Home"])[0]

def set_tab(tab_name: str):
    try:
        st.query_params.update({"tab": tab_name})
    except:
        st.experimental_set_query_params(tab=tab_name)
    st.rerun()

# -------- ส่วนเนื้อหาของแต่ละหน้า --------
def home_page():
    st.header("🏠 หน้าแรก")
    st.write("นี่คือหน้าหลักของแอปตรวจทรงผมนักเรียน")

def check_page():
    st.header("📸 ตรวจทรงผม")
    st.camera_input("ถ่ายภาพเพื่อตรวจสอบ")

def history_page():
    st.header("📜 ประวัติการตรวจ")
    st.write("ยังไม่มีข้อมูลการตรวจที่ผ่านมา")

def settings_page():
    st.header("⚙️ ตั้งค่า")
    st.text_area("กฎระเบียบทรงผม", "1) รองทรงสูง\n2) ด้านบนไม่เกิน 5 ซม.\n3) ห้ามย้อมหรือดัด")

# -------- เนื้อหาหลัก --------
if tab == "Home":
    home_page()
elif tab == "Check":
    check_page()
elif tab == "History":
    history_page()
elif tab == "Settings":
    settings_page()

# -------- Navigation bar (HTML + JS) --------
components.html(f"""
<div class="nav" id="nav">
  <a href="#" class="{ 'active' if tab=='Home' else '' }" data-tab="Home">
    <span class="icon">
      <svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 10v10h14V10"/></svg>
    </span>
    <span>Home</span>
  </a>
  <a href="#" class="{ 'active' if tab=='Check' else '' }" data-tab="Check">
    <span class="icon">
      <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 12h8M12 8v8"/></svg>
    </span>
    <span>Check</span>
  </a>
  <a href="#" class="{ 'active' if tab=='History' else '' }" data-tab="History">
    <span class="icon">
      <svg viewBox="0 0 24 24"><path d="M3 13a9 9 0 1 0 3-7.4l-3 3.4"/><path d="M3 3v6h6"/><path d="M12 7v5l3 3"/></svg>
    </span>
    <span>History</span>
  </a>
  <a href="#" class="{ 'active' if tab=='Settings' else '' }" data-tab="Settings">
    <span class="icon">
      <svg viewBox="0 0 24 24"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.03.03a2 2 0 1 1-2.83 2.83l-.03-.03A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .31 1.8 1.8 0 0 0-.9 1.56v.06a2 2 0 1 1-4 0v-.06A1.8 1.8 0 0 0 7 19.4a1.8 1.8 0 0 0-1.96-.36l-.03.03a2 2 0 1 1-2.83-2.83l.03-.03A1.8 1.8 0 0 0 4.6 15 1.8 1.8 0 0 0 4.29 14a1.8 1.8 0 0 0-1.56-.9H2.67a2 2 0 1 1 0-4h.06A1.8 1.8 0 0 0 4.29 8a1.8 1.8 0 0 0 .31-1 1.8 1.8 0 0 0-.36-1.96l-.03-.03A2 2 0 1 1 7.04 1.18l.03.03A1.8 1.8 0 0 0 8 4.6c.3 0 .68-.1 1-.31.3-.2.7-.29 1.06-.3h.06a2 2 0 1 1 4 0h.06c.36.01.76.1 1.06.3.32.21.7.31 1 .31A1.8 1.8 0 0 0 19.4 5l.03-.03a2 2 0 1 1 2.83 2.83L22.2 7.83A1.8 1.8 0 0 0 19.4 9c0 .3.1.68.31 1 .2.3.29.7.3 1.06v.06Z"/></svg>
    </span>
    <span>Settings</span>
  </a>
</div>

<script>
document.querySelectorAll('.nav a').forEach(el=>{
  el.addEventListener('click', e=>{
    e.preventDefault();
    const tab = el.getAttribute('data-tab');
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tab);
    window.history.replaceState(null, '', url.toString());
    window.location.reload();
  });
});
</script>
""", height=80)
