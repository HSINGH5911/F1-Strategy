import matplotlib.pyplot as plt

from ui.widgets import standings_table, tire_table, strategy_table

def print_standings(drivers):

    print("\n=== STANDINGS ===")
    print(
        standings_table(drivers)
        .to_string(index=False)
    )


def print_tires(drivers):

    print("\n=== TYRES ===")
    print(
        tire_table(drivers)
        .to_string(index=False)
    )


def print_strategy(drivers):

    print("\n=== STRATEGY ===")
    print(
        strategy_table(drivers)
        .to_string(index=False)
    )


def plot_positions(history):

    plt.figure(
        figsize=(10, 6)
    )

    laps = history["laps"]

    for driver, positions in (
        history["positions"].items()
    ):

        plt.plot(
            laps,
            positions,
            label=driver
        )

    plt.gca().invert_yaxis()

    plt.xlabel("Lap")
    plt.ylabel("Position")
    plt.title("Race Positions")
    plt.legend()

    plt.show()


def plot_lap_times(history):

    plt.figure(
        figsize=(10, 6)
    )

    laps = history["laps"]

    for driver, lap_times in (
        history["lap_times"].items()
    ):

        plt.plot(
            laps,
            lap_times,
            label=driver
        )

    plt.xlabel("Lap")
    plt.ylabel("Lap Time (s)")
    plt.title("Lap Time Evolution")
    plt.legend()

    plt.show()


def plot_tire_stints(history):

    plt.figure(
        figsize=(10, 6)
    )

    for i, (
        driver,
        stints
    ) in enumerate(
        history["stints"].items()
    ):

        start = 0

        for compound, laps in stints:

            plt.barh(
                driver,
                laps,
                left=start,
                label=compound
            )

            start += laps

    plt.title(
        "Tire Strategy"
    )

    plt.xlabel("Lap")
    plt.ylabel("Driver")

    plt.show()
