import matplotlib.pyplot as plt
import numpy as np
import folium


class StyleFunction: # wut
    def __init__(self, color):
        self.color = color

    def __call__(self, feature):
        return {'fillColor': self.color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}

# @st.cache_data
def create_interactive_map(file):
    m = folium.Map( # unhardcodify!!!
        location=[52.0693, 19.4803], # piątek dodać
        zoom_start=6,  # center on Poland
        max_zoom=18,   # Maximum zoom level
        min_zoom=6     # Minimum zoom level to keep the focus on Poland
    )

    for i, (mun_geometry, (c, n)) in enumerate(zip(file.municipality_polygons, file.municipality_dict.items())): # aah ok
        color = file.color_mapping_interactive[(tuple(c), n)]
        style_func = StyleFunction(color)
        folium.GeoJson(
            mun_geometry,
            style_function=style_func,
            tooltip=folium.Tooltip(f'{"Gmina" if file == main_plot else "Powiat"}: {n}<br>Najbliższy szpital: {file.min_times_dict[(tuple(c), n)][0]}<br>Czas dojazdu: {file.min_times_dict[(tuple(c), n)][1]:.2f} minut')
        ).add_to(m)

    file.colormap.caption = f'Czas jazdy samochodem od centrum {"gminy" if file == main_plot else "powiatu"} do najbliższego szpitala (w minutach)'
    m.add_child(file.colormap)
    return m

# @st.cache_data # tutaj chyba lepiej trzymać jak najmniej rzeczy..?
def create_static_map(file):
    # Plot the contours (filled with color) and health facility locations
    fig, ax = plt.subplots(figsize=(10, 10))
    file.municipalities.plot(ax=ax, edgecolor='grey', facecolor=[file.color_mapping[(tuple(c), n)] for c, n in file.municipality_dict.items()], linewidth=0.25)
    file.voivodeships.plot(ax=ax, edgecolor='black', facecolor="none", linewidth=0.25) # color czy facecolor? + alpha?
    # health_facilities[health_facilities['amenity'] == 'hospital'].plot(ax=ax, color='orange', markersize=10, label='Szpitale') # remove later? - some are points and some are exact polygons

    ax.set_title(f'Mapa Polski z województwami i {"gminami" if file == main_plot else "powiatami"}')
    ax.set_xlabel("Długość geograficzna")
    ax.set_ylabel("Szerokość geograficzna")
    # fig.legend()

    # Colormap legend as a bar - https://www.mimuw.edu.pl/~walen/vis/wybory2018/
    sm = plt.cm.ScalarMappable(cmap=file.cmap, norm=file.norm)
    cbar = plt.colorbar(
        sm,
        shrink=0.66,
        ax=plt.gca() # what does that do?
    )
    sm.set_array([]) # what does that do?
    cbar.set_label(f'Czas jazdy samochodem od centrum {"gminy" if file == main_plot else "powiatu"} do najbliższego szpitala (w minutach)')

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
def create_statistics_plot(file):
    top_municipalities = [mun_name for (_, mun_name), _ in file.min_times_sorted[:20]]
    top_min_times_in_minutes = [time[1] for _, time in file.min_times_sorted[:20]]
    top_hospital_names = [time[0] for _, time in file.min_times_sorted[:20]]

    bottom_municipalities = [mun_name for (_, mun_name), _ in file.min_times_sorted[-20:]]
    bottom_min_times_in_minutes = [time[1] for _, time in file.min_times_sorted[-20:]]
    bottom_hospital_names = [time[0] for _, time in file.min_times_sorted[-20:]]

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

    ax1.set_xlabel(f'Nazwa {"gminy" if file == main_plot else "powiatu"}')
    ax1.set_ylabel(f'Czas jazdy samochodem od centrum {"gminy" if file == main_plot else "powiatu"} do najbliższego szpitala (w minutach)')
    ax1.set_title(f'Centra {"gmin" if file == main_plot else "powiatów"} położone najbliżej szpitali')
    ax1.tick_params(axis='x', rotation=90, labelsize=10)
    # ========================================

    bars2 = ax2.bar(bottom_municipalities, bottom_min_times_in_minutes, color='lightcoral')

    for bar, hospital_name in zip(bars2, bottom_hospital_names):
        ax2.annotate(f'{hospital_name}',
                    xy=(bar.get_x() + bar.get_width() / 2, 0),
                    xytext=(0, 5), # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, rotation=90)

    ax2.set_xlabel(f'Nazwa {"gminy" if file == main_plot else "powiatu"}')
    ax2.set_ylabel(f'Czas jazdy samochodem od centrum {"gminy" if file == main_plot else "powiatu"} do najbliższego szpitala (w minutach)')
    ax2.set_title(f'Centra {"gmin" if file == main_plot else "powiatów"} położone najdalej szpitali')
    ax2.tick_params(axis='x', rotation=90, labelsize=10)

    top_20_most_often = {k: v for k, v in sorted(file.hospital_counts.items(), key=lambda c: c[1], reverse=True)[:20]} # refactor!!!!!! teraz na szybko

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
    ax3.set_title(f'Szpitale, które były najbliższe dla największej liczby {"gmin" if file == main_plot else "powiatów"}')
    ax3.tick_params(axis='x', rotation=90, labelsize=10)
    ax3.set_xticks([]) # for major ticks
    ax3.set_xticks([], minor=True) # for minor ticks

    plt.tight_layout()
    # st.pyplot(fig)
    return fig

import main_plot # xd ale czy to tak źle w sumie?
static_mun = create_static_map(main_plot)
interactive_mun = create_interactive_map(main_plot)
statistics_mun = create_statistics_plot(main_plot)

import main_plot2 # xd
static_cnt = create_static_map(main_plot2)
interactive_cnt = create_interactive_map(main_plot2)
statistics_cnt = create_statistics_plot(main_plot2)

static_mun.savefig("plots/static_mun.png")
static_cnt.savefig("plots/static_cnt.png")

statistics_mun.savefig("plots/statistics_mun.png")
statistics_cnt.savefig("plots/statistics_cnt.png")

interactive_mun.save('plots/interactive_mun.html')
interactive_cnt.save('plots/interactive_cnt.html')