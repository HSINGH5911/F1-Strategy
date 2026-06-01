def clamp(value, minimum, maximum):
    return max(
        minimum,
        min(value, maximum)
    )

def has_drs(gap):
    return gap <= 1

def percentage(part, total):

    if total == 0:
        return 0

    return (
        part / total
    ) * 100

def format_gap(seconds):
    return f"+{seconds:.3f}"

def format_lap_time(seconds):

    mins = int(seconds // 60)

    secs = seconds % 60

    return (
        f"{mins}:{secs:06.3f}"
    )