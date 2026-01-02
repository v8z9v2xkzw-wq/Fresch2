import streamlit as st
from PIL import Image
from openai import OpenAI
import base64
import json
from io import BytesIO

# ============================
# KONFIGURATION
# ============================
st.set_page_config(page_title="FRESCH KI-Tutor (DEBUG)", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ============================
# SESSION STATE
# ============================
for key in ["image_bytes", "image_preview", "feedback", "raw_response", "ocr_text"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ============================
# HILFSFUNKTIONEN
# ============================
def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def extract_any_text(response) -> str | None:
    """
    Brutal-robustes Auslesen ALLER Textstellen
    """
    texts = []

    try:
        for item in response.output:
            for c in item.get("content", []):
                if "text" in c:
                    texts.append(c["text"])
    except Exception:
        pass

    if texts:
        return "\n".join(texts).strip()
    return None

# ============================
# OCR (DEBUG)
# ============================
def ocr_text(image_bytes: bytes):
    img = Image.open(BytesIO(image_bytes))
    data_url = f"data:image/png;base64,{image_to_base64(img)}"

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Lies jeden sichtbaren deutschen Text im Bild. "
                        "Auch gedruckten oder grauen Text. "
                        "Gib den Text so zurück, wie du ihn siehst."
                    )
                },
                {
                    "type": "input_image",
                    "image_url": data_url
                }
            ]
        }],
        max_output_tokens=800
    )

    st.session_state.raw_response = response
    text = extract_any_text(response)
    st.session_state.ocr_text = text
    return text

# ============================
# UI
# ============================
st.title("✏️ FRESCH KI-Tutor – DEBUG")

uploaded = st.file_uploader(
    "📸 Foto vom Text hochladen",
    type=["png", "jpg", "jpeg"]
)

if uploaded:
    st.session_state.image_bytes = uploaded.getvalue()
    st.session_state.image_preview = Image.open(uploaded)

if st.session_state.image_preview:
    st.image(
        st.session_state.image_preview,
        caption="Dein Text",
        use_container_width=True
    )

if st.session_state.image_bytes:
    if st.button("🔍 OCR TEST"):
        with st.spinner("Lese Text …"):
            text = ocr_text(st.session_state.image_bytes)

        if text:
            st.success("✅ TEXT ERKANNT")
            st.text_area("📄 Erkannter Text", text, height=200)
        else:
            st.error("❌ KEIN TEXT ERKANNT")

# ============================
# DEBUG AUSGABE
# ============================
if st.session_state.raw_response:
    st.subheader("🧪 ROH-ANTWORT DER API")
    st.json(st.session_state.raw_response.model_dump())
