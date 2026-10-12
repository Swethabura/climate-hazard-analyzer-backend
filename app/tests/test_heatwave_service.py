# from app.services.heatwave_service import detect_heatwaves


# def test_detects_three_consecutive_hot_days():
#     observations = [
#         {"date": "2020-01-01", "temperature_max_c": 38.0},
#         {"date": "2020-01-02", "temperature_max_c": 39.0},
#         {"date": "2020-01-03", "temperature_max_c": 40.0},
#         {"date": "2020-01-04", "temperature_max_c": 35.0},
#         {"date": "2020-01-05", "temperature_max_c": 39.0},
#         {"date": "2020-01-06", "temperature_max_c": 40.0},
#     ]

#     events = detect_heatwaves(observations, threshold=37.0)

#     assert len(events) == 1
#     assert events[0]["start_date"] == "2020-01-01"
#     assert events[0]["end_date"] == "2020-01-03"
#     assert events[0]["duration_days"] == 3
#     assert events[0]["peak_temperature_c"] == 40.0


import pytest
from datetime import date

from app.core.exceptions import AppError
from app.services.weather_service import validate_provider_date_coverage


def test_provider_date_coverage_accepts_complete_range():
    validate_provider_date_coverage(
        ["2025-01-01", "2025-01-02", "2025-01-03"],
        date(2025, 1, 1),
        date(2025, 1, 3),
    )


def test_provider_date_coverage_rejects_missing_dates():
    with pytest.raises(AppError) as exc_info:
        validate_provider_date_coverage(
            ["2025-01-01", "2025-01-03"],
            date(2025, 1, 1),
            date(2025, 1, 3),
        )

    assert exc_info.value.error_code == "INVALID_WEATHER_RESPONSE"


def test_provider_date_coverage_rejects_duplicate_dates():
    with pytest.raises(AppError):
        validate_provider_date_coverage(
            ["2025-01-01", "2025-01-02", "2025-01-02"],
            date(2025, 1, 1),
            date(2025, 1, 2),
        )
