from fastapi import APIRouter

from app.core.responses import success_response
from app.schemas.weather import WeatherIngestRequest
from app.services.weather_service import ingest_weather

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.post("/ingest")
async def ingest_weather_endpoint(request: WeatherIngestRequest):
    result = await ingest_weather(request)

    return success_response(
        "Historical weather data retrieved successfully",
        result,
    )
