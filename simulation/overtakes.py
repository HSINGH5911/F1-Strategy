import random


def pace_delta(attacker, defender):
    return defender.last_lap_time - attacker.last_lap_time

def overtake_probability(attacker, defender):
    delta = pace_delta(attacker, defender)

    return max(0.01, min(delta * 0.5, 0.9))


def drs_bonus(gap):
    if gap <= 1:
        return 0.15
    return 0


def overtake_modifier(track):
    return track["overtake_difficulty"]

def attempt_overtake(attacker, defender, gap, track):
    chance = overtake_probability(attacker, defender)
    chance += drs_bonus(gap)
    chance *= overtake_modifier(track)
    chance = min(chance, 0.95)

    return random.random() < chance

def swap_pos(attacker, defender):
    attacker.position, defender.position = (
        defender.position,
        attacker.position
    )