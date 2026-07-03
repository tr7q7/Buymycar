"""
Carburants plausibles par marque et modèle.

Utilisé uniquement pour filtrer les options UI — pas pour la validation API.
Si une marque/modèle n'est pas listée, tous les carburants standards sont proposés.

Règles de priorité :
  1. Modèle exact → _MODEL_FUELS (substring match sur le nom du modèle, du plus précis au plus général)
  2. Marque → _BRAND_FUELS
  3. Fallback → ALL_FUELS
"""

ALL_FUELS = ["essence", "diesel", "electrique"]

# ── Règles marque entière ─────────────────────────────────────────────────────
# Utilisées quand aucune règle modèle ne correspond.

_BRAND_FUELS: dict[str, list[str]] = {
    # Électrique exclusif (toute la gamme)
    "Tesla":    ["electrique"],
    "BYD":      ["electrique"],
    "Xpeng":    ["electrique"],
    "Zeekr":    ["electrique"],
    "Hummer":   ["electrique"],   # EV only en version moderne
    # Essence exclusive — sportives/luxe sans diesel ni EV
    "Ferrari":       ["essence"],
    "Lamborghini":   ["essence"],
    "Aston Martin":  ["essence"],
    "Rolls-Royce":   ["essence"],
    "McLaren":       ["essence"],
    # Essence + électrique — diesel non commercialisé ou abandonné
    "Porsche":   ["essence", "electrique"],
    "Cupra":     ["essence", "electrique"],
    "Polestar":  ["essence", "electrique"],   # Polestar 1 = hybride rechargeable
    # Bentley : diesel commercialisé jusqu'en 2018 puis arrêté
    "Bentley":   ["essence", "diesel"],
    # Maserati : propose du diesel mais gamme sportive essence dominante
    "Maserati":  ["essence", "diesel"],
    # Lynk & Co : hybrides essence + quelques électriques
    "Lynk & Co": ["essence", "electrique"],
    # Saab : essence et diesel, mais plus de production depuis 2011
    "Saab":      ["essence", "diesel"],
}

# ── Règles modèle (substring match sur nom du modèle en minuscules) ───────────
# Format : (marque, sous-chaîne_modèle_minuscule, carburants)
# Ordre : du PLUS SPÉCIFIQUE au moins spécifique (premier match gagne).

_MODEL_FUELS: list[tuple[str, str, list[str]]] = [

    # ── AUDI ──────────────────────────────────────────────────────────────────
    # Électriques Audi
    ("Audi", "e-tron",   ["electrique"]),      # e-tron, e-tron GT, e-tron S, e-tron Sportback
    ("Audi", "q4 e-tron",["electrique"]),      # Q4 e-tron
    ("Audi", "q8 e-tron",["electrique"]),      # Q8 e-tron
    # RS et sportives Audi → Essence uniquement
    ("Audi", "rs",       ["essence"]),          # RS3, RS4, RS5, RS6, RS7, RS Q3, RS Q8, TT RS
    ("Audi", "r8",       ["essence"]),
    ("Audi", "tt",       ["essence"]),          # TT, TTS, TT Roadster, TT RS
    # S-line Audi → Essence (S1, S3, S4, S5, S6, S7, S8, SQ5, SQ7, SQ8)
    ("Audi", "sq",       ["essence"]),
    ("Audi", "s1",       ["essence"]),
    ("Audi", "s3",       ["essence"]),
    ("Audi", "s4",       ["essence"]),
    ("Audi", "s5",       ["essence"]),
    ("Audi", "s6",       ["essence"]),
    ("Audi", "s7",       ["essence"]),
    ("Audi", "s8",       ["essence"]),

    # ── BMW ───────────────────────────────────────────────────────────────────
    # BMW électriques (i + iX)
    ("BMW", "ix",  ["electrique"]),    # iX, iX1, iX2, iX3 — avant "i" pour priorité
    ("BMW", "i3",  ["electrique"]),
    ("BMW", "i3s", ["electrique"]),
    ("BMW", "i4",  ["electrique"]),
    ("BMW", "i5",  ["electrique"]),
    ("BMW", "i7",  ["electrique"]),
    # BMW M sportives → Essence uniquement
    ("BMW", "m2",  ["essence"]),
    ("BMW", "m3",  ["essence"]),
    ("BMW", "m4",  ["essence"]),
    ("BMW", "m5",  ["essence"]),
    ("BMW", "m6",  ["essence"]),
    ("BMW", "m8",  ["essence"]),

    # ── MERCEDES ──────────────────────────────────────────────────────────────
    # EQ électriques
    ("Mercedes", "eqa", ["electrique"]),
    ("Mercedes", "eqb", ["electrique"]),
    ("Mercedes", "eqc", ["electrique"]),
    ("Mercedes", "eqe", ["electrique"]),
    ("Mercedes", "eqs", ["electrique"]),
    # AMG GT → Essence
    ("Mercedes", "amg gt", ["essence"]),
    ("Mercedes", "classe sl",  ["essence"]),
    ("Mercedes", "classe slk", ["essence"]),

    # ── VOLKSWAGEN ────────────────────────────────────────────────────────────
    ("Volkswagen", "id.", ["electrique"]),   # ID.3, ID.4, ID.5, ID.6, ID.7
    ("Volkswagen", "id.buzz", ["electrique"]),

    # ── RENAULT ───────────────────────────────────────────────────────────────
    ("Renault", "zoe",              ["electrique"]),
    ("Renault", "twingo electric",  ["electrique"]),
    ("Renault", "kangoo electrique",["electrique"]),
    ("Renault", "scenic e-tech",    ["electrique"]),
    ("Renault", "megane e-tech",    ["essence", "electrique"]),  # E-Tech existe en hybride et BEV

    # ── PEUGEOT ───────────────────────────────────────────────────────────────
    ("Peugeot", "e-208",       ["electrique"]),
    ("Peugeot", "e-2008",      ["electrique"]),
    ("Peugeot", "ion",         ["electrique"]),
    ("Peugeot", "e-expert",    ["electrique"]),
    ("Peugeot", "e-rifter",    ["electrique"]),
    ("Peugeot", "e-traveller", ["electrique"]),

    # ── CITROEN ───────────────────────────────────────────────────────────────
    ("Citroen", "c-zero",        ["electrique"]),
    ("Citroen", "e-c4",          ["electrique"]),
    ("Citroen", "e-berlingo",    ["electrique"]),
    ("Citroen", "e-jumpy",       ["electrique"]),
    ("Citroen", "e-spacetourer", ["electrique"]),

    # ── OPEL ──────────────────────────────────────────────────────────────────
    ("Opel", "corsa-e",  ["electrique"]),
    ("Opel", "mokka-e",  ["electrique"]),
    ("Opel", "combo-e",  ["electrique"]),
    ("Opel", "vivaro-e", ["electrique"]),

    # ── FIAT ──────────────────────────────────────────────────────────────────
    ("Fiat", "500e",  ["electrique"]),

    # ── HYUNDAI ───────────────────────────────────────────────────────────────
    ("Hyundai", "ioniq 5",      ["electrique"]),
    ("Hyundai", "ioniq 6",      ["electrique"]),
    ("Hyundai", "ioniq 5 n",    ["electrique"]),
    ("Hyundai", "ioniq",        ["essence", "electrique"]),   # Ioniq 1ère gen = hybride
    ("Hyundai", "kona electric",["electrique"]),
    ("Hyundai", "nexo",         ["electrique"]),
    ("Hyundai", "i30 n",        ["essence"]),

    # ── KIA ───────────────────────────────────────────────────────────────────
    ("Kia", "ev3",     ["electrique"]),
    ("Kia", "ev6",     ["electrique"]),
    ("Kia", "ev9",     ["electrique"]),
    ("Kia", "niro ev", ["electrique"]),

    # ── NISSAN ────────────────────────────────────────────────────────────────
    ("Nissan", "leaf",  ["electrique"]),
    ("Nissan", "ariya", ["electrique"]),

    # ── HONDA ─────────────────────────────────────────────────────────────────
    ("Honda", "e:ny1", ["electrique"]),
    ("Honda", " e",    ["electrique"]),   # Honda e (espace avant pour éviter "cr-e…")

    # ── DACIA ─────────────────────────────────────────────────────────────────
    ("Dacia", "spring", ["electrique"]),

    # ── MG ────────────────────────────────────────────────────────────────────
    ("MG", "zs ev",    ["electrique"]),
    ("MG", "marvel r", ["electrique"]),
    ("MG", "5 ev",     ["electrique"]),
    ("MG", "4",        ["electrique"]),

    # ── SMART ─────────────────────────────────────────────────────────────────
    ("Smart", "#1",      ["electrique"]),
    ("Smart", "#3",      ["electrique"]),
    ("Smart", "fortwo",  ["essence", "electrique"]),
    ("Smart", "forfour", ["essence", "electrique"]),

    # ── VOLVO ─────────────────────────────────────────────────────────────────
    ("Volvo", "c40",   ["electrique"]),
    ("Volvo", "ex30",  ["electrique"]),
    ("Volvo", "ex90",  ["electrique"]),

    # ── GENESIS ───────────────────────────────────────────────────────────────
    ("Genesis", "gv60", ["electrique"]),

    # ── FORD ──────────────────────────────────────────────────────────────────
    ("Ford", "mustang mach-e", ["electrique"]),

    # ── JAGUAR ────────────────────────────────────────────────────────────────
    ("Jaguar", "i-pace", ["electrique"]),
    ("Jaguar", "f-type", ["essence"]),

    # ── MINI ──────────────────────────────────────────────────────────────────
    ("Mini", "cooper se",  ["electrique"]),

    # ── PORSCHE ───────────────────────────────────────────────────────────────
    ("Porsche", "taycan",              ["electrique"]),
    ("Porsche", "taycan cross turismo",["electrique"]),
    ("Porsche", "taycan sport turismo",["electrique"]),

    # ── ALFA ROMEO ────────────────────────────────────────────────────────────
    ("Alfa Romeo", "gtv",    ["essence"]),
    ("Alfa Romeo", "gt",     ["essence", "diesel"]),
    ("Alfa Romeo", "spider", ["essence"]),
    ("Alfa Romeo", "brera",  ["essence", "diesel"]),
    ("Alfa Romeo", "4c",     ["essence"]),

    # ── TESLA (redondant mais explicite) ──────────────────────────────────────
    ("Tesla", "", ["electrique"]),
]


def fuels_for(brand: str, model: str = "") -> list[str]:
    """
    Retourne les carburants plausibles pour une marque/modèle donnés.

    Priorité : règle modèle > règle marque > fallback ALL_FUELS.
    """
    model_lc = model.strip().lower()

    if model_lc and model_lc not in ("autre", ""):
        for b, m_substr, fuels in _MODEL_FUELS:
            if b == brand and m_substr in model_lc:
                return fuels

    if brand in _BRAND_FUELS:
        return _BRAND_FUELS[brand]

    return ALL_FUELS
