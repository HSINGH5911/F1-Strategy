def get_clean_laps(laps):
    return laps[
        (laps["IsAccurate"] == True)
        & (laps["PitOutTime"].isna())
        & (laps["PitInTime"].isna())
    ]


def get_driver_laps(session, driver):
    return session.laps.pick_drivers(driver)


def get_fastest_lap(session, driver):
    laps = get_driver_laps(session, driver)
    return laps.pick_fastest()


def average_lap_time(laps):
    return laps["LapTime"].mean()


def get_stints(laps):
    return laps.groupby("Stint")


def get_compound_laps(laps, compound):
    return laps[laps["Compound"] == compound]


def get_tyre_life(laps):
    return laps["TyreLife"]


def lap_delta(lap1, lap2):
    return lap1["LapTime"] - lap2["LapTime"]


def get_position_changes(laps):
    return laps[["LapNumber", "Position"]]


def get_sc_laps(laps):
    return laps[
        laps["TrackStatus"] == "4"
    ]