import streamlit as st
import pandas as pd
import plotly.express as px

from app.providers.provider_factory import get_provider
from app.services.cleaning_service import clean
from app.services.analysis_service import run_analysis
from app.utils.formatting import fmt_price, fmt_mileage, fmt_score

st.set_page_config(page_title="LCB Price Analyser", page_icon="🚗", layout="wide")
st.title("🚗 LCB Price Analyser")
st.caption("Analyse de prix d'annonces automobiles — MVP v1")

# ── Chargement des données ────────────────────────────────────────────────────
@st.cache_data
def load_data():
    provider = get_provider("mock", n=200, seed=42)
    raw = provider.fetch()
    cleaned = clean(raw)
    result = run_analysis(cleaned)
    return result["listings"], result["stats"]

all_listings, global_stats = load_data()
df_all = pd.DataFrame([l.__dict__ for l in all_listings])

# ── Sidebar — Filtres ─────────────────────────────────────────────────────────
st.sidebar.header("Filtres")

brands = sorted(df_all["brand"].unique())
selected_brands = st.sidebar.multiselect("Marque", brands, default=brands)

models_available = sorted(df_all[df_all["brand"].isin(selected_brands)]["model"].unique())
selected_models = st.sidebar.multiselect("Modèle", models_available, default=models_available)

year_min, year_max = int(df_all["year"].min()), int(df_all["year"].max())
selected_years = st.sidebar.slider("Année", year_min, year_max, (year_min, year_max))

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

# ── KPIs ──────────────────────────────────────────────────────────────────────
if df.empty:
    st.warning("Aucune annonce ne correspond aux filtres sélectionnés.")
    st.stop()

from app.models.listing import Listing
from app.analytics.price_stats import compute_stats

filtered_listings = [all_listings[i] for i in df.index]
stats = compute_stats(filtered_listings)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Annonces", stats["count"])
col2.metric("Prix moyen", fmt_price(stats["mean"]))
col3.metric("Prix médian", fmt_price(stats["median"]))
col4.metric("Prix min", fmt_price(stats["min"]))
col5.metric("Prix max", fmt_price(stats["max"]))

st.divider()

# ── Graphique prix vs kilométrage ─────────────────────────────────────────────
st.subheader("Prix vs Kilométrage")

fig = px.scatter(
    df,
    x="mileage",
    y="price",
    color="brand",
    hover_data=["model", "year", "fuel", "location"],
    labels={"mileage": "Kilométrage (km)", "price": "Prix (€)", "brand": "Marque"},
    opacity=0.75,
)
fig.update_layout(height=420)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Tableau des annonces ──────────────────────────────────────────────────────
st.subheader("Annonces")

df_display = df[["brand", "model", "year", "mileage", "price", "fuel", "transmission", "location", "score"]].copy()
df_display["mileage"] = df_display["mileage"].apply(fmt_mileage)
df_display["price"] = df_display["price"].apply(fmt_price)
df_display["score"] = df_display["score"].apply(fmt_score)
df_display.columns = ["Marque", "Modèle", "Année", "Kilométrage", "Prix", "Carburant", "Boîte", "Ville", "Score"]

st.dataframe(df_display, use_container_width=True, hide_index=True)
