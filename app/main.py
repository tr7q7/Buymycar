import logging
import os
import sys
import datetime
from pathlib import Path

# Garantit que la racine du projet est dans sys.path,
# quel que soit le répertoire depuis lequel Streamlit est lancé.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import app.providers.provider_factory as ProviderFactory  # noqa: F401 — conservé pour les tests
from app.providers.piloterr_provider import (
    SearchParams,
    PiloterrServerError, PiloterrTimeoutError, PiloterrError,
)
from app.providers.leboncoin_query_builder import LeboncoinQueryBuilder
from app.utils.car_catalog import brands as catalog_brands, models_for
from app.utils.fuel_compat import fuels_for as catalog_fuels_for
from app.services.search_service import run_search
from app.utils.formatting import fmt_price, fmt_mileage, fmt_score, make_listing_id  # noqa: F401
from app.models.listing import Listing
from app.analytics.price_stats import compute_stats
from app.analytics.market_price_estimator import estimate_market_price
from app.analytics.deal_scorer import score_label as deal_score_label
from app.analytics.resale_time_estimator import estimate_resale_time

st.set_page_config(page_title="LCB Price Analyser", page_icon="🚗", layout="wide")
st.title("🚗 LCB Price Analyser")
st.caption("Analyse de prix d'annonces automobiles — LeBonCoin via Piloterr")

# ── Sidebar — Clé API ─────────────────────────────────────────────────────────
api_key = os.environ.get("PILOTERR_API_KEY", "").strip()
if not api_key:
    st.sidebar.error(
        "PILOTERR_API_KEY absente.\n\n"
        "Ajoutez `PILOTERR_API_KEY=votre_cle` dans le fichier `.env` "
        "à la racine du projet, puis relancez l'app."
    )

_CURRENT_YEAR = datetime.date.today().year

# ── Sidebar — Recherche ───────────────────────────────────────────────────────
st.sidebar.header("Recherche")

# ── Marque ────────────────────────────────────────────────────────────────────
_brands = catalog_brands()
_brand_label = st.sidebar.selectbox("Marque", _brands, index=0)
piloterr_brand = _brand_label.lower()

# ── Modèle (dépend de la marque) ──────────────────────────────────────────────
_models = models_for(_brand_label) + ["Autre"]
_model_label = st.sidebar.selectbox("Modèle", _models, index=0)
if _model_label == "Autre":
    _model_manual = st.sidebar.text_input("Modèle (saisie libre)", value="")
    piloterr_model = _model_manual.strip().lower()
else:
    piloterr_model = _model_label.lower()

# ── Carburant (filtré selon la marque/modèle) ─────────────────────────────────
_compat_fuels = catalog_fuels_for(_brand_label, _model_label)
_fuel_options_all = {"Diesel": "diesel", "Essence": "essence", "Électrique": "electrique"}
# Ne propose que les carburants plausibles + "Tous" comme secours
_fuel_options = {k: v for k, v in _fuel_options_all.items() if v in _compat_fuels}
_fuel_options["Tous"] = ""
_fuel_label = st.sidebar.selectbox("Carburant", list(_fuel_options.keys()), index=0)
piloterr_fuel = _fuel_options[_fuel_label]

# ── Année ─────────────────────────────────────────────────────────────────────
piloterr_year_min, piloterr_year_max = st.sidebar.slider(
    "Année",
    min_value=2000,
    max_value=_CURRENT_YEAR,
    value=(2018, _CURRENT_YEAR),
    step=1,
)

search_clicked = st.sidebar.button(
    "Lancer la recherche",
    type="primary",
    disabled=(not api_key or not piloterr_brand),
)
if search_clicked and not piloterr_fuel:
    st.sidebar.error("Veuillez sélectionner un carburant pour lancer l'analyse Piloterr.")
    search_clicked = False

# ── Exécution de la recherche ─────────────────────────────────────────────────
piloterr_meta = None

if search_clicked:
    with st.spinner("Recherche en cours… (plusieurs pages, ~30 s par page)"):
        try:
            _res = run_search(
                piloterr_brand, piloterr_model, piloterr_fuel,
                piloterr_year_min, piloterr_year_max,
            )
            _filt = _res.filt
            st.session_state["p_listings"]       = _res.listings
            st.session_state["p_stats"]          = _res.stats
            st.session_state["p_low_excl"]       = _res.low_price_excluded
            st.session_state["p_filter_level"]   = _filt.level
            st.session_state["p_strict_count"]   = _filt.strict_count
            st.session_state["p_filter_retained"]= len(_filt.listings)
            st.session_state["p_year_min_used"]  = _filt.year_min_used
            st.session_state["p_year_max_used"]  = _filt.year_max_used
            st.session_state["p_meta"]           = _res.meta
            st.session_state["p_url"]            = _res.lbc_url
            st.session_state["p_raw_count"]      = _res.raw_count
            st.session_state["p_strategy"]       = _res.strategy
            st.session_state.pop("p_error", None)
            st.session_state.pop("p_selected_point", None)
        except (PiloterrServerError, PiloterrTimeoutError) as e:
            _lbc_url = LeboncoinQueryBuilder(
                SearchParams(brand=piloterr_brand, model=piloterr_model or None,
                             fuel=piloterr_fuel or None)
            ).build()
            logging.error("Piloterr indisponible — URL=%s — %s", _lbc_url, e)
            st.session_state["p_error"] = str(e)
        except PiloterrError as e:
            logging.error("Erreur Piloterr — %s", e)
            st.session_state["p_error"] = str(e)

if "p_error" in st.session_state:
    st.error(
        "Le fournisseur de données est momentanément indisponible. "
        "Réessayez dans quelques secondes."
    )
    if st.button("Réessayer la recherche"):
        st.session_state.pop("p_error", None)
        st.rerun()
    if "p_listings" not in st.session_state:
        st.stop()

if "p_listings" not in st.session_state:
    st.info(
        "Sélectionnez une marque, un modèle et un carburant dans la sidebar, "
        "puis cliquez sur **Lancer la recherche**."
    )
    st.stop()

all_listings    = st.session_state["p_listings"]
piloterr_meta   = st.session_state.get("p_meta")
_raw_count      = st.session_state.get("p_raw_count", len(all_listings))
_low_excl       = st.session_state.get("p_low_excl", 0)
_filter_level   = st.session_state.get("p_filter_level", 1)
_strict_count   = st.session_state.get("p_strict_count", len(all_listings))
_filter_retained= st.session_state.get("p_filter_retained", len(all_listings))
_year_min_used  = st.session_state.get("p_year_min_used", piloterr_year_min)
_year_max_used  = st.session_state.get("p_year_max_used", piloterr_year_max)
_strategy       = st.session_state.get("p_strategy", "standard")
_retained       = len(all_listings)
_total          = piloterr_meta.total_results if piloterr_meta else "?"

# ── Bannière principale ───────────────────────────────────────────────────────
_level_labels = {
    1: "filtrage strict (marque · modèle · carburant · année exacte)",
    2: f"année élargie automatiquement à {_year_min_used}–{_year_max_used} (±1 an)",
    3: f"année élargie {_year_min_used}–{_year_max_used} + variantes modèle incluses",
}
st.info(
    f"**{_raw_count}** annonces récupérées · "
    f"**{_strict_count}** strictement comparables · "
    f"**{_retained}** retenues pour l'analyse "
    f"*(Niveau {_filter_level} : {_level_labels[_filter_level]})*"
)

# ── Avertissements contextuels ────────────────────────────────────────────────
if _strategy == "elargie":
    st.info("Recherche élargie à la marque pour enrichir l'échantillon.")

if _filter_level == 2:
    st.warning(
        f"Plage d'année élargie automatiquement à **{_year_min_used}–{_year_max_used}** "
        f"(seulement {_strict_count} annonces dans la plage demandée)."
    )
elif _filter_level == 3:
    st.warning(
        f"Variantes du modèle incluses pour enrichir l'échantillon "
        f"(seulement {_strict_count} annonces strictement comparables). "
        f"Plage d'année élargie à **{_year_min_used}–{_year_max_used}**."
    )
if _low_excl > 0:
    st.warning(
        f"{_low_excl} annonce(s) exclue(s) car prix anormalement bas "
        f"(< 60 % de la médiane — véhicules accidentés, annonces atypiques)."
    )
if _retained < 15 and _filter_level == 3:
    st.error("Échantillon faible malgré élargissement automatique. L'estimation est peu fiable.")
elif _retained < 10:
    st.warning("Échantillon faible : l'estimation peut être peu fiable.")

# ── Garde : aucune annonce retenue ────────────────────────────────────────────
if _retained == 0:
    st.warning(
        "Aucune annonce exploitable après filtrage. "
        "Essayez d'élargir la plage d'année, de changer le carburant, "
        "ou de relancer la recherche."
    )
    st.stop()

# ── DataFrame global ──────────────────────────────────────────────────────────
_expected_cols = ["id", "brand", "model", "year", "mileage", "price",
                  "fuel", "transmission", "location", "source",
                  "score", "title", "url", "published_at", "image_url"]
df_all = pd.DataFrame([l.__dict__ for l in all_listings])
for _col in _expected_cols:
    if _col not in df_all.columns:
        df_all[_col] = None

# ── Sidebar — Filtres ─────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.header("Filtres")

brands = sorted(df_all["brand"].unique())
selected_brands = st.sidebar.multiselect("Marque", brands, default=brands)

models_available = sorted(df_all[df_all["brand"].isin(selected_brands)]["model"].unique())
selected_models = st.sidebar.multiselect("Modèle", models_available, default=models_available)

year_min, year_max = int(df_all["year"].min()), int(df_all["year"].max())
if year_min < year_max:
    selected_years = st.sidebar.slider("Année", year_min, year_max, (year_min, year_max))
else:
    st.sidebar.info(f"Toutes les annonces sont de l'année {year_min}")
    selected_years = (year_min, year_max)

km_max = int(df_all["mileage"].max())
selected_km_max = st.sidebar.slider("Kilométrage max", 0, km_max, km_max, step=5000)

price_max = int(df_all["price"].max())
selected_price_max = st.sidebar.slider("Prix max (€)", 0, price_max, price_max, step=500)

# ── Filtrage ──────────────────────────────────────────────────────────────────
mask = (
    df_all["brand"].isin(selected_brands)
    & df_all["model"].isin(selected_models)
    & df_all["year"].between(*selected_years)
    & (df_all["mileage"] <= selected_km_max)
    & (df_all["price"] <= selected_price_max)
)
df = df_all[mask].copy()

if df.empty:
    st.warning("Aucune annonce ne correspond aux filtres sélectionnés.")
    st.stop()

filtered_listings = [all_listings[i] for i in df.index]
stats = compute_stats(filtered_listings)

# Calculs partagés (KPIs + Interprétation)
_count = stats["count"]
_cv = (df["price"].std() / df["price"].mean()) if _count >= 2 else 1.0
_median = stats["median"]
_seuil_bas  = _median * 0.85
_seuil_haut = _median * 1.15

# ── 1. Graphique Prix vs Kilométrage ─────────────────────────────────────────
st.subheader("Prix vs Kilométrage")

_hover_title = df["title"].where(df["title"] != "", df["brand"] + " " + df["model"])
_df_plot = df.copy()
_df_plot["_titre"] = _hover_title
_df_plot["_prix_label"] = df["price"].apply(fmt_price)
_df_plot["_score_label"] = df["score"].apply(
    lambda s: f"{fmt_score(s)} — {deal_score_label(s)}" if s is not None else "—"
)
_show_labels = len(_df_plot) <= 50

# ── Anneaux radar — construits AVANT le scatter principal ────────────────────
# Ordre final dans fig.data : [anneaux..., scatter]
# → scatter dessiné en dernier = points toujours au-dessus des cercles.
import plotly.graph_objects as go

_score_col = _df_plot["score"].fillna(0)
_score_max  = float(_score_col.max()) if not _score_col.empty else 0.0
_n_above_80 = int((_score_col >= 80).sum())

# ── Diagnostic (expander discret) ────────────────────────────────────────────
with st.expander("🔍 Diagnostic scores", expanded=False):
    st.markdown(
        f"**Score max :** {_score_max:.1f}/100  \n"
        f"**Annonces ≥ 80/100 :** {_n_above_80}  \n"
        f"**Champ utilisé :** `score`"
    )
    _diag_df = (
        _df_plot[["score", "price", "mileage", "year"]]
        .sort_values("score", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    _diag_df["score"] = _diag_df["score"].apply(lambda s: f"{s:.1f}/100")
    st.dataframe(_diag_df, use_container_width=True, hide_index=True)

def _make_ring(sub_df, size, color, lw):
    return go.Scatter(
        x=sub_df["mileage"],
        y=sub_df["price"],
        mode="markers",
        marker=dict(
            symbol="circle-open",
            size=size,
            color=color,
            line=dict(width=lw, color=color),
        ),
        hoverinfo="skip",
        showlegend=False,
    )

_ring_traces = []

if _n_above_80 > 0:
    # Cas normal — du plus externe au plus interne (prepend → dessin de bas en haut)
    for _thresh, _sz, _color, _lw in [
        (95, 38, "rgba(40,255,120,0.20)", 1.5),
        (90, 28, "rgba(40,255,120,0.45)", 1.5),
        (80, 18, "rgba(40,255,120,0.75)", 2.0),
    ]:
        _sub = _df_plot[_score_col >= _thresh]
        if not _sub.empty:
            _ring_traces.append(_make_ring(_sub, _sz, _color, _lw))
else:
    # Fallback — top 5 meilleurs scores, 1 anneau discret
    _top5 = _df_plot.loc[_score_col.nlargest(min(5, len(_score_col))).index]
    if not _top5.empty:
        _ring_traces.append(_make_ring(_top5, 18, "rgba(40,255,120,0.60)", 1.8))

# ── Scatter principal — px.scatter génère la trace ET le layout coloraxis ─────
_fig_px = px.scatter(
    _df_plot,
    x="mileage",
    y="price",
    color="year",
    color_continuous_scale=["orange", "yellowgreen", "green"],
    hover_name="_titre",
    text="_prix_label" if _show_labels else None,
    hover_data={
        "_titre": False,
        "_prix_label": False,
        "mileage": False,
        "year": True,
        "brand": True,
        "location": True,
        "fuel": True,
        "transmission": True,
        "_score_label": True,
        "url": True,
    },
    labels={
        "mileage": "Kilométrage (km)", "price": "Prix (€)",
        "year": "Année", "brand": "Marque", "location": "Ville",
        "fuel": "Carburant", "transmission": "Boîte",
        "_score_label": "Score", "url": "URL LeBonCoin",
    },
    opacity=0.85,
)
_fig_px.update_traces(textposition="top center", textfont_size=11)
_fig_px.update_coloraxes(colorbar_title="Année")

# ── Assemblage final : cercles d'abord, points par-dessus ────────────────────
# go.Figure vide + layout récupéré depuis px → add_trace dans le bon ordre.
fig = go.Figure(layout=_fig_px.layout)
for _rt in _ring_traces:          # anneaux en premier (derrière)
    fig.add_trace(_rt)
for _t in _fig_px.data:           # points px par-dessus (devant)
    fig.add_trace(_t)

# Échelle Y intelligente : percentile 3–97 + marge 20 %
if len(_df_plot) >= 4:
    _p3  = float(np.percentile(_df_plot["price"], 3))
    _p97 = float(np.percentile(_df_plot["price"], 97))
    _spread = max(_p97 - _p3, _p3 * 0.10)
    _ym = _spread * 0.20
    _y_range = [max(0.0, _p3 - _ym), _p97 + _ym]
else:
    _y_range = None

fig.update_layout(height=700, yaxis_range=_y_range)
st.plotly_chart(fig, use_container_width=True)
st.caption("🟢 Les annonces entourées représentent les meilleures opportunités du marché (score ≥ 80/100).")

# ── Tableau annonces utilisées (liens cliquables) ────────────────────────────
_has_url   = "url" in df.columns and df["url"].str.strip().ne("").any()
_has_title = "title" in df.columns

with st.expander(f"Annonces utilisées pour l'estimation ({len(df)})", expanded=False):
    _tbl_graph = pd.DataFrame()
    _tbl_graph["Titre"] = (
        df["title"].where(df["title"].str.strip() != "", df["brand"] + " " + df["model"])
        if _has_title else df["brand"] + " " + df["model"]
    )
    _tbl_graph["Prix"]        = df["price"].apply(fmt_price)
    _tbl_graph["Année"]       = df["year"]
    _tbl_graph["Kilométrage"] = df["mileage"].apply(fmt_mileage)
    _tbl_graph["Ville"]       = df["location"]
    _tbl_graph["Score"]       = df["score"].apply(fmt_score)
    if _has_url:
        _tbl_graph["Lien"] = df["url"]
        st.dataframe(
            _tbl_graph, use_container_width=True, hide_index=True,
            column_config={"Lien": st.column_config.LinkColumn("Lien", display_text="Voir l'annonce ↗")},
        )
    else:
        st.dataframe(_tbl_graph, use_container_width=True, hide_index=True)

st.divider()

# ── 2. KPIs ───────────────────────────────────────────────────────────────────
_dispersion_note = f" Dispersion élevée ({int(_cv * 100)} %)." if _cv > 0.40 and _count >= 5 else ""

if _count < 10:
    _fiabilite = "Faible"
    _fiabilite_icon = "🔴"
    _fiabilite_help = f"{_count} annonce(s). Données insuffisantes pour une analyse fiable.{_dispersion_note}"
elif _count <= 25:
    _fiabilite = "Moyen"
    _fiabilite_icon = "🟠"
    _fiabilite_help = f"{_count} annonces. Échantillon limité.{_dispersion_note}"
else:
    _fiabilite = "Bon" if _cv <= 0.40 else "Moyen"
    _fiabilite_icon = "🟢" if _cv <= 0.40 else "🟠"
    _fiabilite_help = f"{_count} annonces.{_dispersion_note or ' Bon volume de données.'}"

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Annonces analysées", _count)
col2.metric("Prix médian", fmt_price(stats["median"]))
col3.metric("Prix moyen", fmt_price(stats["mean"]))
col4.metric("Prix min", fmt_price(stats["min"]))
col5.metric("Prix max", fmt_price(stats["max"]))
col6.metric("Fiabilité", f"{_fiabilite_icon} {_fiabilite}", help=_fiabilite_help)

st.divider()

# ── 2b. Durée estimée de revente ──────────────────────────────────────────────
_resale = estimate_resale_time(
    n_listings=_count,
    median_price=stats["median"],
    mean_price=stats["mean"],
    cv=_cv,
)
_resale_conf_icon = {"Élevée": "🟢", "Moyenne": "🟠", "Faible": "🔴"}.get(_resale.confidence, "⚪")

with st.container(border=True):
    rc1, rc2 = st.columns([1, 3])
    with rc1:
        st.metric(
            "Durée estimée de revente",
            f"{_resale.days} jours",
            help="Estimation basée sur la liquidité du marché et le positionnement prix.",
        )
        st.caption(f"Confiance : {_resale_conf_icon} {_resale.confidence}")
    with rc2:
        st.markdown(f"_{_resale.explanation}_")

st.divider()

# ── 3. Analyse automatique du marché ─────────────────────────────────────────
st.subheader("Analyse automatique du marché")

_n_affaire = int((df["price"] < _seuil_bas).sum())
_n_marche  = int(((df["price"] >= _seuil_bas) & (df["price"] <= _seuil_haut)).sum())
_n_dessus  = int((df["price"] > _seuil_haut).sum())

icol1, icol2, icol3 = st.columns(3)
with icol1:
    st.markdown("#### 🟢 Bonne affaire")
    st.markdown(f"Prix **< {fmt_price(_seuil_bas)}**")
    st.caption(f"{_n_affaire} annonce(s) — plus de 15 % sous le médian")
with icol2:
    st.markdown("#### 🔵 Prix de marché")
    st.markdown(f"**{fmt_price(_seuil_bas)} – {fmt_price(_seuil_haut)}**")
    st.caption(f"{_n_marche} annonce(s) — fourchette ±15 % autour du médian")
with icol3:
    st.markdown("#### 🔴 Au-dessus du marché")
    st.markdown(f"Prix **> {fmt_price(_seuil_haut)}**")
    st.caption(f"{_n_dessus} annonce(s) — plus de 15 % au-dessus du médian")

st.divider()

# ── 4. Top bonnes affaires ────────────────────────────────────────────────────
st.subheader("Top bonnes affaires")

_has_url   = "url" in df.columns and df["url"].str.strip().ne("").any()
_has_title = "title" in df.columns

_df_top = df.dropna(subset=["score"]).sort_values("score", ascending=False).head(5)
_top = pd.DataFrame()
_top["Titre"] = (
    _df_top["title"].where(_df_top["title"].str.strip() != "", _df_top["brand"] + " " + _df_top["model"])
    if _has_title else _df_top["brand"] + " " + _df_top["model"]
)
_top["Prix"]        = _df_top["price"].apply(fmt_price)
_top["Année"]       = _df_top["year"]
_top["Kilométrage"] = _df_top["mileage"].apply(fmt_mileage)
_top["Ville"]       = _df_top["location"]
_top["Score"]       = _df_top["score"].apply(fmt_score)
_top["Verdict"]     = _df_top["score"].apply(deal_score_label)

if _has_url:
    _top["Lien"] = _df_top["url"]
    st.dataframe(
        _top, use_container_width=True, hide_index=True,
        column_config={"Lien": st.column_config.LinkColumn("Lien", display_text="Voir l'annonce")},
    )
else:
    st.dataframe(_top, use_container_width=True, hide_index=True)

