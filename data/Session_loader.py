import fastf1

def get_session(year, venue, identifier):
    session = fastf1.get_session(year, venue, identifier)
    session.load()
    return session

def get_laps(session):
    return session.laps

def get_drivers(session):
    drivers = session.drivers
    return [session.get_driver(driver)["Abbreviation"] for driver in drivers]
