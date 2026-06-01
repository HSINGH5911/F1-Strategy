def plot_tire_wear(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

    laps = history["laps"]

    for driver, wear in (
        history["tire_distance"].items()
    ):

        plt.plot(
            laps,
            wear,
            label=driver
        )

    plt.xlabel("Lap")
    plt.ylabel("Tyre Distance (km)")
    plt.title("Tyre Wear")

    plt.legend()
    plt.grid()

    plt.show()

def plot_degradation(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

    for driver in history["lap_times"]:

        plt.scatter(
            history["tire_distance"][driver],
            history["lap_times"][driver],
            label=driver
        )

    plt.xlabel("Tyre Distance")
    plt.ylabel("Lap Time")

    plt.title(
        "Tyre Degradation Analysis"
    )

    plt.legend()

    plt.show()