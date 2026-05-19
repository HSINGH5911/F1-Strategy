import fastf1

def get_driver_laps(session, driver):
    return session.laps.pick_drivers(driver)

def get_fastest_lap(session, driver):
    return session.laps.pick_drivers(driver).pick_fastest()

def get_telemetry(lap):
    tel = lap.get_car_data().add_distance()
    return tel


