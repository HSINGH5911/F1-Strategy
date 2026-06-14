import random

from simulation.degredation_model import (
    get_tire_data,
    degradation_penalty,
    tire_performance_curve,
    weather_deg_modifier,
)

from data.random_weather import weather_pace_penalty

def calc_lap_time(driver, track, race_state):
    tire_data = get_tire_data(driver)

    lap_time = track["base_lap_time"]
    lap_time += driver.team.base_pace
    lap_time += tire_data["base_pace"]
    lap_time -= (driver.skill - 0.9) * 2.0

    variance = 0.3 * (1.0 - driver.consistency)
    lap_time += random.uniform(-variance, variance)

    if driver.position > 10:
        # Racecraft helps reduce backmarker penalty, but it shouldn't eliminate it
        # Cap the bonus so even top drivers lose some time when far behind
        racecraft_bonus = min(0.5, (driver.racecraft - 0.75) * 2.0)
        lap_time += max(0.15, (1.0 - driver.racecraft) * 1.5 - racecraft_bonus)

    lap_time += tire_performance_curve(driver)
    lap_time += weather_pace_penalty(race_state.track_wetness)
    lap_time *= weather_deg_modifier(race_state.track_wetness)
    lap_time += driver.fuel_percentage * .03

    if random.random() < driver.aggression * .03:
        lap_time += random.uniform(0.5, 4.0)

    if race_state.safety_car:
        lap_time += 40

    cliff_lap = tire_data["max_distance"] * random.uniform(0.8, 0.95)
    if driver.tire_distance > cliff_lap:
        lap_time += (driver.tire_distance - cliff_lap) * .25

    if driver.tire_distance < 3:
        lap_time += (3 - driver.tire_distance) * 0.4

    if driver.position > 10:
        cars_ahead = driver.position - 1
        lap_time += cars_ahead * .02

    return lap_time




