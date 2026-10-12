from datetime import date

from pydantic import BaseModel, Field, model_validator


from datetime import date

from pydantic import BaseModel, Field, model_validator


class HeatwaveAnalysisRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")

        if (self.end_date - self.start_date).days > 366 * 35:
            raise ValueError("Analysis period cannot exceed 35 years")

        if self.end_date > date.today():
            raise ValueError("end_date cannot be in the future")

        return self
