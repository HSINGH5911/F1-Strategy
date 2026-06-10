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
    lap_time += tire_performance_curve(driver)
    lap_time += weather_pace_penalty(race_state.track_wetness)
    lap_time *= weather_deg_modifier(race_state.track_wetness)
    lap_time += driver.fuel_percentage * .03
    lap_time += random.uniform(-.15, .15)

    if random.random() < driver.aggression * .03:
        lap_time += random.uniform(0.5, 4.0)

    if race_state.safety_car:
        lap_time += 40

    cliff_lap = tire_data["max_distance"] * random.uniform(0.8, 0.95)
    if driver.tire_distance > cliff_lap:
        lap_time += (driver.tire_distance - cliff_lap) * .25

    # Warmup penalty
    if driver.tire_distance < 3:
        warmup_penalty = (3 - driver.tire_distance) * 0.4
        lap_time += warmup_penalty

    return lap_time




