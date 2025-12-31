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
# HILFSFUNKTION
# ============================
def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ============================
# OCR (IMMER MIT RÜCKMELDUNG)
# ============================
@st.cache_data(show_spinner=False)
def ocr_text(image_bytes: bytes):
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
                            "text": "Lies den handgeschriebenen deutschen Text. Gib nur den Text zurück."
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url
                        }
                    ]
                }],
                max_output_tokens=500
            )
            text = response.output_text.strip()
            if text:
                return text
        except RateLimitError:
            time.sleep(2)

    return None  # bewusst: nichts erkannt

# ============================
# FRESCH-ANALYSE
# ============================
def fresch_analysis(text: str):
    prompt = f"""
Du bist eine Grundschullehrkraft und arbeitest streng nach der FRESCH-Methode.

REGELN:
- Nur Rechtschreibung
- Nur FRESCH-Strategien
- Kindgerecht
- Keine Korrekturen

Strategien:
- Silbe klatschen
- Weiterschwingen
- Stopp-Regel
- Ableiten
- Merkwort

ANTWORT NUR ALS JSON:
[
  {{
    "wort": "Beispiel",
    "fehler": true,
    "regel": "Silbe klatschen",
    "erklaerung": "Kurze Hilfe"
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

    return json.loads(response.output_text)

# ============================
# ICONS INS BILD
# ============================
def annotate_image(image: Image.Image, feedback, fokus):
    img = image.copy().convert("RGBA")
    y = 20

    for item in feedback:
        if item["fehler"] and item["regel"] == fokus:
            try:
                icon = Image.open(FRESCH_ICONS[item["regel"]]).convert("RGBA").resize((80, 80))
                img.paste(icon, (20, y), icon)
                y += 100
            except:
                pass

    return img

# ============================
# UI
# ============================
st.title("✏️ FRESCH KI-Tutor")

fokus = st.selectbox(
    "🎯 Wir üben heute:",
    list(FRESCH_ICONS.keys())
)

uploaded = st.file_uploader(
    "📸 Mach ein Foto von deinem Text",
    type=["png", "jpg", "jpeg"]
)

# ============================
# AUSWERTUNG
# ============================
if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Dein Text", width="stretch")

    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text(uploaded.getvalue())

        if not text:
            st.info("😊 Ich konnte den Text noch nicht lesen. Versuch es bitte nochmal.")
        else:
            feedback = fresch_analysis(text)
            result = annotate_image(image, feedback, fokus)

            st.image(result, caption="Dein Feedback", width="stretch")

            st.subheader("📘 Kleine Hilfe")
            for item in feedback:
                if item["fehler"] and item["regel"] == fokus:
                    st.write(item["erklaerung"])
