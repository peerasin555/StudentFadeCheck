import os, io, json
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ===================== Mobile-first config & CSS =====================
st.set_page_config(page_title="ตรวจทรงผมนักเรียน", page_icon="✂️", layout="wide")

MOBILE_CSS = """
<style>
/* เบสฟอนต์ใหญ่ขึ้นสำหรับมือถือ */
html, body, [class*="css"]  { font-size: 18px; }
div.block-container { padding-top: 0.8rem; padding-bottom: 3rem; }

/* ปุ่มใหญ่ แตะง่าย */
.stButton>button {
  width: 100%;
  padding: 0.9rem 1.1rem;
  font-size: 1.1rem;
  border-radius: 14px;
}

/* การ์ดผลลัพธ์ */
.result-card {
  border-radius: 16px;
  padding: 1rem 1.1rem;
  margin-top: 0.5rem;
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}
.badge {
  display:inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.95rem;
  color: #fff;
}
.badge-ok { background: #16a34a; }       /* compliant */
.badge-no { background: #dc2626; }       /* non_compliant */
.badge-unsure { background: #f59e0b; }   /* unsure */

/* label กล้องให้ชัดเจน */
[data-testid="stCameraInputLabel"] { font-size: 1.05rem; }

/* ช่องใส่ข้อความ/ตัวเลือกให้แตะง่าย */
textarea, input, .stTextInput input {
  font-size: 1rem !important;
}

/* ลดระยะห่าง expander */
details > summary { font-size: 1.0rem; }
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ===================== Default rules & schema hint =====================
RULE_TEXT = """\
กฎระเบียบทรงผม (ชาย):
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

# ===================== Helper =====================
def call_gemini(image_bytes: bytes, mime: str, student_id: str, rules: str, retries: int = 2):
    # Priority: Streamlit secrets -> ENV
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set (secrets/env).")

    client = genai.Client(api_key=api_key)

    prompt = f"""
SYSTEM:
คุณเป็นตัวตรวจสอบทรงผมนักเรียน ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น

USER:
วิเคราะห์รูปทรงผมนักเรียนตามกฎต่อไปนี้ (ภาษาไทย):
{rules}

{SCHEMA_HINT}

ข้อควรระวัง: หากรูปไม่ชัด ให้ verdict="unsure" พร้อมเหตุผล
student_id = {student_id or "UNKNOWN"}
rule_set_id = "default-v1"
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
            start, end = text.find("{"), text.rfind("}")
            return json.loads(text[start:end+1])
        except errors.ServerError as e:
            last_err = e
            if "503" in str(e) and i < retries - 1:
                st.toast("เซิร์ฟเวอร์แออัด กำลังลองใหม่…", icon="⏳")
                import time; time.sleep(2 * (i + 1))
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

def compress_for_network(img: Image.Image, mime: str) -> bytes:
    """ลดขนาดภาพเพื่ออัปโหลดเร็วบนมือถือ"""
    # ย่อด้านยาวสุดเหลือ ~1024px เพื่อลด latency
    img = img.copy()
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    if mime == "image/png":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()

def verdict_badge(verdict: str) -> str:
    mp = {
        "compliant": ("ผ่านระเบียบ", "badge-ok"),
        "non_compliant": ("ผิดระเบียบ", "badge-no"),
        "unsure": ("ไม่แน่ใจ", "badge-unsure"),
    }
    label, css = mp.get(verdict, ("ไม่แน่ใจ", "badge-unsure"))
    return f'<span class="badge {css}">{label}</span>'

# ===================== UI =====================
st.markdown("### ✂️ ตรวจทรงผมนักเรียนด้วย Gemini (เหมาะกับมือถือ)")
colA, colB = st.columns([1, 1])
with colA:
    student_id = st.text_input("รหัสนักเรียน", placeholder="ใส่รหัสหรือเว้นว่าง", label_visibility="visible")
with colB:
    auto_analyze = st.toggle("วิเคราะห์อัตโนมัติหลังถ่าย", value=True)

with st.expander("กฎระเบียบ (แตะเพื่อแก้ไข)"):
    rules = st.text_area("RULES", RULE_TEXT, height=120)

st.caption("• อนุญาตการเข้าถึงกล้องในเบราว์เซอร์ • จับมือถือให้นิ่งและให้เห็นทรงผมชัดเจน")
photo = st.camera_input("ถ่ายภาพด้วยกล้อง")

# เก็บ state เพื่อลดการเลื่อนหน้าจอและให้ถ่าย/วิเคราะห์รอบต่อไปเร็วขึ้น
if "last_result" not in st.session_state:
    st.session_state.last_result = None

if photo:
    try:
        img = Image.open(photo).convert("RGB")
        mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"
        st.image(img, caption="ภาพล่าสุด", use_container_width=True)

        # ปุ่มหลักแบบมือถือ
        c1, c2 = st.columns(2)
        with c1:
            do_analyze = st.button("🔎 วิเคราะห์", use_container_width=True) or (auto_analyze and st.session_state.last_result is None)
        with c2:
            clear = st.button("🗑️ ถ่ายใหม่/ล้างผล", use_container_width=True)

        if clear:
            st.session_state.last_result = None
            st.rerun()

        if do_analyze:
            with st.spinner("กำลังวิเคราะห์…"):
                image_bytes = compress_for_network(img, mime)
                result = call_gemini(image_bytes, mime=mime, student_id=student_id, rules=rules)
                st.session_state.last_result = result

    except Exception as e:
        st.error(f"ไม่สามารถอ่านภาพจากกล้องได้: {e}")

# แสดงผลลัพธ์แบบ “การ์ด”
if st.session_state.last_result:
    r = st.session_state.last_result
    verdict = r.get("verdict", "unsure")
    reasons = r.get("reasons", [])
    violations = r.get("violations", [])
    conf = r.get("confidence", 0.0)
    meta = r.get("meta", {})

    st.markdown(
        f"""
        <div class="result-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
            <div style="font-weight:700;font-size:1.05rem;">ผลการประเมิน</div>
            <div>{verdict_badge(verdict)}</div>
          </div>
          <div style="margin-top:6px;color:#475569;">ความเชื่อมั่น: <b>{conf:.2f}</b></div>
          <hr style="opacity:.1;margin:10px 0;">
          <div style="font-weight:600;margin-bottom:6px;">เหตุผล</div>
          <ul style="margin-top:0;">
            {''.join(f'<li>{st._escape_markdown(str(x))}</li>' for x in reasons)}
          </ul>
          {"<div style='font-weight:600;margin-top:8px;'>ข้อผิดระเบียบ</div><ul>" + ''.join(f"<li>{st._escape_markdown(v.get('message',''))}</li>" for v in violations) + "</ul>" if violations else ""}
          <div style="margin-top:6px;color:#64748b;">รหัสนักเรียน: <b>{st._escape_markdown(str(meta.get('student_id','-')))}</b> • ชุดกฎ: <b>{st._escape_markdown(str(meta.get('rule_set_id','default-v1')))}</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )

# แถบคำแนะนำล่างสำหรับมือถือ
st.markdown(
    """
    <div style="margin-top:1.2rem;color:#64748b;font-size:0.95rem;">
      เคล็ดลับ: จัดแสงให้เพียงพอ, จับกล้องระดับสายตา, และให้ด้านข้างศีรษะชัดเจน
    </div>
    """,
    unsafe_allow_html=True
)
