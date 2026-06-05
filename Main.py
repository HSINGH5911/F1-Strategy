from models.driver import Driver
from models.team import Team
from models.race_state import RaceState
from config.Tracks import TRACKS
from simulation.race_simulator import simulate_race
from ui.strategy_gui import main as launch_strategy_gui
from ui.dashboard import (
    print_standings,
    print_tires,
    print_strategy,
    plot_positions,
    plot_lap_times,
)

def create_grid():

    red_bull = Team(
        "Red Bull",
        base_pace=-0.6,
        pit_stop_avg=2.1
    )

    ferrari = Team(
        "Ferrari",
        base_pace=-0.3,
        pit_stop_avg=2.3
    )

    mclaren = Team(
        "McLaren",
        base_pace=-0.4,
        pit_stop_avg=2.2
    )

    drivers = [

        Driver("VER", red_bull),
        Driver("TSU", red_bull),

        Driver("LEC", ferrari),
        Driver("HAM", ferrari),

        Driver("NOR", mclaren),
        Driver("PIA", mclaren)
    ]

    for pos, driver in enumerate(
        drivers,
        start=1
    ):
        driver.position = pos

    return drivers


def run_console_simulation():

    track = TRACKS["Italy"]

    race_state = RaceState()

    drivers = create_grid()

    history = {
        "laps": [],
        "positions": {},
        "lap_times": {},
        "tire_distance": {},
        "compounds": {},
        "gaps": {}
    }

    simulate_race(
        drivers,
        track,
        race_state,
        history
    )

    print_standings(drivers)

    print_tires(drivers)

    print_strategy(drivers)

    plot_positions(history)

    plot_lap_times(history)


def main():
    launch_strategy_gui()


if __name__ == "__main__":
    main()
