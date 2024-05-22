import matplotlib.pyplot as plt
import numpy as np

# interactive map on a website
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu # pip install streamlit-option-menu

import main_plot

class StyleFunction: # wut
    def __init__(self, color):
        self.color = color

    def __call__(self, feature):
        return {'fillColor': self.color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}

# @st.cache_data
def create_interactive_map():
    m = folium.Map( # unhardcodify!!!
        location=[52.0693, 19.4803], # piątek dodać
        zoom_start=6,  # center on Poland
        max_zoom=18,   # Maximum zoom level
        min_zoom=6     # Minimum zoom level to keep the focus on Poland
    )

    for i, (mun_geometry, (c, n)) in enumerate(zip(main_plot.municipality_polygons, main_plot.municipality_dict.items())): # aah ok
        color = main_plot.color_mapping_interactive[(tuple(c), n)]
        style_func = StyleFunction(color)
        folium.GeoJson(
            mun_geometry,
            style_function=style_func,
            tooltip=folium.Tooltip(f"Gmina: {n}<br>Najbliższy szpital: {main_plot.min_times_dict[(tuple(c), n)][0]}<br>Czas dojazdu: {main_plot.min_times_dict[(tuple(c), n)][1]:.2f}")
        ).add_to(m)

    main_plot.colormap.caption = 'Czas jazdy samochodem od centrum gminy do najbliższego szpitala (w minutach)'
    m.add_child(main_plot.colormap)
    return m

# @st.cache_data # tutaj chyba lepiej trzymać jak najmniej rzeczy..?
def create_static_map():
    # Plot the contours (filled with color) and health facility locations
    fig, ax = plt.subplots(figsize=(10, 10))
    main_plot.municipalities.plot(ax=ax, edgecolor='grey', facecolor=[main_plot.color_mapping[(tuple(c), n)] for c, n in main_plot.municipality_dict.items()], linewidth=0.25)
    main_plot.voivodeships.plot(ax=ax, edgecolor='black', facecolor="none", linewidth=0.25) # color czy facecolor? + alpha?
    # health_facilities[health_facilities['amenity'] == 'hospital'].plot(ax=ax, color='orange', markersize=10, label='Szpitale') # remove later? - some are points and some are exact polygons

    ax.set_title("Mapa Polski z województwami i gminami")
    ax.set_xlabel("Długość geograficzna")
    ax.set_ylabel("Szerokość geograficzna")
    # fig.legend()

    # Colormap legend as a bar - https://www.mimuw.edu.pl/~walen/vis/wybory2018/
    sm = plt.cm.ScalarMappable(cmap=main_plot.cmap, norm=main_plot.norm)
    cbar = plt.colorbar(
        sm,
        shrink=0.66,
        ax=plt.gca() # what does that do?
    )
    sm.set_array([]) # what does that do?
    cbar.set_label('Czas jazdy samochodem od centrum gminy do najbliższego szpitala (w minutach)')

    # 60+ instead of just 60 minutes as the top value
    num_ticks = 7
    ticks = np.linspace(0, 60, num_ticks)
    tick_labels = [f'{int(tick)}' for tick in ticks]
    tick_labels[-1] = f'{int(ticks[-1])}+' # change the last label to '60+'

    cbar.set_ticks(ticks)
    cbar.set_ticklabels(tick_labels)

    plt.tight_layout()
    plt.show()
    # fig.show() - wrong! for some reason
    # st.pyplot(fig)
    return fig
    # st.image('svg_plot.svg')

# @st.cache_data
def create_statistics_plot():
    top_municipalities = [mun_name for (_, mun_name), _ in main_plot.min_times_sorted[:20]]
    top_min_times_in_minutes = [time[1] for _, time in main_plot.min_times_sorted[:20]]
    top_hospital_names = [time[0] for _, time in main_plot.min_times_sorted[:20]]

    bottom_municipalities = [mun_name for (_, mun_name), _ in main_plot.min_times_sorted[-20:]]
    bottom_min_times_in_minutes = [time[1] for _, time in main_plot.min_times_sorted[-20:]]
    bottom_hospital_names = [time[0] for _, time in main_plot.min_times_sorted[-20:]]

    subplot_num = 3
    subplot_size = 10
    fig, (ax1, ax2, ax3) = plt.subplots(subplot_num, 1, figsize=(subplot_size, subplot_num * subplot_size))
    bars1 = ax1.bar(top_municipalities, top_min_times_in_minutes, color='lightgreen')

    for bar, hospital_name in zip(bars1, top_hospital_names):
        ax1.annotate(f'{hospital_name}',
                    xy=(bar.get_x() + bar.get_width() / 2, 0),
                    xytext=(0, 5), # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, rotation=90)

    # annot = ax.annotate("", xy=(0,0), xytext=(-20,20),textcoords="offset points",
    #     bbox=dict(boxstyle="round", fc="black", ec="b", lw=2),
    #     arrowprops=dict(arrowstyle="->"))

    # annot.set_visible(False)

    # def update_annot(bar):
    #     x = bar.get_x()+bar.get_width()/2.
    #     y = bar.get_y()+bar.get_height()
    #     annot.xy = (x,y)
    #     text = "({:.2g},{:.2g})".format( x,y )
    #     annot.set_text(text)
    #     annot.get_bbox_patch().set_alpha(0.4)


    # def hover(event):
    #     vis = annot.get_visible()
    #     if event.inaxes == ax:
    #         for bar in bars:
    #             cont, ind = bar.contains(event)
    #             if cont:
    #                 update_annot(bar)
    #                 annot.set_visible(True)
    #                 fig.canvas.draw_idle()
    #                 return
    #     if vis:
    #         annot.set_visible(False)
    #         fig.canvas.draw_idle()

    # fig.canvas.mpl_connect("motion_notify_event", hover)

    ax1.set_xlabel("Nazwa gminy")
    ax1.set_ylabel("Czas jazdy samochodem od centrum gminy do najbliższego szpitala (w minutach)")
    ax1.set_title("Centra gmin położone najbliżej szpitali")
    ax1.tick_params(axis='x', rotation=90, labelsize=10)
    # ========================================

    bars2 = ax2.bar(bottom_municipalities, bottom_min_times_in_minutes, color='lightcoral')

    for bar, hospital_name in zip(bars2, bottom_hospital_names):
        ax2.annotate(f'{hospital_name}',
                    xy=(bar.get_x() + bar.get_width() / 2, 0),
                    xytext=(0, 5), # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, rotation=90)

    ax2.set_xlabel("Nazwa gminy")
    ax2.set_ylabel("Czas jazdy samochodem od centrum gminy do najbliższego szpitala (w minutach)")
    ax2.set_title("Centra gmin położone najdalej szpitali")
    ax2.tick_params(axis='x', rotation=90, labelsize=10)

    top_20_most_often = {k: v for k, v in sorted(main_plot.hospital_counts.items(), key=lambda c: c[1], reverse=True)[:20]} # refactor!!!!!! teraz na szybko

    bars3 = ax3.bar(range(len(top_20_most_often.keys())), top_20_most_often.values(), color='deepskyblue')
    # dlaczego w tym słowniku jako klucz jest po prostu nazwa szpitala? aha, jak się powtarzały, to dodawałem po prostu _n więc nie będzie błędów

    for bar, hospital_name in zip(bars3, top_20_most_often.keys()):
        ax3.annotate(f'{hospital_name}',
                    xy=(bar.get_x() + bar.get_width() / 2, 0),
                    xytext=(0, 5), # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, rotation=90)

    ax3.set_xlabel("Nazwa szpitala")
    ax3.set_ylabel("Liczba wystąpień")
    ax3.set_title("Szpitale, które były najbliższe dla największej liczby gmin")
    ax3.tick_params(axis='x', rotation=90, labelsize=10)
    ax3.set_xticks([]) # for major ticks
    ax3.set_xticks([], minor=True) # for minor ticks

    plt.tight_layout()
    # st.pyplot(fig)
    return fig

static = create_static_map()
interactive = create_interactive_map()
statistics = create_statistics_plot()

# Sidebar menu:
with st.sidebar:
    selected = option_menu(menu_title="Menu", options=["Mapa statyczna", 'Mapa interaktywna', "Statystyki"], 
        icons=['house', 'gear', 'bi-bar-chart'], menu_icon="cast", default_index=0)

if selected == "Mapa statyczna":
    st.header("Najbliższe szpitale od centrum danej gminy", divider='rainbow')
    st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.pyplot(static)
elif selected == "Mapa interaktywna":
    st.header("Interaktywna mapa najbliższych szpitali od centrum danej gminy", divider='rainbow')
    st.subheader("Najedź kursorem na wybraną gminę, żeby zobaczyć dokładne statystyki. Możesz również przybliżać mapę.")
    # m = create_interactive_map()
    st_folium(interactive, width=800, height=600)
elif selected == "Statystyki":
    st.header("Wybrane statystyki", divider='rainbow')
    # st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.pyplot(statistics)