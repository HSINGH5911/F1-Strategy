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
from strategy.undercut import *
from strategy.overcut import *


def race_laps(track):
    """Calculate the number of laps for a given track, using either a specified lap count or by 
        dividing the standard race distance by the track length."""
    
    from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
    race_distance = (
        MONACO_RACE_DISTANCE_KM
        if track.get("name") == "Monaco"
        else DEFAULT_RACE_DISTANCE_KM
    )
    return track.get("laps", math.ceil(race_distance / track["length_km"]))

def simulate_lap(drivers, track, race_state, total_laps):
    """Simulate a single lap for all drivers, updating their lap times, tire wear, fuel levels, 
        and handling potential DNFs and safety car conditions."""
    
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

        if random.random() < dnf_chance:
            driver.dnf = True
            if random.random() < .6:
                race_state.safety_car = True
                race_state.sc_laps_remaining = random.randint(3, 6)
                print(f"{driver.code} HAS CAUSE A SAFETY CAR!!!")
        
        # Adding a random penalty
        if random.random() < 0.001:
            driver.penalties += 1
            driver.penalty_time.append(5)
            print(f"{driver.code} received a 5 second penalty for track limits violation!")
            
        driver.laps_since_last_pit += 1


def update_positions(drivers):
    """Sort drivers by their current race time to update their positions and calculate their gap 
        to the leader."""
    
    drivers.sort(key=lambda d: d.race_time)

    for pos, driver in enumerate(drivers, start=1):
        driver.position = pos

    leader_time = drivers[0].race_time if drivers else 0.0

    for driver in drivers:
        driver.gap_to_lead = driver.race_time - leader_time


def process_overtakes(drivers, track):
    """Iterate through the drivers and attempt overtakes based on their current gap and pace 
        difference, starting from the second driver to compare with the one ahead."""
    
    for i in range(1, len(drivers)):

        attacker = drivers[i]
        defender = drivers[i - 1]

        gap = attacker.race_time - defender.race_time

        if attempt_overtake(attacker, defender, gap, track):
            penalty_chance = random.random()

            if penalty_chance < 0.001:
                attacker.dnf = True
                defender.dnf = True
                print(f"{attacker.code} and {defender.code} collided during an overtake!")

            elif penalty_chance < 0.005:
                attacker.penalties += 1
                attacker.penalty_time.append(10)
                print(f"{attacker.code} received a 10 second penalty for an aggressive overtake on {defender.code}!")
            
            elif penalty_chance < 0.02:
                attacker.penalties += 1
                attacker.penalty_time.append(5)
                print(f"{attacker.code} received a 5 second penalty for an aggressive overtake on {defender.code}!")

            

            else:
                swap_pos(attacker, defender)

def get_num_rec_pit_stops(track, driver):
    """Determine the recommended number of pit stops for a given track, handling cases where the 
        recommendation is 1.5 by randomly choosing between 1 or 2 stops."""
    
    pit_stop_amount = track["reccommended_pit_stops"]

    # Drivers that qualify higher are more likely to use one stop than those further down 
    # the grid who are more likely to use 2 stops when the recommendation is 1.5
    if pit_stop_amount == 1.5:
        if driver.position <= 5:
            pit_stop_amount = 1
        elif 5 < driver.position <= 10:
            pit_stop_amount = random.choice([1, 2])
        else:
            pit_stop_amount = 2

    return pit_stop_amount

def get_pit_window(track, driver):
    """Calculate the optimal pit window(s) for a given track based on the total number of laps 
        and the recommended number of pit stops, returning a list of lap numbers where pit stops 
        should ideally occur."""
    
    total_laps = race_laps(track)

    pit_stop_amount = get_num_rec_pit_stops(track, driver)

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

def serve_penalty(driver):
    """Apply any pending penalties to the driver by adding the penalty time to their race time and 
        clearing the penalty list."""
    
    if driver.penalties > 0:
        driver.race_time += driver.penalty_time.pop(0)
        driver.penalties -= 1

def process_pit_stops(drivers, track, race_state, skip_codes=None):
    """Evaluate each driver's situation to determine if a pit stop should be performed based on 
        tire wear, race conditions, and strategic considerations such as undercut/overcut 
        opportunities, safety car presence, and proximity to optimal pit windows."""
    
    total_laps = race_laps(track)
    current_lap = race_state.current_lap

    

    if skip_codes is None:
        skip_codes = set()

    for i, driver in enumerate(drivers):
        laps_remaining = race_state.laps_remaining
        
        # Pitting due to rain - applies to ALL drivers including player (mandatory safety)
        wet = (
            race_state.weather_state == "WET"
            and driver.current_compound not in ("WET", "INTERMEDIATE")
        )

        if wet:
            perform_stop(
                driver,
                track,
                pick_compound(laps_remaining, track, race_state),
                race_state
            )
            serve_penalty(driver)
            print(f"{driver.code} is pitting due to rain conditions! on lap {race_state.current_lap}")
            continue
        
        # skip drivers explicitly requested (e.g., player when using external strategy)
        # but only for strategic decisions, not safety-critical ones (rain already handled above)
        if driver.code in skip_codes:
            continue
        
        pit_stop_amount = get_num_rec_pit_stops(track, driver)
    
        # Build pit window based on calculated pit_stop_amount
        if pit_stop_amount == 1:
            pit_window = [total_laps // 2]
        elif pit_stop_amount == 2:
            pit_window = [
                total_laps // 3,
                (2 * total_laps) // 3
            ]
        else:
            pit_window = []

        near_window = any(
            abs(race_state.current_lap - lap) <= 3
            for lap in pit_window
        )

        laps_since_pit = driver.laps_since_last_pit

        tire_data = TIRES[driver.current_compound]

        car_ahead = drivers[i - 1] if i > 0 else None
        car_behind = drivers[i + 1] if i < len(drivers) - 1 else None

        target_stops_by_now = sum(
            1 for lap in pit_window
            if current_lap >= lap
        )
        
        # Check if driver has completed their required stops
        has_completed_required_stops = driver.pit_stops >= pit_stop_amount

        # Pitting due to tire reached max possible distance
        if driver.tire_distance >= tire_data["max_distance"] and laps_remaining > 10:
            perform_stop(
                driver,
                track,
                pick_compound(laps_remaining, track, race_state),
                race_state
            )
            serve_penalty(driver)
            print(f"{driver.code} is pitting due to tire wear! on lap {race_state.current_lap}")
            continue

        # Pit for multi-stop strategy and tires are starting to struggle
        # But only if we haven't already done the required stops AND we're near a pit window
        if driver.pit_stops < target_stops_by_now and near_window:
            if driver.tire_distance > tire_data["max_distance"]:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )
                serve_penalty(driver)
                print(f"{driver.code} is pitting to stay on optimal strategy! on lap {race_state.current_lap}")
                continue

        # Undercut -> We are faster than ahead car. Pit now and jump them
        # But only if we haven't already completed our required stops
        if not has_completed_required_stops and car_ahead and laps_since_pit > 10 and near_window:
            laps_before_rival = max(1, (tire_data["max_distance"] - car_ahead.tire_distance) // track["length_km"])
            if can_undercut(driver, car_ahead, track, race_state, laps_before_rival):
                    if random.random() < 0.65:
                        perform_stop(
                            driver,
                            track,
                            "SOFT" if race_state.track_wetness < .2 else "INTERMEDIATE",
                            race_state
                        )
                        serve_penalty(driver)
                        print(f"{driver.code} is pitting for an undercut! on lap {race_state.current_lap}")
           
        # Overcut -> Car behind is faster. Stay out and build gap
        if car_behind and laps_since_pit > 10 and near_window:
            if can_overcut(driver, car_behind, track, race_state):
                best_lap = best_overcut_lap(driver, car_behind, track, race_state)
                if best_lap > 1 and laps_since_pit < 25:
                    print(f"{driver.code} is staying out for an overcut! on lap {race_state.current_lap}")
                    continue
    
        # Car in front is pitting -> Mirror only if we aren't significantly faster and we haven't completed stops
        if not has_completed_required_stops and car_ahead and car_ahead.pit_stops > driver.pit_stops and near_window and laps_since_pit > 10:
            delta = pace_delta(driver, car_ahead)
            if delta < 0.5 and random.random() < 0.55:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )
                serve_penalty(driver)
                print(f"{driver.code} is mirroring a pit stop! on lap {race_state.current_lap}")
                continue

        # Free stop under safety car
        if race_state.safety_car and driver.tire_distance > tire_data["max_distance"] * 0.8:
            if random.random() < 0.75:
                perform_stop(
                    driver,
                    track,
                    pick_compound(laps_remaining, track, race_state),
                    race_state
                )
                serve_penalty(driver)
                print(f"{driver.code} is taking a free stop under the safety car! on lap {race_state.current_lap}")
                continue

        # Forcing pit stop for those who havent stopped yet and we are well past the final pit window
        laps_rem = total_laps - current_lap
        missing_stops = pit_stop_amount - driver.pit_stops
        latest_pit_window = max(pit_window) if pit_window else total_laps

        # Only force pit if actually missing required stops AND far past window AND critical laps remaining
        if missing_stops > 0 and current_lap > latest_pit_window + 5 and laps_rem < missing_stops * 5:
            perform_stop(
                driver,
                track,
                pick_compound(laps_remaining, track, race_state),
                race_state
            )
            serve_penalty(driver)
            print(f"{driver.code} is being forced to pit! on lap {race_state.current_lap}")
            continue

def pick_compound(laps_left, track, race_state):
    """Method to pick the compound to use for the race after pitting"""

    stress = track["tire_stress"]
    distance_left  = laps_left * track["length_km"]

    if race_state.track_wetness >= 0.6:
        return "WET"
    elif race_state.track_wetness < 0.6 and race_state.track_wetness >= 0.2:
        return "INTERMEDIATE"

    if distance_left <= TIRES["SOFT"]["max_distance"]:
        return "SOFT"
    elif distance_left <= TIRES["MEDIUM"]["max_distance"]:
        return random.choice(["SOFT", "MEDIUM"])
    else:
        return "HARD" if stress > 0.75 else random.choice(["MEDIUM", "HARD"])

def update_weather(race_state):
    """Update the track wetness and weather state for the current lap, simulating changing 
        weather conditions"""
    
    race_state.track_wetness = update_track_wetness(race_state.track_wetness)
    race_state.weather_state = weather_state(race_state.track_wetness, race_state)


def record_history(history, race_state, drivers):
    """Record the current state of the race for each driver, including lap times, positions, 
        tire compounds, and pit stops, to allow for later analysis and visualization. This 
        function updates the history dictionary with the relevant data for each driver at"""
    
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

def simulate_race(drivers, track, race_state, history=None):
    """Simulate an entire race, iterating through each lap and updating driver states, positions"""

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
    
    # Add any time penalties to final times at the end of the race
    for driver in drivers:
        serve_penalty(driver)
