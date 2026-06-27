"""
Script de test du CsvProvider professionnel.
Usage : python -m scripts.test_csv_provider
"""
import sys
from pathlib import Path

# Permet d'importer les modules app/ depuis la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.csv_provider import CsvProvider

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "test_annonces_sales.csv"


def main():
    provider = CsvProvider(str(CSV_PATH))
    listings, report = provider.fetch_with_report()

    print("=" * 60)
    print(f"Annonces valides importées : {len(listings)}")
    print("=" * 60)
    print()
    print(report)
    print()

    if listings:
        print("=" * 60)
        print("3 premières annonces valides :")
        print("=" * 60)
        for listing in listings[:3]:
            print(
                f"  [{listing.id[:8]}] "
                f"{listing.brand} {listing.model} {listing.year} — "
                f"{listing.mileage:,} km — "
                f"{listing.price:,.0f} € — "
                f"{listing.fuel} / {listing.transmission} — "
                f"{listing.location}"
            )


if __name__ == "__main__":
    main()
