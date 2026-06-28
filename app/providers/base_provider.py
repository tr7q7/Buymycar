from abc import ABC, abstractmethod
from typing import Any, List, Tuple
from app.models.listing import Listing


class BaseProvider(ABC):

    @abstractmethod
    def fetch(self) -> List[Listing]:
        """Retourne une liste d'annonces normalisées."""
        pass

    def fetch_with_report(self) -> Tuple[List[Listing], Any]:
        """
        Retourne (listings, rapport).

        Implémentation par défaut : appelle fetch() et retourne None comme rapport.
        Les providers qui produisent un rapport structuré (ImportReport, PiloterrMeta…)
        surchargent cette méthode.
        """
        return self.fetch(), None
