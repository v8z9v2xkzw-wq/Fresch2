import streamlit as st
from PIL import Image, ImageDraw
from openai import OpenAI
import json
import base64
from io import BytesIO

# ============================
# GRUNDKONFIGURATION
# ============================
st.set_page_config(page_title="FRESCH KI-Tutor", layout="centered")

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))
LEHRER_PIN = st.secrets.get("LEHRER_PIN", "1234")

# ============================
# FRESCH-ICONS (Dateien im Repo!)
# ============================
FRESCH_ICONS = {
    "Silbe klatschen": "ableiten.png",
    "Weiterschwingen": "merkwoerter.png",
    "Stopp-Regel": "gross_klein.png",
    "Ableiten": "ableiten.png",
    "Merkwort": "merkwoerter.png",
}

# ============================
# Bild → Base64
# ============================
def image_to_base64(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# ============================
# OCR ÜBER OPENAI VISION (FINAL)
# ============================
import time
from openai import RateLimitError

@st.cache_data(show_spinner=False)
def ocr_text_via_openai_cached(image_bytes: bytes) -> str:
    img = Image.open(BytesIO(image_bytes))
    img_b64 = image_to_base64(img)
    data_url = f"data:image/png;base64,{img_b64}"

    for attempt in range(3):
        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Lies den handgeschriebenen deutschen Text auf dem Bild. "
                                "Gib NUR den reinen Text zurück."
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
            return response.output_text.strip()

        except RateLimitError:
            time.sleep(2)  # kurz warten und erneut versuchen

    raise RuntimeError("OCR momentan überlastet. Bitte kurz warten.")

# ============================
# FRESCH-ANALYSE
# ============================
def fresch_analysis(text: str):
    prompt = f"""
Du bist eine erfahrene Grundschullehrkraft und arbeitest streng nach der
FRESCH-Methode (Freiburger Rechtschreibschule nach H.-J. Michel).

REGELN:
- Beurteile NUR Rechtschreibung
- KEINE klassischen Regeln
- NUR FRESCH-Strategien
- kindgerecht, wertschätzend
- KEINE Korrekturen

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
# BILD MIT ICONS MARKIEREN
# ============================
def annotate_image(image, feedback, fokus_regel=None):
    img = image.copy().convert("RGBA")
    y = 20

    for item in feedback:
        if not item.get("fehler"):
            continue
        if fokus_regel and item["regel"] != fokus_regel:
            continue

        icon_path = FRESCH_ICONS.get(item["regel"])
        if not icon_path:
            continue

        try:
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((80, 80))
            img.paste(icon, (20, y), icon)
            y += 100
        except:
            pass

    return img

# ============================
# UI
# ============================
st.title("✏️ FRESCH KI-Tutor")

modus = "👧 Kind"
with st.expander("👩‍🏫 Lehrkraft"):
    pin = st.text_input("PIN", type="password")
    if pin == LEHRER_PIN:
        modus = "👩‍🏫 Lehrkraft"
        st.success("Lehrermodus aktiv")

fokus_regel = None
if modus == "👧 Kind":
    fokus_regel = st.selectbox(
        "🎯 Wir üben heute eine Strategie:",
        list(FRESCH_ICONS.keys())
    )

st.markdown("## 📸 Foto hochladen")
uploaded = st.file_uploader(
    "Bild auswählen",
    type=["png", "jpg", "jpeg"],
    label_visibility="collapsed"
)

# ============================
# VERARBEITUNG
# ============================
if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Dein Text", width="stretch")

    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text_via_openai(image)
            feedback = fresch_analysis(text)
            result_image = annotate_image(image, feedback, fokus_regel)

        st.success("Fertig 😊")
        st.image(result_image, caption="FRESCH-Feedback", width="stretch")

        if modus == "👧 Kind":
            st.subheader("📘 Kleine Hilfe")
            for item in feedback:
                if item["fehler"] and (not fokus_regel or item["regel"] == fokus_regel):
                    st.write(item["erklaerung"])

        if modus == "👩‍🏫 Lehrkraft":
            st.subheader("📊 Auswertung")
            stats = {}
            for item in feedback:
                if item["fehler"]:
                    stats[item["regel"]] = stats.get(item["regel"], 0) + 1

            for regel, anzahl in stats.items():
                st.write(f"{regel}: {anzahl}×")
