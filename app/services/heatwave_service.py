from datetime import date, timedelta

import numpy as np

MIN_HEATWAVE_DAYS = 3


def calculate_threshold(temperatures: list[float]) -> float:
    """Calculate the 95th-percentile temperature threshold."""
    valid_temperatures = [
        temperature for temperature in temperatures if np.isfinite(temperature)
    ]

    if not valid_temperatures:
        raise ValueError("No valid temperatures available")

    return float(np.percentile(valid_temperatures, 95))


def detect_heatwaves(observations: list[dict], threshold: float) -> list[dict]:
    """Find runs of at least three consecutive days above threshold."""
    valid_observations = [
        observation
        for observation in observations
        if observation.get("temperature_max_c") is not None
        and np.isfinite(observation["temperature_max_c"])
    ]

    valid_observations.sort(key=lambda item: item["date"])

    events = []
    current_event = []

    for observation in valid_observations:
        day = date.fromisoformat(observation["date"])
        temperature = observation["temperature_max_c"]

        is_hot = temperature > threshold

        is_consecutive = not current_event or day == date.fromisoformat(
            current_event[-1]["date"]
        ) + timedelta(days=1)

        if is_hot and is_consecutive:
            current_event.append(observation)
        else:
            if len(current_event) >= MIN_HEATWAVE_DAYS:
                events.append(build_event(current_event, threshold))

            current_event = [observation] if is_hot else []

    if len(current_event) >= MIN_HEATWAVE_DAYS:
        events.append(build_event(current_event, threshold))

    return events


def build_event(
    observations: list[dict],
    threshold: float,
) -> dict:
    temperatures = [observation["temperature_max_c"] for observation in observations]

    return {
        "start_date": observations[0]["date"],
        "end_date": observations[-1]["date"],
        "duration_days": len(observations),
        "peak_temperature_c": max(temperatures),
        "mean_temperature_c": round(sum(temperatures) / len(temperatures), 2),
        "mean_excess_above_threshold_c": round(
            sum(temp - threshold for temp in temperatures) / len(temperatures),
            2,
        ),
    }


def calculate_linear_trend(annual: list[dict]) -> dict:
    """Estimate the linear trend in annual heatwave event counts."""
    if len(annual) < 2:
        return {
            "slope_events_per_year": None,
            "direction": "insufficient_data",
            "r_squared": None,
            "period_years": len(annual),
        }

    years = np.array([item["year"] for item in annual], dtype=float)

    counts = np.array([item["event_count"] for item in annual], dtype=float)

    # Fit: predicted_count = slope * year + intercept
    slope, intercept = np.polyfit(years, counts, 1)

    predicted = slope * years + intercept

    residual_sum = np.sum((counts - predicted) ** 2)
    total_sum = np.sum((counts - np.mean(counts)) ** 2)

    r_squared = 1 - residual_sum / total_sum if total_sum > 0 else None

    if np.isclose(slope, 0, atol=1e-9):
        direction = "no_change"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    return {
        "slope_events_per_year": round(float(slope), 3),
        "direction": direction,
        "r_squared": (round(float(r_squared), 3) if r_squared is not None else None),
        "period_years": len(annual),
    }
