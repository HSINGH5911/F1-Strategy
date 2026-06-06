import seaborn as sns
from fontTools.feaLib import location
from matplotlib import pyplot as plt

import fastf1
import fastf1.plotting

def show_dist_data(drivers, year, location, type):
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')
    race = fastf1.get_session(year, location, type)
    race.load()

    point_finishers = drivers
    driver_laps = race.laps.pick_drivers(point_finishers).pick_quicklaps()
    driver_laps = driver_laps.reset_index()

    finishing_order = [race.get_driver(i)["Abbreviation"] for i in point_finishers]

    fig, ax = plt.subplots(figsize=(10, 5))

    driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds()

    sns.violinplot(data=driver_laps,
                   x="Driver",
                   y="LapTime(s)",
                   hue="Driver",
                   inner=None,
                   density_norm="area",
                   order=finishing_order,
                   palette=fastf1.plotting.get_driver_color_mapping(session=race)
                   )

    sns.swarmplot(data=driver_laps,
                  x="Driver",
                  y="LapTime(s)",
                  order=finishing_order,
                  hue="Compound",
                  palette=fastf1.plotting.get_compound_mapping(session=race),
                  hue_order=["SOFT", "MEDIUM", "HARD"],
                  linewidth=0,
                  size=4,
                  )

    ax.set_xlabel("Driver")
    ax.set_ylabel("Lap Time (s)")
    plt.suptitle("2023 Azerbaijan Grand Prix Lap Time Distributions")
    sns.despine(left=True, bottom=True)

    plt.tight_layout()
    plt.show()
