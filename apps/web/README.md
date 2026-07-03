# LCB Price Analyser — Web (Next.js)

Frontend du SaaS. Écran de recherche premium (généré via v0.dev puis intégré),
branché sur l'API FastAPI (`apps/api`).

Stack : Next.js 16 (App Router), React 19, TypeScript, TailwindCSS v4,
shadcn/ui (base-nova), Motion, SWR.

## Configuration

```bash
cp .env.example .env.local
# éditer NEXT_PUBLIC_API_URL selon la cible (voir .env.example)
```

| Valeur de `NEXT_PUBLIC_API_URL` | Usage |
|---|---|
| `http://localhost:8000` | Développement intégré avec le backend FastAPI local |
| `/mock` | UI seule, sans backend (mocks Next.js sous `app/mock/`) |
| `https://lcb-api.onrender.com` | Production (URL Render) |

## Lancer en local

```bash
corepack enable    # active pnpm (déclaré via pnpm-lock.yaml)
pnpm install
pnpm dev           # http://localhost:3000
```

Pour l'expérience complète, lancer aussi l'API depuis la racine du repo :

```bash
uvicorn apps.api.main:app --reload   # http://localhost:8000
```

## Structure

```
app/
├── page.tsx / layout.tsx / globals.css
└── mock/                 ← routes API factices (dev UI sans backend)
components/
├── price-analyser/       ← composants métier (search-form, states, slider…)
└── ui/                   ← primitives shadcn
lib/
├── api.ts                ← client typé (catalog + search + polling)
└── utils.ts
```

Le client `lib/api.ts` lit toujours `NEXT_PUBLIC_API_URL` — aucune URL en dur.
