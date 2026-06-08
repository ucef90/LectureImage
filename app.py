"""
============================================================================
POC LAD — Lecture Automatique de Documents manuscrits — MDPH CD93
============================================================================
Application Streamlit pédagogique pour démontrer l'extraction d'entités
(Nom, Prénom, Âge) depuis des images manuscrites via un Vision LLM.

Workflow : l'utilisateur charge une ou plusieurs images, valide chaque
extraction dans un formulaire éditable, puis génère un PDF récapitulatif.

POC pédagogique uniquement — Ne JAMAIS utiliser sur de vraies données
usagers MDPH sans AIPD validée, hébergement SecNumCloud et contrats
RGPD signés avec les fournisseurs.

Auteur     : Léon Dumas — CD93 — Projet MDPH-2026-04
Version    : 1.0
Lancement  : streamlit run app.py
============================================================================
"""

import base64
import io
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

import name_corrector
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================================
# CONSTANTES — Configuration générale
# ============================================================================

APP_TITLE = "POC LAD MDPH — Extraction de documents manuscrits"
LOGO_PATH = "logo_cd93.png"

MAX_IMAGE_SIZE_PX = 1568

WARNING_BANNER = (
    "**POC pédagogique — Ne pas utiliser sur de vraies données usagers MDPH.** "
    "Cet outil n'est ni validé AIPD, ni hébergé SecNumCloud."
)

# Modèles par défaut pour chaque backend (modifiables dans la sidebar)
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"        # Le moins cher d'Anthropic
DEFAULT_MISTRAL_MODEL = "pixtral-12b-2409"       # Modèle vision Mistral
DEFAULT_OLLAMA_MODEL = "qwen2.5vl:3b"             # Vision LLM local — bon compromis qualité/vitesse CPU
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
ENABLE_RAG_CORRECTION = True                      # Active la correction post-LLM via base de noms

ACCEPTED_IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]


EXTRACTION_PROMPT = """\
Tu es un expert en lecture d'écriture manuscrite française (cursive et script).
Tu lis un document manuscrit et tu extrais 3 informations DEPUIS L'IMAGE.

STRATÉGIE DE LECTURE
1. L'image peut être pivotée (photo prise au téléphone) : analyse-la dans toutes
   les orientations possibles avant de répondre.
2. Repère d'abord les libellés écrits : "Nom", "Prénom", "Prenom", "Age", "Âge",
   "age :", parfois suivis de ":" ou "=". La valeur est juste à droite ou en dessous.
3. Lis la valeur lettre par lettre, en tenant compte des particularités cursives :
   - "EL", "AL", "BEN", "DA", "DE", "VAN" sont des préfixes de noms courants.
   - Les noms peuvent être en MAJUSCULES, les prénoms en minuscules cursives.
   - Le "Y" cursif a une grande boucle descendante, le "J" aussi.
   - Le "ss" double français peut ressembler à un "ff" ou "ll".
4. Si tu hésites entre 2 lectures, choisis la plus plausible comme nom/prénom
   français ou maghrébin/européen courant, mais ne devine PAS si c'est illisible.

CHAMPS À EXTRAIRE (uniquement ce que tu vois, jamais d'invention)
- nom     : nom de famille manuscrit (souvent en MAJUSCULES)
- prenom  : prénom manuscrit (souvent en minuscules cursives)
- age     : âge manuscrit, nombre seul ou avec "ans"

Si un champ est absent, illisible ou douteux, écris exactement : non détecté

ÉVALUATION DE CONFIANCE
- élevée  : les 3 champs sont lisibles sans ambiguïté
- moyenne : au moins un champ est partiellement lisible
- faible  : plusieurs champs sont illisibles

EXEMPLES (apprends le format de sortie, pas les valeurs)

Exemple 1 — image contenant : "age : 43   Nom : EL MOUTEE   Prénom : Youssef"
{"nom": "EL MOUTEE", "prenom": "Youssef", "age": "43", "confiance": "élevée", "remarques": ""}

Exemple 2 — image contenant : "Nom : DUPONT   Prénom : Marie   Âge : 28 ans"
{"nom": "DUPONT", "prenom": "Marie", "age": "28 ans", "confiance": "élevée", "remarques": ""}

Exemple 3 — image avec nom lisible mais âge raturé :
{"nom": "MARTIN", "prenom": "Jean", "age": "non détecté", "confiance": "moyenne", "remarques": "âge raturé"}

Exemple 4 — image vide ou illisible :
{"nom": "non détecté", "prenom": "non détecté", "age": "non détecté", "confiance": "faible", "remarques": "document illisible"}

FORMAT DE SORTIE
Réponds UNIQUEMENT avec un objet JSON contenant ces 5 clés exactes :
nom, prenom, age, confiance, remarques

Les valeurs nom, prenom, age sont celles LUES DANS L'IMAGE FOURNIE (jamais des
exemples ci-dessus, qui sont là pour illustrer le format).
La clé remarques contient une courte note libre (max 100 caractères) ou "".

Réponse = un seul objet JSON, commence par { et termine par }. Rien d'autre.
"""

# ============================================================================
# UTILITAIRES — Encodage et validation
# ============================================================================

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode des octets d'image en base64 (utilisé par Claude, Mistral, Ollama)."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def resize_image_for_llm(image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE_PX) -> bytes:
    """
    Pré-traite l'image avant envoi au LLM (étapes critiques pour la cursive) :
    1. Corrige l'orientation EXIF (photos tournées par le téléphone)
    2. Limite le côté le plus long à max_size pixels
    3. Convertit en niveaux de gris puis renforce le contraste (auto-contrast)
       → le trait à l'encre ressort beaucoup mieux contre le papier
    4. Repasse en RGB et ré-encode en JPEG haute qualité
    Gain de fiabilité majeur sur Vision LLM local + gain de performance.
    """
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    # Renforcement du contraste : étape clé pour les Vision LLM locaux sur manuscrit.
    # On passe en L (niveaux de gris) → autocontrast → retour en RGB.
    if img.mode != "L":
        gray = img.convert("L")
    else:
        gray = img
    gray = ImageOps.autocontrast(gray, cutoff=2)
    img = gray.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


def detect_image_mime(image_bytes: bytes) -> str:
    """Détecte le type MIME de l'image à partir des octets via Pillow."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = (img.format or "").lower()
        mapping = {
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        return mapping.get(fmt, "image/jpeg")
    except Exception:
        return "image/jpeg"


def parse_llm_response(raw_text: str) -> dict:
    """
    Parse la réponse brute du LLM en dict Python.
    Tolérant : retire les blocs Markdown éventuels, et tente d'ajouter les
    accolades { } si le modèle a renvoyé uniquement le contenu interne.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lower().startswith("json"):
                text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])
    if '"nom"' in text or '"prenom"' in text:
        cleaned = text.rstrip(" .,;").rstrip()
        try:
            return json.loads("{" + cleaned + "}")
        except json.JSONDecodeError:
            pass
    raise ValueError(
        f"Aucun objet JSON trouvé dans la réponse du LLM : {raw_text[:200]}"
    )


def normalize_extraction(data: dict) -> dict:
    """Garantit que tous les champs attendus sont présents avec des valeurs par défaut."""
    return {
        "nom": str(data.get("nom") or "non détecté").strip(),
        "prenom": str(data.get("prenom") or "non détecté").strip(),
        "age": str(data.get("age") or "non détecté").strip(),
        "confiance": str(data.get("confiance") or "faible").lower().strip(),
        "remarques": str(data.get("remarques") or "").strip(),
    }


# ============================================================================
# CLIENTS LLM — 3 backends supportés
# ============================================================================

def call_claude(image_bytes: bytes, api_key: str, model: str):
    """Appelle l'API Claude (Anthropic). Retourne (extraction_normalisée, raw_text)."""
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    mime = detect_image_mime(image_bytes)
    b64 = encode_image_to_base64(image_bytes)

    response = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    raw_text = response.content[0].text
    return normalize_extraction(parse_llm_response(raw_text)), raw_text


def call_mistral(image_bytes: bytes, api_key: str, model: str):
    """Appelle l'API Mistral (vision Pixtral). Retourne (extraction_normalisée, raw_text)."""
    from mistralai import Mistral

    client = Mistral(api_key=api_key)
    mime = detect_image_mime(image_bytes)
    b64 = encode_image_to_base64(image_bytes)
    data_url = f"data:{mime};base64,{b64}"

    response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": data_url},
                ],
            }
        ],
    )
    raw_text = response.choices[0].message.content
    return normalize_extraction(parse_llm_response(raw_text)), raw_text


def call_ollama(image_bytes: bytes, model: str, host: str):
    """Appelle Ollama en local (modèle vision). Retourne (extraction_normalisée, raw_text)."""
    import ollama

    client = ollama.Client(host=host)
    b64 = encode_image_to_base64(image_bytes)

    response = client.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT,
                "images": [b64],
            }
        ],
        format="json",
        options={
            "temperature": 0.0,
            "num_predict": 300,     # plafond tokens — suffisant pour JSON court
            "num_ctx": 4096,        # contexte modeste, accélère CPU
            "top_p": 0.1,           # quasi-déterministe
        },
        keep_alive="15m",
    )
    raw_text = response["message"]["content"]
    return normalize_extraction(parse_llm_response(raw_text)), raw_text


# ============================================================================
# GÉNÉRATION PDF — Récapitulatif des extractions validées
# ============================================================================

def generate_pdf(extractions: list) -> bytes:
    """Génère un PDF récapitulatif des extractions validées."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f3a5f"),
        fontSize=18,
        spaceAfter=12,
    )
    warning_style = ParagraphStyle(
        "WarningCustom",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#c0392b"),
        fontSize=10,
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph("POC LAD — Récapitulatif d'extraction", title_style))
    story.append(Paragraph(
        "MDPH — Conseil départemental de Seine-Saint-Denis (CD93)",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "POC PÉDAGOGIQUE — Document à usage interne de démonstration. "
        "Ne reflète aucune donnée usager réelle. "
        "Validation humaine systématique requise.",
        warning_style,
    ))
    story.append(Spacer(1, 0.4 * cm))

    for idx, item in enumerate(extractions, start=1):
        story.append(Paragraph(f"Extraction n° {idx}", h2_style))
        table_data = [
            ["Champ", "Valeur validée"],
            ["Nom",            item.get("nom", "")],
            ["Prénom",         item.get("prenom", "")],
            ["Âge",            item.get("age", "")],
            ["Confiance IA",   item.get("confiance", "")],
            ["Remarques IA",   item.get("remarques", "") or "—"],
            ["Image source",   item.get("image_name", "—")],
            ["Moteur LLM",     item.get("backend", "—")],
            ["Validée le",     item.get("validated_at", "")],
        ]
        table = Table(table_data, colWidths=[5 * cm, 11 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
            ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.whitesmoke, colors.white]),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

def init_session_state():
    """Initialise les variables de session Streamlit (au premier chargement)."""
    defaults = {
        "validated_extractions": [],
        "current_extraction": None,
        "current_image_bytes": None,
        "current_image_name": None,
        "current_raw_response": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> dict:
    """Sidebar : sélection du backend LLM et de ses paramètres."""
    with st.sidebar:
        st.header("Configuration")
        backend = st.selectbox(
            "Moteur Vision LLM",
            options=["Claude (Anthropic)", "Mistral (Pixtral)", "Ollama (local)"],
            index=0,
            help="Choix du moteur d'IA pour l'extraction.",
        )

        config = {"backend": backend}

        if backend == "Claude (Anthropic)":
            config["api_key"] = st.text_input(
                "Clé API Anthropic",
                type="password",
                help="Obtenir une clé sur https://console.anthropic.com/",
            )
            config["model"] = st.text_input(
                "Modèle Claude",
                value=DEFAULT_CLAUDE_MODEL,
                help="claude-haiku-4-5 = le moins cher. claude-sonnet-4-6 = qualité supérieure.",
            )

        elif backend == "Mistral (Pixtral)":
            config["api_key"] = st.text_input(
                "Clé API Mistral",
                type="password",
                help="Obtenir une clé sur https://console.mistral.ai/",
            )
            config["model"] = st.text_input(
                "Modèle Mistral",
                value=DEFAULT_MISTRAL_MODEL,
            )

        else:
            config["model"] = st.text_input(
                "Modèle Ollama",
                value=DEFAULT_OLLAMA_MODEL,
                help="À installer via : ollama pull qwen2.5vl:3b (~2 Go, CPU OK). "
                     "Alternatives : moondream:latest (plus rapide), minicpm-v (plus précis mais lent).",
            )
            config["host"] = st.text_input(
                "Serveur Ollama",
                value=DEFAULT_OLLAMA_HOST,
            )

        st.markdown("---")
        st.subheader("Correction RAG")
        config["enable_rag"] = st.checkbox(
            "Corriger via base de noms",
            value=ENABLE_RAG_CORRECTION,
            help="Applique un fuzzy match contre data/prenoms_fr.txt et data/noms_fr.txt "
                 "pour rattraper les erreurs de lecture du LLM.",
        )
        stats = name_corrector.database_stats()
        st.caption(
            f"Base chargée : **{stats['prenoms']}** prénoms · **{stats['noms']}** noms"
        )

        st.markdown("---")
        st.caption(
            "Flux de travail :\n"
            "1. Charger une image\n"
            "2. Extraire avec l'IA (+ correction RAG)\n"
            "3. Vérifier / corriger manuellement\n"
            "4. Valider (ajout au lot)\n"
            "5. Recommencer ou télécharger le PDF"
        )

        return config


def confidence_badge(level: str) -> str:
    """Retourne un badge HTML coloré selon le niveau de confiance."""
    mapping = {
        "élevée":  ("#2e7d32", "Confiance élevée"),
        "moyenne": ("#ed6c02", "Confiance moyenne"),
        "faible":  ("#c62828", "Confiance faible"),
    }
    color, label = mapping.get(level, ("#757575", f"Confiance : {level}"))
    return (
        f"<span style='display:inline-block;padding:4px 12px;"
        f"background-color:{color};color:white;border-radius:4px;"
        f"font-weight:600;font-size:0.9em;'>{label}</span>"
    )


def run_extraction(image_bytes: bytes, config: dict):
    """
    Aiguille l'appel vers le bon backend selon la config sidebar,
    puis applique la correction RAG via la base de noms locale.
    """
    image_bytes = resize_image_for_llm(image_bytes)
    backend = config["backend"]
    if backend == "Claude (Anthropic)":
        if not config.get("api_key"):
            raise ValueError("Clé API Anthropic manquante (à saisir dans la sidebar).")
        extraction, raw = call_claude(image_bytes, config["api_key"], config["model"])
    elif backend == "Mistral (Pixtral)":
        if not config.get("api_key"):
            raise ValueError("Clé API Mistral manquante (à saisir dans la sidebar).")
        extraction, raw = call_mistral(image_bytes, config["api_key"], config["model"])
    else:
        extraction, raw = call_ollama(image_bytes, config["model"], config["host"])

    # RAG correctif : fuzzy match contre data/prenoms_fr.txt + data/noms_fr.txt
    if config.get("enable_rag", ENABLE_RAG_CORRECTION):
        extraction = name_corrector.apply_corrections(extraction)
    return extraction, raw


def main():
    page_icon = LOGO_PATH if Path(LOGO_PATH).exists() else None
    st.set_page_config(page_title=APP_TITLE, page_icon=page_icon, layout="wide")
    init_session_state()

    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if Path(LOGO_PATH).exists():
            st.image(LOGO_PATH, width=110)
    with col_title:
        st.title("POC LAD — Lecture Automatique de Documents manuscrits")
        st.caption("MDPH — Conseil départemental de Seine-Saint-Denis (CD93)")

    st.warning(WARNING_BANNER)

    config = render_sidebar()

    col_left, col_right = st.columns([1, 1])

    # ---------- Colonne gauche : upload + extraction ----------
    with col_left:
        st.subheader("1. Charger une image manuscrite")
        uploaded = st.file_uploader(
            "Glissez-déposez une image (JPG, PNG, WebP)",
            type=ACCEPTED_IMAGE_TYPES,
            help="L'image doit contenir au moins un nom, prénom et âge manuscrits.",
        )

        if uploaded is not None:
            image_bytes = uploaded.getvalue()
            st.image(image_bytes, caption=uploaded.name, use_container_width=True)

            if st.button("Extraire les informations", type="primary"):
                with st.spinner("Analyse en cours par le Vision LLM..."):
                    try:
                        extraction, raw = run_extraction(image_bytes, config)
                        st.session_state.current_extraction = extraction
                        st.session_state.current_image_bytes = image_bytes
                        st.session_state.current_image_name = uploaded.name
                        st.session_state.current_raw_response = raw
                        st.success("Extraction terminée. Vérifiez les champs à droite.")
                    except json.JSONDecodeError as e:
                        st.error(f"Réponse LLM non valide (JSON malformé) : {e}")
                    except ValueError as e:
                        st.error(f"Format de réponse inattendu : {e}")
                    except Exception as e:
                        st.error(
                            f"Erreur lors de l'appel au LLM : "
                            f"{type(e).__name__} — {e}"
                        )

    # ---------- Colonne droite : formulaire éditable ----------
    with col_right:
        st.subheader("2. Vérifier et corriger")

        if st.session_state.current_extraction is None:
            st.info(
                "Aucune extraction en cours. Chargez une image et cliquez sur "
                "**Extraire les informations**."
            )
        else:
            extraction = st.session_state.current_extraction
            st.markdown(confidence_badge(extraction["confiance"]), unsafe_allow_html=True)

            with st.form(key="validation_form"):
                nom_value = st.text_input("Nom de famille", value=extraction["nom"])
                if extraction.get("nom_corrige"):
                    st.caption(
                        f"🔧 Corrigé via base : *{extraction['nom_lu']}* → "
                        f"**{extraction['nom']}** ({extraction.get('nom_score', 0):.0f}%)"
                    )
                elif extraction.get("nom_lu") and extraction["nom_lu"] not in ("", "non détecté"):
                    score = extraction.get("nom_score", 0)
                    if score >= 95:
                        st.caption(f"✅ Lu directement, présent en base ({score:.0f}%)")
                    elif score > 0:
                        st.caption(f"⚠️ Lu mais absent de la base (meilleur match {score:.0f}%)")

                prenom_value = st.text_input("Prénom", value=extraction["prenom"])
                if extraction.get("prenom_corrige"):
                    st.caption(
                        f"🔧 Corrigé via base : *{extraction['prenom_lu']}* → "
                        f"**{extraction['prenom']}** ({extraction.get('prenom_score', 0):.0f}%)"
                    )
                elif extraction.get("prenom_lu") and extraction["prenom_lu"] not in ("", "non détecté"):
                    score = extraction.get("prenom_score", 0)
                    if score >= 95:
                        st.caption(f"✅ Lu directement, présent en base ({score:.0f}%)")
                    elif score > 0:
                        st.caption(f"⚠️ Lu mais absent de la base (meilleur match {score:.0f}%)")

                age_value = st.text_input("Âge", value=extraction["age"])
                if extraction.get("remarques"):
                    st.caption(f"Remarques IA : *{extraction['remarques']}*")

                col_a, col_b = st.columns(2)
                with col_a:
                    submit_validate = st.form_submit_button(
                        "Valider et ajouter au lot", type="primary"
                    )
                with col_b:
                    submit_cancel = st.form_submit_button("Annuler")

            if submit_validate:
                st.session_state.validated_extractions.append({
                    "nom": nom_value.strip() or "non détecté",
                    "prenom": prenom_value.strip() or "non détecté",
                    "age": age_value.strip() or "non détecté",
                    "confiance": extraction["confiance"],
                    "remarques": extraction["remarques"],
                    "image_name": st.session_state.current_image_name,
                    "backend": config["backend"],
                    "validated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                })
                st.session_state.current_extraction = None
                st.session_state.current_image_bytes = None
                st.session_state.current_raw_response = None
                st.rerun()

            if submit_cancel:
                st.session_state.current_extraction = None
                st.session_state.current_image_bytes = None
                st.session_state.current_raw_response = None
                st.rerun()

            with st.expander("Mode debug — Réponse brute du LLM"):
                st.code(
                    st.session_state.current_raw_response or "",
                    language="json",
                )

    # ---------- Lot d'extractions validées ----------
    st.markdown("---")
    nb = len(st.session_state.validated_extractions)
    st.subheader(f"3. Lot validé ({nb} extraction{'s' if nb > 1 else ''})")

    if nb == 0:
        st.info(
            "Aucune extraction validée pour le moment. "
            "Validez vos extractions une à une, puis téléchargez le récapitulatif PDF."
        )
    else:
        table_rows = [
            {
                "N°": i + 1,
                "Nom": ex["nom"],
                "Prénom": ex["prenom"],
                "Âge": ex["age"],
                "Confiance IA": ex["confiance"],
                "Image": ex["image_name"],
                "Moteur": ex["backend"],
                "Validée le": ex["validated_at"],
            }
            for i, ex in enumerate(st.session_state.validated_extractions)
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        col_pdf, col_clear = st.columns([1, 1])
        with col_pdf:
            pdf_bytes = generate_pdf(st.session_state.validated_extractions)
            filename = (
                f"LAD_MDPH_recapitulatif_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            st.download_button(
                label="Télécharger le récapitulatif PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
            )
        with col_clear:
            if st.button("Vider le lot"):
                st.session_state.validated_extractions = []
                st.rerun()

    st.markdown("---")
    st.caption(
        "Rappel RGPD : ce POC est un démonstrateur pédagogique. "
        "Il ne doit jamais être utilisé sur des données usagers réelles "
        "sans validation AIPD, hébergement SecNumCloud et contrats RGPD "
        "signés avec les fournisseurs d'API."
    )


if __name__ == "__main__":
    main()
