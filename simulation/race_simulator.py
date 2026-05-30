from lap_time_model import *
from degredation_model import *
from overtakes import *
from pit_stop_model import *
from data.weather import update_weather as update_track_wetness, weather_state

def simulate_lap(drivers, track, race_state):
    for driver in drivers:
        lap_time = calc_lap_time(driver, track, race_state)

        driver.last_lap_time = lap_time
        driver.race_time += lap_time

        update_tire_distance(driver, track)

def update_positions(drivers):
    drivers.sort(key=lambda d: d.race_time)

    for pos, driver in enumerate(drivers, start=1):
        driver.position = pos

def process_overtakes(drivers, track):
    for i in range(1, len(drivers)):

        attacker = drivers[i]
        defender = drivers[i - 1]

        gap = attacker.race_time - defender.race_time

        if attempt_overtake(attacker, defender, gap, track):
            swap_pos(attacker, defender)

def process_pit_stops(drivers, track, race_state):
    for driver in drivers:
        if driver.tire_distance > 120:
            perform_stop(driver, track, "MEDIUM")

def update_weather(race_state):
    race_state.track_wetness = update_track_wetness(race_state.track_wetness)
    race_state.weather_state = weather_state(race_state.track_wetness)


def simulate_race(drivers, track, race_state):
    while race_state.current_lap <= track["laps"]:
        simulate_lap(drivers, track, race_state)

        update_positions(drivers)

        process_overtakes(drivers, track)

        process_pit_stops(drivers, track, race_state)

        update_weather(race_state)

        race_state.current_lap += 1