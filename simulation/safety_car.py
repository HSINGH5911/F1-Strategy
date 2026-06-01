import random

def safety_car_prob(race_state):
    base = .01
    base += race_state.track_wetness * .05

    return base

def trigger_safety_car(race_state):
    race_state.safety_car = True
    race_state.sc_laps_remaining = 0

def check_for_safety_car(race_state):
    if race_state.safety_car:
        return

    probability =  safety_car_prob(race_state)

    if random.random() < probability:
        trigger_safety_car(race_state)

def update_safety_car(race_state):
    if not race_state.safety_car:
        return

    race_state.sc_laps_remaining -= 1

    if race_state.sc_laps_remaining == 0:
        race_state.safety_car = False

