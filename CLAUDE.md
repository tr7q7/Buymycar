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
│   └── utils/                ← fonctions transverses
├── data/
│   ├── raw/                  ← données brutes
│   ├── processed/            ← données nettoyées
│   └── database/             ← persistance (v2)
├── exports/                  ← rapports générés
├── tests/
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
| 2026-06-27 | CsvProvider professionnel — réécriture complète | Détection automatique des colonnes, normalisation des formats, rapport d'import, gestion encodages |
| 2026-06-27 | Audit critique MVP — 6 correctifs appliqués | Robustesse, sécurité et exactitude avant v2 |
| 2026-06-27 | CsvProvider : gestion complète des erreurs | Fichier absent / colonnes manquantes / lignes invalides ignorées sans crash |
| 2026-06-27 | Stats recalculées après suppression des outliers | La médiane utilisée pour le scoring est désormais représentative du marché filtré |
| 2026-06-27 | UUID complets (non tronqués) | Élimine les risques de collision d'ID en base de données |
| 2026-06-27 | Constantes SCORE_FLOOR_RATIO et SCORE_NEUTRAL extraites | Formule de scoring documentée et modifiable sans toucher à la logique |
| 2026-06-27 | Correction donnée mock : "Peugeot 308" → "Zoe" sous Renault | Cohérence marque/modèle dans les données de test |
| 2026-06-27 | random.Random(seed) isolé au lieu de random.seed() global | Supprime l'effet de bord sur le générateur aléatoire global Python |
