import random


def update_weather(current_wetness):
    rain_change = random.uniform(-0.05, 0.08)

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


def weather_state(wetness):
    if wetness < 0.2:
        return "DRY"

    if wetness < 0.6:
        return "INTERMEDIATE"

    return "WET"