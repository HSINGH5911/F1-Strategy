import math
import random

from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
from config.Tires import TIRES
from config.Tracks import TRACKS
from simulation.lap_time_model import calc_lap_time
from simulation.degredation_model import update_tire_distance
from simulation.overtakes import attempt_overtake, swap_pos
from simulation.pit_stop_model import perform_stop
from simulation.overtakes import pace_delta
from data.random_weather import update_weather as update_track_wetness, weather_state


def race_laps(track):
    from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
    race_distance = (
        MONACO_RACE_DISTANCE_KM
        if track.get("name") == "Monaco"
        else DEFAULT_RACE_DISTANCE_KM
    )
    return track.get("laps", math.ceil(race_distance / track["length_km"]))

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

        dnf_chance = (1 - driver.team.reliability) * .002
        if random.random() < dnf_chance:
            driver.dnf = True
            drivers.remove(driver)

        if driver.dnf and random.random() < 0.6:
            race_state.safety_car = True
            race_state.sc_laps_remaining = random.randint(3, 6)
        
        driver.laps_since_last_pit += 1


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

def get_num__rec_pit_stops(track):
    pit_stop_amount = track["reccommended_pit_stops"]

    if pit_stop_amount == 1.5:
        # Randomly decide if we want 1 or 2 stops for this
        pit_stop_amount = 1 if random.random() < 0.5 else 2

    return pit_stop_amount

def get_pit_window(track):
    total_laps = race_laps(track)

    pit_stop_amount = get_num__rec_pit_stops(track)

    if pit_stop_amount == 1:
        pit_window = [total_laps // 2]
    elif pit_stop_amount == 2:
        pit_window = [
            total_laps // 3,
            (2 * total_laps) // 3
        ]
    else:
        pit_window = []

    return pit_window

def process_pit_stops(drivers, track, race_state, skip_codes=None):
    total_laps = race_laps(track)
    current_lap = race_state.current_lap

    pit_stop_amount = get_num__rec_pit_stops(track)
    pit_window = get_pit_window(track)

    near_window = any(
        abs(race_state.current_lap - lap) <= 3
        for lap in pit_window
    )

    if skip_codes is None:
        skip_codes = set()

    for i, driver in enumerate(drivers):
        # skip drivers explicitly requested (e.g., player when using external strategy)
        if driver.code in skip_codes:
            continue

        laps_since_pit = driver.laps_since_last_pit

        tire_data = TIRES[driver.current_compound]
        laps_remaining = race_state.laps_remaining

        car_ahead = drivers[i - 1] if i > 0 else None
        car_behind = drivers[i + 1] if i < len(drivers) - 1 else None

        target_stops_by_now = sum(
            1 for lap in pit_window
            if current_lap >= lap
        )

        # Pitting due to tire reached max possible distance
        if driver.tire_distance >= tire_data["max_distance"]:
            perform_stop(
                driver,
                track,
                pick_compound(laps_remaining, track, race_state),
                race_state
            )
            continue

        # Pit for 2 stop strat and the tires are starting to struggle in the second stint
        if driver.pit_stops < target_stops_by_now:
            if driver.tire_distance > tire_data["max_distance"] * 0.6:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )

        # Undercut -> We are faster than ahead car. Pit now and jummp them
        if car_ahead and laps_since_pit > 10 and near_window:
            delta = pace_delta(driver, car_ahead)
            gap = driver.race_time - car_ahead.race_time

            if delta > 0.3 and gap < track["pit_delta"] * 0.6:
                if random.random() < 0.65:
                    perform_stop(driver, track, "SOFT", race_state)
                    continue

        # Overcut -> Car behind is faster. Stay out and build gap
        if car_behind and laps_since_pit > 10 and near_window:
            delta = pace_delta(car_behind, driver)
            gap = car_behind.race_time - driver.race_time

            # They faster but not close enough to pass so skip pit this lap
            if delta > 0.4 and gap > 1.5:
                continue

        # Car in front is pitting -> Mirror only if we aren't significantly faster
        if car_ahead and car_ahead.pit_stops > driver.pit_stops and near_window and laps_since_pit > 10:
            delta = pace_delta(driver, car_ahead)
            if delta < 0.5 and random.random() < 0.55:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )
                continue

        # Free stop under safety car
        if race_state.safety_car and driver.tire_distance > 20:
            if random.random() < 0.75:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )

        # Forcing pit stop for those who havent stopped yet and we are past the window for 1 stop strategy
        laps_rem = total_laps - current_lap
        missing_stops = pit_stop_amount - driver.pit_stops

        if missing_stops > 0 and laps_rem < missing_stops * 5:
            perform_stop(
                driver,
                track,
                pick_compound(laps_remaining, track, race_state),
                race_state
            )
            continue

def pick_compound(laps_left, track, race_state):
    """Method to pick the compound to use for the race after pitting"""
    stress = track["tire_stress"]

    if race_state.track_wetness >= 0.6:
        return "WET"
    elif race_state.track_wetness < 0.6 and race_state.track_wetness >= 0.2:
        return "INTERMEDIATE"

    if laps_left < 15:
        return "SOFT"
    elif laps_left < 30:
        return random.choice(["MEDIUM", "SOFT"])
    else:
        return "HARD" if stress > 0.75 else random.choice(["MEDIUM", "HARD"])



def update_weather(race_state):
    race_state.track_wetness = update_track_wetness(race_state.track_wetness)
    race_state.weather_state = weather_state(race_state.track_wetness)


def record_history(history, race_state, drivers):
    if history is None:
        return

    history.setdefault("laps", []).append(race_state.current_lap)

    for driver in drivers:
        # record cumulative pit counts for change detection
        prev_counts = history.setdefault("pit_counts", {}).setdefault(driver.code, [])
        prev = prev_counts[-1] if prev_counts else 0
        prev_counts.append(driver.pit_stops)

        # if pit count increased this lap, record the lap as a pit
        if driver.pit_stops > prev:
            history.setdefault("pit_laps", {}).setdefault(driver.code, []).append(race_state.current_lap)

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
    race_state.laps_remaining = total_laps - race_state.current_lap + 1

    while race_state.current_lap <= total_laps:
        simulate_lap(drivers, track, race_state, total_laps)

        update_positions(drivers)

        process_overtakes(drivers, track)

        process_pit_stops(drivers, track, race_state)

        update_weather(race_state)

        record_history(history, race_state, drivers)

        race_state.current_lap += 1
        race_state.laps_remaining = max(0, total_laps - race_state.current_lap + 1)

