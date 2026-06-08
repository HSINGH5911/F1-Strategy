from collections.abc import Iterable

import fastf1
import json
from pathlib import Path

from matplotlib import pyplot as plt


def get_session(year, location, session_type):
    """Return the FastF1 session for a year/location/session type."""
    return fastf1.get_session(year, location, session_type)


def write_to_file(years, location, session_type, out_file):
    """Write tire strategy data for one year or many years to JSON.

    ``years`` can be a single integer, or an iterable such as
    ``range(2011, 2026)`` when loading every race strategy from 2011-2025.
    """
    session_type = session_type.upper()

    if is_year_collection(years):
        years = list(years)
        data = {
            "location": location,
            "session_type": session_type,
            "years": {},
            "failed_years": {}
        }

        for year in years:
            try:
                data["years"][year] = get_tire_strategy_data(
                    year,
                    location,
                    session_type
                )
            except Exception as error:
                # Some races did not exist in every season. Keep loading the
                # years that do exist and record the skipped ones for debugging.
                data["failed_years"][year] = str(error)
    else:
        data = get_tire_strategy_data(years, location, session_type)

    if is_year_collection(years) and not data["years"]:
        raise ValueError(
            f"No tire strategy data was found for {location} "
            f"from {min(years)} to {max(years)}."
        )

    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w") as file:
        json.dump(data, file, indent=4)


def is_year_collection(years):
    """Return True when ``years`` should be treated as multiple years."""
    return isinstance(years, Iterable) and not isinstance(years, (str, bytes))


def get_tire_strategy_data(year, location, session_type):
    """Build the serializable tire-strategy payload for one session."""
    session = get_session(year, location, session_type)
    session.load()

    laps = session.laps

    data = {
        "year": year,
        "location": location,
        "session_type": session_type,
        "drivers": {}
    }

    drivers = [
        session.get_driver(driver)["Abbreviation"]
        for driver in session.drivers
    ]

    for driver in drivers:
        driver_laps = laps[laps["Driver"] == driver]

        data["drivers"][driver] = []

        for stint in driver_laps["Stint"].unique():
            stint_laps = driver_laps[driver_laps["Stint"] == stint]

            data["drivers"][driver].append({
                "compound": stint_laps["Compound"].iloc[0],
                "start_lap": int(stint_laps["LapNumber"].min()),
                "end_lap": int(stint_laps["LapNumber"].max())
            })

    return data

def show_tire_strats(year, location, session_type):
    """Plot tire strategies used by the drivers for one session."""
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
        / f"{location.replace(' ', '_')}_Tire_Strats.json"
    )

    write_to_file(year, location, session_type, output_file)
    show_tire_strats(year, location, session_type)


if __name__ == "__main__":
    year = int(input("Year: "))
    location = input("Location: ")
    session_type = input("Session Type: ")

    main(year, location, session_type)
