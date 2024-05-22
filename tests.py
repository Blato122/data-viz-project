import geopandas as gpd
import matplotlib.pyplot as plt

# interactive map on a website
import streamlit as st
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu # pip install streamlit-option-menu

voivodeships = gpd.read_file("poland_voivodeships.json")
municipalities = gpd.read_file("poland_municipalities.json")
municipality_polygons = municipalities['geometry']
municipality_centroids = municipality_polygons.to_crs('+proj=cea').centroid.to_crs(municipality_polygons.crs)
municipality_coords = [[coords.x, coords.y] for coords in municipality_centroids]

# duplicate_names = municipalities['name'][municipalities['name'].duplicated(keep=False)]
# print(f"Number of duplicate municipality names: {duplicate_names.nunique()}")
# print(f"Duplicate municipality names:\n{duplicate_names}")

municipality_dict = {tuple(n) : g for n, g in zip(municipality_coords, municipalities['name'])} 
# print(len(municipality_dict.keys()))
# print(municipalities.shape)

# null_data = municipalities[municipalities.isnull().any(axis=1)]
# print(null_data)

# Interactive folium map
import branca.colormap as cm

class StyleFunction:
    def __init__(self, color):
        self.color = color

    def __call__(self, feature):
        return {'fillColor': self.color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}

# https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data
@st.cache_data
def create_interactive_map():
    colormap = cm.LinearColormap(colors=['green', 'yellow', 'red'], vmin=0, vmax=2477)
    m = folium.Map(
        location=[52.0693, 19.4803], # piątek dodać
        zoom_start=6,  # center on Poland
        max_zoom=18,   # Maximum zoom level
        min_zoom=6     # Minimum zoom level to keep the focus on Poland
    )

    for i, mun_geometry in enumerate(municipalities['geometry']): # aah ok
        color = colormap(i)
        style_func = StyleFunction(color)
        folium.GeoJson(
            mun_geometry,
            style_function=style_func,
            tooltip=folium.Tooltip('test')
        ).add_to(m)

    colormap.caption = 'Distance to Nearest Hospital (km)'
    m.add_child(colormap)
    return m

@st.cache_data
def create_static_map():
    color_mapping = {}
    for i, (mun_coords, mun_name) in enumerate(zip(municipality_coords, municipalities['name'])):
        color_mapping[(tuple(mun_coords), mun_name)] = 'red' if i % 3 else 'green'

    fig, ax = plt.subplots(figsize=(10, 10))
    municipalities.plot(ax=ax, edgecolor='grey', facecolor=[color_mapping.get((tuple(n), g), 'white') for n, g in zip(municipality_coords, municipalities['name'])], linewidth=0.25)
    voivodeships.plot(ax=ax, edgecolor='black', facecolor="none", linewidth=0.75)
    st.pyplot(fig)

# sidebar:
with st.sidebar:
    selected = option_menu(menu_title="Menu", options=["Static", 'Interactive'], 
        icons=['house', 'gear'], menu_icon="cast", default_index=0)

if selected == "Static":
    st.title("Poland Municipalities and Nearest Hospitals")
    create_static_map()
elif selected == "Interactive":
    st.title("Najbliższe szpitale od centrum danej gminy")
    m = create_interactive_map()
    st_folium(m, width=800, height=600)
else:
    pass
    #:(((