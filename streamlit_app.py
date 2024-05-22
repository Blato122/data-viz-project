import matplotlib.pyplot as plt
import numpy as np

# interactive map on a website
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu # pip install streamlit-option-menu

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import openrouteservice as ors
import math
import pickle # switch to json if the dict is to be readable
import numpy as np
import branca.colormap as cm # idk what's the difference tbh

# ================================================================================================== SETUP:

matrix_api_base_url = 'http://localhost:8080/ors/v2/matrix/driving-car'

load_mun = True
# ehh, zmienić nazwę chociaż

# Load the contours of Poland and its municipalities from a GeoJSON file
municipalities = gpd.read_file("poland_municipalities.json" if load_mun else "poland_counties.json")
municipality_polygons = municipalities['geometry']
municipality_centroids = municipality_polygons.to_crs('+proj=cea').centroid.to_crs(municipality_polygons.crs)
municipality_coords = [[coords.x, coords.y] for coords in municipality_centroids]
# Load health facility information from a SHP file
# health_facilities = gpd.read_file("poland_health_facilities_shp/poland.shp")

# Extra - load voivodeships (for plotting only)
voivodeships = gpd.read_file("poland_voivodeships.json")

# For some reason, the SHP file contains incomplete data about hospitals so I switched to GeoJSON (now 1043 hospitals instead of 138)
health_facilities = gpd.read_file("poland_health_facilities.geojson")
hospitals = health_facilities[health_facilities['amenity'] == 'hospital'].copy() # what's that copy for? ah ok, so that the original doesn't get modified instead?
hospitals.reset_index(drop=True, inplace=True) # reset so that the indices are contiunous again - because of removing pharmacies etc. there are gaps
hospital_polygons = hospitals['geometry']
hospital_centroids = hospital_polygons.to_crs('+proj=cea').centroid.to_crs(hospital_polygons.crs) # equal area projection?! returns the same coords as before but no warning...
hospital_coords = [[coords.x, coords.y] for coords in hospital_centroids]

# Because some hospitals have the same names...
name_counts = {}

def make_unique(name):
    if name in name_counts:
        name_counts[name] += 1
        return f"{name}_{name_counts[name]}"
    else:
        name_counts[name] = 0
        return name

hospitals['unique_name'] = hospitals['name'].apply(make_unique) # hospitals.loc[:, 'unique_name'] = hospitals['name'].apply(make_unique)

# Solution to the above "problem":
# /home/blato/everything/data-viz-project/v2.py:23: UserWarning: Geometry is in a geographic CRS. Results from 'centroid' are likely incorrect.
# Use 'GeoSeries.to_crs()' to re-project geometries to a projected CRS before this operation.
# https://gis.stackexchange.com/questions/372564/userwarning-when-trying-to-get-centroid-from-a-polygon-geopandas

# ================================================================================================== MAIN PART, API CALLS:

def tuple_coords(coords, name): # :((((((
    if name == "Suchy Las":
        coords = (16.87743692734896, coords[1]) # original 16.87843692734896
    elif name == "Goniądz":
        coords = (22.744637359181316, coords[1]) # original: 22.745637359181316
    return tuple(coords)

# print(list(tuple(municipality_coords[0]))) that's cool - it doesn't nest these
municipality_dict = {tuple_coords(c, n) : n for c, n in zip(municipality_coords, municipalities['name'])} # https://stackoverflow.com/questions/16476924/how-can-i-iterate-over-rows-in-a-pandas-dataframe
# hospital_list_t = list(zip(*zip(hospitals['name'], hospital_coords)))
# maybe list better than a dict actually
# theres no key but at least there is an ordering
# ALE ZAMIESZANIE JUŻ Z TYMI DICT LIST I ZIP OMG POPRAWIĆ TO POTEM

# why do the coords have to be 'inverted'?!?
# hospital_coords = [(loads(wkt_coords).x, loads(wkt_coords).y) for wkt_coords in hospitals['geometry']] # loads returns a Point object

# Matrix API call - key can be omitted for local host
client = ors.Client(base_url='http://localhost:8080/ors') # won't work on deploy

resume = True # SET TO TRUE AFTER LOADING NEW MAP DATA
if resume:
    try:
        with open('mun_hospital_times.pickle' if load_mun else 'county_hospital_times.pickle', 'rb') as handle:
            mun_hospital_times = pickle.load(handle)
    except FileNotFoundError:
        print('File does not exist (yet)')
        mun_hospital_times = {}
else:
    st.write("???")
    mun_hospital_times = {}

# chunk_size = 10 # even a 100 is too much for a single call AND once (for Osjaków) it even failed with a chunk_size of 50!
# num_chunks = math.ceil(len(hospital_coords) / chunk_size)

# for j, (mun_coords, mun_name) in enumerate(municipality_dict.items()):
#     print(mun_name, f"{j+1}/{len(municipalities['name'])}")

#     if resume and (mun_coords, mun_name) in mun_hospital_times:
#         print("already loaded")
#         continue

#     for i in range(num_chunks):
#         start_idx = i*chunk_size
#         end_idx = min((i+1)*chunk_size, len(hospital_coords))
        
#         chunk_hospital_coords, chunk_hospital_names = hospital_coords[start_idx:end_idx], hospitals['unique_name'][start_idx:end_idx] #hospital_list_t[start_idx:end_idx]
#         locations = [list(mun_coords)] + chunk_hospital_coords # double list because the 1st one converts the tuple to a list and the second one nests it so that lists can be concatenated in the way this API wants it

#         params = {
#             'locations': locations,
#             'destinations': [0],
#             'metrics': ['duration'],
#         }
        

#         # Make the matrix api call
#         matrix = client.distance_matrix(**params)
        
#         travel_times = matrix['durations'][1:] # ignore the first one since it's the time from X to X
#         travel_times = [t for sublist in travel_times for t in sublist] # flatten the list
#         # print(None in travel_times)

#         # Pair each hospital with its travel times
#         new_entries = list(zip(chunk_hospital_names, travel_times))
#         existing_entries = mun_hospital_times.get((mun_coords, mun_name), [])
#         existing_entries.extend(new_entries)
#         mun_hospital_times[(mun_coords, mun_name)] = existing_entries
    
#     # After loading a whole municipality, save the dict so that later this information doesn't have to be loaded again
#     if j % 20 == 0 or j+1 == len(municipalities['name']):
#         with open('mun_hospital_times.pickle' if load_mun else 'county_hospital_times.pickle', 'wb') as handle:
#             print("saving")
#             pickle.dump(mun_hospital_times, handle, protocol=pickle.HIGHEST_PROTOCOL) # może zapisywać co np. 10 gmin, bo zapisywanie też trochę zajmuje

# https://pl.wikipedia.org/wiki/Powiaty_i_gminy_o_identycznych_nazwach XD
# duplicate_names = municipalities['name'][municipalities['name'].duplicated(keep=False)]
# print(f"Number of duplicate municipality names: {duplicate_names.nunique()}")
# print(f"Duplicate municipality names:\n{duplicate_names}")

# ================================================================================================== NEAREST HOSPITALS, COLORS:

# Mapping from a municipality name to a color
# The color will be based on the distance from the center of the municipality to the nearest hospital
# z tego też zrobic funkcję i iterować po poland name (?co)
norm = mcolors.Normalize(vmin=0, vmax=60) # najmniejszy czas dojazdu to niecała minuta, więc równie dobrze może być 0
cmap = plt.cm.RdYlGn_r # https://matplotlib.org/stable/gallery/color/colormap_reference.html
colormap = cm.LinearColormap(colors=['green', 'yellow', 'red'], vmin=0, vmax=60)

min_times = [] # needed for the next step (STATISTICS)
hospital_counts = {} # needed for the next step (STATISTICS)
    
color_mapping = {}
color_mapping_interactive = {}

for (mun_coords, mun_name), times in mun_hospital_times.items():
    mun_closest_hospital = min(times, key=lambda t: t[1]) # t[1] - time, t[0] - hospital name
    mun_closest_hospital_minutes = (mun_closest_hospital[0], mun_closest_hospital[1] / 60)

    hospital_counts[mun_closest_hospital_minutes[0]] = hospital_counts.get(mun_closest_hospital_minutes[0], 0) + 1 # increment top hospital count

    min_times.append(((mun_coords, mun_name), mun_closest_hospital_minutes)) # why is that a LIST?! ah ok, so that it can be sorted probably, nvm
    # print(mun_min)
    unzipped = list(zip(*times))
    # print( unzipped[0][ unzipped[1].index(min(unzipped[1])) ], min(unzipped[1]) ) # blah blah blah efficiency - gets the closest 
    color_mapping[(mun_coords, mun_name)] = cmap(norm(mun_closest_hospital_minutes[1]))
    color_mapping_interactive[(mun_coords, mun_name)] = colormap(mun_closest_hospital_minutes[1])

# ================================================================================================== STATISTICS:

min_times_dict = {(tuple(c), n) : t for (c, n), t in min_times}
print(min_times_dict)

# min_times and best_hospitals_sorted calculated in the previous step (NEAREST HOSPITALS, COLORS)
min_times_sorted = sorted(min_times, key=lambda t: t[1][1])
print("Top 10 hospitals that are the nearest to a center of a municipality:")
print(min_times_sorted[:10])
print("Bottom 10 hospitals that are the nearest to a center of a municipality:")
print(min_times_sorted[-10:])

print("Top 10 hospitals that were the nearest the most often:")
print({k: v for k, v in sorted(hospital_counts.items(), key=lambda c: c[1], reverse=True)[:10]}) # https://stackoverflow.com/questions/613183/how-do-i-sort-a-dictionary-by-value

# ================================================================================================== PLOTTING:

# moved to streamlit_app.py

# REMEMBER to launch Docker on Windows + X server AND do docker compose up -d on WSL2 before!

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

    for i, (mun_geometry, (c, n)) in enumerate(zip(municipality_polygons, municipality_dict.items())): # aah ok
        color = color_mapping_interactive[(tuple(c), n)]
        style_func = StyleFunction(color)
        folium.GeoJson(
            mun_geometry,
            style_function=style_func,
            tooltip=folium.Tooltip(f"Gmina: {n}<br>Najbliższy szpital: {min_times_dict[(tuple(c), n)][0]}<br>Czas dojazdu: {min_times_dict[(tuple(c), n)][1]:.2f}")
        ).add_to(m)

    colormap.caption = 'Czas jazdy samochodem od centrum gminy do najbliższego szpitala (w minutach)'
    m.add_child(colormap)
    return m

# @st.cache_data # tutaj chyba lepiej trzymać jak najmniej rzeczy..?
def create_static_map():
    # Plot the contours (filled with color) and health facility locations
    fig, ax = plt.subplots(figsize=(10, 10))
    municipalities.plot(ax=ax, edgecolor='grey', facecolor=[color_mapping[(tuple(c), n)] for c, n in municipality_dict.items()], linewidth=0.25)
    voivodeships.plot(ax=ax, edgecolor='black', facecolor="none", linewidth=0.25) # color czy facecolor? + alpha?
    # health_facilities[health_facilities['amenity'] == 'hospital'].plot(ax=ax, color='orange', markersize=10, label='Szpitale') # remove later? - some are points and some are exact polygons

    ax.set_title("Mapa Polski z województwami i gminami")
    ax.set_xlabel("Długość geograficzna")
    ax.set_ylabel("Szerokość geograficzna")
    # fig.legend()

    # Colormap legend as a bar - https://www.mimuw.edu.pl/~walen/vis/wybory2018/
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
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
    # plt.show()
    # fig.show() - wrong! for some reason
    # st.pyplot(fig)
    return fig
    # st.image('svg_plot.svg')

# @st.cache_data
def create_statistics_plot():
    top_municipalities = [mun_name for (_, mun_name), _ in min_times_sorted[:20]]
    top_min_times_in_minutes = [time[1] for _, time in min_times_sorted[:20]]
    top_hospital_names = [time[0] for _, time in min_times_sorted[:20]]

    bottom_municipalities = [mun_name for (_, mun_name), _ in min_times_sorted[-20:]]
    bottom_min_times_in_minutes = [time[1] for _, time in min_times_sorted[-20:]]
    bottom_hospital_names = [time[0] for _, time in min_times_sorted[-20:]]

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

    top_20_most_often = {k: v for k, v in sorted(hospital_counts.items(), key=lambda c: c[1], reverse=True)[:20]} # refactor!!!!!! teraz na szybko

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

# Create the maps beforehand (much faster than @st.cache_data...)
# BARDZO DŁUGO SIĘ PRZEZ TO ŁADUJE CHYBA!
# DZIAŁA, ALE jak to wygląda... no cóż, musiało działać na szybko
static = create_static_map()
interactive = create_interactive_map()
statistics = create_statistics_plot()

# static2 = create_static_map()
# interactive2 = create_interactive_map()
# statistics2 = create_statistics_plot()

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

if selected == "Mapa statyczna - gminy":
    st.header("Najbliższe szpitale od centrum danej gminy", divider='rainbow')
    st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.pyplot(static)
elif selected == "Mapa interaktywna - gminy":
    st.header("Interaktywna mapa najbliższych szpitali od centrum danej gminy", divider='rainbow')
    st.subheader("Najedź kursorem na wybraną gminę, żeby zobaczyć dokładne statystyki. Możesz również przybliżać mapę.")
    # m = create_interactive_map()
    st_folium(interactive, width=800, height=600)
elif selected == "Statystyki - gminy":
    st.header("Wybrane statystyki", divider='rainbow')
    # st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
    st.pyplot(statistics)

# elif selected == "Mapa statyczna - powiaty":
#     st.header("Najbliższe szpitale od centrum danego powiatu", divider='rainbow')
#     st.subheader("Kliknij przycisk w prawym górnym rogu, aby powiększyć mapę.")
#     st.pyplot(static2)
# elif selected == "Mapa interaktywna - powiaty":
#     st.header("Interaktywna mapa najbliższych szpitali od centrum danego powiatu", divider='rainbow')
#     st.subheader("Najedź kursorem na wybrany powiat, żeby zobaczyć dokładne statystyki. Możesz również przybliżać mapę.")
#     # m = create_interactive_map()
#     st_folium(interactive2, width=800, height=600)
# elif selected == "Statystyki - powiaty":
#     st.header("Wybrane statystyki", divider='rainbow')
#     st.subheader("Mniej ciekawe, niż w przypadku gmin.")
#     st.pyplot(statistics2)