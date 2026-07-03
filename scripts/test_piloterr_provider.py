"""
Script de test du PiloterrProvider.

Modes :
  - Sans clé API : dry-run automatique (données fictives MockProvider)
  - Avec clé API : appel réel Piloterr avec pagination

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
    pass

from app.providers.piloterr_provider import (
    PiloterrProvider,
    SearchParams,
    PiloterrError,
    _with_page,
)
from app.providers.leboncoin_query_builder import LeboncoinQueryBuilder


def test_with_page():
    """Vérifie que _with_page injecte correctement le paramètre page."""
    base = "https://www.leboncoin.fr/voitures/offres?text=renault+clio&fuel=2"
    assert "page=1" in _with_page(base, 1)
    assert "page=3" in _with_page(base, 3)
    # remplacement d'un page existant
    url_with_page = _with_page(base, 1)
    assert "page=2" in _with_page(url_with_page, 2)
    assert "page=1" not in _with_page(url_with_page, 2)
    print("  [OK] _with_page")


def main():
    print("=" * 60)
    print("Test PiloterrProvider — pagination")
    print("=" * 60)

    # ── Tests unitaires ───────────────────────────────────────────────────────
    print("\n[Tests unitaires]")
    test_with_page()

    # ── Test d'intégration ────────────────────────────────────────────────────
    print("\n[Test d'intégration]")

    params = SearchParams(
        brand="renault",
        model="clio",
        year_min=2018,
        fuel="diesel",
        max_results=200,
    )

    builder = LeboncoinQueryBuilder(params)
    lbc_url = builder.build()
    unsupported = builder.unsupported_filters()

    print(f"URL LBC (page 1) : {_with_page(lbc_url, 1)}")
    if unsupported:
        print("Filtres applicatifs (non encodés dans l'URL) :")
        for f in unsupported:
            print(f"  - {f}")
    print(f"max_results      : {params.max_results}")
    print()

    try:
        provider = PiloterrProvider(search_params=params, lbc_url=lbc_url, dry_run=True)
        listings, meta = provider.fetch_with_meta()
    except PiloterrError as e:
        print(f"Erreur Piloterr : {e}")
        sys.exit(1)

    print(meta)
    print()
    print(f"Annonces récupérées : {len(listings)}")
    print(f"Total Piloterr      : {meta.total_results}")
    print(f"Doublons éliminés   : {meta.total_results - len(listings) if meta.total_results > len(listings) else 0}")
    print()

    if listings:
        # Vérification absence de doublons
        ids = [l.id for l in listings]
        duplicates = len(ids) - len(set(ids))
        print(f"Doublons restants (doit être 0) : {duplicates}")
        assert duplicates == 0, f"Des doublons sont présents : {duplicates}"
        print()

        print("=" * 60)
        print("5 premières annonces :")
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

    print("\n[OK] Tous les tests passent.")


if __name__ == "__main__":
    main()
