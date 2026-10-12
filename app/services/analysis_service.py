from datetime import date
from statistics import mean

from app.core.exceptions import AppError
from app.db.mongo import get_database
from app.schemas.analysis import HeatwaveAnalysisRequest
from app.schemas.weather import WeatherIngestRequest
from app.services.heatwave_service import (
    calculate_threshold,
    detect_heatwaves,
    calculate_linear_trend,
)
from app.services.weather_service import ingest_weather


BASELINE_START = date(1991, 1, 1)
BASELINE_END = date(2020, 12, 31)


async def analyze_heatwaves(request: HeatwaveAnalysisRequest) -> dict:
    # 1. Ensure baseline observations are available.
    baseline_request = WeatherIngestRequest(
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=BASELINE_START,
        end_date=BASELINE_END,
    )

    await ingest_weather(baseline_request)

    # 2. Ensure the requested analysis period is available.
    analysis_request = WeatherIngestRequest(
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    await ingest_weather(analysis_request)

    db = await get_database()
    collection = db["daily_weather"]

    location_filter = {
        "latitude": round(request.latitude, 4),
        "longitude": round(request.longitude, 4),
        "source": "open-meteo",
        "model": "era5",
    }

    # 3. Read baseline temperatures from MongoDB.
    baseline_cursor = collection.find(
        {
            **location_filter,
            "date": {
                "$gte": BASELINE_START.isoformat(),
                "$lte": BASELINE_END.isoformat(),
            },
        },
        {"_id": 0, "date": 1, "temperature_max_c": 1},
    ).sort("date", 1)

    baseline = await baseline_cursor.to_list(length=None)

    valid_baseline = [
        item["temperature_max_c"]
        for item in baseline
        if item.get("temperature_max_c") is not None
    ]

    if len(valid_baseline) < 365 * 20:
        raise AppError(
            "Insufficient historical data to calculate a reliable baseline",
            status_code=422,
            error_code="INSUFFICIENT_BASELINE_DATA",
        )

    # 4. Calculate one fixed threshold for this location.
    threshold = calculate_threshold(valid_baseline)

    # 5. Read observations for the requested analysis period.
    analysis_cursor = collection.find(
        {
            **location_filter,
            "date": {
                "$gte": request.start_date.isoformat(),
                "$lte": request.end_date.isoformat(),
            },
        },
        {"_id": 0, "date": 1, "temperature_max_c": 1},
    ).sort("date", 1)

    observations = await analysis_cursor.to_list(length=None)

    # 6. Detect heatwave events.
    events = detect_heatwaves(observations, threshold)

    # 7. Aggregate event frequency and intensity by start year.
    annual = []

    for year in range(request.start_date.year, request.end_date.year + 1):
        year_events = [
            event
            for event in events
            if date.fromisoformat(event["start_date"]).year == year
        ]

        annual.append(
            {
                "year": year,
                "event_count": len(year_events),
                "heatwave_days": sum(event["duration_days"] for event in year_events),
                "average_duration_days": (
                    round(
                        mean(event["duration_days"] for event in year_events),
                        2,
                    )
                    if year_events
                    else 0
                ),
                "average_excess_c": (
                    round(
                        mean(
                            event["mean_excess_above_threshold_c"]
                            for event in year_events
                        ),
                        2,
                    )
                    if year_events
                    else 0
                ),
            }
        )

    # Compare average annual event counts in the first and last
    # five-year windows (or shorter periods for short analyses).
    analysis_years = request.end_date.year - request.start_date.year + 1
    window = min(5, analysis_years)

    early = [item["event_count"] for item in annual[:window]]
    recent = [item["event_count"] for item in annual[-window:]]

    early_average = mean(early)
    recent_average = mean(recent)

    change_percent = (
        round((recent_average - early_average) / early_average * 100, 2)
        if early_average > 0
        else None
    )

    trend = calculate_linear_trend(annual)

    return {
        "location": {
            "latitude": round(request.latitude, 4),
            "longitude": round(request.longitude, 4),
        },
        "analysis_period": {
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
        },
        "baseline_period": {
            "start_date": BASELINE_START.isoformat(),
            "end_date": BASELINE_END.isoformat(),
        },
        "threshold_c": round(threshold, 2),
        "valid_baseline_days": len(valid_baseline),
        "total_events": len(events),
        "annual_summary": annual,
        "events": events,
        "comparison": {
            "early_window_years": window,
            "early_average_events_per_year": round(early_average, 2),
            "recent_average_events_per_year": round(recent_average, 2),
            "change_percent": change_percent,
        },
        "trend": trend,
    }
