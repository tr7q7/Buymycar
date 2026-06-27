from abc import ABC, abstractmethod
from typing import List
from app.models.listing import Listing


class BaseProvider(ABC):
    @abstractmethod
    def fetch(self) -> List[Listing]:
        """Retourne une liste d'annonces normalisées."""
        pass
