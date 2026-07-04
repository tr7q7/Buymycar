# CLAUDE.md — Documentation permanente du projet LCB_price_analyser

---

## Objectif du projet

Application d'analyse de prix d'annonces automobiles, évolutive et modulaire.
Permet de filtrer, visualiser et scorer des annonces selon leur rapport qualité/prix par rapport au marché.

---

## Règles de développement

- Le seul répertoire de travail est `D:\LCB_price_analyser`
- Ce fichier `CLAUDE.md` est mis à jour à chaque évolution importante
- Pas de commentaires inutiles — uniquement si le "pourquoi" n'est pas évident
- Ne pas ajouter de fonctionnalités non demandées
- Valider uniquement aux frontières système (entrées utilisateur, APIs externes)
- Attendre la validation de l'architecture avant de générer du code

---

## Architecture générale

```
LCB_price_analyser/
├── app/
│   ├── main.py               ← point d'entrée Streamlit
│   ├── providers/            ← sources de données interchangeables
│   ├── services/             ← orchestration (nettoyage, analyse)
│   ├── analytics/            ← calculs statistiques purs
│   ├── models/               ← entités de données
│   └── utils/
│       ├── formatting.py     ← formatage prix/km/score
│       └── car_catalog.py    ← chargement du catalogue marques/modèles
├── data/
│   ├── raw/                  ← données brutes
│   ├── processed/            ← données nettoyées
│   ├── database/             ← persistance (v2)
│   └── reference/
│       └── car_catalog.json  ← catalogue marques/modèles (source de vérité)
├── exports/                  ← rapports générés
├── tests/
│   └── fixtures/
│       └── csv/            ← fichiers CSV de test (versionnés)
├── docs/
├── scripts/
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Technologies utilisées

| Technologie | Usage |
|---|---|
| Python 3.10+ | Langage principal |
| Streamlit | Interface utilisateur web |
| Pandas | Manipulation des données |
| Plotly | Graphiques interactifs |

---

## Conventions de code

- Nommage des fichiers : `snake_case`
- Nommage des variables/fonctions : `snake_case`
- Nommage des classes : `PascalCase`
- Indentation : 4 espaces
- Encodage : UTF-8
- Langue du code : anglais ; docs : français

---

## Périmètre MVP v1 (implémenté)

| Composant | Statut |
|---|---|
| `models/listing.py` | ✅ |
| `providers/base_provider.py` | ✅ |
| `providers/mock_provider.py` | ✅ |
| `providers/csv_provider.py` | ✅ |
| `providers/provider_factory.py` | ✅ |
| `services/cleaning_service.py` | ✅ |
| `services/analysis_service.py` | ✅ |
| `analytics/price_stats.py` | ✅ |
| `analytics/outlier_detector.py` | ✅ |
| `analytics/market_scorer.py` | ✅ |
| `utils/formatting.py` | ✅ |
| `main.py` (Streamlit) | ✅ |

## Hors périmètre MVP v1 (v2+)

- API provider
- Scraper provider
- SQLite / persistance
- Historique des prix
- Page détail annonce
- Tendance des prix (price_trend)
- Export PDF

---

## TODO

- [ ] Résoudre les permissions `git init` (dossier appartient à BUILTIN\Administrateurs)
- [ ] Tester l'application : `streamlit run app/main.py`
- [ ] Implémenter les tests unitaires dans `tests/`
- [ ] Intégrer un vrai fichier CSV de données
- [ ] v2 : SQLite + historique

---

## Journal des décisions techniques

| Date | Décision | Raison |
|---|---|---|
| 2026-06-27 | Répertoire de travail : `D:\LCB_price_analyser` | Choix explicite de l'utilisateur |
| 2026-06-27 | Architecture Provider + Factory | Sources de données interchangeables sans modifier le reste du code |
| 2026-06-27 | Streamlit comme UI | Rapidité de développement, adapté à la data viz, zéro frontend custom |
| 2026-06-27 | Plotly pour les graphiques | Interactivité native (hover, zoom) sans configuration |
| 2026-06-27 | Pas de base de données en v1 | MVP — données en mémoire suffisantes pour valider le concept |
| 2026-06-27 | Score basé sur ratio prix/médiane | Simple, lisible, sans dépendance externe |
| 2026-06-27 | MockProvider avec seed fixe | Reproductibilité des données de test |
| 2026-06-27 | Architecture plugin Provider — ProviderRegistry + auto-découverte | Ajouter un provider = créer un fichier, aucun autre fichier à modifier |
| 2026-06-27 | Fixtures CSV déplacées dans tests/fixtures/csv/ | Sépare données de test (versionnées) et données utilisateur (data/raw/, ignoré git) |
| 2026-06-27 | PiloterrProvider implémenté avec dry_run | Source réelle LBC via Piloterr API ; fallback MockProvider si clé absente |
| 2026-06-27 | IDs déterministes via SHA-256 | Évite les doublons en base de données ; même annonce = même ID quel que soit le run |
| 2026-06-27 | Listing enrichi : title, url, published_at | Prépare l'affichage des vraies annonces et l'intégration PiloterrProvider |
| 2026-06-27 | CsvProvider professionnel — réécriture complète | Détection automatique des colonnes, normalisation des formats, rapport d'import, gestion encodages |
| 2026-06-27 | Audit critique MVP — 6 correctifs appliqués | Robustesse, sécurité et exactitude avant v2 |
| 2026-06-27 | CsvProvider : gestion complète des erreurs | Fichier absent / colonnes manquantes / lignes invalides ignorées sans crash |
| 2026-06-27 | Stats recalculées après suppression des outliers | La médiane utilisée pour le scoring est désormais représentative du marché filtré |
| 2026-06-27 | UUID complets (non tronqués) | Élimine les risques de collision d'ID en base de données |
| 2026-06-27 | Constantes SCORE_FLOOR_RATIO et SCORE_NEUTRAL extraites | Formule de scoring documentée et modifiable sans toucher à la logique |
| 2026-06-27 | Correction donnée mock : "Peugeot 308" → "Zoe" sous Renault | Cohérence marque/modèle dans les données de test |
| 2026-06-27 | random.Random(seed) isolé au lieu de random.seed() global | Supprime l'effet de bord sur le générateur aléatoire global Python |
| 2026-06-28 | Menus déroulants marque/modèle dans Streamlit | Remplace les text_input libres ; modèles filtrés selon la marque choisie ; option "Autre" pour saisie manuelle |
| 2026-06-28 | Catalogue véhicules dans data/reference/car_catalog.json | Source de vérité unique pour marques/modèles, chargée via app/utils/car_catalog.py |
| 2026-06-28 | Slider Année min/max dans sidebar Piloterr (2000–année courante, défaut 2018–courante) | Transmis à SearchParams ; year_min/year_max non encodés dans URL LBC → filtrage local post-fetch |
| 2026-06-28 | Hover riche sur graphique Plotly (titre, année, ville, carburant, boîte, URL) | Utilise hover_name + hover_data ; mileage/price exclus car déjà sur axes |
| 2026-06-28 | Tableau Annonces avec titre et lien cliquable "Voir l'annonce" | Remplace l'ancien tableau ; lien visible uniquement quand url non vide (Piloterr) |
| 2026-06-28 | Page résultat transformée en synthèse marché MVP vendable | KPIs 6 colonnes (+ indice fiabilité), section Interprétation (seuils ±15 % médian), Top bonnes affaires (top 5 par score) |
| 2026-06-28 | Pagination Piloterr — jusqu'à 200 annonces (max_results) | Boucle sur `&page=N` dans l'URL LBC ; dédoublonnage par list_id ; arrêt si page incomplète, total atteint ou max_results ; crédits agrégés |
| 2026-06-28 | Règle produit : max_results=200 fixe, non exposé en UI | Une analyse = un jeton = 200 annonces max automatiquement ; bandeau simplifié "X analysées sur Y disponibles" |
| 2026-06-29 | MockProvider supprimé de l'interface Streamlit | Piloterr est la seule source UI ; MockProvider conservé en backend pour les tests scripts/ |
| 2026-06-29 | Catalogue véhicules enrichi — 30 marques, 280+ modèles | Remplace l'ancien catalogue 9 marques ; couvre marques EU/JP/KR/US ; trié alphabétiquement |
| 2026-06-29 | Carburant obligatoire pour Piloterr (HTTP 500 sans fuel) | URL sans fuel= provoque 500 côté Piloterr ; défaut Diesel ; validation bloquante si "Tous" |
| 2026-06-29 | Carburants filtrés par marque/modèle en UI | app/utils/fuel_compat.py — structure de référence ; ne propose que les carburants plausibles (ex: Tesla=électrique seul, Ferrari=essence seul) ; fallback tous carburants si marque inconnue |
| 2026-06-29 | Exclusion prix aberrants bas avant analyse | exclude_low_prices dans outlier_detector.py — exclut < 60 % médiane brute (véhicules accidentés, annonces atypiques) ; count affiché en warning dans l'UI |
| 2026-06-29 | Échelle Y graphique intelligent (p3–p97 + marge 20 %) | Évite que les extrêmes écrasent la lecture ; spread minimum = 10 % du bas pour éviter le sur-zoom quand les prix sont très concentrés |
| 2026-06-29 | Interaction graphique — clic sur point → carte annonce | streamlit-plotly-events remplace st.plotly_chart ; pointIndex → df.iloc[] → Listing ; carte avec image (images.small_url Piloterr), prix/année/km/ville, lien LBC ; sélection persistée en session_state[p_selected_point] |
| 2026-06-29 | Listing.image_url ajouté | Champ optionnel mappé depuis images.small_url Piloterr (fallback images.urls[0]) ; 199/200 annonces ont une image |
| 2026-06-29 | Filtrage progressif 3 niveaux — filtering_service.py | L1 strict (année exacte) → L2 (±1 an) → L3 (±1 an + modèle mot-à-mot) ; seuil 20 annonces par niveau ; jamais d'autre marque ni modèle non apparenté |
| 2026-06-29 | Bannière enrichie + tableau annonces cliquables | Affiche X récupérées / Y strictes / Z retenues / niveau utilisé ; warnings contextuels par niveau ; tableau "Annonces utilisées" avec lien LBC cliquable sous graphique (expander) |
| 2026-06-29 | Stratégie duale brand+model / brand-only | Si strict_count < 20 et model non vide : 2ème appel Piloterr avec brand seule, merge déduplication par id, re-filtrage progressif ; si merged > initial → strategy="elargie" affiché en bannière ; sinon stratégie standard conservée (pas de 2ème appel pour cas déjà suffisants) |
| 2026-06-29 | Estimateur prix de marché pondéré — market_price_estimator.py | Pondération gaussienne w=exp(-(d_année²+d_km²)) autour du point médian ; intervalle = percentiles 25–75 pondérés ; confiance basée sur ESS et CV ; affiché comme section dédiée entre KPIs et analyse marché |
| 2026-07-02 | Score de bonne affaire 0–100 — deal_scorer.py | Remplace le score 0-10 ; 3 composantes : prix vs marché estimé (60 pts), kilométrage (25 pts), année (15 pts) ; barème 90+ Excellente / 75+ Très intéressant / 55+ Prix correct / 35+ Peu intéressant / <35 Trop cher ; affiché dans hover graphique, tableau annonces, top bonnes affaires avec verdict |
| 2026-07-02 | is_model_match() — fallback titre pour modèles sportifs | filtering_service.py : is_model_match() vérifie d'abord champ model LBC (struct), puis titre normalisé sans espaces/tirets ; corrige Audi RS3 encodé "a3" ou "rs_3" côté LBC ; même logique BMW M3, Golf GTI/R, Mercedes AMG, etc. ; 0 faux positif A3 standard, 0 autre marque |
| 2026-07-02 | Catalogue enrichi — 60 marques, 856+ modèles | RS Q3, RS Q8, TT RS, R8 ajoutés à Audi ; catalogue de référence dans data/reference/car_catalog.json |
| 2026-07-02 | fuel_compat.py — règles carburant par modèle enrichies | 80+ règles modèle : RS/S/TT Audi → essence seule ; BMW i*/iX → électrique ; BMW M → essence ; VW ID.* → électrique ; Tesla/BYD/Xpeng/Zeekr → électrique ; Porsche Taycan → électrique ; Ferrari/Lamborghini/McLaren → essence ; Mercedes EQ* → électrique ; Jaguar I-Pace → électrique, F-Type → essence ; 38 tests unitaires OK |
| 2026-07-02 | Suppression section "Prix de marché estimé" | Section retirée de l'UI (valeur marché estimée, intervalle, confiance) ; le calcul reste disponible en backend via market_price_estimator.py (utilisé par deal_scorer) |
| 2026-07-02 | Durée estimée de revente — resale_time_estimator.py | Fonction 3 MVP : estimation 7–90 jours basée sur liquidité du marché (nb annonces) et positionnement prix (mean/médian) ; confiance Élevée/Moyenne/Faible selon nb annonces et CV ; carte affichée entre KPIs et analyse marché |
| 2026-07-02 | Migration SaaS Étape 0 — filet pytest | Suite pytest figeant analytics + filtrage avant migration Next.js/FastAPI ; requirements-dev.txt isolé ; branche migration/saas-foundation |
| 2026-07-02 | Migration SaaS Étape 1 — extraction search_service.py | Logique d'orchestration (stratégie duale) sortie de main.py vers app/services/search_service.py → run_search() renvoie SearchResult ; réutilisable par tout client (Streamlit + API) ; Streamlit inchangé |
| 2026-07-02 | Migration SaaS Étape 2 — squelette FastAPI (monorepo apps/api) | Routes /health, /catalog/*, /search (job async + polling pour absorber la latence Piloterr 1-3 min) ; JobManager en mémoire (ThreadPoolExecutor) ; schémas Pydantic ; deps API sans Streamlit/Plotly ; déploiement Render (render.yaml) ; app/ conservé en place (pas de move vers packages/) |
| 2026-07-03 | Migration SaaS Étape 3 — frontend Next.js (apps/web) | Écran de recherche premium (v0.dev) intégré : selects dépendants marque→modèle→carburant, double slider années, machine à états idle/loading/error/done, polling ; client lib/api.ts sur NEXT_PUBLIC_API_URL ; E2E validé (front↔FastAPI réel, 110 annonces Audi RS3) |
| 2026-07-04 | Migration SaaS Étape 4a — enrichissement API dashboard | SearchResult/SearchResultOut portent market_estimate (valeur/intervalle/confiance via market_price_estimator) ; nettoyage d'affichage à l'API (clean_model_label masque « Autres », clean_title compacte les espaces) ; tests étendus (68 verts) |
| 2026-07-04 | Migration SaaS Étape 4b — dashboard résultats (v0) | Écran résultats intégré : KPIs marché, graphique prix/km (recharts, meilleures affaires entourées), top affaires, tableau + liens LBC ; dead-end « Voir les résultats » corrigé ; E2E réel Renault Clio Diesel (161 annonces, marché 13 747 €) ; « toujours RS3 » = mock v0 uniquement |
| 2026-07-04 | Lot pré-prod #2/#5/#6 | Renommage produit « LCB Price Analyser » → « AutoCote » (front + baseline + titre + nom API) ; garde-fou anti-mock en prod (lib/api.ts refuse /mock) ; coulisses retirées (generator v0.app, « sur LeBonCoin » → « Analyse du marché en cours… », devIndicators false) |
| 2026-07-04 | Prep déploiement | render.yaml (autocote-api, PYTHON_VERSION 3.11.9) ; DEPLOY.md (checklist Render API + Vercel web + boucle CORS) ; build de prod front validé ; pas encore déployé (nécessite repo GitHub + comptes) |
