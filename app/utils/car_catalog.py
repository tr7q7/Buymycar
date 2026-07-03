import json
from pathlib import Path

_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "reference" / "car_catalog.json"


def load_catalog() -> dict[str, list[str]]:
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def brands() -> list[str]:
    return list(load_catalog().keys())


def models_for(brand: str) -> list[str]:
    return load_catalog().get(brand, [])
