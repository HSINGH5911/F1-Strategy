from matplotlib import pyplot as plt

import fastf1
import fastf1.plotting

def show_tire_strats(year, location, session_type):
    session = fastf1.get_session(year, location, session_type)
    session.load()
    laps = session.laps

    drivers = session.drivers
    drivers = [session.get_driver(driver)["Abbreviation"] for driver in drivers]

    stints = laps[["Driver", "Stint", "Compound", "LapNumber"]]
    stints = stints.groupby(["Driver", "Stint", "Compound"])
    stints = stints.count().reset_index()

    stints = stints.rename(columns={"LapNumber": "StintLength"})

    fig, ax = plt.subplots(figsize=(5, 10))

    for driver in drivers:
        driver_stints = stints.loc[stints["Driver"] == driver]

        previous_stint_end = 0
        for idx, row in driver_stints.iterrows():
            compound_colors = {
                "SOFT": "#FF6961", #red
                "MEDIUM": "#FDFD96", #yellow
                "HARD": "#FFFFFF", #white
                "INTERMEDIATE": "green",
                "WET": "blue"
            }

            compound_color = compound_colors[row["Compound"]]

            plt.barh(
                y=driver,
                width=row["StintLength"],
                left=previous_stint_end,
                color=compound_color,
                edgecolor="black",
                fill=True
            )

            previous_stint_end += row["StintLength"]

    plt.title(str(year) + " " + location + " Grand Prix Strats")
    plt.xlabel("Lap Number")
    plt.grid(False)

    ax.invert_yaxis()

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.tight_layout()
    plt.show()

show_tire_strats(2025, "Monaco", "R")