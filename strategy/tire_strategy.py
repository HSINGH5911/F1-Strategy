from config.Tires import TIRES

def choose_compound(driver, track, race_state):
    wet = race_state.track_wetness

    if wet > .6:
        return "WET"

    if wet > .2:
        return "INTERMEDIATE"

    return "MEDIUM"

def estimate_stint_length(compound, track):
    tire = TIRES[compound]

    return tire["max_distance"] / track["length_km"]

def estimate_tire_life(driver):
    tire = TIRES[driver.current_compound]

    return tire["max_distance"] - driver.tire_distance

def tire_score(compound, track, race_state):
    tire = TIRES[compound]
    score = 0

    score -= tire["base_pace"]
    score -= tire["wear_rate"] * track["tire_stress"]

    return score

def best_compound(track, race_state):
    compounds = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]

    return max(compounds, key=lambda compound: tire_score(compound, track, race_state))
