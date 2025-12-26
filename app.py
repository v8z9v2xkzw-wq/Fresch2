# Mini-FRESCH-KI-Tutor
# Streamlit Web-App – Foto hochladen, FRESCH-Rechtschreibung auswerten
# Website-Version mit OpenAI + PIN-geschütztem Lehrer-Modus

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import openai
import json

# ============================
# GRUNDKONFIGURATION
# ============================
st.set_page_config(page_title="FRESCH KI-Tutor", layout="centered")

openai.api_key = st.secrets.get("OPENAI_API_KEY", "")
LEHRER_PIN = st.secrets.get("LEHRER_PIN", "1234")

# ============================
# FRESCH-SYMBOLE (nach Michel/Braun)
# ============================
FRESCH_SYMBOLS = {
    "Silbe klatschen": "👏",
    "Weiterschwingen": "➰",
    "Stopp-Regel": "⛔",
    "Ableiten": "🔁",
    "Merkwort": "⭐",
}

# ============================
# OCR
# ============================
def ocr_text(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="deu")

# ============================
# OPENAI – FRESCH-ANALYSE
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
- Silbe klatschen (Rhythmus hören)
- Weiterschwingen (Vokal verlängern)
- Stopp-Regel (Doppelkonsonanten, ck, tz)
- Ableiten (Wortfamilie)
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

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    return json.loads(response.choices[0].message.content)

# ============================
# BILD MARKIEREN + SILBENBÖGEN
# ============================
def annotate_image(image, feedback, fokus_regel=None):
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()

    y = 10
    for item in feedback:
        if not item.get("fehler"):
            continue
        if fokus_regel and item.get("regel") != fokus_regel:
            continue

        symbol = FRESCH_SYMBOLS.get(item.get("regel"), "❓")
        draw.text((10, y), f"{symbol} {item['wort']}", fill="red", font=font)

        if item.get("regel") == "Silbe klatschen":
            draw.arc((10, y + 35, 220, y + 70), start=0, end=180, fill="blue", width=3)

        y += 80

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
        list(FRESCH_SYMBOLS.keys())
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
            text = ocr_text(image)
            feedback = fresch_analysis(text)
            result_image = annotate_image(image, feedback, fokus_regel)

        st.success("Fertig! 😊")
        st.image(result_image, caption="Feedback mit FRESCH-Symbolen", use_container_width=True)

        if modus == "👧 Kind":
            st.subheader("📘 Kleine Hilfe")
            for item in feedback:
                if item.get("fehler") and (not fokus_regel or item.get("regel") == fokus_regel):
                    st.write(f"{FRESCH_SYMBOLS.get(item['regel'], '')} {item['erklaerung']}")

        if modus == "👩‍🏫 Lehrkraft":
            st.subheader("📊 FRESCH-Auswertung")
            stats = {}
            for item in feedback:
                if item.get("fehler"):
                    regel = item["regel"]
                    stats[regel] = stats.get(regel, 0) + 1

            for regel, anzahl in stats.items():
                st.write(f"{FRESCH_SYMBOLS.get(regel, '')} **{regel}**: {anzahl}×")
