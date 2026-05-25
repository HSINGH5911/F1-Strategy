import fastf1

fastf1.Cache.enable_cache("cache")

def load_session(year, gp, session_type):
    session = fastf1.get_session(
        year,
        gp,
        session_type
    )
    session.load()

    return session

def load_race(year, gp):
    return load_session(year, gp, "R")


def load_qualifying(year, gp):
    return load_session(year, gp, "Q")


def load_sprint(year, gp):
    return load_session(year, gp, "S")


def get_event_name(session):
    return session.event["EventName"]


def get_track_name(session):
    return session.event["Location"]