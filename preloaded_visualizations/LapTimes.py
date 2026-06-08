import seaborn as sns
from matplotlib import pyplot as plt

import fastf1
import fastf1.plotting
from util.fastf1_cache import enable_fastf1_cache

def show_lap_time_data(driver, year, location, session_type):
    enable_fastf1_cache()
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

    race = fastf1.get_session(year, location, session_type)
    race.load()

    driver_laps = race.laps.pick_drivers(driver).pick_quicklaps().reset_index()

    fig, ax = plt.subplots(figsize=(8, 8))

    sns.scatterplot(data=driver_laps,
                    x="LapNumber",
                    y="LapTime",
                    ax=ax,
                    hue="Compound",
                    palette=fastf1.plotting.get_compound_mapping(session=race),
                    s=80,
                    linewidth=0,
                    legend='auto')

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")

    ax.invert_yaxis()
    title = driver + " Laptimes in the " + str(year) + " " + location + " grand prix"
    plt.suptitle(title)


    plt.grid(color='w', which='major', axis='both')
    sns.despine(left=True, bottom=True)

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    show_lap_time_data("HAM", 2023, "Monaco", "R")
