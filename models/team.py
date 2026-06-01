class Team:
    def __init__(
            self,
            name,
            base_pace,
            pit_stop_avg,
            reliability=1.0,
            tire_management=1.0
    ):
        self.name = name
        self.base_pace = base_pace
        self.reliability = reliability
        self.tire_management = tire_management
        self.pit_stop_avg = pit_stop_avg

