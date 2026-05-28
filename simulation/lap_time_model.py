import random

from simulation.degredation_model import (
    degradation_penalty,
    tire_performance_curve,
    weather_deg_modifier,
)

from data.weather import weather_pace_penalty

def calc_lap_time(driver, track, race_state):
    lap_time = track["base_lap_time"]
    lap_time += driver.team.base_pace
    lap_time += tire_performance_curve(driver)
    lap_time += weather_pace_penalty(race_state.track_wetness)
    lap_time *= weather_deg_modifier(race_state.track_wetness)
    lap_time += driver.fuel_percentage * .03
    lap_time += random.uniform(-.15, .15)

    return lap_time




