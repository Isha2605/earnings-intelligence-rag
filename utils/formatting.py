import statistics


def format_millions(value):
    return f"${value / 1000:.1f}B"


def format_delta(current, previous):
    if not previous:
        return "N/A"
    pct = ((current - previous) / previous) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def format_abs_delta(current, previous):
    diff = (current - previous) / 1000
    sign = "+" if diff >= 0 else ""
    return f"{sign}${abs(diff):.1f}B"


def flag_anomaly(values_list):
    if len(values_list) < 2:
        return False
    mean = statistics.mean(values_list)
    try:
        std = statistics.stdev(values_list)
    except statistics.StatisticsError:
        return False
    if std == 0:
        return False
    return abs(values_list[-1] - mean) > 1.0 * std
