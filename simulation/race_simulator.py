import math

from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
from config.Tires import TIRES
from simulation.lap_time_model import calc_lap_time
from simulation.degredation_model import update_tire_distance
from simulation.overtakes import attempt_overtake, swap_pos
from simulation.pit_stop_model import perform_stop
from data.weather import update_weather as update_track_wetness, weather_state


def simulate_lap(drivers, track, race_state, total_laps):
    for driver in drivers:
        lap_time = calc_lap_time(driver, track, race_state)

        driver.last_lap_time = lap_time
        driver.race_time += lap_time
        driver.fastest_lap = (
            lap_time
            if driver.fastest_lap is None
            else min(driver.fastest_lap, lap_time)
        )

        update_tire_distance(driver, track)
        driver.fuel_percentage = max(0.0, driver.fuel_percentage - (100 / total_laps))


def update_positions(drivers):
    drivers.sort(key=lambda d: d.race_time)

    for pos, driver in enumerate(drivers, start=1):
        driver.position = pos

    leader_time = drivers[0].race_time if drivers else 0.0

    for driver in drivers:
        driver.gap_to_lead = driver.race_time - leader_time


def process_overtakes(drivers, track):
    for i in range(1, len(drivers)):

        attacker = drivers[i]
        defender = drivers[i - 1]

        gap = attacker.race_time - defender.race_time

        if attempt_overtake(attacker, defender, gap, track):
            swap_pos(attacker, defender)


def process_pit_stops(drivers, track, race_state):
    for driver in drivers:
        tire_data = TIRES[driver.current_compound]

        if driver.tire_distance >= tire_data["max_distance"]:
            perform_stop(driver, track, "HARD", race_state)


def update_weather(race_state):
    race_state.track_wetness = update_track_wetness(race_state.track_wetness)
    race_state.weather_state = weather_state(race_state.track_wetness)


def record_history(history, race_state, drivers):
    if history is None:
        return

    history.setdefault("laps", []).append(race_state.current_lap)

    for driver in drivers:
        history.setdefault("positions", {}).setdefault(driver.code, []).append(driver.position)
        history.setdefault("lap_times", {}).setdefault(driver.code, []).append(driver.last_lap_time)
        history.setdefault("tire_distance", {}).setdefault(driver.code, []).append(driver.tire_distance)
        history.setdefault("compounds", {}).setdefault(driver.code, []).append(driver.current_compound)
        history.setdefault("gaps", {}).setdefault(driver.code, []).append(driver.gap_to_lead)


def race_laps(track):
    race_distance = (
        MONACO_RACE_DISTANCE_KM
        if track.get("name") == "Monaco"
        else DEFAULT_RACE_DISTANCE_KM
    )

    return track.get("laps", math.ceil(race_distance / track["length_km"]))


def simulate_race(drivers, track, race_state, history=None):
    total_laps = race_laps(track)

    while race_state.current_lap <= total_laps:
        simulate_lap(drivers, track, race_state, total_laps)

        update_positions(drivers)

        process_overtakes(drivers, track)

        process_pit_stops(drivers, track, race_state)

        update_weather(race_state)

        record_history(history, race_state, drivers)

        race_state.current_lap += 1
