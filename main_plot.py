import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import openrouteservice as ors
import math
import pickle # switch to json if the dict is to be readable
import numpy as np
import branca.colormap as cm # idk what's the difference tbh

# not needed anymore tbh
def convert_keys_to_strings(d):
    return {str(k): v for k, v in d.items()}

def convert_keys_back(d):
    new_dict = {}
    for k, v in d.items():
        try:
            new_key = eval(k)
            new_dict[new_key] = v
        except Exception as e:
            print(f"Error converting key: {k}")
            print(f"Exception: {e}")
    return new_dict

# ================================================================================================== SETUP:

matrix_api_base_url = 'http://localhost:8080/ors/v2/matrix/driving-car'

load_mun = True
# ehh, zmienić nazwę chociaż

# Load the contours of Poland and its municipalities from a GeoJSON file
municipalities = gpd.read_file("json_data/poland_municipalities.json" if load_mun else "json_data/poland_counties.json")
municipality_polygons = municipalities['geometry']
municipality_centroids = municipality_polygons.to_crs('+proj=cea').centroid.to_crs(municipality_polygons.crs)
municipality_coords = [[coords.x, coords.y] for coords in municipality_centroids]
# Load health facility information from a SHP file
# health_facilities = gpd.read_file("poland_health_facilities_shp/poland.shp")

# Extra - load voivodeships (for plotting only)
voivodeships = gpd.read_file("json_data/poland_voivodeships.json")

# For some reason, the SHP file contains incomplete data about hospitals so I switched to GeoJSON (now 1043 hospitals instead of 138)
health_facilities = gpd.read_file("json_data/poland_health_facilities.geojson")
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

# why do the coords have to be 'inverted'?!?
# hospital_coords = [(loads(wkt_coords).x, loads(wkt_coords).y) for wkt_coords in hospitals['geometry']] # loads returns a Point object

# Matrix API call - key can be omitted for local host
client = ors.Client(base_url='http://localhost:8080/ors') # won't work on deploy

resume = True # SET TO TRUE AFTER LOADING NEW MAP DATA
if resume:
    try:
        with open('saved_data/mun_hospital_times.pickle' if load_mun else 'saved_data/county_hospital_times.pickle', 'rb') as handle:
            mun_hospital_times = pickle.load(handle)
            # mun_hospital_times_str_keys = pickle.load(handle)
            # mun_hospital_times = convert_keys_back(mun_hospital_times_str_keys) # tu jest chyba problem dla deploya...
    except FileNotFoundError:
        print('File does not exist (yet)')
        mun_hospital_times = {}
else:
    mun_hospital_times = {}

chunk_size = 10 # even a 100 is too much for a single call AND once (for Osjaków) it even failed with a chunk_size of 50!
num_chunks = math.ceil(len(hospital_coords) / chunk_size)

for j, (mun_coords, mun_name) in enumerate(municipality_dict.items()):
    print(mun_name, f"{j+1}/{len(municipalities['name'])}")

    if resume and (mun_coords, mun_name) in mun_hospital_times:
        print("already loaded")
        continue

    for i in range(num_chunks):
        start_idx = i*chunk_size
        end_idx = min((i+1)*chunk_size, len(hospital_coords))
        
        chunk_hospital_coords, chunk_hospital_names = hospital_coords[start_idx:end_idx], hospitals['unique_name'][start_idx:end_idx] #hospital_list_t[start_idx:end_idx]
        locations = [list(mun_coords)] + chunk_hospital_coords # double list because the 1st one converts the tuple to a list and the second one nests it so that lists can be concatenated in the way this API wants it

        params = {
            'locations': locations,
            'destinations': [0],
            'metrics': ['duration'],
        }
        
        # Make the matrix api call
        matrix = client.distance_matrix(**params)
        
        travel_times = matrix['durations'][1:] # ignore the first one since it's the time from X to X
        travel_times = [t for sublist in travel_times for t in sublist] # flatten the list
        # print(None in travel_times)

        # Pair each hospital with its travel times
        new_entries = list(zip(chunk_hospital_names, travel_times))
        existing_entries = mun_hospital_times.get((mun_coords, mun_name), [])
        existing_entries.extend(new_entries)
        mun_hospital_times[(mun_coords, mun_name)] = existing_entries
    
    # After loading a whole municipality, save the dict so that later this information doesn't have to be loaded again
    if j % 20 == 0 or j+1 == len(municipalities['name']):
        with open('saved_data/mun_hospital_times.pickle' if load_mun else 'saved_data/county_hospital_times.pickle', 'wb') as handle:
            print("saving")
            # mun_hospital_times_str_keys = convert_keys_to_strings(mun_hospital_times)
            pickle.dump(mun_hospital_times, handle, protocol=pickle.HIGHEST_PROTOCOL) # może zapisywać co np. 10 gmin, bo zapisywanie też trochę zajmuje

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