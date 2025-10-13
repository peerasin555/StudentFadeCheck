import os, io, json
from PIL import Image
import streamlit as st
from google import genai
from google.genai import errors

# ----------------- กฎ/สคีมาที่แสดงใน UI -----------------
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

# ----------------- ฟังก์ชันเรียก Gemini + retry 503 -----------------
def call_gemini(image_bytes: bytes, mime: str, student_id: str, rules: str, retries: int = 3):
    # ลำดับการค้นหา: st.secrets -> ENV
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set (use .streamlit/secrets.toml or environment variable).")

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
            # รองรับเคส 503 overloaded ด้วย backoff สั้น ๆ
            last_err = e
            if "503" in str(e) and i < retries - 1:
                st.info(f"เซิร์ฟเวอร์แออัด ลองใหม่อัตโนมัติ ({i+1}/{retries-1}) ...")
                import time; time.sleep(2 * (i + 1))
                continue
            break
        except Exception as e:
            last_err = e
            break

    # Fallback กรณีตอบไม่ใช่ JSON หรือ error
    return {
        "verdict": "unsure",
        "reasons": [f"เกิดข้อผิดพลาดระหว่างเรียกโมเดล: {last_err}"],
        "violations": [],
        "confidence": 0.0,
        "meta": {"student_id": student_id or "UNKNOWN", "rule_set_id": "default-v1"}
    }

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="ตรวจทรงผมนักเรียน", page_icon="✂️", layout="centered")
st.title("✂️ ตรวจทรงผมนักเรียนด้วย - Gemini")

student_id = st.text_input("รหัสนักเรียน (ไม่บังคับ):", "")

with st.expander("กฎระเบียบ (ปรับได้)"):
    rules = st.text_area("RULES", RULE_TEXT, height=140)

st.caption("อนุญาตการเข้าถึงกล้องในเบราว์เซอร์ จากนั้นกดถ่ายภาพด้านล่าง")
photo = st.camera_input("ถ่ายภาพด้วยกล้อง")

if photo:
    # โหลดภาพจาก webcam (ส่วนใหญ่จะได้ image/png)
    try:
        img = Image.open(photo).convert("RGB")
        st.image(img, caption="ตัวอย่างภาพที่ถ่าย", use_container_width=True)
        mime = photo.type if photo.type in ("image/png", "image/jpeg") else "image/jpeg"

        # เข้ารหัสภาพตาม MIME จริง
        buf = io.BytesIO()
        fmt = "PNG" if mime == "image/png" else "JPEG"
        img.save(buf, format=fmt)
        image_bytes = buf.getvalue()

        if st.button("วิเคราะห์"):
            with st.spinner("กำลังวิเคราะห์..."):
                result = call_gemini(image_bytes, mime=mime, student_id=student_id, rules=rules)
            st.subheader("ผลลัพธ์ (JSON)")
            st.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")

    except Exception as e:
        st.error(f"ไม่สามารถอ่านภาพจากกล้องได้: {e}")
