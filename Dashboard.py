# dashboard_reunion_complet_fixed.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Immobilier La Réunion - Tous biens",
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

# Coordonnées approximatives des communes (centres) pour fallback
COMMUNES_COORDS = {
    "Saint-Denis": (20.8823, 55.4504),
    "Saint-Pierre": (21.3419, 55.4778),
    "Saint-Paul": (21.0096, 55.2696),
    "Saint-Louis": (21.2862, 55.4095),
    "Saint-André": (20.9601, 55.6502),
    "Saint-Benoît": (21.0342, 55.7121),
    "Saint-Joseph": (21.3782, 55.6194),
    "Saint-Leu": (21.1674, 55.2861),
    "Sainte-Marie": (20.8969, 55.5493),
    "Sainte-Suzanne": (20.9064, 55.6075),
    "Le Tampon": (21.2800, 55.5200),
    "Les Avirons": (21.2425, 55.3394),
    "Bras-Panon": (20.9953, 55.6778),
    "Cilaos": (21.1347, 55.4661),
    "Entre-Deux": (21.2464, 55.4706),
    "L'Étang-Salé": (21.2633, 55.3644),
    "Petite-Île": (21.3531, 55.5644),
    "La Plaine-des-Palmistes": (21.1356, 55.6250),
    "Le Port": (20.9389, 55.2903),
    "La Possession": (20.9300, 55.3350),
    "Saint-Philippe": (21.3594, 55.7678),
    "Sainte-Rose": (21.1289, 55.7933),
    "Salazie": (21.0275, 55.5386),
    "Les Trois-Bassins": (21.1150, 55.2900),
}

def convert_utm_to_wgs84(x, y):
    """Convertit approximativement les coordonnées UTM (RGF93) en WGS84 pour La Réunion"""
    # Ces valeurs sont approximatives - La Réunion est en zone UTM 40S
    # Facteurs simplifiés pour la conversion
    if pd.isna(x) or pd.isna(y):
        return None, None
    
    try:
        x_f = float(x)
        y_f = float(y)
        
        # Conversion approximative pour La Réunion
        # Centre approximatif de l'île
        lon_center = 55.5
        lat_center = -21.1
        
        # Facteurs de conversion (approximatifs)
        lon = lon_center + (x_f - 350000) / 111000
        lat = lat_center + (y_f - 7638000) / 111000
        
        return lat, lon
    except:
        return None, None

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
    """Nettoie les données en incluant TOUS les types de biens"""
    if df.empty:
        return df
    
    df_clean = df.copy()
    
    # Conversion des dates
    df_clean['date_mutation'] = pd.to_datetime(df_clean['datemut'], errors='coerce')
    df_clean['annee'] = df_clean['date_mutation'].dt.year
    df_clean['mois'] = df_clean['date_mutation'].dt.month
    
    # Valeur foncière
    df_clean['valeur_fonciere'] = pd.to_numeric(df_clean['valeurfonc'], errors='coerce')
    
    # Surface bâtie
    df_clean['surface_reelle_bati'] = pd.to_numeric(df_clean['sbati'], errors='coerce')
    
    # Type de bien
    df_clean['type_local'] = df_clean['libtypbien']
    
    # Code commune et nom
    df_clean['code_commune'] = df_clean['l_codinsee'].astype(str).str.zfill(5)
    df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_REUNION)
    
    # Conversion des coordonnées UTM -> WGS84
    df_clean['raw_x'] = pd.to_numeric(df_clean['geompar_x'], errors='coerce')
    df_clean['raw_y'] = pd.to_numeric(df_clean['geompar_y'], errors='coerce')
    
    # Appliquer la conversion
    coords = df_clean.apply(
        lambda row: convert_utm_to_wgs84(row['raw_x'], row['raw_y']), 
        axis=1
    )
    df_clean['latitude'] = coords.apply(lambda x: x[0] if x else None)
    df_clean['longitude'] = coords.apply(lambda x: x[1] if x else None)
    
    # Fallback: utiliser coordonnées communes pour ceux sans géoloc
    for commune, (lat, lon) in COMMUNES_COORDS.items():
        mask = (df_clean['nom_commune'] == commune) & (df_clean['latitude'].isna())
        df_clean.loc[mask, 'latitude'] = lat
        df_clean.loc[mask, 'longitude'] = lon
    
    # Code postal
    df_clean['code_postal'] = df_clean['codservch'].astype(str).str[:5]
    
    # Supprimer les valeurs manquantes critiques
    df_clean = df_clean.dropna(subset=['valeur_fonciere', 'nom_commune'])
    
    # Filtrage des valeurs aberrantes
    df_clean = df_clean[df_clean['valeur_fonciere'] > 5000]
    df_clean = df_clean[df_clean['valeur_fonciere'] < 5000000]
    
    # Prix au m² (uniquement pour surface > 0)
    mask_surface_valide = (df_clean['surface_reelle_bati'] > 9) & (df_clean['surface_reelle_bati'] < 10000)
    df_clean['prix_m2'] = np.nan
    df_clean.loc[mask_surface_valide, 'prix_m2'] = (
        df_clean.loc[mask_surface_valide, 'valeur_fonciere'] / 
        df_clean.loc[mask_surface_valide, 'surface_reelle_bati']
    )
    
    return df_clean

# Interface principale
st.title("🌴 Dashboard Immobilier La Réunion")
st.markdown("*Source : DVF Plus - Tous types de biens (maisons, appartements, terrains)*")

# Chargement
df_raw = load_data()
if df_raw.empty:
    st.stop()

# Nettoyage
with st.spinner("🧹 Nettoyage des données..."):
    df = prepare_data(df_raw)

if df.empty:
    st.error("❌ Aucune transaction valide après nettoyage")
    st.stop()

# Succès
annees_dispo = sorted(df['annee'].dropna().unique())
types_dispo = df['type_local'].value_counts()

st.success(f"✅ {len(df):,} transactions valides ({min(annees_dispo)} - {max(annees_dispo)})")

# Vérifier les coordonnées
coord_count = df['latitude'].notna().sum()
if coord_count > 0:
    st.info(f"📍 {coord_count:,} transactions géolocalisées sur {len(df):,}")
else:
    st.warning("⚠️ Aucune donnée de géolocalisation disponible - les cartes ne s'afficheront pas")

# Sidebar - Filtres
st.sidebar.header("📅 Filtres")

# Filtre année
selected_annee = st.sidebar.selectbox(
    "Année",
    options=['Toutes'] + [int(a) for a in annees_dispo if a <= 2026 and pd.notna(a)],
    index=0
)

# Filtre type de bien
type_options = ['Tous'] + list(types_dispo.head(10).index)
selected_type = st.sidebar.selectbox("Type de bien", type_options)

# Filtre prix
prix_max = int(df['valeur_fonciere'].max())
prix_range = st.sidebar.slider(
    "Prix (€)",
    min_value=0,
    max_value=prix_max,
    value=(0, prix_max)
)

# Application des filtres
df_filtered = df.copy()

if selected_annee != 'Toutes':
    df_filtered = df_filtered[df_filtered['annee'] == selected_annee]

if selected_type != 'Tous':
    df_filtered = df_filtered[df_filtered['type_local'] == selected_type]

df_filtered = df_filtered[
    (df_filtered['valeur_fonciere'] >= prix_range[0]) & 
    (df_filtered['valeur_fonciere'] <= prix_range[1])
]

if df_filtered.empty:
    st.warning("Aucune transaction avec ces filtres")
    st.stop()

# Statistiques globales
st.header("📊 Vue d'ensemble")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Communes", f"{df_filtered['nom_commune'].nunique()}")

with col2:
    st.metric("Transactions", f"{len(df_filtered):,}")

with col3:
    prix_m2_moyen = df_filtered['prix_m2'].mean()
    if pd.notna(prix_m2_moyen):
        st.metric("Prix moyen / m²", f"{prix_m2_moyen:,.0f} €")
    else:
        st.metric("Prix moyen / m²", "N/A")

with col4:
    st.metric("Prix médian", f"{df_filtered['valeur_fonciere'].median():,.0f} €")

with col5:
    surface_non_zero = df_filtered[df_filtered['surface_reelle_bati'] > 0]
    if not surface_non_zero.empty:
        st.metric("Surface moyenne (bâti)", f"{surface_non_zero['surface_reelle_bati'].mean():.0f} m²")

# Top communes
st.subheader("🏆 Classement des communes")

stats_communes = df_filtered.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'mean', 'median'],
    'prix_m2': 'mean'
}).round(0)

stats_communes.columns = ['Transactions', 'Prix moyen', 'Prix médian', 'Prix m² moyen']
stats_communes = stats_communes.sort_values('Transactions', ascending=False).reset_index()

stats_communes['Prix moyen'] = stats_communes['Prix moyen'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix médian'] = stats_communes['Prix médian'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix m² moyen'] = stats_communes['Prix m² moyen'].apply(
    lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A"
)

st.dataframe(stats_communes, use_container_width=True, hide_index=True)

# Graphiques
col1, col2 = st.columns(2)

with col1:
    fig = px.bar(stats_communes.head(10), x='nom_commune', y='Transactions',
                 title="Top 10 communes les plus actives",
                 color='Prix moyen', color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    df_prix = df_filtered.dropna(subset=['prix_m2'])
    if not df_prix.empty:
        top_prix = df_prix.groupby('nom_commune')['prix_m2'].mean().round(0).sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(top_prix, x='nom_commune', y='prix_m2',
                     title="Top 10 communes les plus chères au m²",
                     color='prix_m2', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig, use_container_width=True)

# Carte des transactions (si coordonnées disponibles)
st.subheader("🗺️ Carte des transactions")

df_carte = df_filtered.dropna(subset=['latitude', 'longitude'])

if not df_carte.empty:
    # Échantillonnage pour performance
    if len(df_carte) > 1000:
        df_carte = df_carte.sample(1000, random_state=42)
        st.caption(f"Affichage de 1000 transactions sur {len(df_filtered)} (échantillon)")
    
    fig = px.scatter_mapbox(
        df_carte,
        lat="latitude",
        lon="longitude",
        color="valeur_fonciere",
        size="valeur_fonciere",
        hover_name="nom_commune",
        hover_data={
            "valeur_fonciere": ":.0f",
            "type_local": True,
            "annee": True,
            "surface_reelle_bati": ":.0f"
        },
        color_continuous_scale="Viridis",
        size_max=15,
        zoom=9,
        mapbox_style="open-street-map",
        title=f"Transactions immobilières à La Réunion ({selected_annee if selected_annee != 'Toutes' else 'toutes années'})"
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("📍 Aucune donnée de géolocalisation disponible pour afficher la carte")
    
    # Afficher un graphique alternatif
    st.subheader("📊 Répartition géographique alternative")
    transactions_par_commune = df_filtered['nom_commune'].value_counts().head(15)
    fig = px.bar(x=transactions_par_commune.values, 
                 y=transactions_par_commune.index,
                 orientation='h',
                 title="Nombre de transactions par commune",
                 labels={'x': 'Nombre de transactions', 'y': 'Commune'})
    st.plotly_chart(fig, use_container_width=True)

# Sélection commune
st.sidebar.header("📍 Commune")
communes_disponibles = sorted(df_filtered['nom_commune'].unique())
selected_commune = st.sidebar.selectbox("Choisissez une commune", communes_disponibles)

df_commune = df_filtered[df_filtered['nom_commune'] == selected_commune]

if not df_commune.empty:
    st.header(f"📊 {selected_commune}")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Transactions", f"{len(df_commune):,}")
    with k2:
        st.metric("Prix médian", f"{df_commune['valeur_fonciere'].median():,.0f} €")
    with k3:
        prix_m2 = df_commune['prix_m2'].mean()
        if pd.notna(prix_m2):
            st.metric("Prix moyen / m²", f"{prix_m2:,.0f} €")
        else:
            st.metric("Prix moyen / m²", "N/A")
    with k4:
        surface_non_zero = df_commune[df_commune['surface_reelle_bati'] > 0]
        if not surface_non_zero.empty:
            st.metric("Surface moyenne", f"{surface_non_zero['surface_reelle_bati'].mean():.0f} m²")
    
    # Distribution des prix
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(df_commune, x='valeur_fonciere', nbins=30,
                           title=f"Distribution des prix - {selected_commune}",
                           log_x=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        types_commune = df_commune['type_local'].value_counts().head(8)
        fig = px.pie(values=types_commune.values, names=types_commune.index,
                     title=f"Types de biens - {selected_commune}")
        st.plotly_chart(fig, use_container_width=True)
    
    # Évolution temporelle
    df_commune_annuel = df_commune.groupby('annee').agg({
        'valeur_fonciere': ['count', 'median']
    }).round(0)
    df_commune_annuel.columns = ['nb_transactions', 'prix_median']
    df_commune_annuel = df_commune_annuel.reset_index()
    df_commune_annuel = df_commune_annuel.dropna()
    
    if len(df_commune_annuel) > 1:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(df_commune_annuel, x='annee', y='nb_transactions',
                          title=f"Nombre de transactions - {selected_commune}",
                          markers=True)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(df_commune_annuel, x='annee', y='prix_median',
                          title=f"Prix médian - {selected_commune}",
                          markers=True)
            st.plotly_chart(fig, use_container_width=True)
    
    # Carte pour la commune
    df_commune_carte = df_commune.dropna(subset=['latitude', 'longitude'])
    if not df_commune_carte.empty:
        st.subheader(f"🗺️ Carte - {selected_commune}")
        
        fig = px.scatter_mapbox(
            df_commune_carte,
            lat="latitude",
            lon="longitude",
            color="valeur_fonciere",
            size="valeur_fonciere",
            hover_data={"type_local": True, "valeur_fonciere": ":.0f"},
            color_continuous_scale="Viridis",
            zoom=12,
            mapbox_style="open-street-map"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

# Pied de page
st.markdown("---")
st.markdown(f"*📊 {len(df_filtered):,} transactions - Données DVF Plus - {datetime.now().strftime('%d/%m/%Y')}*")
