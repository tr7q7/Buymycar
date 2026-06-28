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
    if score >= 8:
        return f"⭐ {score}/10"
    if score >= 5:
        return f"✅ {score}/10"
    return f"⚠️ {score}/10"
