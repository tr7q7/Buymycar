import logging
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import requests

from app.models.listing import Listing
from app.providers.base_provider import BaseProvider
from app.utils.formatting import make_listing_id

logger = logging.getLogger(__name__)

_API_BASE = "https://piloterr.com/api/v2/leboncoin/search"
_TIMEOUT = 10        # secondes
_MAX_RETRIES = 1
_RETRY_DELAY = 2     # secondes

# ── Normalisation carburant / boîte (réutilise la logique CsvProvider) ────────

_FUEL_MAP = {
    "essence": "essence", "sp95": "essence", "sp98": "essence", "sans plomb": "essence",
    "diesel": "diesel", "gazole": "diesel",
    "electrique": "electrique", "électrique": "electrique", "ev": "electrique",
    "hybride": "hybride", "hybrid": "hybride", "phev": "hybride",
    "gpl": "gpl", "gnv": "gnv",
}

_TRANSMISSION_MAP = {
    "manuelle": "manuelle", "bvm": "manuelle", "manual": "manuelle",
    "automatique": "automatique", "bva": "automatique", "auto": "automatique",
    "cvt": "automatique", "dsg": "automatique",
}


def _norm(value: str, table: dict) -> str:
    return table.get(value.strip().lower(), value.strip().lower())


# ── Exceptions ────────────────────────────────────────────────────────────────

class PiloterrError(Exception):
    """Erreur de base Piloterr."""


class PiloterrConfigError(PiloterrError):
    """Clé API absente ou vide."""


class PiloterrAuthError(PiloterrError):
    """HTTP 401 — clé invalide ou expirée."""


class PiloterrQuotaError(PiloterrError):
    """HTTP 429 — quota de crédits dépassé."""


class PiloterrServerError(PiloterrError):
    """HTTP 5xx — erreur côté Piloterr."""


class PiloterrTimeoutError(PiloterrError):
    """Pas de réponse dans le délai imparti."""


class PiloterrParseError(PiloterrError):
    """Réponse 200 mais JSON inattendu ou illisible."""


# ── Objets de paramètres et de métadonnées ────────────────────────────────────

@dataclass
class SearchParams:
    brand: str
    model: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    mileage_max: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    location: Optional[str] = None
    limit: int = 50

    def to_query_params(self) -> dict:
        params: dict = {"brand": self.brand, "limit": self.limit}
        if self.model:
            params["model"] = self.model
        if self.year_min:
            params["regdate_min"] = self.year_min
        if self.year_max:
            params["regdate_max"] = self.year_max
        if self.mileage_max:
            params["mileage_max"] = self.mileage_max
        if self.price_min:
            params["price_min"] = int(self.price_min)
        if self.price_max:
            params["price_max"] = int(self.price_max)
        if self.fuel:
            params["fuel"] = self.fuel
        if self.transmission:
            params["gearbox"] = self.transmission
        if self.location:
            params["locations"] = self.location
        return params


@dataclass
class PiloterrMeta:
    credits_used: int = 0
    credits_remaining: int = 0
    total_results: int = 0
    returned_results: int = 0
    response_time_ms: int = 0
    is_dry_run: bool = False

    def __str__(self) -> str:
        if self.is_dry_run:
            return "Mode dry-run — aucun crédit consommé (données fictives MockProvider)"
        return (
            f"Crédits utilisés : {self.credits_used} | "
            f"Restants : {self.credits_remaining} | "
            f"Résultats : {self.returned_results}/{self.total_results} | "
            f"Temps : {self.response_time_ms} ms"
        )


# ── Provider ──────────────────────────────────────────────────────────────────

class PiloterrProvider(BaseProvider):
    """
    Provider Piloterr — récupère des annonces LeBonCoin via l'API Piloterr.

    La clé API est lue depuis la variable d'environnement PILOTERR_API_KEY.
    Si dry_run=True et que la clé est absente, délègue à MockProvider.
    """

    def __init__(self, search_params: SearchParams, dry_run: bool = False):
        self.search_params = search_params
        self.dry_run = dry_run
        self._api_key = self._load_api_key()

    def _load_api_key(self) -> Optional[str]:
        key = os.environ.get("PILOTERR_API_KEY", "").strip()
        if key:
            return key
        if self.dry_run:
            logger.warning(
                "PILOTERR_API_KEY absente — mode dry-run activé (données fictives MockProvider)"
            )
            return None
        raise PiloterrConfigError(
            "Variable d'environnement PILOTERR_API_KEY absente ou vide. "
            "Définissez-la ou instanciez le provider avec dry_run=True."
        )

    # ── Interface publique ────────────────────────────────────────────────────

    def fetch(self) -> List[Listing]:
        listings, _ = self.fetch_with_meta()
        return listings

    def fetch_with_meta(self) -> Tuple[List[Listing], PiloterrMeta]:
        if self._api_key is None:
            return self._fallback_mock()
        return self._call_api()

    # ── Appel API ─────────────────────────────────────────────────────────────

    def _call_api(self) -> Tuple[List[Listing], PiloterrMeta]:
        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        params = self.search_params.to_query_params()
        last_error: Exception = PiloterrError("Erreur inconnue")

        for attempt in range(_MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                response = requests.get(_API_BASE, headers=headers, params=params, timeout=_TIMEOUT)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                return self._handle_response(response, elapsed_ms)

            except (PiloterrAuthError, PiloterrQuotaError, PiloterrParseError):
                raise  # pas de retry sur ces erreurs

            except requests.Timeout as e:
                last_error = PiloterrTimeoutError(f"Timeout après {_TIMEOUT}s")
                logger.warning("Tentative %d/%d — timeout", attempt + 1, _MAX_RETRIES + 1)

            except requests.ConnectionError as e:
                last_error = PiloterrTimeoutError(f"Erreur réseau : {e}")
                logger.warning("Tentative %d/%d — connexion impossible", attempt + 1, _MAX_RETRIES + 1)

            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

        raise last_error

    def _handle_response(self, response: requests.Response, elapsed_ms: int) -> Tuple[List[Listing], PiloterrMeta]:
        if response.status_code == 401:
            raise PiloterrAuthError("Clé API invalide ou expirée (HTTP 401)")

        if response.status_code == 429:
            raise PiloterrQuotaError("Quota de crédits épuisé (HTTP 429)")

        if response.status_code >= 500:
            raise PiloterrServerError(f"Erreur serveur Piloterr (HTTP {response.status_code})")

        if response.status_code != 200:
            raise PiloterrError(f"Réponse inattendue (HTTP {response.status_code})")

        try:
            data = response.json()
        except Exception as e:
            raise PiloterrParseError(f"JSON illisible : {e}") from e

        listings = self._parse_response(data)

        meta = PiloterrMeta(
            credits_used=data.get("credits_used", 0),
            credits_remaining=data.get("credits_remaining", 0),
            total_results=data.get("total", len(listings)),
            returned_results=len(listings),
            response_time_ms=elapsed_ms,
        )
        return listings, meta

    # ── Parsing JSON → Listing ────────────────────────────────────────────────

    def _parse_response(self, data: dict) -> List[Listing]:
        if not isinstance(data, dict):
            raise PiloterrParseError("La réponse n'est pas un objet JSON")

        raw_list = data.get("data", [])
        if not isinstance(raw_list, list):
            raise PiloterrParseError("Clé 'data' absente ou non-liste dans la réponse")

        listings: List[Listing] = []
        skipped = 0

        for item in raw_list:
            try:
                listing = self._map_item(item)
                listings.append(listing)
            except Exception as e:
                skipped += 1
                logger.debug("Annonce ignorée au parsing : %s — %s", item.get("id", "?"), e)

        if skipped:
            logger.info("%d annonce(s) ignorée(s) sur %d au parsing", skipped, skipped + len(listings))

        return listings

    @staticmethod
    def _map_item(item: dict) -> Listing:
        attrs = item.get("attributes") or {}
        loc = item.get("location") or {}

        # ── Champs obligatoires ───────────────────────────────────────────────
        price_list = item.get("price") or []
        if not price_list:
            raise ValueError("Prix absent")
        price = float(price_list[0])

        regdate = attrs.get("regdate", "")
        if not regdate:
            raise ValueError("Date d'immatriculation absente")
        year = int(str(regdate)[:4])

        mileage_raw = attrs.get("mileage")
        if mileage_raw is None:
            raise ValueError("Kilométrage absent")
        mileage = int(mileage_raw)

        brand = (attrs.get("brand") or "").strip()
        if not brand:
            raise ValueError("Marque absente")

        model = (attrs.get("model") or "").strip()

        # ── Champs optionnels ─────────────────────────────────────────────────
        fuel = _norm(attrs.get("fuel") or "", _FUEL_MAP)
        transmission = _norm(attrs.get("gearbox") or "", _TRANSMISSION_MAP)
        location = (loc.get("city") or loc.get("department_id") or "").strip()
        title = (item.get("subject") or "").strip()
        url = (item.get("url") or "").strip()
        published_at = (item.get("first_publication_date") or "").strip()
        source_id = str(item.get("id") or "")

        listing_id = make_listing_id(
            url=url,
            brand=brand, model=model, year=year,
            mileage=mileage, price=price,
            location=location, title=title,
        ) if not source_id else source_id

        return Listing(
            id=listing_id,
            brand=brand.title(),
            model=model,
            year=year,
            mileage=mileage,
            price=price,
            fuel=fuel,
            transmission=transmission,
            location=location,
            source="piloterr-leboncoin",
            title=title,
            url=url,
            published_at=published_at,
        )

    # ── Fallback dry-run ──────────────────────────────────────────────────────

    def _fallback_mock(self) -> Tuple[List[Listing], PiloterrMeta]:
        from app.providers.mock_provider import MockProvider
        listings = MockProvider(n=50).fetch()
        meta = PiloterrMeta(is_dry_run=True, returned_results=len(listings))
        logger.info("Dry-run : %d annonces fictives générées", len(listings))
        return listings, meta
