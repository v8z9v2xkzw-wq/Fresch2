# Mini-FRESCH-KI-Tutor
# Streamlit App – Foto hochladen, Rechtschreibung nach FRESCH auswerten

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import openai
import io

# ----------------------------
# KONFIGURATION
# ----------------------------
st.set_page_config(page_title="FRESCH KI-Tutor", layout="centered")

openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

# ----------------------------
# FRESCH-SYMBOLE (Original-orientiert nach Michel/Braun)
# ----------------------------
# Die Symbole stehen für STRATEGIEN, nicht für Fehlerarten
FRESCH_SYMBOLS = {
    "Silbe klatschen": "👏",        # Silbieren / Rhythmus
    "Weiterschwingen": "➰",        # Silben verlängern (Dehnung hören)
    "Stopp-Regel": "⛔",            # Doppelkonsonanten / ck / tz
    "Ableiten": "🔁",              # Wortfamilie nutzen
    "Merkwort": "⭐",               # nicht ableitbar
}

# ----------------------------
# OCR FUNKTION
# ----------------------------
def ocr_text(image):
    return pytesseract.image_to_string(image, lang="deu")

# ----------------------------
# OPENAI ANALYSE
# ----------------------------
def fresch_analysis(text):
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
- Silbe klatschen (Rhythmus, Silben hören)
- Weiterschwingen (Vokal hören)
- Stopp-Regel (Doppelkonsonanten, ck, tz)
- Ableiten (Wortfamilie)
- Merkwort

Gib das Ergebnis AUSSCHLIESSLICH als JSON zurück:
[
  {
    "wort": "Beispiel",
    "fehler": true,
    "regel": "Silbe klatschen | Weiterschwingen | Stopp-Regel | Ableiten | Merkwort",
    "erklaerung": "Kurze kindgerechte Hilfe, z.B. 'Klatsch die Silben.'"
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

    return response.choices[0].message.content

# ----------------------------
# BILD MARKIEREN (mit Silbenbögen)
# ----------------------------
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

        # einfacher Silbenbogen (schematisch)
        if item.get("regel") == "Silbe klatschen":
            draw.arc((10, y + 30, 200, y + 60), start=0, end=180, fill="blue", width=3)

        y += 70

    return img

# ----------------------------
# UI
# ----------------------------
st.title("✏️ FRESCH KI-Tutor")

# ----------------------------
# MODUS-WAHL (PIN-geschützter Lehrer-Modus)
# ----------------------------
LEHRER_PIN = st.secrets.get("LEHRER_PIN", "1234")

modus = "👧 Kind"

col1, col2 = st.columns([2,1])
with col1:
    st.markdown("### 👧 Kinderansicht")
with col2:
    with st.expander("👩‍🏫 Lehrkraft"):
        pin = st.text_input("PIN", type="password")
        if pin == LEHRER_PIN:
            modus = "👩‍🏫 Lehrkraft"
            st.success("Lehrermodus aktiv")("Wer nutzt die App?", ["👧 Kind", "👩‍🏫 Lehrkraft"], horizontal=True)

fokus_regel = None
if modus == "👧 Kind":
    fokus_regel = st.selectbox(
        "Wir üben heute nur eine Strategie:",
        list(FRESCH_SYMBOLS.keys())
    )

st.markdown("## 📸 Mach ein Foto von deinem Text")
uploaded = st.file_uploader("", type=["png", "jpg", "jpeg"])("Foto vom Text", type=["png", "jpg", "jpeg"])

if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Dein Text", use_container_width=True)

    if st.button("🔍 Auswerten"):
        with st.spinner("Ich schaue mir deinen Text an …"):
            text = ocr_text(image)
            analysis_raw = fresch_analysis(text)

            import json
            feedback = json.loads(analysis_raw)

            result_image = annotate_image(image, feedback, fokus_regel)

        st.success("Fertig! 😊")
        st.image(result_image, caption="Feedback mit FRESCH‑Symbolen", use_container_width=True)

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
            stats[item['regel']] = stats.get(item['regel'], 0) + 1

    for regel, anzahl in stats.items():
        st.write(f"{FRESCH_SYMBOLS.get(regel, '')} **{regel}**: {anzahl}×")
