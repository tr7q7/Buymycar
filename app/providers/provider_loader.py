import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Fichiers du système du registre — ne pas importer comme providers
_SYSTEM_FILES = {
    "__init__",
    "base_provider",
    "provider_registry",
    "provider_factory",
    "provider_loader",
}


def load_all(providers_dir: Path | None = None) -> None:
    """
    Scanne providers_dir et importe chaque fichier provider.
    L'import suffit à déclencher @register_provider sur chaque classe.

    Les erreurs d'import individuelles sont loguées mais n'arrêtent pas
    le chargement des autres providers.
    """
    if providers_dir is None:
        providers_dir = Path(__file__).parent

    loaded = 0
    errors = 0

    for path in sorted(providers_dir.glob("*.py")):
        module_name = path.stem
        if module_name in _SYSTEM_FILES:
            continue

        full_module = f"app.providers.{module_name}"
        try:
            importlib.import_module(full_module)
            loaded += 1
        except ImportError as e:
            errors += 1
            logger.warning("Impossible de charger le provider '%s' : %s", module_name, e)
        except Exception as e:
            errors += 1
            logger.error("Erreur inattendue lors du chargement de '%s' : %s", module_name, e)

    logger.debug("ProviderLoader : %d provider(s) chargé(s), %d erreur(s)", loaded, errors)
