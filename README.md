# AutoCote

Estimation de la **cote automobile** à partir des annonces du marché de l'occasion,
en temps réel. Un pro saisit marque / modèle / carburant / années et obtient une
valeur de marché estimée, un graphique prix vs kilométrage, les meilleures affaires
et le détail des annonces.

Monétisation MVP : **2 analyses gratuites par email**, puis **pack de 5 analyses
pour 2 €** via Stripe Checkout (sans compte, sans abonnement).

## Architecture (monorepo)

```
app/                 Cœur métier Python (providers, services, analytics) — réutilisable
apps/api/            API FastAPI (catalogue, recherche async, crédits, Stripe)
apps/web/            Frontend Next.js 16 (écran de recherche + dashboard résultats)
tests/               Suite pytest (92 tests)
```

- **Recherche** : Piloterr (LeBonCoin) → filtrage progressif → scoring → estimation.
  Pattern job asynchrone (`POST /search` → `job_id` → polling) pour absorber la
  latence (1–3 min).
- **Paiement** : crédits par email en base (SQLAlchemy, SQLite en local / Postgres en
  prod), Stripe Checkout (prix dynamique), webhook idempotent.

## Développement local

```bash
# API (depuis la racine)
pip install -r apps/api/requirements.txt
uvicorn apps.api.main:app --reload        # http://localhost:8000  (docs: /docs)

# Frontend
cp apps/web/.env.example apps/web/.env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
corepack pnpm --dir apps/web install
corepack pnpm --dir apps/web dev          # http://localhost:3000

# Tests backend
python -m pytest
```

Sans clé Stripe locale, `/checkout/create-session` renvoie 503 (attendu) : le reste
du flux crédits reste testable.

## Déploiement & lancement

- [DEPLOY.md](DEPLOY.md) — Render (API + Postgres), Vercel (front), Stripe, variables d'env.
- [GO_LIVE.md](GO_LIVE.md) — checklist de lancement, tests en mode test Stripe, risques.

## Endpoints principaux (API)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | sonde |
| GET | `/catalog/{brands,models,fuels}` | catalogue dépendant |
| POST | `/credits/init` · GET `/credits` | crédits par email |
| POST | `/search` · GET `/search/{job_id}` | recherche (email + crédit requis) |
| POST | `/checkout/create-session` | session Stripe Checkout |
| POST | `/stripe/webhook` | crédit après paiement (idempotent) |
