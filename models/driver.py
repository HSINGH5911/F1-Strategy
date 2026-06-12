class Driver:
    def __init__(
            self,
            code,
            team
    ):
        self.code = code
        self.team = team
        self.position = 0
        self.race_time = 0.0
        self.gap_to_lead = 0.0
        self.current_compound = "MEDIUM"
        self.tire_distance = 0.0
        self.pit_stops = 0
        self.fuel_percentage = 100.0
        self.dnf = False
        self.fastest_lap = None
        self.last_lap_time = None
        self.laps_since_last_pit = 0
        self.penalties = 0
        self.penalty_time = []

    def pitted(self):
        self.pit_stops += 1

    def gained_pos(self):
        self.position -= 1

    def dropped_pos(self):
        self.position += 1
