import random

def update_weather(current_wetness):
    rain_change = random.uniform(-0.05, 0.05)

    current_wetness += rain_change

    return max(0, min(current_wetness, 1))


def tire_weather_multiplier(compound, wetness):
    match compound:

        case "SOFT":
            return 1 + (wetness * 8)

        case "INTERMEDIATE":
            return 1 + abs(wetness - 0.5)

        case "WET":
            return 1 + (
                (1 - wetness) * 6
            )

        case _:
            return 1


def weather_pace_penalty(wetness):
    return wetness * 12


def rain_sc_probability(wetness):
    return 0.05 + (
        wetness * 0.35
    )

def dry_track(wetness):
    wetness -= 0.02

    return max(wetness, 0)


def weather_state(wetness, race_state):
    # Use hysteresis to avoid oscillation around thresholds
    # Current state is stored, use different thresholds to exit vs enter a state
    current_state = getattr(race_state, 'weather_state', 'DRY')
    
    if current_state == "DRY":
        # Need wetness > 0.25 to switch to INTERMEDIATE (hysteresis zone 0.2-0.25)
        if wetness >= 0.25:
            race_state.weather_state = "INTERMEDIATE"
            return "INTERMEDIATE"
    elif current_state == "INTERMEDIATE":
        # If wetness gets very low (< 0.15), go back to DRY
        if wetness < 0.15:
            race_state.weather_state = "DRY"
            return "DRY"
        # If wetness gets high (> 0.55), go to WET (hysteresis zone 0.6-0.55)
        elif wetness > 0.55:
            race_state.weather_state = "WET"
            return "WET"
    elif current_state == "WET":
        # Need wetness < 0.55 to switch back to INTERMEDIATE (hysteresis zone 0.55-0.6)
        if wetness < 0.55:
            race_state.weather_state = "INTERMEDIATE"
            return "INTERMEDIATE"
    
    # Default: return current state
    return current_state