"""
============================================================================
Module RAG correctif — Correction post-extraction des noms / prénoms
============================================================================
Charge les bases de référence (data/prenoms_fr.txt et data/noms_fr.txt)
et fournit une correction par similarité (fuzzy matching) sur les valeurs
extraites par le Vision LLM local.

Pourquoi : un LLM local (Moondream, Qwen2.5-VL 3B…) sur CPU fait régulièrement
des erreurs de lecture sur la cursive ("Mautee" au lieu de "MOUTEE",
"Yousef" au lieu de "Youssef"). Le fuzzy match contre une base de noms
français + maghrébins + européens permet de rattraper ces erreurs.

Stratégie : RapidFuzz WRatio (weighted ratio) — robuste aux différences de
casse, d'accents, et aux fautes ponctuelles. Pas d'embeddings nécessaires
pour des noms propres (chaînes courtes, écart faible).
============================================================================
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).parent / "data"
PRENOMS_FILE = DATA_DIR / "prenoms_fr.txt"
NOMS_FILE = DATA_DIR / "noms_fr.txt"

# Seuils de similarité (0-100). En dessous → on garde la valeur d'origine.
# Calibré pour éviter les corrections abusives sur des noms rares non en base.
THRESHOLD_PRENOM = 82
THRESHOLD_NOM = 80


def _strip_accents(text: str) -> str:
    """Retire les accents pour un matching plus tolérant."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _load_file(path: Path) -> list[str]:
    """Lit un fichier .txt (une entrée par ligne, # = commentaire)."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


@lru_cache(maxsize=1)
def load_prenoms() -> list[str]:
    """Charge la base des prénoms (mis en cache une fois pour toutes)."""
    return _load_file(PRENOMS_FILE)


@lru_cache(maxsize=1)
def load_noms() -> list[str]:
    """Charge la base des noms de famille (mis en cache une fois pour toutes)."""
    return _load_file(NOMS_FILE)


def _best_match(
    candidate: str,
    database: list[str],
    threshold: int,
) -> tuple[str, float, bool]:
    """
    Cherche le meilleur match dans la base.
    Retourne (valeur_finale, score, fut_corrigée).

    On compare la version sans accents pour être tolérant aux diacritiques,
    mais on retourne la valeur originale de la base (avec ses accents).
    """
    if not database:
        return candidate, 0.0, False

    # Pré-normalisation du candidat (sans accents, espaces compactés)
    cand_norm = _strip_accents(candidate).strip()
    if not cand_norm:
        return candidate, 0.0, False

    # Index normalisé → valeur originale (pour conserver accents en sortie)
    norm_to_orig = {_strip_accents(entry): entry for entry in database}
    normalized_db = list(norm_to_orig.keys())

    # WRatio gère bien les variations de casse, mots multiples, etc.
    match = process.extractOne(cand_norm, normalized_db, scorer=fuzz.WRatio)
    if match is None:
        return candidate, 0.0, False

    matched_norm, score, _ = match
    if score >= threshold:
        # Si le match est identique au candidat (casse/accents près) → pas de correction
        if matched_norm.casefold() == cand_norm.casefold():
            return norm_to_orig[matched_norm], score, False
        return norm_to_orig[matched_norm], score, True

    return candidate, score, False


def correct_prenom(value: str) -> tuple[str, float, bool]:
    """
    Corrige un prénom via la base de référence.
    Retourne (prenom_final, score_0_100, fut_corrigé).
    Si la valeur est "non détecté" ou vide, retourne tel quel.
    """
    if not value or value.strip().lower() in ("non détecté", "non detecte", ""):
        return value, 0.0, False
    return _best_match(value.strip(), load_prenoms(), THRESHOLD_PRENOM)


def correct_nom(value: str) -> tuple[str, float, bool]:
    """
    Corrige un nom de famille via la base de référence.
    Retourne (nom_final, score_0_100, fut_corrigé).
    Si la valeur est "non détecté" ou vide, retourne tel quel.
    """
    if not value or value.strip().lower() in ("non détecté", "non detecte", ""):
        return value, 0.0, False
    return _best_match(value.strip(), load_noms(), THRESHOLD_NOM)


def apply_corrections(extraction: dict) -> dict:
    """
    Applique le RAG correctif sur un dict d'extraction normalisé.
    Retourne un nouveau dict enrichi avec les métadonnées de correction.

    Champs ajoutés :
    - nom_lu / prenom_lu : valeurs originales avant correction
    - nom_score / prenom_score : score de similarité 0-100
    - nom_corrige / prenom_corrige : booléen, True si la valeur a été corrigée
    """
    nom_lu = extraction.get("nom", "")
    prenom_lu = extraction.get("prenom", "")

    nom_final, nom_score, nom_corr = correct_nom(nom_lu)
    prenom_final, prenom_score, prenom_corr = correct_prenom(prenom_lu)

    result = dict(extraction)
    result["nom"] = nom_final
    result["prenom"] = prenom_final
    result["nom_lu"] = nom_lu
    result["prenom_lu"] = prenom_lu
    result["nom_score"] = round(nom_score, 1)
    result["prenom_score"] = round(prenom_score, 1)
    result["nom_corrige"] = nom_corr
    result["prenom_corrige"] = prenom_corr

    # Note dans les remarques si une correction a eu lieu
    notes = []
    if nom_corr:
        notes.append(f"nom corrigé via base ({nom_lu} → {nom_final}, {nom_score:.0f}%)")
    if prenom_corr:
        notes.append(f"prénom corrigé via base ({prenom_lu} → {prenom_final}, {prenom_score:.0f}%)")
    if notes:
        existing = result.get("remarques", "").strip()
        sep = " | " if existing else ""
        result["remarques"] = (existing + sep + "; ".join(notes))[:200]

    return result


def database_stats() -> dict:
    """Retourne le nombre d'entrées chargées dans chaque base (pour affichage)."""
    return {
        "prenoms": len(load_prenoms()),
        "noms": len(load_noms()),
    }
