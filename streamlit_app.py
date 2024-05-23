# interactive map on a website
import streamlit as st
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu # pip install streamlit-option-menu
import streamlit.components.v1 as components # new

# Sidebar menu:
with st.sidebar:
    selected = option_menu(
        menu_title="Menu", 
        options=["Mapa statyczna - gminy", 'Mapa interaktywna - gminy', "Statystyki - gminy", 
                "Mapa statyczna - powiaty", 'Mapa interaktywna - powiaty', "Statystyki - powiaty"], 
        icons=['house', 'gear', 'bi-bar-chart']*2, 
        menu_icon="bi-menu-button", 
        default_index=0
    )
interactive_mun = open('plots/interactive_mun.html')
interactive_cnt = open('plots/interactive_cnt.html')

# st.image() instead of st.pyplot() now!
if selected == "Mapa statyczna - gminy":
    st.header("Najbliższe szpitale od centrum danej gminy", divider='rainbow')
    st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.image("plots/static_mun.png")
elif selected == "Mapa interaktywna - gminy":
    st.header("Interaktywna mapa najbliższych szpitali od centrum danej gminy", divider='rainbow')
    st.subheader("Najedź kursorem na wybraną gminę, żeby zobaczyć dokładne statystyki. Możesz również przybliżać mapę.")
    # st_folium('plots/interactive_mun.html', width=800, height=600)
    components.html(interactive_mun.read(), width=800, height=600)
elif selected == "Statystyki - gminy":
    st.header("Wybrane statystyki", divider='rainbow')
    # st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.image("plots/statistics_mun.png")

elif selected == "Mapa statyczna - powiaty":
    st.header("Najbliższe szpitale od centrum danego powiatu", divider='rainbow')
    st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.image("plots/static_cnt.png")
elif selected == "Mapa interaktywna - powiaty":
    st.header("Interaktywna mapa najbliższych szpitali od centrum danego powiatu", divider='rainbow')
    st.subheader("Najedź kursorem na wybrany powiat, żeby zobaczyć dokładne statystyki. Możesz również przybliżać mapę.")
    # st_folium('plots/interactive_mun.html', width=800, height=600)
    components.html(interactive_cnt.read(), width=800, height=600)
elif selected == "Statystyki - powiaty":
    st.header("Wybrane statystyki", divider='rainbow')
    st.subheader("Mniej ciekawe, niż w przypadku gmin.")
    st.image("plots/statistics_cnt.png")