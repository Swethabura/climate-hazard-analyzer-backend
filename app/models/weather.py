from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DailyWeatherDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    date: date
    temperature_max_c: float | None
    source: str
    model: str
