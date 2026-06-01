def fresh_tire_gain(driver, new_compound):
    current_wear = driver.tire_distance / 100

    return current_wear * 1.5

def undercut_gain(driver, rival, track, race_state, laps_before_rival):
    gain = 0
    gain += fresh_tire_gain(driver, "MEDIUM") * laps_before_rival

    return gain

def can_undercut(driver, rival, track, race_state, laps_before_rival):
    gain = undercut_gain(driver, rival, track, race_state, laps_before_rival)
    return gain > 1

def best_undercut_window(driver, rival, track, race_state):
    best_gain = float('-inf')
    best_lap = race_state.current_lap

    for offset in range(1, 6):
        gain = undercut_gain(driver, rival, track, race_state, offset)

        if gain > best_gain:
            best_gain = gain
            best_lap = offset

    return best_gain
