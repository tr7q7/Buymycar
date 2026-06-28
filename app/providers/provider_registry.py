import logging
from typing import Callable, Type, TypeVar

from app.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseProvider)


class RegistryConflictError(Exception):
    """Deux providers enregistrés sous le même nom."""


class ProviderNotFoundError(Exception):
    """Nom de provider inconnu du registre."""


class _ProviderRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type[BaseProvider]] = {}

    def register(self, name: str, cls: type[BaseProvider]) -> None:
        if name in self._registry:
            raise RegistryConflictError(
                f"Provider '{name}' déjà enregistré par {self._registry[name].__name__}. "
                f"Impossible d'enregistrer {cls.__name__} sous le même nom."
            )
        self._registry[name] = cls
        logger.debug("Provider enregistré : '%s' → %s", name, cls.__name__)

    def get(self, name: str) -> type[BaseProvider]:
        if name not in self._registry:
            available = ", ".join(sorted(self._registry)) or "(aucun)"
            raise ProviderNotFoundError(
                f"Provider '{name}' inconnu. Providers disponibles : {available}"
            )
        return self._registry[name]

    def list_providers(self) -> list[str]:
        return sorted(self._registry.keys())

    def is_registered(self, name: str) -> bool:
        return name in self._registry


# Singleton partagé par toute l'application
registry = _ProviderRegistry()


def register_provider(name: str) -> Callable[[Type[T]], Type[T]]:
    """
    Décorateur d'enregistrement automatique.

    Usage :
        @register_provider("mon_provider")
        class MonProvider(BaseProvider):
            ...
    """
    def decorator(cls: Type[T]) -> Type[T]:
        registry.register(name, cls)
        return cls
    return decorator
