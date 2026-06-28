"""
Tests du LeboncoinQueryBuilder.
Usage : python -m scripts.test_leboncoin_query_builder
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.providers.piloterr_provider import SearchParams
from app.providers.leboncoin_query_builder import LeboncoinQueryBuilder

TESTS = [
    ("Brand seul",
     SearchParams(brand="renault"),
     "https://www.leboncoin.fr/recherche?category=2&text=renault"),

    ("Brand + model (text combine)",
     SearchParams(brand="peugeot", model="308"),
     "https://www.leboncoin.fr/recherche?category=2&text=peugeot+308"),

    ("Fuel essence (code=1 valide)",
     SearchParams(brand="renault", model="clio", fuel="essence"),
     "https://www.leboncoin.fr/recherche?category=2&text=renault+clio&fuel=1"),

    ("Fuel diesel (code=2 valide)",
     SearchParams(brand="volkswagen", model="golf", fuel="diesel"),
     "https://www.leboncoin.fr/recherche?category=2&text=volkswagen+golf&fuel=2"),

    ("Fuel electrique (code=4 valide)",
     SearchParams(brand="renault", model="zoe", fuel="electrique"),
     "https://www.leboncoin.fr/recherche?category=2&text=renault+zoe&fuel=4"),

    ("Fuel hybride (non valide, omis)",
     SearchParams(brand="toyota", model="yaris", fuel="hybride"),
     "https://www.leboncoin.fr/recherche?category=2&text=toyota+yaris"),

    ("Gearbox manuelle (code=1 valide)",
     SearchParams(brand="renault", transmission="manuelle"),
     "https://www.leboncoin.fr/recherche?category=2&text=renault&gearbox=1"),

    ("Gearbox automatique (non valide, omis)",
     SearchParams(brand="bmw", transmission="automatique"),
     "https://www.leboncoin.fr/recherche?category=2&text=bmw"),

    ("Filtres non valides signales",
     SearchParams(brand="renault", model="clio", year_min=2018,
                  price_max=15000, mileage_max=100000, transmission="automatique"),
     "https://www.leboncoin.fr/recherche?category=2&text=renault+clio"),
]

passed = 0
failed = 0

print("=" * 65)
print("Tests LeboncoinQueryBuilder")
print("=" * 65)

for label, params, expected_url in TESTS:
    builder = LeboncoinQueryBuilder(params)
    result = builder.build()
    ok = result == expected_url
    status = "OK" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"[{status}] {label}")
    if not ok:
        print(f"     attendu : {expected_url}")
        print(f"     obtenu  : {result}")

    unsupported = builder.unsupported_filters()
    if unsupported:
        print(f"     filtres applicatifs : {unsupported}")

print()
print(f"Resultat : {passed}/{len(TESTS)} passes, {failed} echec(s)")
