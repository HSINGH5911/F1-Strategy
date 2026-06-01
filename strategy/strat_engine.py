from config.Tires import TIRES
from simulation.lap_time_model import calc_lap_time
from strategy.tire_strategy import choose_compound

def should_pit(driver, track, race_state):
    tire_data = TIRES[driver.current_compound]

    return driver.tire_distance >= tire_data["max_distance"]

def project_stint_time(driver, track, race_state, laps):
    total = 0
    temp_distance = driver.tire_distance

    for _ in range(laps):
        total += calc_lap_time(driver, track, race_state)
        temp_distance += track["length_km"]

    return total

def evaluate_stay_out(driver, track, race_state):
    return project_stint_time(driver, track, race_state, 5)

def evaluate_pit(driver, track, race_state):
    compound = choose_compound(driver, track, race_state)

    tire_data = TIRES[compound]

    projected = track["pit_delta"] + project_stint_time(driver, track, race_state, 5)

    return projected

def find_best_strategy(driver, track, race_state):
    stay_out = evaluate_stay_out(driver, track, race_state)
    pit = evaluate_pit(driver, track, race_state)

    if pit < stay_out:
        return "PIT"
    return "STAY_OUT"

def safety_car_reaction(driver, track, race_state):
    if not race_state.safety_car:
        return False

    tire_data = TIRES[driver.current_compound]

    wear_ratio = driver.tire_distance / tire_data["max_distance"]

    return wear_ratio > .5
