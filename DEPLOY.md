# Déploiement — AutoCote

Architecture cible : **API** (FastAPI) sur **Render**, **Front** (Next.js) sur **Vercel**.
Les deux se déploient depuis le même dépôt GitHub (monorepo).

> Les étapes marquées 🧑 nécessitent **tes comptes/identifiants** — à faire par toi.
> Claude ne crée pas de compte et ne saisit aucun secret.

---

## 0. Prérequis — pousser le code sur GitHub 🧑

Le repo n'a pas encore de remote. Crée un dépôt GitHub (privé conseillé), puis :

```bash
git remote add origin https://github.com/<toi>/autocote.git
git push -u origin migration/saas-foundation
```

Tu peux déployer depuis la branche `migration/saas-foundation`, ou d'abord la
fusionner dans `main` et déployer depuis `main` (plus « propre » pour la prod).

⚠️ Vérifie qu'aucun secret n'est poussé : `.env` (clé Piloterr) et `apps/web/.env.local`
sont **gitignorés** — c'est déjà le cas.

---

## 1. Backend API sur Render 🧑

1. Render → **New** → **Blueprint**, sélectionne le repo. Render lit `render.yaml`
   et propose le service **autocote-api**.
2. Renseigne les variables d'environnement (onglet Environment) :
   - `PILOTERR_API_KEY` = ta clé Piloterr (la même que dans `.env` local)
   - `CORS_ORIGINS` = *(laisser vide pour l'instant — on y met l'URL Vercel à l'étape 3)*
3. Déploie. Récupère l'URL publique, ex. `https://autocote-api.onrender.com`.
4. Test : ouvrir `https://autocote-api.onrender.com/health` → doit renvoyer
   `{"status":"ok","service":"AutoCote API",...}`.

> Plan **free** : le service s'endort après ~15 min d'inactivité. Le premier appel
> après réveil prend 30–60 s (cold start). Acceptable pour une démo ; passer en
> plan payant pour un usage commercial.

---

## 2. Frontend sur Vercel 🧑

1. Vercel → **Add New Project**, importe le repo.
2. **Root Directory** = `apps/web` (important : c'est un monorepo).
3. Framework : **Next.js** (auto-détecté). Si le build échoue sur l'étape pnpm,
   forcer **Build Command** = `next build` et **Install Command** = `pnpm install`.
4. Variable d'environnement :
   - `NEXT_PUBLIC_API_URL` = l'URL Render de l'étape 1
     (ex. `https://autocote-api.onrender.com`) — **sans** `/` final, **jamais** `/mock`.
5. Déploie. Récupère l'URL, ex. `https://autocote.vercel.app`.

---

## 3. Boucler le CORS (indispensable) 🧑

L'API n'accepte par défaut que `http://localhost:3000`. Il faut autoriser le front prod :

1. Render → service `autocote-api` → Environment → `CORS_ORIGINS` =
   l'URL Vercel exacte (ex. `https://autocote.vercel.app`).
   Plusieurs origines possibles, séparées par des virgules.
2. Redéployer l'API (Render le fait automatiquement au changement d'env).

---

## 4. Test de bout en bout après déploiement

1. Ouvrir l'URL Vercel.
2. La liste des marques doit se charger (60 marques) — si elle reste vide,
   c'est un problème CORS (étape 3) ou l'API endormie (attendre le cold start).
3. Lancer une recherche (ex. Renault Clio Diesel) → loading → dashboard résultats.
4. Vérifier dans l'onglet Réseau du navigateur que les appels ciblent bien
   l'URL Render (et non `/mock`).

---

## Récapitulatif des variables d'environnement

| Service | Variable | Valeur |
|---|---|---|
| Render (API) | `PILOTERR_API_KEY` | clé Piloterr |
| Render (API) | `CORS_ORIGINS` | URL(s) du front Vercel |
| Render (API) | `PYTHON_VERSION` | `3.11.9` (déjà dans render.yaml) |
| Vercel (web) | `NEXT_PUBLIC_API_URL` | URL de l'API Render |

## Garde-fous déjà en place
- Le front **refuse les mocks en production** (`lib/api.ts`) : si `NEXT_PUBLIC_API_URL`
  pointe vers `/mock` en prod, une erreur claire s'affiche au lieu de fausses données.
- Les deps de l'API n'incluent ni Streamlit ni Plotly → image Render légère.
