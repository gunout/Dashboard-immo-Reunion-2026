# dashboard_reunion_2026.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Immobilier La Réunion 2026",
    page_icon="🌴",
    layout="wide"
)

# Dictionnaire des communes
COMMUNES = {
    "97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Cilaos",
    "97404": "Entre-Deux", "97405": "L'Étang-Salé", "97406": "Petite-Île",
    "97407": "La Plaine-des-Palmistes", "97408": "Le Port", "97409": "La Possession",
    "97410": "Saint-André", "97411": "Saint-Benoît", "97412": "Saint-Denis",
    "97413": "Saint-Joseph", "97414": "Saint-Leu", "97415": "Saint-Louis",
    "97416": "Saint-Paul", "97417": "Saint-Pierre", "97418": "Saint-Philippe",
    "97419": "Sainte-Marie", "97420": "Sainte-Rose", "97421": "Sainte-Suzanne",
    "97422": "Salazie", "97423": "Le Tampon", "97424": "Les Trois-Bassins",
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
    """Nettoie et prépare les données"""
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
    df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES)
    
    # Code postal
    if 'codservch' in df_clean.columns:
        df_clean['code_postal'] = df_clean['codservch'].astype(str).str[:5]
    
    # Supprimer les valeurs manquantes critiques
    df_clean = df_clean.dropna(subset=['valeur_fonciere', 'nom_commune'])
    
    # Filtrage des valeurs aberrantes
    df_clean = df_clean[df_clean['valeur_fonciere'] > 5000]    # Min 5k€
    df_clean = df_clean[df_clean['valeur_fonciere'] < 5000000] # Max 5M€
    
    # Prix au m² (uniquement pour les biens avec surface)
    mask_surface = (df_clean['surface_reelle_bati'] > 9) & (df_clean['surface_reelle_bati'] < 10000)
    df_clean['prix_m2'] = np.nan
    df_clean.loc[mask_surface, 'prix_m2'] = (
        df_clean.loc[mask_surface, 'valeur_fonciere'] / 
        df_clean.loc[mask_surface, 'surface_reelle_bati']
    )
    
    return df_clean

# --- Interface principale ---
st.title("🌴 Dashboard Immobilier La Réunion")
st.markdown("*Source : DVF Plus - Données 2014-2026*")

# Chargement des données
with st.spinner("📥 Chargement des données..."):
    df_raw = load_data()

if df_raw.empty:
    st.stop()

with st.spinner("🧹 Nettoyage des données..."):
    df = prepare_data(df_raw)

if df.empty:
    st.error("❌ Aucune transaction valide après nettoyage")
    st.stop()

# --- Sidebar - Filtres ---
st.sidebar.header("🔍 Filtres")

# Filtre année
annees_dispo = sorted([int(a) for a in df['annee'].dropna().unique()])
selected_annee = st.sidebar.selectbox(
    "Année",
    options=['Toutes'] + annees_dispo,
    index=0
)

# Filtre type de bien
types_dispo = df['type_local'].value_counts()
selected_type = st.sidebar.selectbox(
    "Type de bien",
    options=['Tous'] + list(types_dispo.index),
    index=0
)

# Filtre prix
valeur_min = int(df['valeur_fonciere'].min())
valeur_max = int(df['valeur_fonciere'].max())
prix_range = st.sidebar.slider(
    "Prix (€)",
    min_value=valeur_min,
    max_value=valeur_max,
    value=(valeur_min, valeur_max),
    step=10000
)

# Filtre surface (optionnel)
afficher_surface = st.sidebar.checkbox("Filtrer par surface (m²)")
if afficher_surface:
    surface_min = st.sidebar.number_input("Surface minimum (m²)", min_value=0, value=0)
    surface_max = st.sidebar.number_input("Surface maximum (m²)", min_value=0, value=500)
else:
    surface_min = 0
    surface_max = 10000

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

if afficher_surface:
    df_filtered = df_filtered[
        (df_filtered['surface_reelle_bati'] >= surface_min) & 
        (df_filtered['surface_reelle_bati'] <= surface_max)
    ]

if df_filtered.empty:
    st.warning("⚠️ Aucune transaction ne correspond aux filtres sélectionnés.")
    st.stop()

# --- Statistiques globales ---
st.header("📊 Vue d'ensemble")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    nb_transactions = len(df_filtered)
    st.metric("Transactions", f"{nb_transactions:,}")

with col2:
    nb_communes = df_filtered['nom_commune'].nunique()
    st.metric("Communes", f"{nb_communes}")

with col3:
    prix_median = df_filtered['valeur_fonciere'].median()
    st.metric("Prix médian", f"{prix_median:,.0f} €")

with col4:
    prix_moyen = df_filtered['valeur_fonciere'].mean()
    st.metric("Prix moyen", f"{prix_moyen:,.0f} €")

with col5:
    prix_m2_moyen = df_filtered['prix_m2'].mean()
    if pd.notna(prix_m2_moyen):
        st.metric("Prix moyen / m²", f"{prix_m2_moyen:,.0f} €")
    else:
        st.metric("Prix moyen / m²", "N/A")

# --- Évolution temporelle (toutes communes) ---
st.subheader("📈 Évolution temporelle")

col1, col2 = st.columns(2)

with col1:
    df_annuel = df_filtered.groupby('annee').agg({
        'prix_m2': 'mean',
        'valeur_fonciere': 'count'
    }).round(0).reset_index()
    df_annuel.columns = ['année', 'prix_m2_moyen', 'nb_transactions']
    df_annuel = df_annuel.dropna()
    
    if not df_annuel.empty:
        fig = px.line(
            df_annuel, 
            x='année', 
            y='prix_m2_moyen',
            title="Évolution du prix au m² (€)",
            markers=True,
            text='prix_m2_moyen'
        )
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if not df_annuel.empty:
        fig = px.bar(
            df_annuel,
            x='année',
            y='nb_transactions',
            title="Nombre de transactions par année",
            text='nb_transactions',
            color='nb_transactions',
            color_continuous_scale='Blues'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# --- Classement des communes ---
st.subheader("🏆 Classement des communes")

communes_stats = df_filtered.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'median', 'mean'],
    'prix_m2': 'mean',
    'surface_reelle_bati': 'mean'
}).round(0)

communes_stats.columns = ['Transactions', 'Prix médian', 'Prix moyen', 'Prix m² moyen', 'Surface moyenne']
communes_stats = communes_stats.sort_values('Transactions', ascending=False).reset_index()

# Formatage
communes_stats['Prix médian'] = communes_stats['Prix médian'].apply(lambda x: f"{x:,.0f} €")
communes_stats['Prix moyen'] = communes_stats['Prix moyen'].apply(lambda x: f"{x:,.0f} €")
communes_stats['Prix m² moyen'] = communes_stats['Prix m² moyen'].apply(
    lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A"
)
communes_stats['Surface moyenne'] = communes_stats['Surface moyenne'].apply(
    lambda x: f"{x:.0f} m²" if x > 0 else "N/A"
)

st.dataframe(communes_stats, use_container_width=True, hide_index=True)

# --- Graphiques comparatifs ---
col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        communes_stats.head(10),
        x='nom_commune',
        y='Transactions',
        title="Top 10 des communes les plus actives",
        color='Prix m² moyen',
        color_continuous_scale='Viridis',
        labels={'nom_commune': 'Commune', 'Transactions': 'Nombre de transactions'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    top_prix = df_filtered.dropna(subset=['prix_m2']).groupby('nom_commune')['prix_m2'].mean().round(0).sort_values(ascending=False).head(10)
    if not top_prix.empty:
        fig = px.bar(
            x=top_prix.values,
            y=top_prix.index,
            orientation='h',
            title="Top 10 des communes les plus chères au m²",
            color=top_prix.values,
            color_continuous_scale='RdYlGn_r',
            labels={'x': 'Prix au m² (€)', 'y': 'Commune'}
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Distribution des prix ---
st.subheader("📊 Distribution des prix")

col1, col2 = st.columns(2)

with col1:
    fig = px.histogram(
        df_filtered,
        x='valeur_fonciere',
        nbins=50,
        title="Distribution des prix (€)",
        log_x=True,
        log_y=True,
        color='type_local' if len(df_filtered['type_local'].unique()) <= 10 else None,
        labels={'valeur_fonciere': 'Prix (€)', 'count': 'Nombre de transactions'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.box(
        df_filtered,
        x='nom_commune',
        y='valeur_fonciere',
        title="Distribution des prix par commune (€)",
        labels={'nom_commune': 'Commune', 'valeur_fonciere': 'Prix (€)'}
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

# --- Analyse par type de bien ---
st.subheader("🏠 Analyse par type de bien")

types_stats = df_filtered.groupby('type_local').agg({
    'valeur_fonciere': ['count', 'median'],
    'prix_m2': 'mean'
}).round(0)

types_stats.columns = ['Transactions', 'Prix médian', 'Prix m² moyen']
types_stats = types_stats.sort_values('Transactions', ascending=False).reset_index()

types_stats['Prix médian'] = types_stats['Prix médian'].apply(lambda x: f"{x:,.0f} €")
types_stats['Prix m² moyen'] = types_stats['Prix m² moyen'].apply(
    lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A"
)

st.dataframe(types_stats.head(15), use_container_width=True, hide_index=True)

# --- Sélection d'une commune spécifique ---
st.sidebar.header("📍 Commune détaillée")
communes_list = sorted(df_filtered['nom_commune'].unique())
selected_commune = st.sidebar.selectbox("Choisissez une commune", communes_list)

df_commune = df_filtered[df_filtered['nom_commune'] == selected_commune]

if not df_commune.empty:
    st.header(f"📊 Détail - {selected_commune}")
    
    # KPIs commune
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Transactions", f"{len(df_commune):,}")
    
    with col2:
        st.metric("Prix médian", f"{df_commune['valeur_fonciere'].median():,.0f} €")
    
    with col3:
        prix_m2_commune = df_commune['prix_m2'].mean()
        if pd.notna(prix_m2_commune):
            st.metric("Prix moyen / m²", f"{prix_m2_commune:,.0f} €")
        else:
            st.metric("Prix moyen / m²", "N/A")
    
    with col4:
        surface_moy = df_commune[df_commune['surface_reelle_bati'] > 0]['surface_reelle_bati'].mean()
        if pd.notna(surface_moy):
            st.metric("Surface moyenne", f"{surface_moy:.0f} m²")
        else:
            st.metric("Surface moyenne", "N/A")
    
    # Graphiques commune
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(
            df_commune,
            x='valeur_fonciere',
            nbins=30,
            title=f"Distribution des prix - {selected_commune}",
            log_x=True,
            labels={'valeur_fonciere': 'Prix (€)', 'count': 'Nombre de transactions'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        types_commune = df_commune['type_local'].value_counts().head(8)
        fig = px.pie(
            values=types_commune.values,
            names=types_commune.index,
            title=f"Types de biens - {selected_commune}"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Évolution pour la commune
    df_commune_annuel = df_commune.groupby('annee').agg({
        'valeur_fonciere': ['count', 'median'],
        'prix_m2': 'mean'
    }).round(0)
    df_commune_annuel.columns = ['Transactions', 'Prix médian', 'Prix m² moyen']
    df_commune_annuel = df_commune_annuel.reset_index().dropna()
    
    if len(df_commune_annuel) > 1:
        st.subheader(f"📈 Évolution temporelle - {selected_commune}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                df_commune_annuel,
                x='annee',
                y='Transactions',
                title="Nombre de transactions par année",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                df_commune_annuel,
                x='annee',
                y='Prix médian',
                title="Prix médian par année (€)",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Top ventes dans la commune
    st.subheader(f"💰 Top 10 des ventes - {selected_commune}")
    top_ventes = df_commune.nlargest(10, 'valeur_fonciere')[
        ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local']
    ].copy()
    
    if not top_ventes.empty:
        top_ventes['valeur_fonciere'] = top_ventes['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
        top_ventes['prix_m2'] = top_ventes['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²" if pd.notna(x) else "N/A")
        top_ventes['surface_reelle_bati'] = top_ventes['surface_reelle_bati'].apply(lambda x: f"{x:.0f} m²" if x > 0 else "Terrain")
        st.dataframe(top_ventes, use_container_width=True, hide_index=True)

# --- Dernières transactions ---
st.subheader("📋 Dernières transactions")
df_recent = df_filtered.sort_values('date_mutation', ascending=False).head(100)

display_cols = ['date_mutation', 'nom_commune', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local']
available_cols = [col for col in display_cols if col in df_recent.columns]

if available_cols:
    df_display = df_recent[available_cols].copy()
    df_display['valeur_fonciere'] = df_display['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
    if 'prix_m2' in df_display.columns:
        df_display['prix_m2'] = df_display['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²" if pd.notna(x) else "N/A")
    if 'surface_reelle_bati' in df_display.columns:
        df_display['surface_reelle_bati'] = df_display['surface_reelle_bati'].apply(lambda x: f"{x:.0f} m²" if x > 0 else "Terrain")
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# --- Pied de page ---
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>Source :</b> DVF Plus - Cerema / data.gouv.fr - La Réunion (974)<br>
        <b>Données :</b> {len(df_filtered):,} transactions affichées<br>
        <b>Période :</b> {selected_annee if selected_annee != 'Toutes' else '2014-2026'}<br>
        <b>Mise à jour :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
    """,
    unsafe_allow_html=True
)
