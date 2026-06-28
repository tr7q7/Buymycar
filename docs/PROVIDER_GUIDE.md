# Guide — Créer un nouveau Provider

Ajouter une source de données ne nécessite de modifier aucun fichier existant.
Il suffit de créer un seul fichier dans `app/providers/`.

---

## Étape 1 — Créer le fichier (30 secondes)

```
app/providers/mon_provider.py
```

## Étape 2 — Copier ce squelette (2 minutes)

```python
from typing import List
from app.providers.base_provider import BaseProvider
from app.providers.provider_registry import register_provider
from app.models.listing import Listing


@register_provider("mon_provider")   # nom unique utilisé dans provider_factory.create()
class MonProvider(BaseProvider):

    def __init__(self, **kwargs):
        # récupérer les paramètres nécessaires depuis kwargs
        # exemple : self.filepath = kwargs["filepath"]
        pass

    def fetch(self) -> List[Listing]:
        # retourner une liste d'objets Listing normalisés
        # ignorer les entrées invalides sans faire planter fetch()
        return []
```

## Étape 3 — Implémenter `fetch()` (5-7 minutes)

Chaque `Listing` doit avoir au minimum :

| Champ | Type | Description |
|---|---|---|
| `id` | `str` | Identifiant stable — utiliser `make_listing_id()` si absent |
| `brand` | `str` | Marque du véhicule |
| `model` | `str` | Modèle |
| `year` | `int` | Année de mise en circulation |
| `mileage` | `int` | Kilométrage |
| `price` | `float` | Prix en EUR |
| `fuel` | `str` | essence / diesel / electrique / hybride |
| `transmission` | `str` | manuelle / automatique |
| `location` | `str` | Ville ou département |
| `source` | `str` | Identifiant de la source (ex: "mon_provider") |

Champs optionnels : `title`, `url`, `published_at`, `score`.

Pour générer un ID déterministe :
```python
from app.utils.formatting import make_listing_id
listing_id = make_listing_id(url=url, brand=brand, model=model, ...)
```

## Étape 4 — Optionnel : rapport d'import

Si votre provider produit un rapport structuré, surchargez `fetch_with_report()` :

```python
def fetch_with_report(self):
    listings = self.fetch()
    rapport = {"total": len(listings), "source": "mon_provider"}
    return listings, rapport
```

## Étape 5 — Tester (1 minute)

```python
import app.providers  # déclenche l'auto-découverte
from app.providers import provider_factory

listings = provider_factory.create("mon_provider", mon_param="valeur").fetch()
print(f"{len(listings)} annonces importées")
```

## C'est tout

Aucun autre fichier à modifier.
Le provider est automatiquement découvert au démarrage de l'application.

---

## Règles à respecter

- `fetch()` ne doit **jamais** lever d'exception non gérée
- Les annonces invalides sont ignorées silencieusement (log en DEBUG)
- La clé API ou le chemin de fichier vient des `kwargs`, jamais hardcodé
- Le nom passé à `@register_provider` doit être unique dans tout le projet

## Providers existants (exemples)

| Nom | Fichier | Usage |
|---|---|---|
| `mock` | `mock_provider.py` | Données fictives pour les tests |
| `csv` | `csv_provider.py` | Import fichier CSV local |
| `piloterr` | `piloterr_provider.py` | Annonces LeBonCoin via API Piloterr |
