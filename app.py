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
# SESSION STATE
# ============================
for key in ["image_bytes", "image_preview", "feedback", "last_error"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ============================
# HILFSFUNKTIONEN
# ============================
def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def extract_text(response) -> str | None:
    texts = []
    for item in response.output:
        for c in item.get("content", []):
            if "text" in c:
                texts.append(c["text"])
    return "\n".join(texts).strip() if texts else None

# ============================
# OCR MIT RATE-LIMIT-SCHUTZ
# ============================
def ocr_text(image_bytes: bytes):
    img = Image.open(BytesIO(image_bytes))
    data_url = f"data:image/png;base64,{image_to_base64(img)}"

    backoff = 2

    for attempt in range(5):
        try:
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
                                "Gib nur den Text zurück."
                            )
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url
                        }
                    ]
                }],
                max_output_tokens=600
            )

            return extract_text(response)

        except RateLimitError:
            st.session_state.last_error = (
                f"⏳ Server ist gerade ausgelastet "
                f"(Versuch {attempt + 1}/5)."
            )
            time.sleep(backoff)
            backoff *= 2

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

    return json.loads(extract_text(response))

# ============================
# UI
# ============================
st.title("✏️ FRESCH KI-Tutor")

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
    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text(st.session_state.image_bytes)

        if text:
            st.session_state.feedback = fresch_analysis(text)
            st.success("Fertig 😊")
        else:
            st.warning(
                st.session_state.last_error
                or "😕 Ich konnte den Text gerade nicht lesen. Bitte kurz warten."
            )

# ============================
# ERGEBNIS
# ============================
if st.session_state.feedback:
    st.subheader("📘 Kleine Hilfe")
    for item in st.session_state.feedback:
        if item["fehler"]:
            st.write(item["erklaerung"])
