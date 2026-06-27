import csv
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from app.providers.base_provider import BaseProvider
from app.models.listing import Listing

logger = logging.getLogger(__name__)

# ── Synonymes de colonnes ─────────────────────────────────────────────────────

_COLUMN_ALIASES: dict[str, list[str]] = {
    "brand":        ["brand", "marque", "make", "constructeur", "fabricant"],
    "model":        ["model", "modele", "modèle", "version"],
    "year":         ["year", "annee", "année", "an", "mise_en_circulation", "year_of_registration"],
    "mileage":      ["mileage", "kilometrage", "kilométrage", "km", "miles", "odometer"],
    "price":        ["price", "prix", "tarif", "cout", "coût", "montant"],
    "fuel":         ["fuel", "carburant", "energie", "énergie", "motorisation"],
    "transmission": ["transmission", "boite", "boîte", "gearbox", "gear"],
    "location":     ["location", "ville", "city", "departement", "département", "lieu"],
    "id":           ["id", "identifiant", "ref", "reference", "référence"],
    "source":       ["source", "origine", "plateforme"],
}

_REQUIRED_FIELDS = {"brand", "model", "year", "mileage", "price"}

# ── Tables de normalisation ───────────────────────────────────────────────────

_FUEL_MAP: dict[str, str] = {
    "essence": "essence", "sp95": "essence", "sp98": "essence",
    "sans plomb": "essence", "sp": "essence", "superethanol": "essence",
    "diesel": "diesel", "gazole": "diesel", "gasoil": "diesel", "go": "diesel",
    "electrique": "electrique", "électrique": "electrique",
    "ev": "electrique", "bev": "electrique", "electric": "electrique",
    "hybride": "hybride", "hybrid": "hybride", "hev": "hybride",
    "phev": "hybride", "hybride rechargeable": "hybride",
    "gpl": "gpl", "gnv": "gnv",
}

_TRANSMISSION_MAP: dict[str, str] = {
    "manuelle": "manuelle", "bvm": "manuelle", "mecanique": "manuelle",
    "mécanique": "manuelle", "manual": "manuelle",
    "automatique": "automatique", "bva": "automatique", "auto": "automatique",
    "cvt": "automatique", "dsg": "automatique", "automatic": "automatique",
}


# ── Dataclasses du rapport ────────────────────────────────────────────────────

@dataclass
class ImportError:
    line: int
    reason: str
    raw_data: dict


@dataclass
class ImportReport:
    source_file: str
    total_rows: int = 0
    valid_rows: int = 0
    ignored_rows: int = 0
    errors: List[ImportError] = field(default_factory=list)
    unmapped_columns: List[str] = field(default_factory=list)
    critical_error: Optional[str] = None

    def __str__(self) -> str:
        lines = [
            f"Import terminé — fichier : {self.source_file}",
            f"  Lignes lues      : {self.total_rows}",
            f"  Annonces valides : {self.valid_rows}",
            f"  Lignes ignorées  : {self.ignored_rows}",
        ]
        if self.unmapped_columns:
            lines.append(f"  Colonnes non reconnues : {self.unmapped_columns}")
        if self.critical_error:
            lines.append(f"  ERREUR CRITIQUE : {self.critical_error}")
        if self.errors:
            lines.append("Erreurs rencontrées :")
            for e in self.errors[:20]:
                lines.append(f"  L.{e.line:>4}  — {e.reason}")
            if len(self.errors) > 20:
                lines.append(f"  ... et {len(self.errors) - 20} autres erreurs")
        return "\n".join(lines)


# ── Fonctions de nettoyage ────────────────────────────────────────────────────

def _strip_accents(text: str) -> str:
    replacements = str.maketrans("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ",
                                 "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return text.translate(replacements)


def _normalize_key(text: str) -> str:
    return _strip_accents(text.strip().lower().replace(" ", "_").replace("-", "_"))


def _build_column_map(headers: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Retourne (mapping {nom_original → champ_cible}, colonnes_non_reconnues).
    """
    alias_lookup: dict[str, str] = {}
    for target, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_normalize_key(alias)] = target

    mapping: dict[str, str] = {}
    unmapped: list[str] = []
    for header in headers:
        key = _normalize_key(header)
        if key in alias_lookup:
            mapping[header] = alias_lookup[key]
        else:
            unmapped.append(header)
    return mapping, unmapped


def _parse_number(raw: str) -> float:
    """
    Convertit une chaîne en float en gérant les formats européens et anglo-saxons.
    Exemples : "9 500 €" → 9500.0 / "9.500" → 9500.0 / "9,500.50" → 9500.5
    """
    cleaned = re.sub(r"[€$£\s]", "", raw).strip()
    # Supprimer les séparateurs de milliers ambigus
    # Si le nombre contient à la fois . et , → format mixte
    if "." in cleaned and "," in cleaned:
        # "9,500.50" → anglo-saxon
        if cleaned.index(",") < cleaned.index("."):
            cleaned = cleaned.replace(",", "")
        else:
            # "9.500,50" → européen
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        # "9500,50" → décimale européenne ou "9,500" → milliers anglo-saxon
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            cleaned = cleaned.replace(",", "")   # séparateur milliers
        else:
            cleaned = cleaned.replace(",", ".")  # décimale européenne
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            cleaned = cleaned.replace(".", "")   # "9.500" européen = 9500
        # sinon c'est un vrai point décimal → rien à faire

    return float(cleaned)


def _parse_year(raw: str) -> int:
    """Accepte : 2019 / 01/2019 / 2019-03-15 / 03-2019"""
    raw = raw.strip()
    # Année seule
    if re.fullmatch(r"\d{4}", raw):
        return int(raw)
    # MM/YYYY ou MM-YYYY
    m = re.fullmatch(r"\d{1,2}[/\-]\d{4}", raw)
    if m:
        return int(raw[-4:])
    # YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})-\d{2}-\d{2}", raw)
    if m:
        return int(m.group(1))
    raise ValueError(f"Format d'année non reconnu : {raw!r}")


def _parse_mileage(raw: str) -> int:
    cleaned = re.sub(r"[kKmM\s]", "", raw).strip()
    return int(_parse_number(cleaned))


def _normalize_fuel(raw: str) -> str:
    return _FUEL_MAP.get(_normalize_key(raw), raw.strip().lower())


def _normalize_transmission(raw: str) -> str:
    return _TRANSMISSION_MAP.get(_normalize_key(raw), raw.strip().lower())


def _validate(listing_data: dict) -> Optional[str]:
    """Retourne un message d'erreur si la ligne est invalide, None sinon."""
    current_year = date.today().year

    brand = listing_data.get("brand", "").strip()
    if not brand:
        return "Marque manquante"

    model = listing_data.get("model", "").strip()
    if not model:
        return "Modèle manquant"

    year = listing_data.get("year")
    if year is None or not (1990 <= year <= current_year + 1):
        return f"Année hors plage : {year!r}"

    mileage = listing_data.get("mileage")
    if mileage is None or not (0 <= mileage <= 1_000_000):
        return f"Kilométrage invalide : {mileage!r}"

    price = listing_data.get("price")
    if price is None or not (0 < price <= 500_000):
        return f"Prix invalide : {price!r}"

    return None


# ── Provider ──────────────────────────────────────────────────────────────────

class CsvProvider(BaseProvider):
    """
    Provider CSV universel.

    Détecte automatiquement les colonnes, normalise les formats et ignore
    les lignes invalides sans faire planter l'import.

    Utiliser fetch_with_report() pour obtenir le rapport d'import détaillé,
    ou fetch() pour rester compatible avec BaseProvider.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    def fetch(self) -> List[Listing]:
        listings, _ = self.fetch_with_report()
        return listings

    def fetch_with_report(self) -> Tuple[List[Listing], ImportReport]:
        path = Path(self.filepath)
        report = ImportReport(source_file=path.name)

        if not path.exists():
            msg = f"Fichier introuvable : {self.filepath}"
            report.critical_error = msg
            logger.error(msg)
            return [], report

        content = self._read_file(path)
        if content is None:
            report.critical_error = "Impossible de lire le fichier (encodage inconnu)"
            return [], report

        if not content.strip():
            report.critical_error = "Fichier vide"
            return [], report

        try:
            dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;|\t")
        except csv.Error:
            dialect = csv.excel  # fallback : virgule

        reader = csv.DictReader(content.splitlines(), dialect=dialect)

        if not reader.fieldnames:
            report.critical_error = "Aucun en-tête détecté"
            return [], report

        col_map, unmapped = _build_column_map(list(reader.fieldnames))
        report.unmapped_columns = unmapped

        mapped_targets = set(col_map.values())
        missing_required = _REQUIRED_FIELDS - mapped_targets
        if missing_required:
            report.critical_error = f"Colonnes obligatoires introuvables : {missing_required}"
            logger.error(report.critical_error)
            return [], report

        listings: List[Listing] = []

        for line_num, row in enumerate(reader, start=2):
            report.total_rows += 1
            raw = {col_map[k]: v for k, v in row.items() if k in col_map}

            try:
                parsed = self._parse_row(raw)
            except Exception as e:
                reason = str(e)
                report.ignored_rows += 1
                report.errors.append(ImportError(line=line_num, reason=reason, raw_data=dict(row)))
                logger.debug("Ligne %d ignorée : %s", line_num, reason)
                continue

            error = _validate(parsed)
            if error:
                report.ignored_rows += 1
                report.errors.append(ImportError(line=line_num, reason=error, raw_data=dict(row)))
                logger.debug("Ligne %d invalide : %s", line_num, error)
                continue

            listings.append(Listing(
                id=parsed.get("id") or str(uuid.uuid4()),
                brand=parsed["brand"].strip().title(),
                model=parsed["model"].strip(),
                year=parsed["year"],
                mileage=parsed["mileage"],
                price=parsed["price"],
                fuel=parsed.get("fuel", ""),
                transmission=parsed.get("transmission", ""),
                location=parsed.get("location", "").strip(),
                source=parsed.get("source", "csv"),
            ))
            report.valid_rows += 1

        logger.info(str(report))
        return listings, report

    # ── Helpers privés ────────────────────────────────────────────────────────

    @staticmethod
    def _read_file(path: Path) -> Optional[str]:
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "windows-1252"):
            try:
                return path.read_text(encoding=encoding)
            except (UnicodeDecodeError, OSError):
                continue
        return None

    @staticmethod
    def _parse_row(raw: dict) -> dict:
        parsed: dict = {}

        parsed["brand"] = raw.get("brand", "").strip()
        parsed["model"] = raw.get("model", "").strip()

        year_raw = raw.get("year", "").strip()
        if not year_raw:
            raise ValueError("Année manquante")
        parsed["year"] = _parse_year(year_raw)

        mileage_raw = raw.get("mileage", "").strip()
        if not mileage_raw:
            raise ValueError("Kilométrage manquant")
        parsed["mileage"] = _parse_mileage(mileage_raw)

        price_raw = raw.get("price", "").strip()
        if not price_raw:
            raise ValueError("Prix manquant")
        parsed["price"] = _parse_number(price_raw)

        fuel_raw = raw.get("fuel", "").strip()
        parsed["fuel"] = _normalize_fuel(fuel_raw) if fuel_raw else ""

        trans_raw = raw.get("transmission", "").strip()
        parsed["transmission"] = _normalize_transmission(trans_raw) if trans_raw else ""

        parsed["location"] = raw.get("location", "").strip()
        parsed["source"] = raw.get("source", "csv").strip() or "csv"

        raw_id = raw.get("id", "").strip()
        parsed["id"] = raw_id if raw_id else str(uuid.uuid4())

        return parsed
