# AutoCote — Checklist « Go Live »

Référence unique jusqu'au lancement officiel. Dernier audit : **2026-07-07**.

Produit : recherche de cote automobile. Modèle : **2 analyses gratuites par email,
puis pack de 10 analyses pour 2 €** (Stripe Checkout, sans compte ni abonnement).

---

## 0. Constat d'audit (à corriger EN PRIORITÉ)

🔴 **Le code de paiement n'est pas déployé.** L'API en ligne
(`autocote-api-f24d.onrender.com`) n'expose que `/health`, `/catalog/*`, `/search`
(version pré-paiement). Les routes `/credits`, `/checkout`, `/stripe/webhook`
renvoient **404**. Conséquences tant que ce n'est pas corrigé :
- Le webhook Stripe configuré pointe vers un endpoint **404** → un paiement ne
  crédite **rien**.
- `/search` accepte les recherches **sans crédit** (aucun contrôle).
- Le front en ligne n'a pas le champ email / l'achat.

✅ Ce qui est déjà bon côté déployé : API vivante, **CORS autorise** bien
`https://buymycar.vercel.app`, nom de marque « AutoCote ».

✅ Ce qui est bon côté code (local, testé — 92 tests verts) : endpoints corrects,
décrément atomique, webhook idempotent, aucune clé secrète dans le front, URLs de
retour Stripe basées sur `FRONTEND_URL`.

---

## 1. À FAIRE avant d'accepter les premiers paiements

| # | Action | Où | Vérif |
|---|---|---|---|
| 1 | `git push origin main` | local | commit paiement en ligne |
| 2 | Créer **Render Postgres** + coller l'URL dans `DATABASE_URL` | Render | données persistantes |
| 3 | Renseigner `STRIPE_SECRET_KEY` (test), `STRIPE_WEBHOOK_SECRET`, `FRONTEND_URL=https://buymycar.vercel.app` | Render | — |
| 4 | Confirmer `CORS_ORIGINS=https://buymycar.vercel.app` et `PILOTERR_API_KEY` | Render | déjà OK pour CORS |
| 5 | **Redéployer l'API** (Render) puis vérifier l'OpenAPI | Render | `/credits`, `/checkout`, `/stripe/webhook` présents |
| 6 | Confirmer `NEXT_PUBLIC_API_URL` = URL Render, **redéployer le front** | Vercel | champ email visible |
| 7 | Webhook Stripe → endpoint `…/stripe/webhook`, événement `checkout.session.completed` | Stripe | « test » renvoie 200 |
| 8 | (Option) Enregistrer le domaine Vercel pour **Apple Pay** | Stripe | wallet visible |

**Vérifications rapides en ligne de commande (après redeploy) :**
```bash
API=https://autocote-api-f24d.onrender.com
curl "$API/openapi.json" | grep -o '/stripe/webhook\|/credits\|/checkout'   # doivent apparaître
curl -X POST "$API/search" -H 'Content-Type: application/json' \
  -d '{"brand":"renault","fuel":"diesel","year_min":2018,"year_max":2026}' -o /dev/null -w '%{http_code}\n'  # 422 (email requis)
```

---

## 2. Tests fonctionnels à réaliser (mode test Stripe)

Carte de test : **`4242 4242 4242 4242`**, date future, CVC quelconque, code postal quelconque.

1. **Crédits gratuits** : ouvrir le site, saisir un email neuf → « 2 analyses restantes ».
2. **Recherche** : lancer une analyse (ex. Renault Clio Diesel) → résultats + « 1 analyse restante ».
3. **Épuisement** : relancer jusqu'à 0 → le bouton « Acheter 10 analyses — 2 € » apparaît.
4. **Paiement test** : cliquer → Stripe Checkout → payer avec `4242…` → retour sur le site.
5. **Crédit après paiement** : le message « 10 analyses ajoutées » s'affiche, le solde passe à **10**.
6. **Idempotence** : dans Stripe → Webhooks → renvoyer l'événement `checkout.session.completed` → le solde **reste 10** (pas 20).
7. **Persistance** : redéployer l'API → le solde de l'email est **conservé** (valide Postgres).
8. **Sécurité front** : DevTools → onglet Réseau → aucun `sk_test`/`sk_live` ; appels vers l'API Render.
9. **Échec de carte** (option) : carte `4000 0000 0000 0002` → paiement refusé, aucun crédit ajouté.

> Passage en **réel** : remplacer les clés `sk_test`/`whsec` (test) par les clés
> **live** dans Render, recréer le webhook en mode live, refaire les tests 1→7.

---

## 3. Risques connus du MVP (assumés)

| Risque | Impact | Mitigation actuelle / plus tard |
|---|---|---|
| **Email non vérifié** | Tier gratuit « farmable » (nouvel email = 2 gratuits) ; un tiers peut consommer les crédits d'un email connu | Accepté pour un MVP à 2 € ; plus tard : vérification email / lien magique |
| **Pas de remboursement auto** si le job échoue après décrément | 1 crédit perdu en cas de panne Piloterr | Traçé dans `searches` ; remboursement manuel/auto à ajouter |
| **JobManager en mémoire** | Un redeploy pendant une recherche perd le job en cours (crédit déjà débité) | Acceptable (rare) ; file Redis plus tard |
| **Render free tier** | Cold start 30–60 s ; le 1er appel peut sembler lent | Passer en plan payant pour la prod sérieuse |
| **Pas de rate limiting** | Abus possible (spam de recherches gratuites via emails jetables) | Ajouter un rate-limit par IP/email |
| **SQLite si `DATABASE_URL` oublié** | Perte des crédits/paiements au redeploy | Checklist #2 (Postgres obligatoire) |
| **Webhook = seule source de crédit** | Si le webhook est mal configuré, le paiement n'ajoute rien | Test #6 obligatoire avant live |

---

## 4. Améliorations prioritaires après les premiers utilisateurs

1. **Remboursement automatique** d'un crédit si le job échoue techniquement (via `searches`).
2. **Vérification d'email** légère (lien magique) pour fiabiliser crédits et anti-abus.
3. **Rate limiting** par IP/email sur `/search` et `/credits/init`.
4. **Reçu / historique** minimal par email (liste des paiements).
5. **Observabilité** : logs structurés + alerte sur échec de webhook.
6. **Page de succès dédiée** (`/merci`) plutôt que le retour `?payment=success` sur l'accueil.
7. **File de jobs persistante** (Redis/RQ) pour survivre aux redeploys et scaler.

---

## 5. Probabilité d'un premier paiement réel sans problème

- **En l'état actuel (rien de déployé)** : ~**5 %** — le webhook pointe vers un 404,
  aucun crédit ne serait ajouté.
- **Après avoir exécuté la section 1 (déploiement) et validé la section 2 (tests test-mode)** :
  ~**85–90 %**. Le flux est simple, testé (92 tests), idempotent et sans secret exposé.
  Les 10–15 % de risque résiduel tiennent surtout à la **configuration** (une variable
  d'env oubliée, `DATABASE_URL` non branché, ou le webhook non repassé en clés **live**),
  pas au code.

**Conclusion** : le code est prêt. Le lancement dépend d'une checklist de
**déploiement/configuration** rigoureuse — les tests 1→7 en mode test Stripe sont le
juge de paix avant d'ouvrir les paiements réels.
