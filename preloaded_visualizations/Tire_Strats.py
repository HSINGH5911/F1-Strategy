from collections.abc import Iterable

import fastf1
import json
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from util.fastf1_cache import enable_fastf1_cache


def get_session(year, location, session_type):
    """Return the FastF1 session for a year/location/session type."""
    enable_fastf1_cache()
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
        data["drivers"][driver] = build_tire_runs(driver_laps)

    return data


def build_tire_runs(driver_laps):
    """Collapse FastF1 lap rows into real tire runs.

    FastF1's ``Stint`` column can split during safety-car, red-flag, or
    pit-lane timing oddities. This function keeps same-compound stops when the
    lap data shows a genuinely fresh tire, while merging same-compound timing
    artifacts back into the surrounding run.
    """
    valid_laps = driver_laps.dropna(subset=["LapNumber", "Compound"])
    valid_laps = valid_laps.sort_values("LapNumber")
    stint_lengths = valid_laps.groupby("Stint")["LapNumber"].count().to_dict()

    tire_runs = []

    for _, lap in valid_laps.iterrows():
        lap_number = int(lap["LapNumber"])
        compound = lap["Compound"]
        tire_life = lap.get("TyreLife")

        if not tire_runs:
            tire_runs.append(new_tire_run(compound, lap_number, tire_life))
            continue

        current_run = tire_runs[-1]

        if starts_new_tire_run(lap, current_run, stint_lengths):
            tire_runs.append(new_tire_run(compound, lap_number, tire_life))
        else:
            current_run["end_lap"] = lap_number

        tire_runs[-1]["last_tire_life"] = tire_life

    for tire_run in tire_runs:
        tire_run.pop("last_tire_life", None)

    return tire_runs


def new_tire_run(compound, lap_number, tire_life):
    """Create the internal tire-run structure used while parsing laps."""
    return {
        "compound": compound,
        "start_lap": lap_number,
        "end_lap": lap_number,
        "last_tire_life": tire_life
    }


def starts_new_tire_run(lap, current_run, stint_lengths):
    """Return True if a lap should start a new plotted tire run."""
    if lap["Compound"] != current_run["compound"]:
        return True

    return is_real_same_compound_change(lap, current_run, stint_lengths)


def is_real_same_compound_change(lap, current_run, stint_lengths):
    """Detect same-compound pit stops without counting timing artifacts."""
    if not bool(lap.get("FreshTyre")):
        return False

    tire_life = lap.get("TyreLife")
    previous_tire_life = current_run.get("last_tire_life")

    if pd.isna(tire_life) or pd.isna(previous_tire_life):
        return False

    if tire_life > 3 or tire_life >= previous_tire_life:
        return False

    if is_one_lap_pit_lane_artifact(lap, stint_lengths):
        return False

    return True


def is_one_lap_pit_lane_artifact(lap, stint_lengths):
    """Catch same-compound one-lap timing splits during messy race periods."""
    stint = lap.get("Stint")
    if pd.isna(stint) or stint_lengths.get(stint, 0) > 1:
        return False

    return pd.notna(lap.get("PitInTime")) and pd.notna(lap.get("PitOutTime"))


def show_tire_strats(year, location, session_type):
    """Plot tire strategies used by the drivers for one session."""
    session = get_session(year, location, session_type)
    session.load()

    laps = session.laps

    drivers = [session.get_driver(driver)["Abbreviation"]
               for driver in session.drivers]

    fig, ax = plt.subplots(figsize=(5, 10))

    compound_colors = {
        "SOFT": "#FF6961",
        "MEDIUM": "#FDFD96",
        "HARD": "#FFFFFF",
        "INTERMEDIATE": "green",
        "WET": "blue"
    }

    for driver in drivers:
        driver_laps = laps[laps["Driver"] == driver]
        tire_runs = build_tire_runs(driver_laps)

        for tire_run in tire_runs:
            stint_length = tire_run["end_lap"] - tire_run["start_lap"] + 1
            plt.barh(
                y=driver,
                width=stint_length,
                left=tire_run["start_lap"] - 1,
                color=compound_colors.get(tire_run["compound"], "gray"),
                edgecolor="black"
            )

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
