"""
Script de test du PiloterrProvider.

Modes :
  - Sans clé API : dry-run automatique (données fictives MockProvider)
  - Avec clé API : appel réel Piloterr

Usage :
  python -m scripts.test_piloterr_provider
  PILOTERR_API_KEY=xxx python -m scripts.test_piloterr_provider
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.piloterr_provider import (
    PiloterrProvider,
    SearchParams,
    PiloterrError,
)


def main():
    params = SearchParams(
        brand="renault",
        model="clio",
        year_min=2018,
        price_max=15000,
        limit=20,
    )

    print("=" * 60)
    print("Test PiloterrProvider")
    print("=" * 60)
    print(f"Recherche : {params.brand} {params.model or ''} "
          f">={params.year_min} <={params.price_max} EUR")
    print()

    try:
        provider = PiloterrProvider(search_params=params, dry_run=True)
        listings, meta = provider.fetch_with_meta()
    except PiloterrError as e:
        print(f"Erreur Piloterr : {e}")
        sys.exit(1)

    print(meta)
    print()
    print(f"Annonces reçues : {len(listings)}")
    print()

    if listings:
        print("=" * 60)
        print("3 premières annonces :")
        print("=" * 60)
        for listing in listings[:3]:
            print(
                f"  [{listing.id[:12]}] "
                f"{listing.brand} {listing.model} {listing.year} — "
                f"{listing.mileage:,} km — "
                f"{listing.price:,.0f} € — "
                f"{listing.fuel} / {listing.transmission} — "
                f"{listing.location}"
            )
            if listing.url:
                print(f"    {listing.url}")


if __name__ == "__main__":
    main()
