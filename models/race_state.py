class RaceState:

    def __init__(self):

        self.current_lap = 1

        self.track_wetness = 0.0

        self.weather_state = "DRY"

        self.safety_car = False

        self.race_order = []

        self.session_status = "GREEN"