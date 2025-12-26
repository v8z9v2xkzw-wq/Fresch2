# Mini-FRESCH-KI-Tutor
# Streamlit Web-App – Foto hochladen, FRESCH-Rechtschreibung auswerten
# Website-Version OHNE Tesseract (OCR über OpenAI Vision)

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import openai
import json
import base64
from io import BytesIO

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
# OPENAI VISION OCR
# ============================
def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def ocr_text_via_openai(image: Image.Image) -> str:
    img_b64 = image_to_base64(image)

    prompt = (
        "Lies den handgeschriebenen deutschen Text auf dem Bild. "
        "Gib NUR den reinen Text zurück, ohne Kommentare."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }
        ],
        max_tokens=800,
    )

    return response.choices[0].message.content.strip()

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

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
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
        list(FRESCH_SYMBOLS.keys()),
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
