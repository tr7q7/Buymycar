"""
Constructeur d'URL de recherche LeBonCoin.

Paramètres validés empiriquement via l'API Piloterr (2026-06-28) :
  VALIDÉS   : category=2, text=<brand> <model>, fuel=1/2/4, gearbox=1
  INVALIDES (404) : brand=, model= (paramètres séparés — LBC retourne 404)
  NON VALIDÉS (ignorés) : price_min, price_max, regdate_min, regdate_max,
                           mileage_max, fuel=6 (hybride), gearbox=2 (automatique)

La marque et le modèle sont combinés dans text= (ex: "renault clio").
Le filtrage prix/année/km est appliqué côté applicatif après réception.
"""
from urllib.parse import urlencode
from app.providers.piloterr_provider import SearchParams

_LBC_BASE = "https://www.leboncoin.fr/recherche"
_LBC_CATEGORY_VOITURES = "2"

# Codes carburant LeBonCoin validés
_FUEL_CODES: dict[str, str] = {
    "essence": "1",
    "diesel":  "2",
    "electrique": "4",
    # "hybride": inconnu — fuel=6 retourne 404, omis volontairement
}

# Codes boîte de vitesses LeBonCoin validés
_GEARBOX_CODES: dict[str, str] = {
    "manuelle": "1",
    # "automatique": inconnu — gearbox=2 retourne 404, omis volontairement
}


class LeboncoinQueryBuilder:
    """
    Construit une URL de recherche LeBonCoin à partir d'un objet SearchParams.

    Paramètres appliqués dans l'URL (validés) :
      text=<brand> <model>, fuel, gearbox (manuelle uniquement)

    NOTE: brand= et model= en paramètres séparés génèrent des HTTP 404 via Piloterr.
    On utilise text=<brand> <model> à la place.

    Paramètres ignorés côté URL (non validés) :
      price_min, price_max, year_min, year_max, mileage_max, transmission=automatique

    Ces filtres doivent être appliqués en post-traitement sur les Listing retournés.
    """

    def __init__(self, params: SearchParams):
        self.params = params

    def build(self) -> str:
        p = self.params
        query: dict[str, str] = {"category": _LBC_CATEGORY_VOITURES}

        # brand et model combinés dans text= (brand= et model= séparés retournent 404)
        parts = []
        if p.brand:
            parts.append(p.brand.strip().lower())
        if p.model:
            parts.append(p.model.strip().lower())
        if parts:
            query["text"] = " ".join(parts)

        if p.fuel:
            code = _FUEL_CODES.get(p.fuel.strip().lower())
            if code:
                query["fuel"] = code

        if p.transmission:
            code = _GEARBOX_CODES.get(p.transmission.strip().lower())
            if code:
                query["gearbox"] = code

        return _LBC_BASE + "?" + urlencode(query)

    def unsupported_filters(self) -> list[str]:
        """Liste les filtres de SearchParams qui ne peuvent pas être encodés dans l'URL LBC."""
        p = self.params
        unsupported = []
        if p.price_min:
            unsupported.append(f"price_min={p.price_min} (non validé)")
        if p.price_max:
            unsupported.append(f"price_max={p.price_max} (non validé)")
        if p.year_min:
            unsupported.append(f"year_min={p.year_min} (non validé)")
        if p.year_max:
            unsupported.append(f"year_max={p.year_max} (non validé)")
        if p.mileage_max:
            unsupported.append(f"mileage_max={p.mileage_max} (non validé)")
        if p.fuel and p.fuel.strip().lower() not in _FUEL_CODES:
            unsupported.append(f"fuel={p.fuel} (code LBC inconnu)")
        if p.transmission and p.transmission.strip().lower() not in _GEARBOX_CODES:
            unsupported.append(f"transmission={p.transmission} (code LBC inconnu)")
        if p.location:
            unsupported.append(f"location={p.location} (format non validé)")
        return unsupported
