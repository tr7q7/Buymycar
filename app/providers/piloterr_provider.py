import logging
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from app.models.listing import Listing
from app.providers.base_provider import BaseProvider
from app.providers.provider_registry import register_provider


logger = logging.getLogger(__name__)

_API_BASE = "https://piloterr.com/api/v2/leboncoin/search"

# Piloterr attend un paramètre `query` contenant une URL LeBonCoin complète.
# Les filtres (marque, prix…) sont encodés directement dans cette URL LBC,
# pas en paramètres Piloterr séparés.
_TIMEOUT = 90        # secondes — chaque page Piloterr peut prendre ~30 s
_MAX_RETRIES = 1
_RETRY_DELAY = 2     # secondes
_LBC_PAGE_SIZE = 35  # nombre d'annonces par page LeBonCoin

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
    max_results: int = 200

    def to_query_params(self, lbc_url: str) -> dict:
        """
        Construit les paramètres Piloterr.

        Piloterr attend l'URL LeBonCoin complète dans `query`.
        Les filtres sont encodés directement dans cette URL, pas ici.
        """
        return {
            "query": lbc_url,
            "return_page_source": "false",
        }


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


# ── Utilitaire pagination ─────────────────────────────────────────────────────

def _with_page(url: str, page: int) -> str:
    """Ajoute ou remplace le paramètre `page` dans une URL LeBonCoin."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["page"] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


# ── Provider ──────────────────────────────────────────────────────────────────

@register_provider("piloterr")
class PiloterrProvider(BaseProvider):
    """
    Provider Piloterr — récupère des annonces LeBonCoin via l'API Piloterr.

    La clé API est lue depuis la variable d'environnement PILOTERR_API_KEY.
    Si dry_run=True et que la clé est absente, délègue à MockProvider.
    """

    def __init__(self, search_params: SearchParams, lbc_url: str = "", dry_run: bool = False):
        self.search_params = search_params
        self.lbc_url = lbc_url  # URL LeBonCoin complète à passer à Piloterr
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

    # ── Appel API — boucle de pagination ─────────────────────────────────────

    def _call_api(self) -> Tuple[List[Listing], PiloterrMeta]:
        if not self.lbc_url:
            raise PiloterrConfigError(
                "lbc_url est requis. Fournissez une URL LeBonCoin complète à PiloterrProvider."
            )

        all_listings: List[Listing] = []
        seen_ids: set = set()
        total_credits_used = 0
        total_credits_remaining = 0
        total_results = 0
        total_elapsed_ms = 0
        page = 1

        print(f"[DEBUG] _call_api démarré — max_results={self.search_params.max_results}", flush=True)
        while len(all_listings) < self.search_params.max_results:
            # page 1 : URL base sans paramètre page
            paged_url = self.lbc_url if page == 1 else _with_page(self.lbc_url, page)
            print(f"[DEBUG] page={page} url={paged_url}", flush=True)
            try:
                page_listings, page_meta = self._call_api_page(paged_url)
            except Exception as e:
                print(f"[DEBUG] page={page} EXCEPTION type={type(e).__name__} msg={e}", flush=True)
                if page == 1:
                    raise  # page 1 obligatoire : on laisse remonter l'erreur
                # pages suivantes : on conserve les annonces déjà collectées
                logger.warning("Page %d ignorée (%s) — arrêt pagination", page, e)
                break

            total_credits_used += page_meta.credits_used
            total_credits_remaining = page_meta.credits_remaining
            total_elapsed_ms += page_meta.response_time_ms
            if page == 1:
                total_results = page_meta.total_results

            # dédoublonnage par list_id
            new_count = 0
            for listing in page_listings:
                if listing.id not in seen_ids:
                    seen_ids.add(listing.id)
                    all_listings.append(listing)
                    new_count += 1

            print(f"[DEBUG] page={page} reçues={len(page_listings)} nouvelles={new_count} cumul={len(all_listings)}", flush=True)
            logger.info(
                "Page %d — %d annonces (+%d nouvelles, %d total)",
                page, len(page_listings), new_count, len(all_listings),
            )

            # conditions d'arrêt
            if not page_listings:
                break
            if len(page_listings) < _LBC_PAGE_SIZE:
                break  # dernière page (incomplète)
            if total_results > 0 and len(seen_ids) >= total_results:
                break

            page += 1

        all_listings = all_listings[: self.search_params.max_results]

        meta = PiloterrMeta(
            credits_used=total_credits_used,
            credits_remaining=total_credits_remaining,
            total_results=total_results,
            returned_results=len(all_listings),
            response_time_ms=total_elapsed_ms,
        )
        return all_listings, meta

    def _call_api_page(self, paged_url: str) -> Tuple[List[Listing], PiloterrMeta]:
        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        params = self.search_params.to_query_params(paged_url)
        last_error: Exception = PiloterrError("Erreur inconnue")

        for attempt in range(_MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                response = requests.get(_API_BASE, headers=headers, params=params, timeout=_TIMEOUT)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                return self._handle_response(response, elapsed_ms)

            except (PiloterrAuthError, PiloterrQuotaError, PiloterrParseError):
                raise

            except requests.Timeout:
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
            print(f"[DEBUG] HTTP 500 body={response.text[:300]}", flush=True)
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
            total_results=data.get("total", 0),
            returned_results=len(listings),
            response_time_ms=elapsed_ms,
        )
        return listings, meta

    # ── Parsing JSON → Listing ────────────────────────────────────────────────

    def _parse_response(self, data: dict) -> List[Listing]:
        if not isinstance(data, dict):
            raise PiloterrParseError("La réponse n'est pas un objet JSON")

        raw_list = data.get("ads", [])
        if not isinstance(raw_list, list):
            raise PiloterrParseError("Clé 'ads' absente ou non-liste dans la réponse")

        listings: List[Listing] = []
        skipped = 0

        for item in raw_list:
            try:
                listing = self._map_item(item)
                listings.append(listing)
            except Exception as e:
                skipped += 1
                logger.debug("Annonce ignorée au parsing : %s — %s", item.get("list_id", "?"), e)

        if skipped:
            logger.info("%d annonce(s) ignorée(s) sur %d au parsing", skipped, skipped + len(listings))

        return listings

    @staticmethod
    def _map_item(item: dict) -> Listing:
        # Construire un index {key: attribute} depuis la liste attributes
        raw_attrs = item.get("attributes") or []
        attrs = {a["key"]: a for a in raw_attrs if isinstance(a, dict) and "key" in a}
        loc = item.get("location") or {}

        def attr_value(key: str) -> str:
            return str(attrs[key]["value"]).strip() if key in attrs else ""

        def attr_label(key: str) -> str:
            return str(attrs[key].get("value_label", attrs[key]["value"])).strip() if key in attrs else ""

        # ── Champs obligatoires ───────────────────────────────────────────────
        price_list = item.get("price") or []
        if not price_list:
            raise ValueError("Prix absent")
        price = float(price_list[0])

        regdate = attr_value("regdate")
        if not regdate:
            raise ValueError("Date d'immatriculation absente")
        year = int(str(regdate)[:4])

        mileage_raw = attr_value("mileage")
        if not mileage_raw:
            raise ValueError("Kilométrage absent")
        mileage = int(mileage_raw)

        brand = attr_value("brand")
        if not brand:
            raise ValueError("Marque absente")

        model = attr_value("model")

        # ── Champs optionnels ─────────────────────────────────────────────────
        # fuel et gearbox : value_label contient le libellé lisible ("Hybride", "Automatique")
        fuel = _norm(attr_label("fuel"), _FUEL_MAP)
        transmission = _norm(attr_label("gearbox"), _TRANSMISSION_MAP)
        location = (loc.get("city") or loc.get("department_name") or "").strip()
        title = (item.get("subject") or "").strip()
        url = (item.get("url") or "").strip()
        published_at = (item.get("first_publication_date") or "").strip()

        listing_id = str(item.get("list_id") or "").strip()
        if not listing_id:
            raise ValueError("list_id absent")

        images = item.get("images") or {}
        image_url = (
            images.get("small_url")
            or (images.get("urls") or [None])[0]
            or ""
        ).strip()

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
            image_url=image_url,
        )

    # ── Fallback dry-run ──────────────────────────────────────────────────────

    def _fallback_mock(self) -> Tuple[List[Listing], PiloterrMeta]:
        from app.providers.mock_provider import MockProvider
        listings = MockProvider(n=50).fetch()
        meta = PiloterrMeta(is_dry_run=True, returned_results=len(listings))
        logger.info("Dry-run : %d annonces fictives générées", len(listings))
        return listings, meta
