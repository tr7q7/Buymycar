from app.providers.base_provider import BaseProvider
from app.providers.mock_provider import MockProvider
from app.providers.csv_provider import CsvProvider


def get_provider(source: str, **kwargs) -> BaseProvider:
    if source == "mock":
        return MockProvider(
            n=kwargs.get("n", 120),
            seed=kwargs.get("seed", 42),
        )
    if source == "csv":
        return CsvProvider(filepath=kwargs["filepath"])
    raise ValueError(f"Source inconnue : {source}")
