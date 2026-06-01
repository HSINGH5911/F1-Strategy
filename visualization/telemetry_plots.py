def plot_lap_times(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

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
    plt.grid()

    plt.show()

def plot_pace_delta(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))

    laps = history["laps"]

    leader = min(
        history["lap_times"],
        key=lambda d:
        sum(history["lap_times"][d])
    )

    leader_times = (
        history["lap_times"][leader]
    )

    for driver, lap_times in (
        history["lap_times"].items()
    ):

        delta = [
            lap_times[i]
            - leader_times[i]
            for i in range(
                len(lap_times)
            )
        ]

        plt.plot(
            laps,
            delta,
            label=driver
        )

    plt.xlabel("Lap")
    plt.ylabel("Delta (s)")
    plt.title("Pace Delta")

    plt.legend()
    plt.grid()

    plt.show()