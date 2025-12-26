# Mini-FRESCH-KI-Tutor
# Streamlit Web-App – Foto hochladen, FRESCH-Rechtschreibung auswerten
# Website-Version mit OpenAI (API v1) + Vision + PIN-geschütztem Lehrer-Modus

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import json
import base64
from io import BytesIO

# ============================
# GRUNDKONFIGURATION
# ============================
st.set_page_config(page_title="FRESCH KI-Tutor", layout="centered")

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))
LEHRER_PIN = st.secrets.get("LEHRER_PIN", "1234")

# ============================
# FRESCH-SYMBOLE (nach Michel/Braun)
# ============================
# ============================
# FRESCH-ICONS (Original-Bildsymbole)
# ============================
FRESCH_ICONS = {
    "Silbe klatschen": "ableiten.png",
    "Weiterschwingen": "merkwörter.png",
    "Stopp-Regel": "Groß und Kleinschreibung.png",
    "Ableiten": "ableiten.png",
    "Merkwort": "merkwörter.png",
}

# ============================
# HILFSFUNKTION: Bild → Base64
# ============================
def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ============================
# OCR ÜBER OPENAI VISION (API v1)
# ============================
def ocr_text_via_openai(image: Image.Image) -> str:
    img_b64 = image_to_base64(image)

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Lies den handgeschriebenen deutschen Text. Gib nur den reinen Text zurück."},
                    {
                        "type": "input_image",
                        "image_base64": img_b64,
                    },
                ],
            }
        ],
        max_output_tokens=800,
    )

    return response.output_text.strip()

# ============================
# OPENAI – FRESCH-ANALYSE (Text → JSON)
# ============================
def fresch_analysis(text: str):
    prompt = f"""
Du bist eine erfahrene Grundschullehrkraft und arbeitest streng nach der
FRESCH-Methode (Freiburger Rechtschreibschule nach H.-J. Michel).

WICHTIG:
- Beurteile NUR die Rechtschreibung.
- Nutze KEINE klassischen Rechtschreibregeln.
- Gib STRATEGIEN nach FRESCH an.
- Schreibe kindgerecht, wertschätzend und kurz.
- KEINE Korrekturen hinschreiben, nur Hinweise.

Erlaubte Strategien:
- Silbe klatschen
- Weiterschwingen
- Stopp-Regel
- Ableiten
- Merkwort

Gib das Ergebnis AUSSCHLIESSLICH als JSON zurück:
[
  {
    "wort": "Beispiel",
    "fehler": true,
    "regel": "Silbe klatschen | Weiterschwingen | Stopp-Regel | Ableiten | Merkwort",
    "erklaerung": "Kurze kindgerechte Hilfe"
  }
]

Text:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.1,
        max_output_tokens=800,
    )

    return json.loads(response.output_text)

# ============================
# BILD MARKIEREN + SILBENBÖGEN
# ============================
def annotate_image(image, feedback, fokus_regel=None):
    img = image.copy().convert("RGBA")

    y = 20
    for item in feedback:
        if not item.get("fehler"):
            continue
        if fokus_regel and item.get("regel") != fokus_regel:
            continue

        icon_path = FRESCH_ICONS.get(item.get("regel"))
        if icon_path:
            try:
                icon = Image.open(icon_path).convert("RGBA")
                icon = icon.resize((80, 80))
                img.paste(icon, (20, y), icon)
                y += 100
            except:
                pass

    return img

# ============================
# UI – MODUS (PIN-GESCHÜTZT)
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
        "🎯 Wir üben heute nur eine Strategie:",
        list(FRESCH_ICONS.keys()),
    )

st.markdown("## 📸 Mach ein Foto von deinem Text")
uploaded = st.file_uploader("", type=["png", "jpg", "jpeg"])

# ============================
# VERARBEITUNG
# ============================
if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Dein Text", use_container_width=True)

    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text_via_openai(image)
            feedback = fresch_analysis(text)
            result_image = annotate_image(image, feedback, fokus_regel)

        st.success("Fertig! 😊")
        st.image(result_image, caption="Feedback mit FRESCH-Symbolen", use_container_width=True)

        if modus == "👧 Kind":
            st.subheader("📘 Kleine Hilfe")
            for item in feedback:
                if item.get("fehler") and (not fokus_regel or item.get("regel") == fokus_regel):
                    st.write(f"{FRESCH_ICONS.get(item['regel'], '')} {item['erklaerung']}")

        if modus == "👩‍🏫 Lehrkraft":
            st.subheader("📊 FRESCH-Auswertung")
            stats = {}
            for item in feedback:
                if item.get("fehler"):
                    regel = item["regel"]
                    stats[regel] = stats.get(regel, 0) + 1

            for regel, anzahl in stats.items():
                st.write(f"{FRESCH_ICONS.get(regel, '')} **{regel}**: {anzahl}×")
