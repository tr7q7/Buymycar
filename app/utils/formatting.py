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
