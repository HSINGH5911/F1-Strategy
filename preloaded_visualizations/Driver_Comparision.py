from matplotlib import pyplot as plt

import fastf1
from fastf1 import plotting
from util.fastf1_cache import enable_fastf1_cache

def show_comparison_data(drivers, year, location, session_type):
    enable_fastf1_cache()
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')
    session = fastf1.get_session(year, location, session_type)
    session.load()

    fig, ax = plt.subplots(figsize=(8, 5))

    for driver in drivers:
        laps = session.laps.pick_drivers(driver).pick_quicklaps()

        if laps.empty:
            continue

        style = plotting.get_driver_style(
            identifier=driver,
            style=['color', 'linestyle'],
            session=session
        )

        ax.plot(
            laps['LapNumber'],
            laps['LapTime'],
            label=driver,
            **style
        )

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    plotting.add_sorted_driver_legend(ax, session)

    plt.show()

def main(drives, year, location, session_type):
    show_comparison_data(drives, year, location, session_type)

if __name__ == '__main__':
    show_comparison_data(["HAM", "VER"], 2023, "Monaco", "R")