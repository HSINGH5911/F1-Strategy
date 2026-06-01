def plot_strategy(history):

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 8))

    drivers = list(
        history["compounds"].keys()
    )

    for i, driver in enumerate(drivers):

        compounds = (
            history["compounds"][driver]
        )

        start = 0

        current = compounds[0]
        length = 0

        for compound in compounds:

            if compound == current:
                length += 1

            else:

                plt.barh(
                    driver,
                    length,
                    left=start
                )

                start += length

                current = compound

                length = 1

        plt.barh(
            driver,
            length,
            left=start
        )

    plt.xlabel("Lap")
    plt.title("Tire Strategy")

    plt.show()