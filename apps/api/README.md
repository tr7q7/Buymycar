# LCB Price Analyser — API (FastAPI)

Backend HTTP qui expose le cœur métier Python (`app/`) au futur frontend Next.js.
Aucune logique métier ici : uniquement le câblage HTTP, la config CORS et
l'asynchrone. La logique vit dans `app/services`, `app/analytics`, `app/providers`.

## Lancer en local

```bash
pip install -r apps/api/requirements.txt
# depuis la racine du repo :
uvicorn apps.api.main:app --reload
```

Documentation interactive : http://127.0.0.1:8000/docs

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | Sonde de vie (utilisée par Render) |
| GET | `/catalog/brands` | Liste des marques |
| GET | `/catalog/models?brand=Audi` | Modèles d'une marque |
| GET | `/catalog/fuels?brand=Audi&model=RS3` | Carburants plausibles |
| POST | `/search` | Soumet une recherche → `job_id` (202) |
| GET | `/search/{job_id}` | État + résultat quand `status=done` |

## Recherche asynchrone (job + polling)

Une recherche Piloterr prend 1 à 3 min. Elle n'est donc **pas** bloquante :

```
POST /search { brand, model, fuel, year_min, year_max }
  → 202 { "job_id": "...", "status": "pending" }

GET /search/{job_id}
  → { "status": "running" }           # tant que ça calcule
  → { "status": "done", "result": … } # résultat complet
  → { "status": "error", "error": … } # Piloterr indisponible, etc.
```

Le registre de jobs est en mémoire (MVP mono-instance). À migrer vers Redis/RQ
le jour d'un déploiement multi-instances.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `PILOTERR_API_KEY` | Clé Piloterr (jamais committée) |
| `CORS_ORIGINS` | Origines front autorisées, séparées par des virgules |

## Déploiement

Render, via `render.yaml` à la racine du repo.
