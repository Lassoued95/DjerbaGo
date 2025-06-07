import streamlit as st
# --- Page Config ---
st.set_page_config(
    page_title="Djerba Travel Recommender 🌴", 
    layout="wide",
    page_icon="🌴"
)
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from PIL import Image
from io import BytesIO
import requests
import os
from geopy.distance import geodesic
from datetime import datetime

# --- Show Streamlit version for debugging ---
st.sidebar.markdown(f"**Streamlit version:** {st.__version__}")



# --- Load and apply external CSS ---
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css("custom.css")

# --- Load Data ---
@st.cache_data
def load_data():
    return pd.read_csv("spots.csv")

df = load_data()

# --- Initialize Session State ---
for key in ['favorites', 'ratings', 'visited', 'itinerary']:
    if key not in st.session_state:
        st.session_state[key] = {} if key in ['ratings', 'visited'] else set() if key == 'favorites' else []

# --- Default Center Location ---
center_location = (33.813, 10.900)

# --- Sidebar Filters ---
with st.sidebar:
    st.image("assets/images/bg.jpg", use_container_width=True)
    st.header("🎯 Vos préférences de voyage")
    
    name = st.text_input("👋 Votre nom")
    if name:
        st.success(f"Bienvenue à Djerba, {name} !")
    
    with st.expander("🔍 Filtres de recherche", expanded=True):
        preferences = st.multiselect("Catégories à explorer", df['category'].unique(), default=df['category'].unique())
        age_groups = st.multiselect("Tranche d'âge", df['age_group'].unique(), default=df['age_group'].unique())
        moods = st.multiselect("Humeur / Ambiance", df['mood'].unique(), default=df['mood'].unique())
        prices = st.multiselect("Niveau de prix", df['price_level'].unique(), default=df['price_level'].unique())
        access = st.multiselect("Accessibilité", df['accessibility'].unique(), default=df['accessibility'].unique())

    with st.expander("🗺️ Paramètres carte"):
        map_style = st.selectbox("Style de la carte", ["Clair", "Sombre", "Satellite"])
        tiles = {
            "Clair": "cartodbpositron",
            "Sombre": "cartodbdark_matter",
            "Satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        }[map_style]

        max_distance_km = st.slider("📍 Distance max. du centre (km)", 1, 30, 20)

# --- Filter Data ---
filtered_df = df[
    df['category'].isin(preferences) &
    df['age_group'].isin(age_groups) &
    df['mood'].isin(moods) &
    df['price_level'].isin(prices) &
    df['accessibility'].isin(access)
]

filtered_df = filtered_df[
    filtered_df.apply(lambda row: geodesic(center_location, (row['latitude'], row['longitude'])).km <= max_distance_km, axis=1)
]

# --- Discovery Button ---
with st.sidebar.expander("✨ Recommandations perso"):
    st.info("Basé sur vos préférences")
    if not filtered_df.empty:
        if st.button("🎲 Découverte aléatoire"):
            random_place = filtered_df.sample(1).iloc[0]
            st.session_state.random_pick = random_place
        if 'random_pick' in st.session_state:
            st.success(f"Essayez: {st.session_state.random_pick['name']}")
    else:
        st.warning("Aucun lieu trouvé avec les filtres actuels.")

# --- Hero Section ---
st.image("assets/images/bg2.jpg", use_container_width=True)
st.title(":palm_tree: Bienvenue à Djerba - Votre Guide Intelligent de Voyage -DjerbaGo- ")
st.subheader("Filtrez selon vos envies pour explorer les merveilles de l'île")

# --- Stats ---
col1, col2, col3 = st.columns(3)
col1.metric("Lieux disponibles", len(filtered_df), f"{len(filtered_df)/len(df):.0%} des options")
col2.metric("Vos favoris", len(st.session_state.favorites))
col3.metric("Vos visites", len(st.session_state.visited))

# --- Tabs Section ---
st.markdown("## 📍 Lieux recommandés")
if filtered_df.empty:
    st.info("Aucun lieu trouvé selon les filtres actuels. Élargissez vos critères de recherche.")
else:
    tab1, tab2, tab3 = st.tabs(["Liste complète", "Vos favoris ❤️", "Itinéraire 🗓️"])

    with tab1:
        for _, row in filtered_df.iterrows():
            with st.container():
                distance = geodesic(center_location, (row['latitude'], row['longitude'])).km
                st.markdown(f"### 🌴 {row['name']} ({row['category']})")
                st.caption(f"📍 {distance:.1f} km | 👥 {row['age_group']} | 💰 {row['price_level']} | 🌟 {st.session_state.ratings.get(row['name'], 'Non noté')}")

                col1, col2 = st.columns([2, 3])
                with col1:
                    img_path = str(row['image']).strip()
                    try:
                        if img_path.startswith("http"):
                            response = requests.get(img_path, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                            response.raise_for_status()
                            image = Image.open(BytesIO(response.content))
                            st.image(image, use_container_width=True, caption=row['name'])
                        elif os.path.exists(img_path):
                            image = Image.open(img_path)
                            st.image(image, use_container_width=True, caption=row['name'])
                        else:
                            st.warning("🖼️ Image non trouvée")
                    except Exception as e:
                        st.warning(f"⚠️ Erreur image : {e}")

                with col2:
                    with st.expander("📖 Description complète"):
                        st.write(row['description'])
                        st.markdown(f"**Ambiance :** {row['mood']} | **Accès :** {row['accessibility']}")

                    rating_col, fav_col, visit_col, itin_col = st.columns([2,1,1,1])
                    with rating_col:
                        new_rating = st.slider(f"Noter {row['name']}", 1, 5, 
                                               value=st.session_state.ratings.get(row['name'], 3),
                                               key=f"rate_{row['name']}")
                        if new_rating != st.session_state.ratings.get(row['name']):
                            st.session_state.ratings[row['name']] = new_rating
                            st.success(f"Note enregistrée: {new_rating} ⭐")
                    
                    with fav_col:
                        if st.button("❤️", key=f"fav_{row['name']}"):
                            if row['name'] in st.session_state.favorites:
                                st.session_state.favorites.remove(row['name'])
                                st.warning("Retiré des favoris")
                            else:
                                st.session_state.favorites.add(row['name'])
                                st.success("Ajouté aux favoris!")
                    
                    with visit_col:
                        if st.button("✔️", key=f"visit_{row['name']}"):
                            st.session_state.visited[row['name']] = datetime.now().strftime("%Y-%m-%d")
                            st.success("Marqué comme visité!")
                    
                    with itin_col:
                        if st.button("➕", key=f"itin_{row['name']}"):
                            st.session_state.itinerary.append({
                                "name": row['name'],
                                "date": datetime.now().strftime("%Y-%m-%d")
                            })
                            st.success("Ajouté à l'itinéraire!")
                st.divider()

    with tab2:
        if not st.session_state.favorites:
            st.info("Vous n'avez encore aucun favori.")
        else:
            for fav in st.session_state.favorites:
                place = df[df['name'] == fav].iloc[0]
                st.markdown(f"### ❤️ {place['name']}")
                st.write(place['description'])
                st.caption(f"Catégorie: {place['category']} | Prix: {place['price_level']}")
                st.divider()

    with tab3:
        if not st.session_state.itinerary:
            st.info("Votre itinéraire est vide.")
        else:
            st.write("### 🗓️ Votre plan de voyage")
            for i, item in enumerate(st.session_state.itinerary):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"#### {i+1}. {item['name']}")
                with col2:
                    if st.button(f"❌ Retirer", key=f"remove_{i}"):
                        st.session_state.itinerary.pop(i)
                        st.rerun()
  # Make sure your Streamlit version supports this

# --- Statistics ---
st.markdown("## 📊 Statistiques & Insights")
col1, col2 = st.columns(2)

with col1:
    st.metric("Nombre total de lieux", len(df))
    st.metric("Nombre de catégories", len(df['category'].unique()))
    st.metric("Nombre de favoris sélectionnés", len(st.session_state.favorites))

with col2:
    most_rated = sorted(st.session_state.ratings.items(), key=lambda x: x[1], reverse=True)
    if most_rated:
        st.write(f"⭐ Lieu le mieux noté: **{most_rated[0][0]}** avec {most_rated[0][1]} étoiles")
    else:
        st.write("⭐ Aucun lieu noté pour le moment.")

# --- Interactive Map ---
st.markdown("## 🗺️ Carte interactive")
m = folium.Map(location=center_location, zoom_start=12, tiles=tiles)

marker_cluster = MarkerCluster().add_to(m)
for _, row in filtered_df.iterrows():
    popup_html = f"""
    <b>{row['name']}</b><br>
    {row['description'][:100]}...<br>
    Catégorie: {row['category']}<br>
    Ambiance: {row['mood']}<br>
    Prix: {row['price_level']}
    """
    folium.Marker(
        location=(row['latitude'], row['longitude']),
        popup=popup_html,
        tooltip=row['name'],
        icon=folium.Icon(color="green", icon="info-sign"),
    ).add_to(marker_cluster)

st_folium(m, width=1000, height=600)

# --- Footer ---
st.markdown("---")
st.caption("© 2025 DjerbaGo - Guide Intelligent de Voyage. Tous droits réservés.")
