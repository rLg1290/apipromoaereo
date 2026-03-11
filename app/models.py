from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Promotion(BaseModel):
    id: Optional[int] = None
    message_id: int
    destination: str
    origin_city: str
    origin_code: str
    destination_city: str
    destination_code: str
    airline: str
    program: str
    cabin_class: str
    miles_per_segment: int
    outbound_dates: dict[str, list[int]]   # e.g. {"Mar/2026": [26, 31]}
    return_dates: dict[str, list[int]]     # e.g. {"Abr/2026": [7, 8, 10]}
    raw_text: str
    collected_at: datetime = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
