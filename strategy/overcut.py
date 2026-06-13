from simulation.lap_time_model import calc_lap_time

def estimate_future_pace(driver, track, race_state, laps):
    """Estimates the future pace of the car"""

    total = 0

    for _ in range(laps):
        total += calc_lap_time(driver, track, race_state)

    return total

def overcut_gain(driver, rival, track, race_state, extra_laps):
    """Time stood to gain by overcutting"""
    driver_time = estimate_future_pace(driver, track, race_state, extra_laps)
    rival_time = estimate_future_pace(rival, track, race_state, extra_laps)

    return rival_time - driver_time

def can_overcut(driver, rival, track, race_state):
    """Should driver overcut"""
    gain = overcut_gain(driver, rival, track, race_state, 3)

    return gain > 1

def best_overcut_lap(driver, rival, track, race_state):
    """Finds best lap to overcut"""
    best_gain = float('-inf')
    best_lap = 0

    for laps in range(1, 6):
        gain = overcut_gain(driver, rival, track, race_state, laps)
        if gain > best_gain:
            best_gain = gain
            best_lap = laps

    return best_lap


