import pandas as pd

def standings_table(drivers):
    data = []

    for driver in sorted(drivers,key=lambda d: d.position):
        data.append({
            "Position": driver.position,
            "Driver": driver.code,
            "Team": driver.team.name,
            "Race Time": round(driver.race_time, 3),
            "Stops": driver.pit_stops,
            "Tyre": driver.current_compound
        })

    return pd.DataFrame(data)


def tire_table(drivers):
    data = []

    for driver in drivers:

        data.append({
            "Driver": driver.code,
            "Compound": driver.current_compound,
            "Distance": round(
                driver.tire_distance,
                1
            )
        })

    return pd.DataFrame(data)


def strategy_table(drivers):
    data = []

    for driver in drivers:

        data.append({
            "Driver": driver.code,
            "Pit Stops": driver.pit_stops,
            "Current Tyre": driver.current_compound
        })

    return pd.DataFrame(data)