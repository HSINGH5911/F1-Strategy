from matplotlib import pyplot as plt

import fastf1
from fastf1 import plotting

fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

race = fastf1.get_session(2022, "Hungary", 'R')
race.load()

fig, ax = plt.subplots(figsize=(8, 5))

for driver in ("VER", "RUS"):
    laps = race.laps.pick_drivers(driver).pick_quicklaps().reset_index()
    style = plotting.get_driver_style(identifier=driver,
                                      style=['color', 'linestyle'],
                                      session=race)
    ax.plot(laps['LapTime'], **style, label=driver)


ax.set_xlabel("Lap Number")
ax.set_ylabel("Lap Time")
ax.legend()

# add axis labels and a legend
ax.set_xlabel("Lap Number")
ax.set_ylabel("Lap Time")
plotting.add_sorted_driver_legend(ax, race)
plt.show()
