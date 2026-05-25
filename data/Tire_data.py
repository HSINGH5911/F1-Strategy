from lap_data import get_compound_laps

def degradation_curve(laps):
    return laps.groupby("TyreLife")["LapTime"].mean()

def average_compound_pace(laps, compound):
    compound_laps = get_compound_laps(laps, compound)

    return compound_laps["LapTime"].mean()

def average_tire_life(laps, compound):
    compound_laps = get_compound_laps(laps, compound)
    return compound_laps["TyreLife"].mean()

def tire_wear_rate(laps):
    deg = degradation_curve(laps)

    first = deg.iloc[0]
    last = deg.iloc[-1]

    laps_used = len(deg)

    return (last - first) / laps_used

def get_stint_length(laps):
    return laps.groupby("Stint")["LapNumber"].count()

def pace_by_tire(laps):
    return laps.groupby("TyreLife")["LapTime"].mean()

def compare_compounds(laps):
    return laps.groupby("Compound")["LapTime"].mean()

def compund_delta(laps, c1, c2):
    pace1 = average_compound_pace(laps, c1)
    pace2 = average_compound_pace(laps, c2)

    return pace1 - pace2

