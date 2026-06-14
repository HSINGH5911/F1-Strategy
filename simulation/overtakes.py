import random

def pace_delta(attacker, defender):
    """Calculate the pace difference between the attacking and defending drivers based on their 
        last lap times. A positive delta indicates the attacker is faster, while a negative 
        delta indicates the defender is faster."""
    
    return defender.last_lap_time - attacker.last_lap_time

def overtake_probability(attacker, defender):
    """Calculate the probability of a successful overtake based on the pace difference between the 
        two drivers. The probability is scaled to be between 0.01 and 0.9, with a higher pace 
        difference increasing the chances of a successful overtake."""
    
    delta = pace_delta(attacker, defender)

    if delta <= 0:
        return 0.01

    return max(0.01, min(delta * 0.04, 0.12))

def drs_bonus(gap):
    """Calculate the DRS bonus for an overtake attempt based on the gap between the attacking and 
        defending drivers. If the gap is less than or equal to 1 second, a DRS bonus of 0.15 
        is applied to the overtake probability."""
    
    if gap <= 1:
        return 0.05
    return 0

def overtake_modifier(track):
    """Calculate a modifier for the overtake probability based on the track's overtaking 
        difficulty. Tracks with higher overtaking difficulty will reduce the chances of a 
        successful overtake, while tracks with lower difficulty will increase the chances."""
    
    difficulty = track.get("overtake_difficulty", track.get("overtaking_difficulty", 0.5))
    return max(0.05, 1 - difficulty)

def attempt_overtake(attacker, defender, gap, track):
    """Determine whether an overtake attempt by the attacking driver on the defending driver is 
        successful. The function calculates the base overtake probability based on the pace 
        difference."""
    
    if attacker.laps_since_last_pit < 2:
        return False
    
    chance = overtake_probability(attacker, defender)
    chance += drs_bonus(gap)
    chance *= overtake_modifier(track)
    chance = min(chance, 0.95)

    return random.random() < chance

def swap_pos(attacker, defender):
    """Swap the positions of the attacking and defending drivers after a successful overtake."""
    
    attacker.position, defender.position = (
        defender.position,
        attacker.position
    )
