"""
Filtrage progressif à 3 niveaux.

Niveau 1 (strict)   : marque exacte, modèle correspondant, carburant exact, année dans la plage
Niveau 2            : idem + plage d'année élargie de ±1 an
Niveau 3            : niveau 2 + correspondance modèle par intersection de mots

La marque n'est jamais élargie. Un modèle non apparenté n'est jamais inclus.

is_model_match() gère les modèles sportifs dont le champ LBC "model" diffère du nom
commercial (ex: Audi RS3 encodé "a3" ou "rs_3" côté LBC → fallback sur le titre).
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional

from app.models.listing import Listing

_WORD_RE = re.compile(r"\S+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def _words(text: str) -> List[str]:
    """Mots bruts (minuscules, séparés par des espaces ; tirets conservés)."""
    return _WORD_RE.findall(text.lower())


def _compact(word: str) -> str:
    """Un mot sans aucune ponctuation ("s-line" -> "sline")."""
    return _NON_ALNUM_RE.sub("", word)


def _word_matches(spec_word: str, title_words: List[str]) -> bool:
    """
    Vrai si spec_word est présent dans le titre, en tolérant :
    - la ponctuation ("s-line" ≈ "sline") ;
    - une inclusion partielle ("amg" contenu dans un mot composé "amgline") ;
    - une légère faute d'orthographe (mots d'au moins 4 caractères, similarité
      ≥ 0.82 — ex: "s-ligne" ≈ "s-line").

    Comparaison faite sur des MOTS entiers (jamais des fragments d'une ou deux
    lettres) pour éviter les faux positifs (ex: "AMG" ne doit pas matcher le
    simple "A" de "Classe A").
    """
    spec_c = _compact(spec_word)
    if len(spec_c) < 2:
        return spec_c in (_compact(t) for t in title_words)

    for t in title_words:
        t_c = _compact(t)
        if len(t_c) < 2:
            continue
        if spec_c == t_c or spec_c in t_c or t_c in spec_c:
            return True
        if len(spec_c) >= 4 and len(t_c) >= 4:
            if SequenceMatcher(None, spec_c, t_c).ratio() >= 0.82:
                return True
    return False

_THRESHOLD_ENOUGH = 20   # en dessous → on tente le niveau suivant
_THRESHOLD_WARN   = 15   # en dessous même après niveau 3 → avertissement


@dataclass
class FilterResult:
    listings: List[Listing]
    strict_count: int       # annonces retenues au niveau 1 (année exacte, modèle strict)
    level: int              # niveau de filtrage utilisé : 1, 2 ou 3
    year_min_used: int
    year_max_used: int

    @property
    def is_expanded(self) -> bool:
        return self.level > 1

    @property
    def is_weak(self) -> bool:
        return len(self.listings) < _THRESHOLD_WARN


def _model_strict(search: str, listing: str) -> bool:
    """search_model contenu dans listing_model (insensible à la casse)."""
    return search.lower() in listing.lower()


def _model_loose(search: str, listing: str) -> bool:
    """
    Correspondance bidirectionnelle par mots (mots ≥ 2 caractères).

    Exemples :
      search="Yaris Cross", listing="Yaris"  → {"yaris"} ∩ {"yaris"} ≠ ∅  → True
      search="Clio",        listing="Clio 5" → {"clio"} ∩ {"clio","5"} ≠ ∅ → True
      search="308",         listing="3008"   → {"308"} ∩ {"3008"} = ∅       → False
    """
    sm = {w for w in search.lower().split() if len(w) >= 2}
    lm = {w for w in listing.lower().split() if len(w) >= 2}
    return bool(sm & lm)


def is_model_match(listing: Listing, selected_model: str) -> bool:
    """
    Vrai si l'annonce correspond au modèle sélectionné.

    Deux niveaux, dans l'ordre :
    1. Champ model structuré LBC  : selected_model contenu dans listing.model
    2. Titre libre de l'annonce   : selected_model normalisé (sans espaces ni tirets)
                                    contenu dans le titre normalisé

    Le fallback titre gère les modèles sportifs dont le code LBC diffère du nom
    commercial : Audi RS3 souvent encodé "a3" ou "rs_3" dans le champ model,
    mais "RS3" présent dans le sujet de l'annonce.
    Même logique pour BMW M3, VW Golf GTI/R, Mercedes AMG, etc.

    La marque est vérifiée séparément — cette fonction ne regarde que le modèle.
    """
    if not selected_model:
        return True

    search_lc = selected_model.strip().lower()

    # Niveau 1 : champ model structuré
    if search_lc in listing.model.lower():
        return True

    # Niveau 2 : titre normalisé (espaces et tirets supprimés)
    # "rs3" correspond à "RS 3", "RS-3", "RS3" dans le titre
    # "golf r" correspond à "Golf R Compétition"
    # "m3" correspond à "M3 Competition" mais PAS à "Serie 3 320d"
    search_norm = search_lc.replace(" ", "").replace("-", "")
    title_norm  = listing.title.lower().replace(" ", "").replace("-", "")
    if len(search_norm) >= 2 and search_norm in title_norm:
        return True

    return False


def has_specification(listing: Listing, specification: str) -> bool:
    """
    Vrai si tous les mots de la spécification (ex: "S-line", "AMG Line") se
    retrouvent dans le titre de l'annonce, quel que soit :
    - la casse ;
    - l'ordre des mots ("AMG Line" ou "Line AMG" correspondent tous les deux) ;
    - une légère faute d'orthographe ("sline" ≈ "S-Line").

    Filtre strict, jamais élargi par le fallback progressif : une fois une
    spécification demandée, seules les annonces qui la mentionnent comptent.
    """
    spec_words = _words(specification)
    if not spec_words:
        return True
    title_words = _words(listing.title)
    return all(_word_matches(w, title_words) for w in spec_words)


def _filter(
    listings: List[Listing],
    brand: str,
    model: Optional[str],
    fuel: Optional[str],
    year_min: int,
    year_max: int,
    loose_model: bool = False,
    specification: Optional[str] = None,
) -> List[Listing]:
    # La marque n'est jamais élargie
    result = [l for l in listings if l.brand.lower() == brand.lower()]

    if model:
        if loose_model:
            # Niveau 3 : union de is_model_match (struct + titre) et _model_loose (mots)
            result = [
                l for l in result
                if is_model_match(l, model) or _model_loose(model, l.model)
            ]
        else:
            # Niveaux 1 et 2 : champ model structuré + fallback titre
            result = [l for l in result if is_model_match(l, model)]

    if fuel:
        result = [l for l in result if l.fuel.lower() == fuel.lower()]

    result = [l for l in result if year_min <= l.year <= year_max]

    if specification:
        # Filtre strict sur le titre, appliqué à tous les niveaux (jamais élargi).
        result = [l for l in result if has_specification(l, specification)]

    return result


def progressive_filter(
    listings: List[Listing],
    brand: str,
    model: Optional[str],
    fuel: Optional[str],
    year_min: int,
    year_max: int,
    specification: Optional[str] = None,
) -> FilterResult:
    # ── Niveau 1 : strict ────────────────────────────────────────────────────
    l1 = _filter(listings, brand, model, fuel, year_min, year_max, specification=specification)
    strict_count = len(l1)

    if strict_count >= _THRESHOLD_ENOUGH:
        return FilterResult(
            listings=l1,
            strict_count=strict_count,
            level=1,
            year_min_used=year_min,
            year_max_used=year_max,
        )

    # ── Niveau 2 : année ±1 ──────────────────────────────────────────────────
    y2_min, y2_max = year_min - 1, year_max + 1
    l2 = _filter(listings, brand, model, fuel, y2_min, y2_max, specification=specification)

    if len(l2) >= _THRESHOLD_ENOUGH:
        return FilterResult(
            listings=l2,
            strict_count=strict_count,
            level=2,
            year_min_used=y2_min,
            year_max_used=y2_max,
        )

    # ── Niveau 3 : année ±1 + modèle élargi ─────────────────────────────────
    l3 = _filter(
        listings, brand, model, fuel, y2_min, y2_max,
        loose_model=True, specification=specification,
    )

    return FilterResult(
        listings=l3,
        strict_count=strict_count,
        level=3,
        year_min_used=y2_min,
        year_max_used=y2_max,
    )
