from pathlib import Path

import fastf1

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
CACHE_DIR.mkdir(exist_ok=True)

fastf1.Cache.enable_cache(str(CACHE_DIR))

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
