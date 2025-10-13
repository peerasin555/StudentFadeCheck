# app.py
import os, io, json, html, time
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ===================== ตั้งค่าพื้นฐาน & ธีมมือถือ =====================
st.set_page_config(page_title="ตรวจทรงผมนักเรียน", page_icon="✂️", layout="wide")

MOBILE_CSS = """
<style>
/* ฐานฟอนต์และระยะห่างสำหรับมือถือ */
html, body, [class*="css"]  { font-size: 18px; }
div.block-container { padding-top: 0.6rem; padding-bottom: 2.4rem; }

/* กล่องคำแนะนำด้านบน */
.hint-bar {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.8rem 1rem;
  margin-bottom: 0.8rem;
  color: #0f172a;
}

/* ปุ่มหลัก */
.stButton > button {
  width: 100%;
  padding: 0.95rem 1.1rem;
  font-size: 1.12rem;
  font-weight: 700;
  border-radius: 14px;
}
.btn-primary { background: #2563eb !important; color:#fff !important; border: none !important; }
.btn-secondary { background: #e2e8f0 !important; color:#0f172a !important; border: none !important; }

/* การ์ดผลลัพธ์ */
.result-card {
  border-radius: 16px;
  padding: 1rem 1.1rem;
  margin-top: 0.6rem;
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  background: #fff;
}
.badge {
  display:inline-block;
  padding: 0.2rem 0.66rem;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.98rem;
  color: #fff;
}
.badge-ok { background: #16a34a; }       /* ผ่าน */
.badge-no { background: #dc2626; }       /* ไม่ผ่าน */
.badge-unsure { background: #f59e0b; }   /* ไม่แน่ใจ */

/* กล้อง/label ให้ชัด */
[data-testid="stCameraInputLabel"] { font-size: 1.05rem; }

/* ช่องกรอก/textarea ใหญ่พอสำหรับนิ้ว */
textarea, input, .stTextInput input { font-size: 1rem !important; }

/* กลุ่มปุ่มแนวนอน */
.btn-row { display:flex; gap:12px; }
.btn-row > div { flex:1; }

/* รายการเหตุผล */
.result-list { margin: 0.4rem 0 0 1rem; }
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ===================== ค่าเริ่มต้น + ข้อความ =====================
DEFAULT_RULES = """\
กฎระเบียบทรงผม (ชาย)
1) รองทรงสูง ด้านข้าง/ด้านหลังสั้น
2) ด้านบนยาวไม่เกิน 5 ซม.
3) ห้ามย้อม/ดัด/ไว้หนวดเครา
"""

SCHEMA_HINT = """\
จงตอบเป็น JSON เท่านั้น ตามสคีมา:
{
  "verdict": "compliant | non_compliant | unsure",
  "reasons": ["string"],
  "violations": [{"code":"STRING","message":"STRING"}],
  "confidence": 0.0,
  "meta": {"student_id":"STRING","rule_set_id":"default-v1","timestamp":"AUTO"}
}
"""

# ===================== Utilities =====================
def esc(s: object) -> str:
    return html.escape(str(s), quote=True)

def verdict_badge(verdict: str) -> str:
    mp = {
        "compliant": ("ผ่านระเบียบ", "badge-ok"),
        "non_compliant": ("ไม่ผ่านระเบียบ", "badge-no"),
        "unsure": ("ไม่แน่ใจ", "badge-unsure"),
    }
    label, css = mp.get(verdict, ("ไม่แน่ใจ", "badge-unsure"))
    return f'<span class="badge {css}">{label}</span>'

def compress_image(img: Image.Image, mime: str) -> bytes:
    """ลดขนาดภาพให้เร็วขึ้นและประหยัดเน็ต โดยคงชนิดไฟล์สอดคล้องกับ MIME"""
    img = img.copy()
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    if mime == "image/png":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()

# ===================== เรียก Gemini (พร้อม retry เบื้องต้น) =====================
def call_gemini(image_bytes: bytes, mime: str, student_id: str, rules: str, retries: int = 2):
    # คีย์: st.secrets -> ENV
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY (Secrets/Env).")

    client = genai.Client(api_key=api_key)

    prompt = f"""
SYSTEM:
คุณเป็นผู้ช่วยตรวจทรงผมนักเรียน ให้ตอบเป็น JSON เท่านั้น

USER (ไทย):
ตรวจรูปนี้ตามกฎ:
{rules}

{SCHEMA_HINT}

เงื่อนไข:
- ถ้ารูปไม่ชัด/ไม่เห็นทรงผมพอ ให้ verdict="unsure" และบอกเหตุผล
- เหตุผลควรกระชับ เข้าใจง่าย
- meta.student_id = {student_id or "UNKNOWN"}
- meta.rule_set_id = "default-v1"
"""

    last_err = None
    for i in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": image_bytes}}
                    ]
                }],
            )
            text = (resp.text or "").strip()
            s, e = text.find("{"), text.rfind("}")
            return json.loads(text[s:e+1])
        except errors.ServerError as e:
            last_err = e
            if "503" in str(e) and i < retries - 1:
                st.toast("ระบบกำลังใช้งานหนาแน่น กำลังลองใหม่…", icon="⏳")
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
        "meta": {"student_id": student_id or "UNKNOWN", "rule_set_id": "default-v1"}
    }

# ===================== ส่วนหัว & คำแนะนำ =====================
st.markdown("### ✂️ ตรวจทรงผมนักเรียน (ใช้งานง่ายสำหรับทุกคน)")
st.markdown(
    """
    <div class="hint-bar">
      ✅ <b>ขั้นตอนง่าย ๆ</b> — ใส่รหัส (ถ้ามี) → ถ่ายภาพให้เห็นทรงผมชัด → กด <b>ยืนยันและตรวจ</b><br>
      💡 <b>เคล็ดลับ</b> — จัดแสงให้เพียงพอ, ไม่ให้ผมบังหู, หันด้านข้างเล็กน้อย<br>
      🔒 <b>ความเป็นส่วนตัว</b> — ภาพใช้เฉพาะการตรวจและไม่เผยแพร่ต่อ
    </div>
    """,
    unsafe_allow_html=True
)

# ===================== โหมดผู้เชี่ยวชาญ (ซ่อนเป็นค่าเริ่มต้น) =====================
with st.expander("ตัวเลือกผู้เชี่ยวชาญ (แก้ไขกฎระเบียบ/ตั้งค่าเพิ่มเติม)"):
    rules = st.text_area("กฎระเบียบ (ปรับได้)", DEFAULT_RULES, height=120)
else:
    # ถ้าไม่ขยาย expander ให้ใช้ค่าเริ่มต้น
    if "rules_cache" not in st.session_state:
        st.session_state.rules_cache = DEFAULT_RULES
    rules = st.session_state.get("rules_cache", DEFAULT_RULES)

# ===================== ฟอร์มเดียว: รหัส + กล้อง + ปุ่มยืนยัน =====================
with st.form("capture_form", clear_on_submit=False):
    student_id = st.text_input("รหัสนักเรียน (ไม่บังคับ)", placeholder="เช่น 68301430004")

    photo = st.camera_input("ถ่ายภาพด้วยกล้อง")

    # ปุ่มสองปุ่ม: ยืนยัน, ล้างข้อมูล
    c1, c2 = st.columns(2)
    with c1:
        submitted = st.form_submit_button("✅ ยืนยันและตรวจ", use_container_width=True)
    with c2:
        reset = st.form_submit_button("🗑️ ถ่ายใหม่/ล้าง", use_container_width=True)

if reset:
    st.session_state.pop("last_result", None)
    st.rerun()

# ===================== ประมวลผลเมื่อยืนยัน =====================
if submitted:
    if not photo:
        st.warning("กรุณาถ่ายภาพก่อนกด “ยืนยันและตรวจ”")
    else:
        # แสดงภาพให้ผู้ใช้เห็นก่อน
        img = Image.open(photo).convert("RGB")
        mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
        st.image(img, caption="ภาพที่ถ่าย", use_container_width=True)

        # แถบความคืบหน้าแบบเรียบง่าย
        prog = st.progress(0, text="กำลังเตรียมภาพ…")
        image_bytes = compress_image(img, mime); prog.progress(40, text="กำลังส่งไปตรวจ…")

        with st.spinner("ระบบกำลังตรวจ…"):
            result = call_gemini(image_bytes, mime=mime, student_id=student_id, rules=rules)
        prog.progress(100, text="เสร็จสิ้น")
        st.toast("ตรวจเสร็จเรียบร้อย", icon="✅")

        st.session_state.last_result = result

# ===================== การ์ดผลลัพธ์ (อ่านง่าย) =====================
if st.session_state.get("last_result"):
    r = st.session_state["last_result"]
    verdict = r.get("verdict", "unsure")
    reasons = r.get("reasons", []) or []
    violations = r.get("violations", []) or []
    conf = r.get("confidence", 0.0)
    meta = r.get("meta", {}) or {}

    st.markdown(
        f"""
        <div class="result-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
            <div style="font-weight:800;font-size:1.06rem;">ผลการตรวจ</div>
            <div>{verdict_badge(verdict)}</div>
          </div>
          <div style="margin-top:6px;color:#475569;">ความมั่นใจของระบบ: <b>{conf:.2f}</b></div>
          <hr style="opacity:.12;margin:12px 0;">
          <div style="font-weight:700;margin-bottom:6px;">เหตุผลสรุป</div>
          <ul class="result-list">
            {''.join(f'<li>{esc(x)}</li>' for x in reasons)}
          </ul>
          {"<div style='font-weight:700;margin-top:10px;'>ข้อที่ไม่ตรงระเบียบ</div><ul class='result-list'>" + ''.join(f"<li>{esc(v.get('message',''))}</li>" for v in violations) + "</ul>" if violations else ""}
          <div style="margin-top:8px;color:#64748b;">รหัสนักเรียน: <b>{esc(meta.get('student_id','-'))}</b> • ชุดกฎ: <b>{esc(meta.get('rule_set_id','default-v1'))}</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()
    st.caption("ถ้าผลไม่ชัดเจน: ลองถ่ายใหม่ให้เห็นด้านข้างศีรษะและใบหูชัดเจนขึ้น")
