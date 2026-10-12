from datetime import timedelta, date
import logging
import math

import httpx
from fastapi import status
from pymongo import UpdateOne

from app.core.exceptions import AppError
from app.db.mongo import get_database
from app.schemas.weather import WeatherIngestRequest
from app.models.weather import DailyWeatherDocument

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_COLLECTION = "daily_weather"


async def ingest_weather(request: WeatherIngestRequest) -> dict:
    db = await get_database()
    collection = db[WEATHER_COLLECTION]

    latitude = round(request.latitude, 4)
    longitude = round(request.longitude, 4)

    expected_days = (request.end_date - request.start_date).days + 1

    query = {
        "latitude": latitude,
        "longitude": longitude,
        "date": {
            "$gte": request.start_date.isoformat(),
            "$lte": request.end_date.isoformat(),
        },
        "source": "open-meteo",
        "model": "era5",
    }

    cached_records = await collection.find(
        query, {"_id": 0, "date": 1, "temperature_max_c": 1}
    ).to_list(length=None)

    cached_dates = {
        record["date"]
        for record in cached_records
        if isinstance(record.get("temperature_max_c"), (int, float))
        and math.isfinite(record["temperature_max_c"])
    }

    expected_dates = {
        (request.start_date + timedelta(days=offset)).isoformat()
        for offset in range(expected_days)
    }

    if expected_dates.issubset(cached_dates):
        return {
            "source": "cache",
            "records": len(expected_dates),
            "latitude": latitude,
            "longitude": longitude,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
        }

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "daily": "temperature_2m_max",
        "timezone": "auto",
        "temperature_unit": "celsius",
        "models": "era5",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()

    except httpx.HTTPStatusError as exc:
        logger.warning("Open-Meteo returned HTTP %s", exc.response.status_code)

        raise AppError(
            "Historical weather provider returned an error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="WEATHER_PROVIDER_ERROR",
        ) from exc

    except (httpx.RequestError, ValueError) as exc:
        logger.exception("Failed to retrieve historical weather")
        raise AppError(
            "Could not retrieve historical weather data",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="WEATHER_PROVIDER_UNAVAILABLE",
        ) from exc

    daily = payload.get("daily")

    if not isinstance(daily, dict):
        raise AppError(
            "Weather provider returned an invalid response",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="INVALID_WEATHER_RESPONSE",
        )

    dates = daily.get("time")
    temperatures = daily.get("temperature_2m_max")

    if (
        not isinstance(dates, list)
        or not isinstance(temperatures, list)
        or len(dates) != len(temperatures)
    ):
        raise AppError(
            "Weather provider returned incomplete daily data",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="INVALID_WEATHER_RESPONSE",
        )

    validate_provider_date_coverage(
        dates,
        request.start_date,
        request.end_date,
    )

    operations = []

    for day, temperature in zip(dates, temperatures):
        day_date = request.start_date.fromisoformat(day)

        if not request.start_date <= day_date <= request.end_date:
            continue

        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)
        ):
            raise AppError(
                "Weather provider returned an invalid temperature",
                status_code=status.HTTP_502_BAD_GATEWAY,
                error_code="INVALID_WEATHER_RESPONSE",
            )

        document = {
            "latitude": latitude,
            "longitude": longitude,
            "date": day,
            "temperature_max_c": (
                float(temperature) if temperature is not None else None
            ),
            "source": "open-meteo",
            "model": "era5",
        }

        validated_document = DailyWeatherDocument.model_validate(document)
        stored_document = validated_document.model_dump(mode="json")

        operations.append(
            UpdateOne(
                {
                    "latitude": validated_document.latitude,
                    "longitude": validated_document.longitude,
                    "date": validated_document.date.isoformat(),
                    "source": validated_document.source,
                    "model": validated_document.model,
                },
                {"$set": stored_document},
                upsert=True,
            )
        )

    if not operations:
        raise AppError(
            "No weather observations were returned",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="NO_WEATHER_DATA",
        )

    await collection.bulk_write(operations, ordered=False)

    logger.info(
        "Stored %s daily weather records",
        len(operations),
    )

    return {
        "source": "open-meteo",
        "records": len(operations),
        "latitude": latitude,
        "longitude": longitude,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
    }


def validate_provider_date_coverage(
    dates: list[str],
    start_date: date,
    end_date: date,
) -> None:
    """Ensure every requested date appears exactly once."""

    try:
        parsed_dates = [date.fromisoformat(day) for day in dates]
    except (TypeError, ValueError) as exc:
        raise AppError(
            "Weather provider returned invalid dates",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="INVALID_WEATHER_RESPONSE",
        ) from exc

    expected_dates = {
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    }

    in_range_dates = [day for day in parsed_dates if start_date <= day <= end_date]

    if (
        len(in_range_dates) != len(set(in_range_dates))
        or set(in_range_dates) != expected_dates
    ):
        raise AppError(
            "Weather provider did not return complete daily coverage",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="INVALID_WEATHER_RESPONSE",
        )
