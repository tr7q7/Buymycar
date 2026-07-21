"""
Filtrage progressif à 3 niveaux.

Niveau 1 (strict)   : marque exacte, modèle correspondant, carburant exact, année dans la plage
Niveau 2            : idem + plage d'année élargie de ±1 an
Niveau 3            : niveau 2 + correspondance modèle par intersection de mots

La marque n'est jamais élargie. Un modèle non apparenté n'est jamais inclus.

is_model_match() gère les modèles sportifs dont le champ LBC "model" diffère du nom
commercial (ex: Audi RS3 encodé "a3" ou "rs_3" côté LBC → fallback sur le titre).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.models.listing import Listing

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
    Vrai si le texte de spécification (ex: "S-line", "AMG") apparaît dans le
    titre de l'annonce (normalisé : casse, espaces et tirets ignorés).

    Filtre strict, jamais élargi par le fallback progressif : une fois une
    spécification demandée, seules les annonces qui la mentionnent comptent.
    """
    spec_norm = specification.strip().lower().replace(" ", "").replace("-", "")
    if not spec_norm:
        return True
    title_norm = listing.title.lower().replace(" ", "").replace("-", "")
    return spec_norm in title_norm


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
