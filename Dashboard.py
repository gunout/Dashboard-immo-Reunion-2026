# dashboard_reunion_2026.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Immobilier La Réunion 2026 - Toutes communes",
    page_icon="🌴",
    layout="wide"
)

# --- Dictionnaire COMPLET de toutes les communes de La Réunion ---
COMMUNES_REUNION = {
    "97401": "Les Avirons",
    "97402": "Bras-Panon",
    "97403": "Cilaos",
    "97404": "Entre-Deux",
    "97405": "L'Étang-Salé",
    "97406": "Petite-Île",
    "97407": "La Plaine-des-Palmistes",
    "97408": "Le Port",
    "97409": "La Possession",
    "97410": "Saint-André",
    "97411": "Saint-Benoît",
    "97412": "Saint-Denis",
    "97413": "Saint-Joseph",
    "97414": "Saint-Leu",
    "97415": "Saint-Louis",
    "97416": "Saint-Paul",
    "97417": "Saint-Pierre",
    "97418": "Saint-Philippe",
    "97419": "Sainte-Marie",
    "97420": "Sainte-Rose",
    "97421": "Sainte-Suzanne",
    "97422": "Salazie",
    "97423": "Le Tampon",
    "97424": "Les Trois-Bassins"
}

# --- Fonction de chargement des données 2026 depuis GitHub Releases ---
@st.cache_data(ttl=3600)
def load_reunion_2026_data():
    """
    Charge les données DVF 2026 pour toutes les communes de La Réunion
    depuis GitHub Releases
    """
    url = "https://github.com/gunout/Dashboard-immo-Reunion-2026/releases/download/Dvf_plus_2026/dvf_plus_d974.csv"
    
    try:
        with st.spinner("📥 Téléchargement des données DVF 2026 pour La Réunion..."):
            df = pd.read_csv(url, sep='|', encoding='utf-8', low_memory=False)
        
        if df.empty:
            st.warning("Aucune donnée trouvée pour La Réunion en 2026")
            return pd.DataFrame()
        
        st.sidebar.success(f"✅ {len(df):,} transactions brutes chargées")
        return df
        
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        st.info("📅 Vérifiez que le fichier est bien accessible sur GitHub Releases")
        return pd.DataFrame()

# --- Fonction de nettoyage et préparation ---
def prepare_data(df):
    """
    Nettoie et prépare les données pour l'analyse
    Adapté pour La Réunion avec des seuils de prix appropriés au marché insulaire
    """
    if df.empty:
        return pd.DataFrame()
    
    df_clean = df.copy()
    
    # Conversion des dates
    if 'datemut' in df_clean.columns:
        df_clean["date_mutation"] = pd.to_datetime(df_clean["datemut"], 
                                                   format='%Y-%m-%d', 
                                                   errors='coerce')
    elif 'date_mutation' in df_clean.columns:
        df_clean["date_mutation"] = pd.to_datetime(df_clean["date_mutation"], 
                                                   format='%Y-%m-%d', 
                                                   errors='coerce')
    
    # Conversion des valeurs numériques
    if 'valeurfonc' in df_clean.columns:
        df_clean["valeur_fonciere"] = pd.to_numeric(df_clean["valeurfonc"], 
                                                    errors='coerce')
    elif 'valeur_fonciere' in df_clean.columns:
        df_clean["valeur_fonciere"] = pd.to_numeric(df_clean["valeur_fonciere"], 
                                                    errors='coerce')
    
    if 'sbati' in df_clean.columns:
        df_clean["surface_reelle_bati"] = pd.to_numeric(df_clean["sbati"], 
                                                       errors='coerce')
    elif 'surface_reelle_bati' in df_clean.columns:
        df_clean["surface_reelle_bati"] = pd.to_numeric(df_clean["surface_reelle_bati"], 
                                                       errors='coerce')
    
    # Filtrage sur les types de biens principaux
    if 'libtypbien' in df_clean.columns:
        df_clean = df_clean[df_clean["libtypbien"].isin(['Maison', 'Appartement'])]
    elif 'type_local' in df_clean.columns:
        df_clean = df_clean[df_clean["type_local"].isin(['Maison', 'Appartement'])]
    
    # Suppression des valeurs manquantes critiques
    critical_cols = [col for col in ['valeur_fonciere', 'surface_reelle_bati'] 
                    if col in df_clean.columns]
    if critical_cols:
        df_clean = df_clean.dropna(subset=critical_cols)
    
    # Filtrage des valeurs aberrantes pour La Réunion
    if 'valeur_fonciere' in df_clean.columns:
        df_clean = df_clean[df_clean['valeur_fonciere'] > 15000]    # Min 15k€
        df_clean = df_clean[df_clean['valeur_fonciere'] < 3500000]  # Max 3.5M€
    
    if 'surface_reelle_bati' in df_clean.columns:
        df_clean = df_clean[df_clean['surface_reelle_bati'] > 9]     # Min 9m²
        df_clean = df_clean[df_clean['surface_reelle_bati'] < 500]   # Max 500m²
    
    # Calcul du prix au m²
    if 'valeur_fonciere' in df_clean.columns and 'surface_reelle_bati' in df_clean.columns:
        df_clean['prix_m2'] = df_clean['valeur_fonciere'] / df_clean['surface_reelle_bati']
        # Seuils adaptés au marché réunionnais
        df_clean = df_clean[(df_clean['prix_m2'] > 300) & (df_clean['prix_m2'] < 11000)]
    
    # Ajout du nom de commune
    if 'l_codinsee' in df_clean.columns:
        df_clean['code_commune'] = df_clean['l_codinsee'].astype(str).str.zfill(5)
        df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_REUNION)
        df_clean = df_clean.dropna(subset=['nom_commune'])
    elif 'code_commune' in df_clean.columns:
        df_clean['code_commune'] = df_clean['code_commune'].astype(str).str.zfill(5)
        df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_REUNION)
        df_clean = df_clean.dropna(subset=['nom_commune'])
    
    # Ajout des coordonnées géographiques si disponibles
    if 'geompar_x' in df_clean.columns and 'geompar_y' in df_clean.columns:
        df_clean['longitude'] = pd.to_numeric(df_clean['geompar_x'], errors='coerce')
        df_clean['latitude'] = pd.to_numeric(df_clean['geompar_y'], errors='coerce')
    
    # Code postal
    if 'codservch' in df_clean.columns:
        df_clean['code_postal'] = df_clean['codservch'].astype(str).str[:5]
    
    return df_clean

# --- Interface Utilisateur ---
st.title("🌴 Dashboard Immobilier La Réunion - Toutes Communes (974)")
st.markdown("*Source : data.gouv.fr / DVF Plus - Données 2026*")
st.markdown("Île de La Réunion - Les 24 communes")

# Chargement des données
df_brut = load_reunion_2026_data()

if df_brut.empty:
    st.info("💡 Les données 2026 sont en cours de chargement...")
    st.stop()

# Préparation des données
with st.spinner("🧹 Nettoyage et préparation des données..."):
    df = prepare_data(df_brut)

if df.empty:
    st.warning("⚠️ Aucune transaction valide après nettoyage des données")
    
    with st.expander("🔍 Voir les colonnes disponibles dans votre fichier"):
        st.write("Colonnes dans le fichier source :")
        st.write(df_brut.columns.tolist())
        
        if 'l_codinsee' in df_brut.columns or 'code_commune' in df_brut.columns:
            st.write("Communes présentes dans les données brutes :")
            code_col = 'l_codinsee' if 'l_codinsee' in df_brut.columns else 'code_commune'
            communes_presentes = df_brut[code_col].astype(str).str[:5].unique()
            st.write(sorted(communes_presentes)[:30])
    st.stop()

# --- Statistiques globales ---
st.header("📊 Vue d'ensemble de La Réunion - 2026")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    nb_communes_avec_transactions = df['nom_commune'].nunique()
    st.metric("Communes avec transactions", f"{nb_communes_avec_transactions}")
    st.caption(f"sur {len(COMMUNES_REUNION)} communes")

with col2:
    total_transactions = len(df)
    st.metric("Total transactions", f"{total_transactions:,}")

with col3:
    prix_m2_moyen_dep = df['prix_m2'].mean()
    st.metric("Prix moyen / m²", f"{prix_m2_moyen_dep:,.0f} €")

with col4:
    prix_median_dep = df['valeur_fonciere'].median()
    st.metric("Prix médian", f"{prix_median_dep:,.0f} €")

with col5:
    surface_moy_dep = df['surface_reelle_bati'].mean()
    st.metric("Surface moyenne", f"{surface_moy_dep:.0f} m²")

# --- Classement des communes ---
st.subheader("🏆 Classement des communes par dynamisme immobilier - 2026")

# Calcul des statistiques par commune
stats_communes = df.groupby('nom_commune').agg({
    'valeur_fonciere': ['count', 'mean', 'median', 'std'],
    'prix_m2': ['mean', 'median'],
    'surface_reelle_bati': 'mean'
}).round(0)

stats_communes.columns = ['Nb transactions', 'Prix moyen', 'Prix médian', 'Écart-type', 
                         'Prix m² moyen', 'Prix m² médian', 'Surface moyenne']
stats_communes = stats_communes.sort_values('Nb transactions', ascending=False).reset_index()

# Formatage
stats_communes['Prix moyen'] = stats_communes['Prix moyen'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix médian'] = stats_communes['Prix médian'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix m² moyen'] = stats_communes['Prix m² moyen'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Prix m² médian'] = stats_communes['Prix m² médian'].apply(lambda x: f"{x:,.0f} €")
stats_communes['Surface moyenne'] = stats_communes['Surface moyenne'].apply(lambda x: f"{x:.0f} m²")

st.dataframe(stats_communes, use_container_width=True, hide_index=True)

# Graphiques comparatifs
col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        stats_communes.head(10),
        x='nom_commune',
        y='Nb transactions',
        title="Top 10 des communes les plus actives - 2026",
        color='Prix m² moyen',
        color_continuous_scale='Viridis',
        labels={'Nb transactions': 'Nombre de transactions', 'nom_commune': 'Commune'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        stats_communes.sort_values('Prix m² moyen', ascending=False).head(10),
        x='nom_commune',
        y='Prix m² moyen',
        title="Top 10 des communes les plus chères au m² - 2026",
        color='Prix m² moyen',
        color_continuous_scale='RdYlGn_r',
        labels={'Prix m² moyen': 'Prix au m² (€)', 'nom_commune': 'Commune'}
    )
    st.plotly_chart(fig, use_container_width=True)

# Carte de l'île avec toutes les communes
st.subheader("🗺️ Carte interactive de La Réunion - 2026")

if 'latitude' in df.columns and 'longitude' in df.columns:
    df_carte = df.dropna(subset=['latitude', 'longitude'])
    
    if not df_carte.empty:
        # Échantillonnage pour performance
        if len(df_carte) > 1000:
            df_carte_sample = df_carte.sample(1000, random_state=42)
            st.caption(f"Affichage de 1000 transactions sur {len(df_carte)} (échantillon aléatoire)")
        else:
            df_carte_sample = df_carte
        
        fig = px.scatter_mapbox(
            df_carte_sample,
            lat="latitude",
            lon="longitude",
            color="prix_m2",
            size="surface_reelle_bati",
            hover_name="nom_commune",
            hover_data={
                "valeur_fonciere": ":.0f",
                "surface_reelle_bati": ":.0f",
                "prix_m2": ":.0f",
            },
            color_continuous_scale="RdYlGn_r",
            size_max=12,
            zoom=8,
            mapbox_style="open-street-map",
            title="Transactions immobilières à La Réunion - 2026"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📍 Données de géolocalisation non disponibles pour certaines transactions")
else:
    st.info("📍 Colonnes de géolocalisation non disponibles dans ce fichier")

# --- Sélection de la commune ---
st.sidebar.header("📍 Sélection de la commune")
communes_disponibles = sorted(df['nom_commune'].unique())

# Option recherche
recherche_commune = st.sidebar.text_input("🔍 Rechercher une commune", "")

if recherche_commune:
    communes_filtrees = [c for c in communes_disponibles if recherche_commune.lower() in c.lower()]
    if communes_filtrees:
        selected_commune_name = st.sidebar.selectbox(
            "Résultats de recherche :",
            options=communes_filtrees
        )
    else:
        st.sidebar.warning("Aucune commune trouvée")
        selected_commune_name = st.sidebar.selectbox(
            "Choisissez une commune :",
            options=communes_disponibles,
            index=communes_disponibles.index("Saint-Denis") if "Saint-Denis" in communes_disponibles else 0
        )
else:
    selected_commune_name = st.sidebar.selectbox(
        "Choisissez une commune :",
        options=communes_disponibles,
        index=communes_disponibles.index("Saint-Denis") if "Saint-Denis" in communes_disponibles else 0
    )

# Filtrage par commune
df_commune = df[df['nom_commune'] == selected_commune_name].copy()

if df_commune.empty:
    st.warning(f"Aucune donnée pour {selected_commune_name} en 2026")
    st.stop()

# --- Filtres avancés ---
st.sidebar.header("🔧 Filtres")

# Filtre code postal
if 'code_postal' in df_commune.columns:
    codes_postaux = sorted(df_commune['code_postal'].astype(str).unique())
    code_postal_selection = st.sidebar.multiselect(
        "Code postal", 
        codes_postaux, 
        default=codes_postaux
    )
else:
    code_postal_selection = []

# Filtre type de bien
type_local_options = ['Tous', 'Maison', 'Appartement']
type_local = st.sidebar.selectbox("Type de bien", type_local_options)

# Filtre prix avec valeurs dynamiques
prix_min = st.sidebar.number_input(
    "Prix minimum (€)", 
    value=0, 
    step=10000,
    min_value=0
)
prix_max = st.sidebar.number_input(
    "Prix maximum (€)", 
    value=int(df_commune['valeur_fonciere'].max()), 
    step=20000,
    min_value=0
)

# Filtre surface
surface_min = st.sidebar.slider(
    "Surface minimum (m²)",
    min_value=0,
    max_value=int(df_commune['surface_reelle_bati'].max()),
    value=0
)

# Application des filtres
df_filtre = df_commune.copy()

if code_postal_selection and 'code_postal' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['code_postal'].astype(str).isin(code_postal_selection)]

df_filtre = df_filtre[
    (df_filtre['valeur_fonciere'] >= prix_min) & 
    (df_filtre['valeur_fonciere'] <= prix_max) &
    (df_filtre['surface_reelle_bati'] >= surface_min)
]

if type_local != 'Tous':
    if 'libtypbien' in df_filtre.columns:
        df_filtre = df_filtre[df_filtre['libtypbien'] == type_local]
    elif 'type_local' in df_filtre.columns:
        df_filtre = df_filtre[df_filtre['type_local'] == type_local]

if df_filtre.empty:
    st.warning("Aucune transaction ne correspond à vos filtres.")
    st.stop()

# --- KPIs pour la commune sélectionnée ---
st.header(f"📊 Indicateurs Clés - {selected_commune_name} (2026)")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    prix_m2_moyen = df_filtre['prix_m2'].mean()
    st.metric(
        "Prix moyen / m²", 
        f"{prix_m2_moyen:,.0f} €",
        delta=f"{prix_m2_moyen - df['prix_m2'].mean():,.0f} € vs île" if not df.empty else None
    )

with col2:
    prix_median = df_filtre['valeur_fonciere'].median()
    st.metric("Prix médian", f"{prix_median:,.0f} €")

with col3:
    nb_transactions = len(df_filtre)
    st.metric("Transactions", f"{nb_transactions:,}")

with col4:
    surface_moyenne = df_filtre['surface_reelle_bati'].mean()
    st.metric("Surface moyenne", f"{surface_moyenne:.0f} m²")

with col5:
    if 'nb_pieces' in df_filtre.columns:
        pieces_moyennes = df_filtre['nb_pieces'].mean()
        st.metric("Pièces principales", f"{pieces_moyennes:.1f}")
    elif 'nombre_pieces_principales' in df_filtre.columns:
        pieces_moyennes = df_filtre['nombre_pieces_principales'].mean()
        st.metric("Pièces principales", f"{pieces_moyennes:.1f}")

# --- Visualisations ---
st.header(f"📈 Analyses - {selected_commune_name} (2026)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribution des prix au m²")
    fig = px.histogram(
        df_filtre, 
        x='prix_m2', 
        nbins=30,
        color='libtypbien' if 'libtypbien' in df_filtre.columns else ('type_local' if 'type_local' in df_filtre.columns else None),
        marginal="box",
        title=f"Prix au m² - {selected_commune_name} (2026)",
        labels={'prix_m2': 'Prix au m² (€)', 'count': 'Nombre de transactions'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Prix selon la surface")
    fig = px.scatter(
        df_filtre,
        x='surface_reelle_bati',
        y='valeur_fonciere',
        color='libtypbien' if 'libtypbien' in df_filtre.columns else ('type_local' if 'type_local' in df_filtre.columns else None),
        hover_data=['code_postal'] if 'code_postal' in df_filtre.columns else None,
        title="Corrélation surface / prix - 2026",
        labels={
            'surface_reelle_bati': 'Surface (m²)',
            'valeur_fonciere': 'Prix (€)'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Carte communale ---
st.subheader(f"🗺️ Carte des transactions - {selected_commune_name} (2026)")

if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    df_carte = df_filtre.dropna(subset=['latitude', 'longitude'])
    
    if not df_carte.empty:
        # Limiter à 300 points pour la performance
        if len(df_carte) > 300:
            df_carte = df_carte.sample(300, random_state=42)
            st.caption(f"Affichage de 300 transactions sur {len(df_filtre)} (échantillon aléatoire)")
        
        # Ajuster le zoom selon la commune
        if selected_commune_name in ["Saint-Denis", "Saint-Pierre", "Saint-Paul"]:
            zoom_level = 13
        else:
            zoom_level = 12
        
        fig = px.scatter_mapbox(
            df_carte,
            lat="latitude",
            lon="longitude",
            color="prix_m2",
            size="surface_reelle_bati",
            hover_data={
                "valeur_fonciere": ":.0f",
                "surface_reelle_bati": ":.0f",
                "prix_m2": ":.0f"
            },
            color_continuous_scale="RdYlGn_r",
            size_max=15,
            zoom=zoom_level,
            mapbox_style="open-street-map",
            title=f"Transactions à {selected_commune_name} - 2026"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📍 Données de géolocalisation non disponibles pour cette commune")
else:
    st.info("📍 Colonnes de géolocalisation non disponibles dans ce fichier")

# --- Évolution temporelle ---
st.subheader(f"📅 Évolution des transactions - {selected_commune_name} (2026)")

if 'date_mutation' in df_filtre.columns and not df_filtre.empty:
    df_filtre['mois'] = df_filtre['date_mutation'].dt.to_period('M')
    df_mensuel = df_filtre.groupby('mois').agg({
        'prix_m2': 'mean',
        'valeur_fonciere': ['count', 'mean']
    }).round(0)
    
    df_mensuel.columns = ['prix_m2_moyen', 'nb_transactions', 'prix_moyen']
    df_mensuel = df_mensuel.reset_index()
    df_mensuel['mois'] = df_mensuel['mois'].astype(str)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.line(
            df_mensuel,
            x='mois',
            y='prix_m2_moyen',
            title="Évolution du prix au m² - 2026",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            df_mensuel,
            x='mois',
            y='nb_transactions',
            title="Nombre de transactions par mois - 2026"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📅 Données temporelles non disponibles")

# --- Analyse par secteur (via code postal) ---
if 'code_postal' in df_filtre.columns and df_filtre['code_postal'].nunique() > 1:
    st.subheader("🏘️ Analyse par secteur - 2026")
    
    stats_secteur = df_filtre.groupby('code_postal').agg({
        'valeur_fonciere': ['count', 'mean'],
        'prix_m2': 'mean',
        'surface_reelle_bati': 'mean'
    }).round(0)
    
    stats_secteur.columns = ['Nb transactions', 'Prix moyen', 'Prix m² moyen', 'Surface moyenne']
    stats_secteur = stats_secteur.sort_values('Prix m² moyen', ascending=False).reset_index()
    
    stats_secteur['Prix moyen'] = stats_secteur['Prix moyen'].apply(lambda x: f"{x:,.0f} €")
    stats_secteur['Prix m² moyen'] = stats_secteur['Prix m² moyen'].apply(lambda x: f"{x:,.0f} €")
    stats_secteur['Surface moyenne'] = stats_secteur['Surface moyenne'].apply(lambda x: f"{x:.0f} m²")
    
    st.dataframe(stats_secteur, use_container_width=True, hide_index=True)

# --- Top des ventes ---
st.subheader("💰 Top 5 des ventes les plus élevées - 2026")
top_ventes = df_filtre.nlargest(5, 'valeur_fonciere')[
    ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2']
]
colonnes_dispo = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2']
if 'libtypbien' in df_filtre.columns:
    top_ventes = df_filtre.nlargest(5, 'valeur_fonciere')[['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'libtypbien']]
    colonnes_dispo.append('libtypbien')
elif 'type_local' in df_filtre.columns:
    top_ventes = df_filtre.nlargest(5, 'valeur_fonciere')[['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local']]
    colonnes_dispo.append('type_local')

if not top_ventes.empty:
    top_ventes['valeur_fonciere'] = top_ventes['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
    top_ventes['prix_m2'] = top_ventes['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(top_ventes, use_container_width=True, hide_index=True)

# --- Dernières transactions ---
st.subheader("📋 Dernières transactions - 2026")
if 'date_mutation' in df_filtre.columns:
    df_display = df_filtre.sort_values('date_mutation', ascending=False).head(50)
    
    display_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2']
    if 'libtypbien' in df_display.columns:
        display_cols.append('libtypbien')
    elif 'type_local' in df_display.columns:
        display_cols.append('type_local')
    if 'code_postal' in df_display.columns:
        display_cols.append('code_postal')
    
    available_cols = [col for col in display_cols if col in df_display.columns]
    
    for col in ['valeur_fonciere', 'prix_m2']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:,.0f} €" + ("/m²" if col == 'prix_m2' else "")
            )
    
    st.dataframe(df_display[available_cols], use_container_width=True, hide_index=True)

# --- Informations sur le marché local ---
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Marché réunionnais 2026")
st.sidebar.info(
    """
    **Spécificités locales :**
    - Forte demande dans les zones littorales
    - Prix plus élevés à l'Ouest et Nord
    - Marché dynamique à Saint-Denis, Saint-Pierre, Saint-Paul
    - Spécificités des micro-régions
    - 📊 Données DVF Plus 2026
    """
)

# --- Pied de page ---
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>Source :</b> DVF Plus - Cerema / data.gouv.fr - La Réunion (974)<br>
        <b>Données :</b> {len(df_filtre):,} transactions affichées pour {selected_commune_name}<br>
        <b>Total île :</b> {len(df):,} transactions dans {nb_communes_avec_transactions} communes<br>
        <b>Année :</b> 2026<br>
        <b>Mise à jour :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
    """,
    unsafe_allow_html=True
)
