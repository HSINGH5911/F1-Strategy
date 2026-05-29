import random

def pit_stop_time(driver):
    base_time = driver.team.pit_stop_avg

    variation = random.uniform(-.3, .3)

    return base_time + variation

def total_pit_loss(driver, track, race_state):
    return pit_delta(track, race_state) + pit_stop_time(driver) + pit_error()

def change_compound(driver, new_compound):
    driver.current_compound = new_compound
    driver.tire_distance = 0
    driver.pit_stops += 1

def perform_stop(driver, track, new_compound):
    driver.race_time += total_pit_loss(driver, track)
    change_compound(driver, new_compound)

def pit_error():
    if random.random() < .01:
        return random.uniform(3, 10)
    return 0

def pit_delta(track, race_state):
    delta = track["pit_delta"]
    if race_state.safety_car:
        delta *= .6

    return delta

