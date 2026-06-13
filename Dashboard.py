# dashboard_reunion_communes_map.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Immobilier La Réunion",
    page_icon="🌴",
    layout="wide"
)

# Dictionnaire des communes AVEC coordonnées WGS84 (centres)
COMMUNES_COORDS = {
    "Saint-Denis": {"lat": -20.8823, "lon": 55.4504, "code": "97412"},
    "Saint-Pierre": {"lat": -21.3419, "lon": 55.4778, "code": "97417"},
    "Saint-Paul": {"lat": -21.0096, "lon": 55.2696, "code": "97416"},
    "Saint-Louis": {"lat": -21.2862, "lon": 55.4095, "code": "97415"},
    "Saint-André": {"lat": -20.9601, "lon": 55.6502, "code": "97410"},
    "Saint-Benoît": {"lat": -21.0342, "lon": 55.7121, "code": "97411"},
    "Saint-Joseph": {"lat": -21.3782, "lon": 55.6194, "code": "97413"},
    "Saint-Leu": {"lat": -21.1674, "lon": 55.2861, "code": "97414"},
    "Sainte-Marie": {"lat": -20.8969, "lon": 55.5493, "code": "97419"},
    "Sainte-Suzanne": {"lat": -20.9064, "lon": 55.6075, "code": "97421"},
    "Sainte-Rose": {"lat": -21.1289, "lon": 55.7933, "code": "97420"},
    "Le Tampon": {"lat": -21.2800, "lon": 55.5200, "code": "97423"},
    "Les Avirons": {"lat": -21.2425, "lon": 55.3394, "code": "97401"},
    "Bras-Panon": {"lat": -20.9953, "lon": 55.6778, "code": "97402"},
    "Cilaos": {"lat": -21.1347, "lon": 55.4661, "code": "97403"},
    "Entre-Deux": {"lat": -21.2464, "lon": 55.4706, "code": "97404"},
    "L'Étang-Salé": {"lat": -21.2633, "lon": 55.3644, "code": "97405"},
    "Petite-Île": {"lat": -21.3531, "lon": 55.5644, "code": "97406"},
    "La Plaine-des-Palmistes": {"lat": -21.1356, "lon": 55.6250, "code": "97407"},
    "Le Port": {"lat": -20.9389, "lon": 55.2903, "code": "97408"},
    "La Possession": {"lat": -20.9300, "lon": 55.3350, "code": "97409"},
    "Saint-Philippe": {"lat": -21.3594, "lon": 55.7678, "code": "97418"},
    "Salazie": {"lat": -21.0275, "lon": 55.5386, "code": "97422"},
    "Les Trois-Bassins": {"lat": -21.1150, "lon": 55.2900, "code": "97424"},
}

@st.cache_data(ttl=3600)
def load_data():
    """Charge les données depuis GitHub Releases"""
    url = "https://github.com/gunout/Dashboard-immo-Reunion-2026/releases/download/Dvf_plus_2026/dvf_plus_d974.csv"
    try:
        df = pd.read_csv(url, sep='|', encoding='utf-8', low_memory=False)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement: {e}")
        return pd.DataFrame()

def prepare_data(df):
    """Nettoie les données"""
    if df.empty:
        return df
    
    df_clean = df.copy()
    
    # Dates
    df_clean['date_mutation'] = pd.to_datetime(df_clean['datemut'], errors='coerce')
    df_clean['annee'] = df_clean['date_mutation'].dt.year
    
    # Valeur foncière
    df_clean['valeur_fonciere'] = pd.to_numeric(df_clean['valeurfonc'], errors='coerce')
    
    # Surface
    df_clean['surface_reelle_bati'] = pd.to_numeric(df_clean['sbati'], errors='coerce')
    
    # Type de bien
    df_clean['type_local'] = df_clean['libtypbien']
    
    # Code commune et nom
    df_clean['code_commune'] = df_clean['l_codinsee'].astype(str).str.zfill(5)
    
    # Associer le nom de commune via notre dictionnaire
    code_to_name = {v['code']: k for k, v in COMMUNES_COORDS.items()}
    df_clean['nom_commune'] = df_clean['code_commune'].map(code_to_name)
    
    # Ajouter les coordonnées des communes
    df_clean['latitude'] = df_clean['nom_commune'].map(lambda x: COMMUNES_COORDS.get(x, {}).get('lat') if x else None)
    df_clean['longitude'] = df_clean['nom_commune'].map(lambda x: COMMUNES_COORDS.get(x, {}).get('lon') if x else None)
    
    # Code postal
    df_clean['code_postal'] = df_clean['codservch'].astype(str).str[:5]
    
    # Filtrage
    df_clean = df_clean.dropna(subset=['valeur_fonciere', 'nom_commune'])
    df_clean = df_clean[df_clean['valeur_fonciere'] > 5000]
    df_clean = df_clean[df_clean['valeur_fonciere'] < 5000000]
    
    # Prix au m²
    mask_surface = (df_clean['surface_reelle_bati'] > 9) & (df_clean['surface_reelle_bati'] < 10000)
    df_clean['prix_m2'] = np.nan
    df_clean.loc[mask_surface, 'prix_m2'] = (
        df_clean.loc[mask_surface, 'valeur_fonciere'] / 
        df_clean.loc[mask_surface, 'surface_reelle_bati']
    )
    
    return df_clean

# Chargement
st.title("🌴 Dashboard Immobilier La Réunion")
st.markdown("*Source : DVF Plus - Tous types de biens*")

df_raw = load_data()
if df_raw.empty:
    st.stop()

with st.spinner("Nettoyage des données..."):
    df = prepare_data(df_raw)

if df.empty:
    st.error("❌ Aucune transaction valide")
    st.stop()

# Sidebar
st.sidebar.header("📅 Filtres")

annees_dispo = sorted(df['annee'].dropna().unique())
selected_annee = st.sidebar.selectbox("Année", ['Toutes'] + [int(a) for a in annees_dispo if pd.notna(a)])

types_dispo = df['type_local'].value_counts()
selected_type = st.sidebar.selectbox("Type de bien", ['Tous'] + list(types_dispo.head(10).index))

prix_max = int(df['valeur_fonciere'].max())
prix_range = st.sidebar.slider("Prix (€)", 0, prix_max, (0, prix_max))

# Application filtres
df_filtered = df.copy()
if selected_annee != 'Toutes':
    df_filtered = df_filtered[df_filtered['annee'] == selected_annee]
if selected_type != 'Tous':
    df_filtered = df_filtered[df_filtered['type_local'] == selected_type]
df_filtered = df_filtered[(df_filtered['valeur_fonciere'] >= prix_range[0]) & (df_filtered['valeur_fonciere'] <= prix_range[1])]

if df_filtered.empty:
    st.warning("Aucune transaction avec ces filtres")
    st.stop()

# KPIs
st.header("📊 Vue d'ensemble")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Transactions", f"{len(df_filtered):,}")
with col2:
    st.metric("Communes", f"{df_filtered['nom_commune'].nunique()}")
with col3:
    st.metric("Prix médian", f"{df_filtered['valeur_fonciere'].median():,.0f} €")
with col4:
    prix_m2 = df_filtered['prix_m2'].mean()
    if pd.notna(prix_m2):
        st.metric("Prix moyen / m²", f"{prix_m2:,.0f} €")

# Classement communes
st.subheader("🏆 Classement des communes")
stats = df_filtered.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'median'],
    'prix_m2': 'mean'
}).round(0)
stats.columns = ['Transactions', 'Prix médian', 'Prix m² moyen']
stats = stats.sort_values('Transactions', ascending=False).reset_index()
stats['Prix médian'] = stats['Prix médian'].apply(lambda x: f"{x:,.0f} €")
stats['Prix m² moyen'] = stats['Prix m² moyen'].apply(lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A")
st.dataframe(stats, use_container_width=True, hide_index=True)

# Carte de l'île (agrégée par commune)
st.subheader("🗺️ Carte des transactions par commune")

# Agrégation par commune pour la carte
commune_stats = df_filtered.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'median'],
    'latitude': 'first',
    'longitude': 'first'
}).round(0)
commune_stats.columns = ['nb_transactions', 'prix_median', 'latitude', 'longitude']
commune_stats = commune_stats.dropna(subset=['latitude', 'longitude']).reset_index()

if not commune_stats.empty:
    fig = px.scatter_mapbox(
        commune_stats,
        lat="latitude",
        lon="longitude",
        size="nb_transactions",
        color="prix_median",
        hover_name="nom_commune",
        hover_data={
            "nb_transactions": True,
            "prix_median": ":.0f"
        },
        color_continuous_scale="Viridis",
        size_max=25,
        zoom=8,
        mapbox_style="open-street-map",
        title=f"Transactions par commune - {'Toutes années' if selected_annee == 'Toutes' else selected_annee}"
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Impossible d'afficher la carte")

# Top communes graphiques
col1, col2 = st.columns(2)
with col1:
    fig = px.bar(stats.head(10), x='nom_commune', y='Transactions', 
                 title="Top 10 communes les plus actives")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    top_prix = df_filtered.dropna(subset=['prix_m2']).groupby('nom_commune')['prix_m2'].mean().round(0).sort_values(ascending=False).head(10)
    if not top_prix.empty:
        fig = px.bar(x=top_prix.values, y=top_prix.index, orientation='h',
                     title="Top 10 communes les plus chères (m²)")
        st.plotly_chart(fig, use_container_width=True)

# Sélection commune
st.sidebar.header("📍 Commune")
communes_list = sorted(df_filtered['nom_commune'].unique())
selected_commune = st.sidebar.selectbox("Choisissez une commune", communes_list)

df_commune = df_filtered[df_filtered['nom_commune'] == selected_commune]

if not df_commune.empty:
    st.header(f"📊 {selected_commune}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Transactions", f"{len(df_commune):,}")
    with col2:
        st.metric("Prix médian", f"{df_commune['valeur_fonciere'].median():,.0f} €")
    with col3:
        prix_m2 = df_commune['prix_m2'].mean()
        if pd.notna(prix_m2):
            st.metric("Prix moyen / m²", f"{prix_m2:,.0f} €")
    with col4:
        surface = df_commune[df_commune['surface_reelle_bati'] > 0]['surface_reelle_bati'].mean()
        if pd.notna(surface):
            st.metric("Surface moyenne", f"{surface:.0f} m²")
    
    # Graphiques commune
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(df_commune, x='valeur_fonciere', nbins=30,
                           title=f"Distribution des prix - {selected_commune}",
                           log_x=True)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        types = df_commune['type_local'].value_counts().head(8)
        fig = px.pie(values=types.values, names=types.index,
                     title=f"Types de biens - {selected_commune}")
        st.plotly_chart(fig, use_container_width=True)
    
    # Évolution
    annuel = df_commune.groupby('annee').agg({
        'valeur_fonciere': ['count', 'median']
    }).round(0)
    annuel.columns = ['nb', 'prix_median']
    annuel = annuel.reset_index().dropna()
    
    if len(annuel) > 1:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(annuel, x='annee', y='nb', markers=True,
                          title=f"Transactions par année - {selected_commune}")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(annuel, x='annee', y='prix_median', markers=True,
                          title=f"Prix médian par année - {selected_commune}")
            st.plotly_chart(fig, use_container_width=True)

# Pied de page
st.markdown("---")
st.markdown(f"*📊 {len(df_filtered):,} transactions - Données DVF Plus - {datetime.now().strftime('%d/%m/%Y')}*")
