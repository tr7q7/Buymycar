# Déploiement — AutoCote

Architecture : **API** (FastAPI) sur **Render**, **Front** (Next.js) sur **Vercel**,
**paiement** via Stripe Checkout, **base** Postgres (Render).

- API prod : `https://autocote-api-f24d.onrender.com`
- Front prod : `https://buymycar.vercel.app`
- Webhook Stripe : `https://autocote-api-f24d.onrender.com/stripe/webhook`

> Étapes marquées 🧑 = tes comptes/identifiants. Claude ne pousse pas et ne saisit
> aucun secret.

> ⚠️ **État au dernier audit** : le code **paiement** (routes `/credits`,
> `/checkout`, `/stripe/webhook`, frontend email/crédits) est committé en local
> mais **PAS encore déployé** — l'API en ligne n'expose que `/health`, `/catalog/*`,
> `/search`. Il faut **pousser `main` puis redéployer Render + Vercel** (voir
> [GO_LIVE.md](GO_LIVE.md)).

---

## 1. Pousser le code 🧑

```bash
git push origin main
```
Render et Vercel redéploient automatiquement sur push de `main` (si l'auto-deploy
est activé), sinon déclencher un « Manual Deploy » / « Redeploy » dans chaque dashboard.

⚠️ Backend et frontend doivent être **sur le même commit** : depuis l'Étape 3,
`/search` exige un `email` — un front sans email (ancienne version) renverrait 422.

---

## 2. Variables d'environnement

### Backend (Render) 🧑
| Variable | Valeur | Requis |
|---|---|---|
| `PILOTERR_API_KEY` | clé Piloterr | ✅ recherche |
| `DATABASE_URL` | URL Postgres Render (`postgresql://…`) | ✅ persistance crédits/paiements |
| `CORS_ORIGINS` | `https://buymycar.vercel.app` | ✅ (sinon appels navigateur bloqués) |
| `STRIPE_SECRET_KEY` | `sk_test_…` puis `sk_live_…` | ✅ paiement |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` (donné par Stripe à la création du webhook) | ✅ crédit après paiement |
| `FRONTEND_URL` | `https://buymycar.vercel.app` | ✅ URLs de retour Stripe |
| `STRIPE_PRICE_AMOUNT` | `200` (centimes) | défaut 200 |
| `STRIPE_CURRENCY` | `eur` | défaut eur |

### Frontend (Vercel) 🧑
| Variable | Valeur |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://autocote-api-f24d.onrender.com` |

> `DATABASE_URL` : **indispensable pour le paiement**. Sans lui, l'API retombe sur
> SQLite sur le disque éphémère de Render → crédits et paiements **effacés à chaque
> redeploy**. Créer une instance **Render Postgres** (free tier) et coller son
> « Internal Database URL ».

---

## 3. Base Postgres (Render) 🧑

1. Render → **New → Postgres** (free), récupérer l'**Internal Database URL**.
2. La coller dans `DATABASE_URL` du service `autocote-api`.
3. Les tables (`customers`, `payments`, `searches`) sont créées automatiquement au
   démarrage de l'API (lifespan `init_db`). Aucune migration manuelle.

---

## 4. Stripe 🧑

1. **Clé secrète** : Dashboard Stripe → Développeurs → Clés API → copier la clé
   secrète (mode **test** d'abord) dans `STRIPE_SECRET_KEY` (Render).
2. **Webhook** : Développeurs → Webhooks → **Add endpoint**
   `https://autocote-api-f24d.onrender.com/stripe/webhook`, événement
   **`checkout.session.completed`**. Copier le **Signing secret** (`whsec_…`) dans
   `STRIPE_WEBHOOK_SECRET` (Render).
3. **Apple Pay** (optionnel) : Stripe → Payment methods → Apple Pay → enregistrer le
   domaine `buymycar.vercel.app`. Google Pay/Apple Pay s'affichent sinon nativement
   dans Checkout selon l'appareil.
4. Pas de produit/prix à créer : le montant est dynamique (`price_data`, 200 EUR).

---

## 5. Test de bout en bout après déploiement

Voir [GO_LIVE.md](GO_LIVE.md) pour la procédure complète (carte de test
`4242 4242 4242 4242`).

---

## Garde-fous en place
- Front : refuse les mocks en production (`lib/api.ts`).
- Aucune clé Stripe côté frontend (vérifié).
- Décrément de crédit atomique ; webhook idempotent (un paiement crédite une fois).
- Deps API sans Streamlit/Plotly → image légère.

---

## 6. PostHog (analytics produit) 🧑

**Clé** : PostHog → Settings → Project settings → **Project API Key** (`phc_…`,
même clé pour front et back). **Host** (région EU) : `https://eu.i.posthog.com`.

### Frontend (Vercel) 🧑
| Variable | Valeur |
|---|---|
| `NEXT_PUBLIC_POSTHOG_KEY` | `phc_…` |
| `NEXT_PUBLIC_POSTHOG_HOST` | `https://eu.i.posthog.com` |

### Backend (Render) 🧑
| Variable | Valeur |
|---|---|
| `POSTHOG_API_KEY` | `phc_…` (même clé) |
| `POSTHOG_HOST` | `https://eu.i.posthog.com` |

Sans ces variables, le tracking est un no-op silencieux (dev/tests non impactés).

### Événements envoyés
`landing_page_view`, `analysis_started`, `analysis_completed`, `free_credit_used`,
`credits_exhausted`, `checkout_started` (front) · `payment_completed` (back, webhook
+ confirm). Tous reliés au même `distinct_id` = `visitor_id` (+ `identify(email)`
dès que connu).

### Dashboard "AutoCote MVP" 🧑
Créer un dashboard dans PostHog (Dashboards → New dashboard → "AutoCote MVP") et y
ajouter :
1. **Un funnel** (Insights → Funnel) avec les étapes, dans l'ordre :
   `landing_page_view` → `analysis_started` → `credits_exhausted` →
   `checkout_started` → `payment_completed` → `paid_analysis`
   (nécessaire pour l'étape "Analyse payante" — utiliser `analysis_started` filtré
   sur has_paid=true, ou l'event `paid_analysis` émis directement).
2. **Trends** simples en complément : nombre d'`analysis_completed`/jour, taux
   `credits_exhausted` → `checkout_started` (conversion vers l'achat), nombre de
   `payment_completed`/semaine (revenu proxy).
3. Épingler ("Add to dashboard") chaque insight créé sur le dashboard "AutoCote MVP".

Ceci se fait dans l'UI PostHog (pas d'API simple pour créer un dashboard depuis le
code) — compter ~10 min.
