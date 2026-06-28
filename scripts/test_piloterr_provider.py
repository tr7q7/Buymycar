"""
Script de test du PiloterrProvider.

Modes :
  - Sans clé API : dry-run automatique (données fictives MockProvider)
  - Avec clé API : appel réel Piloterr

Usage :
  python -m scripts.test_piloterr_provider
  PILOTERR_API_KEY=xxx python -m scripts.test_piloterr_provider

La clé peut aussi être définie dans un fichier .env à la racine du projet :
  PILOTERR_API_KEY=ta_cle_ici
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # python-dotenv absent : on continue sans lui, dry-run prendra le relais

from app.providers.piloterr_provider import (
    PiloterrProvider,
    SearchParams,
    PiloterrError,
)
from app.providers.leboncoin_query_builder import LeboncoinQueryBuilder


def main():
    params = SearchParams(
        brand="renault",
        model="clio",
        year_min=2018,
        price_max=15000,
        fuel="diesel",
    )

    builder = LeboncoinQueryBuilder(params)
    lbc_url = builder.build()
    unsupported = builder.unsupported_filters()

    print("=" * 60)
    print("Test PiloterrProvider")
    print("=" * 60)
    print(f"URL LBC : {lbc_url}")
    if unsupported:
        print(f"Filtres applicatifs (non encodes dans l'URL) :")
        for f in unsupported:
            print(f"  - {f}")
    print()

    try:
        provider = PiloterrProvider(search_params=params, lbc_url=lbc_url, dry_run=True)
        listings, meta = provider.fetch_with_meta()
    except PiloterrError as e:
        print(f"Erreur Piloterr : {e}")
        sys.exit(1)

    print(meta)
    print()
    print(f"Annonces parsees  : {len(listings)}")
    print(f"Total Piloterr    : {meta.total_results}")
    print()

    if listings:
        print("=" * 60)
        print("5 premieres annonces :")
        print("=" * 60)
        for listing in listings[:5]:
            print(
                f"  {listing.brand} {listing.model} {listing.year} — "
                f"{listing.mileage:,} km — "
                f"{listing.price:,.0f} EUR — "
                f"{listing.location}"
            )
            print(f"    {listing.title[:70]}")
            print(f"    {listing.url}")


if __name__ == "__main__":
    main()
