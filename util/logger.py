def race_log(
    lap,
    message
):

    print(
        f"[LAP {lap}] {message}"
    )

def overtake_log(
    attacker,
    defender
):

    print(
        f"{attacker.code} passed {defender.code}"
    )

def safety_car_log():

    print(
        "SAFETY CAR DEPLOYED"
    )