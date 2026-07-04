import hashlib


def make_listing_id(url: str = "", brand: str = "", model: str = "",
                    year: int = 0, mileage: int = 0, price: float = 0.0,
                    location: str = "", title: str = "") -> str:
    """
    Génère un ID déterministe de 16 caractères hexadécimaux.
    Priorité : hash(url) si disponible, sinon hash des champs métier.
    """
    if url:
        raw = url.strip()
    else:
        raw = "|".join([
            brand.strip().lower(),
            model.strip().lower(),
            str(year),
            str(mileage),
            str(int(price)),
            location.strip().lower(),
            title.strip().lower(),
        ])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def fmt_price(price: float) -> str:
    return f"{int(price):,} €".replace(",", " ")


def fmt_mileage(km: int) -> str:
    return f"{km:,} km".replace(",", " ")


def fmt_score(score: float) -> str:
    if score is None:
        return "—"
    s = int(round(score))
    if s >= 90:
        return f"🏆 {s}/100"
    if s >= 75:
        return f"⭐ {s}/100"
    if s >= 55:
        return f"✅ {s}/100"
    if s >= 35:
        return f"🔶 {s}/100"
    return f"⚠️ {s}/100"


# Valeurs de modèle « fourre-tout » renvoyées par LeBonCoin quand la catégorie
# de modèle n'est pas renseignée. À masquer côté affichage (fait « amateur »).
_GENERIC_MODELS = {"", "autre", "autres", "autre modele", "non renseigne"}


def clean_model_label(model: str) -> str:
    """
    Nettoie un libellé de modèle pour l'affichage.

    Renvoie "" pour les valeurs génériques ("Autres", vide…) afin que le client
    retombe sur le titre de l'annonce plutôt que d'afficher « Audi Autres ».
    """
    if not model:
        return ""
    if model.strip().lower() in _GENERIC_MODELS:
        return ""
    return model.strip()


def clean_title(title: str) -> str:
    """Normalise un titre d'annonce brut : espaces multiples compactés, trim."""
    if not title:
        return ""
    return " ".join(title.split())
