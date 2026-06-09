from dataclasses import dataclass
from itertools import product
import math

from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
from config.Tires import TIRES


DRY_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
WET_COMPOUNDS = ("INTERMEDIATE", "WET")


@dataclass(frozen=True)
class Stint:
    compound: str
    start_lap: int
    end_lap: int
    laps: int


@dataclass(frozen=True)
class StrategyResult:
    rank: int
    total_time: float
    gap_to_best: float
    stops: int
    compounds: tuple[str, ...]
    pit_laps: tuple[int, ...]
    stints: tuple[Stint, ...]
    lap_times: tuple[float, ...]
    pit_loss: float
    validity: str

    @property
    def label(self):
        compounds = "-".join(self.compounds)
        pits = ", ".join(str(lap) for lap in self.pit_laps) or "none"
        return f"{compounds} | pit laps: {pits}"


def race_laps(track_name, track, override_laps=None):
    if override_laps:
        return max(1, int(override_laps))

    race_distance = (
        MONACO_RACE_DISTANCE_KM
        if track_name == "Monaco"
        else DEFAULT_RACE_DISTANCE_KM
    )

    return track.get("laps", math.ceil(race_distance / track["length_km"]))


def available_compounds(wetness):
    if wetness >= 0.6:
        return WET_COMPOUNDS

    if wetness >= 0.2:
        return ("MEDIUM", "HARD", "INTERMEDIATE")

    return DRY_COMPOUNDS


def recommended_starting_compound(wetness):
    if wetness >= 0.6:
        return "WET"

    if wetness >= 0.2:
        return "INTERMEDIATE"

    return "MEDIUM"


def weather_penalty(compound, wetness):
    if wetness < 0.2:
        return 0.0 if compound in DRY_COMPOUNDS else 7.0

    if wetness < 0.6:
        if compound == "INTERMEDIATE":
            return 0.0
        if compound == "WET":
            return 3.0
        return 6.0 + wetness * 8.0

    if compound == "WET":
        return 0.0
    if compound == "INTERMEDIATE":
        return 3.5 + wetness * 3.0
    return 14.0 + wetness * 12.0


def tyre_degradation(compound, stint_distance, track):
    tire = TIRES[compound]
    wear_ratio = stint_distance / tire["max_distance"]
    stress = track["tire_stress"] * track.get("abrasion", 1.0)
    return (wear_ratio ** 2) * 4.5 * stress


def lap_time(track, compound, stint_distance, fuel_percent, team_pace, wetness):
    tire = TIRES[compound]
    time = track["base_lap_time"]
    time += team_pace
    time += tire["base_pace"]
    time += tyre_degradation(compound, stint_distance, track)
    time += weather_penalty(compound, wetness)
    time += fuel_percent * track.get("fuel_sensitivity", 0.035)
    return time


def pit_loss(track, pit_stop_avg):
    return track["pit_delta"] + pit_stop_avg


def build_stints(compounds, pit_laps, total_laps):
    starts = (1, *(lap + 1 for lap in pit_laps))
    ends = (*pit_laps, total_laps)

    return tuple(
        Stint(compound, start, end, end - start + 1)
        for compound, start, end in zip(compounds, starts, ends)
    )


def is_plan_valid(stints, track):
    for stint in stints:
        distance = stint.laps * track["length_km"]
        max_distance = TIRES[stint.compound]["max_distance"]

        if distance > max_distance * 1.05:
            return False

    return True


def evaluate_plan(track, total_laps, compounds, pit_laps, team_pace, pit_stop_avg, wetness):
    stints = build_stints(compounds, pit_laps, total_laps)
    validity = "OK" if is_plan_valid(stints, track) else "Over tyre life"
    total = 0.0
    lap_times = []

    stint_index = 0
    stint_distance = 0.0

    for lap in range(1, total_laps + 1):
        stint = stints[stint_index]
        fuel_percent = max(0.0, 100.0 - ((lap - 1) / total_laps) * 100.0)
        current_lap = lap_time(
            track,
            stint.compound,
            stint_distance,
            fuel_percent,
            team_pace,
            wetness,
        )

        if lap in pit_laps:
            current_lap += pit_loss(track, pit_stop_avg)

        lap_times.append(current_lap)
        total += current_lap
        stint_distance += track["length_km"]

        if lap in pit_laps:
            stint_index += 1
            stint_distance = 0.0

    return StrategyResult(
        rank=0,
        total_time=total,
        gap_to_best=0.0,
        stops=len(pit_laps),
        compounds=tuple(compounds),
        pit_laps=tuple(pit_laps),
        stints=stints,
        lap_times=tuple(lap_times),
        pit_loss=pit_loss(track, pit_stop_avg) * len(pit_laps),
        validity=validity,
    )


def one_stop_windows(total_laps):
    start = max(8, int(total_laps * 0.25))
    end = min(total_laps - 8, int(total_laps * 0.75))
    step = max(1, total_laps // 14)
    return range(start, end + 1, step)


def two_stop_windows(total_laps):
    first_start = max(6, int(total_laps * 0.18))
    first_end = max(first_start, int(total_laps * 0.42))
    second_start = min(total_laps - 10, int(total_laps * 0.48))
    second_end = min(total_laps - 6, int(total_laps * 0.78))
    step = max(1, total_laps // 16)

    for first in range(first_start, first_end + 1, step):
        for second in range(max(first + 5, second_start), second_end + 1, step):
            yield first, second


def candidate_plans(total_laps, starting_compound, wetness, max_stops):
    compounds = available_compounds(wetness)
    candidates = []

    candidates.append(((starting_compound,), ()))

    if max_stops >= 1:
        for next_compound, pit_lap in product(compounds, one_stop_windows(total_laps)):
            candidates.append(((starting_compound, next_compound), (pit_lap,)))

    if max_stops >= 2:
        for second, third in product(compounds, repeat=2):
            for pit_laps in two_stop_windows(total_laps):
                candidates.append(((starting_compound, second, third), pit_laps))

    return candidates


def predict_strategies(
    track_name,
    track,
    starting_compound="MEDIUM",
    team_pace=0.0,
    pit_stop_avg=2.4,
    wetness=0.0,
    max_stops=2,
    override_laps=None,
    limit=12,
):
    total_laps = race_laps(track_name, track, override_laps)
    results = []

    for compounds, pit_laps in candidate_plans(total_laps, starting_compound, wetness, max_stops):
        result = evaluate_plan(
            track,
            total_laps,
            compounds,
            pit_laps,
            team_pace,
            pit_stop_avg,
            wetness,
        )

        if result.validity == "OK":
            results.append(result)

    if not results:
        for compounds, pit_laps in candidate_plans(total_laps, starting_compound, wetness, max_stops):
            results.append(
                evaluate_plan(
                    track,
                    total_laps,
                    compounds,
                    pit_laps,
                    team_pace,
                    pit_stop_avg,
                    wetness,
                )
            )

    results.sort(key=lambda result: result.total_time)
    best_time = results[0].total_time
    ranked = []

    for rank, result in enumerate(results[:limit], start=1):
        ranked.append(
            StrategyResult(
                rank=rank,
                total_time=result.total_time,
                gap_to_best=result.total_time - best_time,
                stops=result.stops,
                compounds=result.compounds,
                pit_laps=result.pit_laps,
                stints=result.stints,
                lap_times=result.lap_times,
                pit_loss=result.pit_loss,
                validity=result.validity,
            )
        )

    return ranked
