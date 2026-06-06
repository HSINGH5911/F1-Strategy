from pathlib import Path
import fastf1
from matplotlib import pyplot as plt


def get_session(year, location, session_type):
    return fastf1.get_session(year, location, session_type)


def write_to_file(year, location, session_type, out_file):
    session = get_session(year, location, session_type)
    session.load()

    drivers = [session.get_driver(driver)["Abbreviation"]
               for driver in session.drivers]

    laps = session.laps

    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w") as file:  # overwrite instead of append
        file.write(f"{year} {location} {session_type}\n\n")

        for driver in drivers:
            driver_laps = laps[laps["Driver"] == driver]

            file.write(f"{driver}\n")

            for stint in driver_laps["Stint"].unique():
                stint_laps = driver_laps[driver_laps["Stint"] == stint]

                compound = stint_laps["Compound"].iloc[0]
                start_lap = int(stint_laps["LapNumber"].min())
                end_lap = int(stint_laps["LapNumber"].max())

                file.write(
                    f"  {compound}: Laps {start_lap}-{end_lap}\n"
                )

            file.write("\n")


def show_tire_strats(year, location, session_type):
    session = get_session(year, location, session_type)
    session.load()

    laps = session.laps

    drivers = [session.get_driver(driver)["Abbreviation"]
               for driver in session.drivers]

    stints = laps[["Driver", "Stint", "Compound", "LapNumber"]]
    stints = stints.groupby(
        ["Driver", "Stint", "Compound"]
    ).count().reset_index()

    stints = stints.rename(columns={"LapNumber": "StintLength"})

    fig, ax = plt.subplots(figsize=(5, 10))

    compound_colors = {
        "SOFT": "#FF6961",
        "MEDIUM": "#FDFD96",
        "HARD": "#FFFFFF",
        "INTERMEDIATE": "green",
        "WET": "blue"
    }

    for driver in drivers:
        driver_stints = stints[stints["Driver"] == driver]

        previous_stint_end = 0

        for _, row in driver_stints.iterrows():
            plt.barh(
                y=driver,
                width=row["StintLength"],
                left=previous_stint_end,
                color=compound_colors.get(row["Compound"], "gray"),
                edgecolor="black"
            )

            previous_stint_end += row["StintLength"]

    plt.title(f"{year} {location} Grand Prix Strats")
    plt.xlabel("Lap Number")

    ax.invert_yaxis()

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    plt.tight_layout()
    plt.show()


def main(year, location, session_type):
    output_file = (
        Path(__file__).resolve().parents[1]
        / "data_found"
        / "Tire_Strategies"
        / f"{location.replace(' ', '_')}_Tire_Strats.txt"
    )

    write_to_file(year, location, session_type, output_file)
    show_tire_strats(year, location, session_type)


if __name__ == "__main__":
    year = int(input("Year: "))
    location = input("Location: ")
    session_type = input("Session Type: ")

    main(year, location, session_type)