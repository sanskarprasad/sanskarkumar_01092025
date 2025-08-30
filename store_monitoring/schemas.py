from pydantic import BaseModel, Field
from datetime import datetime, time

class StoreStatusPollCsv(BaseModel):
    store_id: str
    timestamp_utc: datetime
    status: str

class BusinessHoursCsv(BaseModel):
    store_id: str
    day_of_week: int = Field(alias='dayOfWeek')
    start_time_local: time = Field(alias='start_time_local')
    end_time_local: time = Field(alias='end_time_local')

class StoreTimezoneCsv(BaseModel):
    store_id: str
    timezone_str: str