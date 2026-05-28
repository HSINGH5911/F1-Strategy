from config.Tires import TIRES
from config.Tracks import TRACKS

def get_tire_data(driver):
    return TIRES[driver.current_compound]

def tire_wear(driver, track):
    tire_data = get_tire_data(driver)

    return tire_data['wear_rate'] * track["tire_stress"]

def update_tire_distance(driver, track):
    driver.distance += track["length_km"]

def degradation_penalty(driver):
    tire_data = get_tire_data(driver)
    wear_ratio = (driver.distance / tire_data["max_distance"])

    return wear_ratio * 2

def weather_deg_modifier(wetness):
    return 1 - (wetness * .4)

def tire_performance_curve(driver):
    wear_ratio = degradation_penalty(driver) / 2
    wear_ratio = (wear_ratio ** 2) / 2
    return wear_ratio