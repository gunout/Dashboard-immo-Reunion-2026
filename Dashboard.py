# dashboard_reunion_complet.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Immobilier La Réunion - Toutes années",
    page_icon="🌴",
    layout="wide"
)

# Dictionnaire des communes
COMMUNES_REUNION = {
    "97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Cilaos",
    "97404": "Entre-Deux", "97405": "L'Étang-Salé", "97406": "Petite-Île",
    "97407": "La Plaine-des-Palmistes", "97408": "Le Port", "97409": "La Possession",
    "97410": "Saint-André", "97411": "Saint-Benoît", "97412": "Saint-Denis",
    "97413": "Saint-Joseph", "97414": "Saint-Leu", "97415": "Saint-Louis",
    "97416": "Saint-Paul", "97417": "Saint-Pierre", "97418": "Saint-Philippe",
    "97419": "Sainte-Marie", "97420": "Sainte-Rose", "97421": "Sainte-Suzanne",
    "97422": "Salazie", "97423": "Le Tampon", "97424": "Les Trois-Bassins"
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
    """Nettoie les données avec les colonnes du fichier"""
    if df.empty:
        return df
    
    df_clean = df.copy()
    
    # Conversion des dates
    df_clean['date_mutation'] = pd.to_datetime(df_clean['datemut'], errors='coerce')
    df_clean['annee'] = df_clean['date_mutation'].dt.year
    df_clean['mois'] = df_clean['date_mutation'].dt.month
    
    # Valeur foncière
    df_clean['valeur_fonciere'] = pd.to_numeric(df_clean['valeurfonc'], errors='coerce')
    
    # Surface bâtie (sbati)
    df_clean['surface_reelle_bati'] = pd.to_numeric(df_clean['sbati'], errors='coerce')
    
    # Type de bien
    df_clean['type_local'] = df_clean['libtypbien']
    
    # Code commune et nom
    df_clean['code_commune'] = df_clean['l_codinsee'].astype(str).str.zfill(5)
    df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_REUNION)
    
    # Coordonnées
    df_clean['longitude'] = pd.to_numeric(df_clean['geompar_x'], errors='coerce')
    df_clean['latitude'] = pd.to_numeric(df_clean['geompar_y'], errors='coerce')
    
    # Code postal
    df_clean['code_postal'] = df_clean['codservch'].astype(str).str[:5]
    
    # Filtrage : on garde uniquement les maisons et appartements
    df_clean = df_clean[df_clean['type_local'].isin(['Maison', 'Appartement'])]
    
    # Supprimer les valeurs manquantes critiques
    df_clean = df_clean.dropna(subset=['valeur_fonciere', 'surface_reelle_bati', 'nom_commune'])
    
    # Filtrage des valeurs aberrantes (seuils adaptés)
    df_clean = df_clean[df_clean['valeur_fonciere'] > 15000]
    df_clean = df_clean[df_clean['valeur_fonciere'] < 3000000]
    df_clean = df_clean[df_clean['surface_reelle_bati'] > 9]
    df_clean = df_clean[df_clean['surface_reelle_bati'] < 500]
    
    # Prix au m²
    df_clean['prix_m2'] = df_clean['valeur_fonciere'] / df_clean['surface_reelle_bati']
    df_clean = df_clean[(df_clean['prix_m2'] > 300) & (df_clean['prix_m2'] < 10000)]
    
    return df_clean

# Interface principale
st.title("🌴 Dashboard Immobilier La Réunion")
st.markdown("*Source : DVF Plus - Toutes années confondues*")

# Chargement
df_raw = load_data()
if df_raw.empty:
    st.stop()

# Nettoyage
with st.spinner("🧹 Nettoyage des données..."):
    df = prepare_data(df_raw)

if df.empty:
    st.error("❌ Aucune transaction valide après nettoyage")
    
    with st.expander("🔍 Diagnostic"):
        st.write("**Colonnes disponibles:**", df_raw.columns.tolist())
        st.write("**Types de biens trouvés:**", df_raw['libtypbien'].unique())
        st.write("**Exemple de données brutes:**")
        st.dataframe(df_raw.head(3))
    
    # Vérification spécifique
    st.info("""
    **Causes possibles :**
    - Pas de Maisons/Appartements dans les données
    - Surfaces (sbati) toutes à 0
    - Valeurs aberrantes filtrées
    """)
    
    # Afficher les stats des surfaces
    if 'sbati' in df_raw.columns:
        st.write("**Statistiques des surfaces (sbati) :**")
        st.write(df_raw['sbati'].describe())
    
    st.stop()

# Succès
annees_dispo = sorted(df['annee'].dropna().unique())
st.success(f"✅ {len(df):,} transactions valides ({min(annees_dispo)} - {max(annees_dispo)})")

# Sidebar - Filtre année
st.sidebar.header("📅 Période")
selected_annee = st.sidebar.selectbox(
    "Année",
    options=['Toutes'] + [int(a) for a in annees_dispo if a <= 2026],
    index=0
)

if selected_annee != 'Toutes':
    df = df[df['annee'] == selected_annee]

# Statistiques globales
st.header("📊 Vue d'ensemble")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Communes", f"{df['nom_commune'].nunique()}")

with col2:
    st.metric("Transactions", f"{len(df):,}")

with col3:
    st.metric("Prix moyen / m²", f"{df['prix_m2'].mean():,.0f} €")

with col4:
    st.metric("Prix médian", f"{df['valeur_fonciere'].median():,.0f} €")

with col5:
    st.metric("Surface moyenne", f"{df['surface_reelle_bati'].mean():.0f} m²")

# Évolution temporelle
st.subheader("📈 Évolution historique (toutes communes)")

df_annuel = df.groupby('annee').agg({
    'prix_m2': 'mean',
    'valeur_fonciere': 'count'
}).round(0).reset_index()

df_annuel.columns = ['année', 'prix_m2_moyen', 'nb_transactions']

col1, col2 = st.columns(2)

with col1:
    fig = px.line(df_annuel, x='année', y='prix_m2_moyen', 
                  title="Évolution du prix au m² (€)",
                  markers=True, text='prix_m2_moyen')
    fig.update_traces(textposition='top center')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_annuel, x='année', y='nb_transactions',
                 title="Nombre de transactions par année",
                 text='nb_transactions')
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# Classement des communes
st.subheader("🏆 Classement des communes")

stats_communes = df.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'mean'],
    'prix_m2': 'mean',
    'surface_reelle_bati': 'mean'
}).round(0)

stats_communes.columns = ['Transactions', 'Prix moyen', 'Prix m² moyen', 'Surface moyenne']
stats_communes = stats_communes.sort_values('Transactions', ascending=False).reset_index()

stats_communes['Prix moyen'] = stats_communes['Prix moyen'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix m² moyen'] = stats_communes['Prix m² moyen'].apply(lambda x: f"{x:,.0f} €")

st.dataframe(stats_communes, use_container_width=True, hide_index=True)

# Top 10 graphiques
col1, col2 = st.columns(2)

with col1:
    fig = px.bar(stats_communes.head(10), x='nom_commune', y='Transactions',
                 title="Top 10 communes les plus actives",
                 color='Prix m² moyen', color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    top_prix = df.groupby('nom_commune')['prix_m2'].mean().round(0).sort_values(ascending=False).head(10).reset_index()
    fig = px.bar(top_prix, x='nom_commune', y='prix_m2',
                 title="Top 10 communes les plus chères au m²",
                 color='prix_m2', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig, use_container_width=True)

# Sélection commune
st.sidebar.header("📍 Commune")
communes_disponibles = sorted(df['nom_commune'].unique())
selected_commune = st.sidebar.selectbox("Choisissez une commune", communes_disponibles)

df_commune = df[df['nom_commune'] == selected_commune]

if not df_commune.empty:
    st.header(f"📊 {selected_commune}")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Transactions", f"{len(df_commune):,}")
    with k2:
        st.metric("Prix moyen / m²", f"{df_commune['prix_m2'].mean():,.0f} €")
    with k3:
        st.metric("Prix médian", f"{df_commune['valeur_fonciere'].median():,.0f} €")
    with k4:
        st.metric("Surface moyenne", f"{df_commune['surface_reelle_bati'].mean():.0f} m²")
    
    # Graphiques pour la commune
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(df_commune, x='prix_m2', nbins=30,
                           title=f"Distribution prix m² - {selected_commune}",
                           color='type_local')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(df_commune, x='surface_reelle_bati', y='valeur_fonciere',
                         title="Prix vs Surface",
                         color='type_local', opacity=0.6,
                         labels={'surface_reelle_bati': 'Surface (m²)',
                                'valeur_fonciere': 'Prix (€)'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Évolution pour la commune
    df_commune_annuel = df_commune.groupby('annee').agg({
        'prix_m2': 'mean',
        'valeur_fonciere': 'count'
    }).round(0).reset_index()
    
    if len(df_commune_annuel) > 1:
        fig = px.line(df_commune_annuel, x='annee', y='prix_m2_moyen',
                      title=f"Évolution prix m² - {selected_commune}",
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)

# Carte
if 'latitude' in df.columns and 'longitude' in df.columns:
    df_carte = df.dropna(subset=['latitude', 'longitude'])
    if not df_carte.empty:
        st.subheader("🗺️ Carte des transactions")
        
        echantillon = df_carte.sample(min(500, len(df_carte)))
        
        fig = px.scatter_mapbox(
            echantillon,
            lat="latitude", lon="longitude",
            color="prix_m2", size="surface_reelle_bati",
            hover_name="nom_commune",
            hover_data={"valeur_fonciere": ":.0f", "prix_m2": ":.0f"},
            color_continuous_scale="RdYlGn_r",
            zoom=8, mapbox_style="open-street-map"
        )
        st.plotly_chart(fig, use_container_width=True)

# Pied de page
st.markdown("---")
st.markdown(f"*📊 {len(df):,} transactions - Données DVF Plus - {datetime.now().strftime('%d/%m/%Y')}*")
