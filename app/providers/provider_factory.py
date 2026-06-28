from app.providers.base_provider import BaseProvider
from app.providers.provider_registry import registry, ProviderNotFoundError


def create(name: str, **kwargs) -> BaseProvider:
    """
    Instancie le provider enregistré sous 'name' avec les kwargs fournis.

    Ne connaît aucun provider directement — délègue entièrement au registre.
    Ajouter un nouveau provider ne nécessite jamais de modifier ce fichier.

    Raises:
        ProviderNotFoundError : si le nom n'est pas enregistré.
    """
    cls = registry.get(name)
    return cls(**kwargs)


def list_available() -> list[str]:
    """Retourne les noms de tous les providers actuellement enregistrés."""
    return registry.list_providers()
