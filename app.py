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
LEHRER_PIN = st.secrets.get("LEHRER_PIN", "1234")

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
# OCR (CACHE + SANFTES RETRY)
# ============================
@st.cache_data(show_spinner=False)
def ocr_text_cached(image_bytes: bytes):
    img = Image.open(BytesIO(image_bytes))
    b64 = image_to_base64(img)
    data_url = f"data:image/png;base64,{b64}"

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
            return response.output_text.strip(), None

        except RateLimitError:
            time.sleep(2)

    return None, "Die KI ist gerade kurz überlastet. Bitte gleich noch einmal versuchen."

# ============================
# FRESCH-ANALYSE
# ============================
def fresch_analysis(text: str):
    prompt = f"""
Du bist eine Grundschullehrkraft und arbeitest streng nach der
FRESCH-Methode (nach Michel).

REGELN:
- Nur Rechtschreibung
- Keine klassischen Regeln
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
def annotate_image(image: Image.Image, feedback, fokus=None):
    img = image.copy().convert("RGBA")
    y = 20

    for item in feedback:
        if not item.get("fehler"):
            continue
        if fokus and item["regel"] != fokus:
            continue

        icon_file = FRESCH_ICONS.get(item["regel"])
        if not icon_file:
            continue

        try:
            icon = Image.open(icon_file).convert("RGBA").resize((80, 80))
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

fokus = None
if modus == "👧 Kind":
    fokus = st.selectbox(
        "🎯 Wir üben heute nur eine Strategie:",
        list(FRESCH_ICONS.keys())
    )

uploaded = st.file_uploader(
    "📸 Foto vom Text hochladen",
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
            text, error = ocr_text_cached(uploaded.getvalue())

        if error:
            st.warning(error)
            st.info("💡 Tipp: Warte kurz oder lade das Bild erneut hoch.")
        else:
            feedback = fresch_analysis(text)
            result_img = annotate_image(image, feedback, fokus)

            st.success("Fertig 😊")
            st.image(result_img, caption="FRESCH-Feedback", width="stretch")

            if modus == "👧 Kind":
                st.subheader("📘 Kleine Hilfe")
                for item in feedback:
                    if item["fehler"] and (not fokus or item["regel"] == fokus):
                        st.write(item["erklaerung"])

            if modus == "👩‍🏫 Lehrkraft":
                st.subheader("📊 Übersicht")
                stats = {}
                for item in feedback:
                    if item["fehler"]:
                        stats[item["regel"]] = stats.get(item["regel"], 0) + 1
                for regel, anzahl in stats.items():
                    st.write(f"{regel}: {anzahl}×")
