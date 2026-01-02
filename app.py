import streamlit as st
from PIL import Image
from openai import OpenAI, RateLimitError
import base64
import json
import time
from io import BytesIO

# ============================
# KONFIGURATION
# ============================
st.set_page_config(page_title="FRESCH KI-Tutor", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ============================
# SESSION STATE INIT
# ============================
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "image_preview" not in st.session_state:
    st.session_state.image_preview = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# ============================
# FRESCH-ICONS
# ============================
FRESCH_ICONS = {
    "Silbe klatschen": "ableiten.png",
    "Weiterschwingen": "merkwoerter.png",
    "Stopp-Regel": "gross_klein.png",
    "Ableiten": "ableiten.png",
    "Merkwort": "merkwoerter.png",
}

# ============================
# HILFSFUNKTIONEN
# ============================
def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def extract_text_from_response(response) -> str | None:
    """
    Robustes Auslesen von Text aus der OpenAI Responses API
    """
    for item in response.output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "").strip()
    return None

# ============================
# OCR
# ============================
@st.cache_data(show_spinner=False)
def ocr_text(image_bytes: bytes) -> str | None:
    img = Image.open(BytesIO(image_bytes))
    data_url = f"data:image/png;base64,{image_to_base64(img)}"

    for _ in range(3):
        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Lies jeden erkennbaren deutschen Text im Bild "
                                "(handschriftlich oder gedruckt, auch grauer Text). "
                                "Gib ausschließlich den Text zurück."
                            )
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url
                        }
                    ]
                }],
                max_output_tokens=500
            )

            text = extract_text_from_response(response)
            if text:
                return text

        except RateLimitError:
            time.sleep(2)

    return None

# ============================
# FRESCH-ANALYSE
# ============================
def fresch_analysis(text: str):
    prompt = f"""
Du arbeitest streng nach der FRESCH-Methode.
Beurteile ausschließlich Rechtschreibung.

ANTWORTE NUR ALS GÜLTIGES JSON:
[
  {{
    "wort": "Beispiel",
    "fehler": true,
    "regel": "Silbe klatschen",
    "erklaerung": "Kurze kindgerechte Hilfe"
  }}
]

Text:
{text}
"""
    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.1,
        max_output_tokens=800
    )

    text_output = extract_text_from_response(response)
    return json.loads(text_output)

# ============================
# UI
# ============================
st.title("✏️ FRESCH KI-Tutor")

fokus = st.selectbox("🎯 Wir üben heute:", list(FRESCH_ICONS.keys()))

uploaded = st.file_uploader(
    "📸 Foto vom Text hochladen",
    type=["png", "jpg", "jpeg"]
)

# ============================
# DATEI SICHERN
# ============================
if uploaded:
    st.session_state.image_bytes = uploaded.getvalue()
    st.session_state.image_preview = Image.open(uploaded)

# ============================
# VORSCHAU
# ============================
if st.session_state.image_preview:
    st.image(
        st.session_state.image_preview,
        caption="Dein Text",
        use_container_width=True
    )

# ============================
# AUSWERTUNG
# ============================
if st.session_state.image_bytes:
    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text(st.session_state.image_bytes)

        if text:
            st.session_state.feedback = fresch_analysis(text)
            st.success("Fertig 😊")
        else:
            st.info("😊 Ich konnte den Text noch nicht lesen. Versuch es bitte nochmal.")

# ============================
# ERGEBNIS
# ============================
if st.session_state.feedback:
    st.subheader("📘 Kleine Hilfe")
    for item in st.session_state.feedback:
        if item["fehler"] and item["regel"] == fokus:
            st.write(item["erklaerung"])
