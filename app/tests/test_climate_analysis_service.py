# import pytest

# from app.services.heatwave_service import (
#     calculate_linear_trend,
# )


# def test_calculate_linear_trend_increasing():
#     annual = [
#         {"year": 2020, "event_count": 2},
#         {"year": 2021, "event_count": 3},
#         {"year": 2022, "event_count": 4},
#         {"year": 2023, "event_count": 5},
#     ]

#     result = calculate_linear_trend(annual)

#     assert result["slope_events_per_year"] == 1.0
#     assert result["direction"] == "increasing"
#     assert result["r_squared"] == 1.0
#     assert result["period_years"] == 4


# def test_calculate_linear_trend_decreasing():
#     annual = [
#         {"year": 2020, "event_count": 5},
#         {"year": 2021, "event_count": 4},
#         {"year": 2022, "event_count": 3},
#         {"year": 2023, "event_count": 2},
#     ]

#     result = calculate_linear_trend(annual)

#     assert result["slope_events_per_year"] == -1.0
#     assert result["direction"] == "decreasing"
#     assert result["r_squared"] == 1.0


# def test_calculate_linear_trend_constant_counts():
#     annual = [
#         {"year": 2020, "event_count": 3},
#         {"year": 2021, "event_count": 3},
#         {"year": 2022, "event_count": 3},
#     ]

#     result = calculate_linear_trend(annual)

#     assert result["slope_events_per_year"] == 0.0
#     assert result["direction"] == "no_change"
#     assert result["r_squared"] is None


# def test_calculate_linear_trend_insufficient_data():
#     annual = [{"year": 2020, "event_count": 3}]

#     result = calculate_linear_trend(annual)

#     assert result == {
#         "slope_events_per_year": None,
#         "direction": "insufficient_data",
#         "r_squared": None,
#         "period_years": 1,
#     }


# def test_calculate_linear_trend_empty_data():
#     result = calculate_linear_trend([])

#     assert result == {
#         "slope_events_per_year": None,
#         "direction": "insufficient_data",
#         "r_squared": None,
#         "period_years": 0,
#     }


from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.schemas.analysis import HeatwaveAnalysisRequest
from app.services.analysis_service import analyze_heatwaves


@pytest.mark.asyncio
async def test_analyze_heatwaves_returns_trend_and_annual_summary():
    request = HeatwaveAnalysisRequest(
        latitude=17.385,
        longitude=78.4867,
        start_date=date(2020, 1, 1),
        end_date=date(2022, 12, 31),
    )

    events = [
        {
            "start_date": "2020-04-01",
            "end_date": "2020-04-03",
            "duration_days": 3,
            "peak_temperature_c": 42.0,
            "mean_temperature_c": 40.0,
            "mean_excess_above_threshold_c": 2.0,
        },
        {
            "start_date": "2021-04-01",
            "end_date": "2021-04-03",
            "duration_days": 3,
            "peak_temperature_c": 43.0,
            "mean_temperature_c": 41.0,
            "mean_excess_above_threshold_c": 3.0,
        },
        {
            "start_date": "2022-04-01",
            "end_date": "2022-04-03",
            "duration_days": 3,
            "peak_temperature_c": 44.0,
            "mean_temperature_c": 42.0,
            "mean_excess_above_threshold_c": 4.0,
        },
    ]

    baseline = [
        {"temperature_max_c": 30.0}
        for _ in range(365 * 20)
    ]

    def make_cursor(records):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.to_list = AsyncMock(return_value=records)
        return cursor

    baseline_cursor = make_cursor(baseline)

    analysis_cursor = make_cursor(
        [
            {
                "date": f"{year}-04-01",
                "temperature_max_c": 42.0 + year - 2020,
            }
            for year in range(2020, 2023)
        ]
    )

    collection = MagicMock()
    collection.find.side_effect = [
        baseline_cursor,
        analysis_cursor,
    ]

    database = {"daily_weather": collection}

    with (
        patch(
            "app.services.analysis_service.ingest_weather",
            new_callable=AsyncMock,
        ) as mock_ingest,
        patch(
            "app.services.analysis_service.get_database",
            new_callable=AsyncMock,
            return_value=database,
        ),
        patch(
            "app.services.analysis_service.detect_heatwaves",
            return_value=events,
        ),
    ):
        result = await analyze_heatwaves(request)

    assert mock_ingest.await_count == 2

    assert result["total_events"] == 3
    assert len(result["annual_summary"]) == 3

    assert [
        item["event_count"]
        for item in result["annual_summary"]
    ] == [1, 1, 1]

    assert result["trend"]["direction"] == "no_change"
    assert result["trend"]["slope_events_per_year"] == 0.0
    assert result["trend"]["period_years"] == 3

    assert result["comparison"]["early_window_years"] == 3
    assert result["comparison"]["change_percent"] == 0.0
