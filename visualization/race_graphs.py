def plot_positions(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

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
    plt.title("Race Position History")

    plt.legend()
    plt.grid()

    plt.show()

def plot_gaps(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

    laps = history["laps"]

    for driver, gaps in (
        history["gaps"].items()
    ):

        plt.plot(
            laps,
            gaps,
            label=driver
        )

    plt.xlabel("Lap")
    plt.ylabel("Gap (s)")
    plt.title("Gap To Leader")

    plt.legend()
    plt.grid()

    plt.show()

