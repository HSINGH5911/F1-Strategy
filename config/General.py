# =========================
# SIMULATION SETTINGS
# =========================

SIMULATION_RUNS = 1000

RANDOM_SEED = 42

ENABLE_DRS = True
ENABLE_SAFETY_CAR = True
ENABLE_WEATHER = False

DEBUG_MODE = False


# =========================
# RACE SETTINGS
# =========================

DEFAULT_RACE_DISTANCE_KM = 305
MONACO_RACE_DISTANCE_KM = 260

FORMATION_LAP = True

MAX_LAPS_UNDER_SC = 6


# =========================
# DRS SETTINGS
# =========================

DRS_GAP = 1.0

DRS_TIME_GAIN = 0.35


# =========================
# OVERTAKE SETTINGS
# =========================

OVERTAKE_THRESHOLD = 0.7

DIRTY_AIR_PENALTY = 0.25

MAX_OVERTAKES_PER_LAP = 4


# =========================
# RANDOMNESS SETTINGS
# =========================

PACE_RANDOMNESS = 0.15

PIT_STOP_VARIATION = 0.3

WEATHER_VARIATION = 0.2


# =========================
# SAFETY CAR SETTINGS
# =========================

BASE_SAFETY_CAR_DURATION = (2, 6)

VSC_PROBABILITY = 0.18


# =========================
# WEATHER SETTINGS
# =========================

TRACK_EVOLUTION_RATE = 0.015

RAIN_INTENSITY_CHANGE = 0.05


# =========================
# VISUALIZATION SETTINGS
# =========================

SHOW_PLOTS = True

SAVE_PLOTS = False

LIVE_VISUALIZATION = False