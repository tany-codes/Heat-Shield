from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    name: str
    role: str = "worker"          # worker | supervisor
    job_role: Optional[str] = "General"


class LoginResponse(BaseModel):
    worker_id: int
    name: str
    role: str


class ReadingRequest(BaseModel):
    worker_id: int
    lat: float
    lon: float
    work_type: str = "moderate"    # light | moderate | heavy
    clothing: str = "light"        # light | heavy
    hydration_glasses: int = 3
    rest_minutes: int = 45
    health: str = "none"           # none | cardiac | other


class ReadingResponse(BaseModel):
    temp_c: float
    humidity: float
    heat_index_c: float
    score: int
    label: str
    level: str
    description: str
    recommendations: List[str]
    alert: bool
    location_label: Optional[str] = None


class WorkerStatus(BaseModel):
    worker_id: int
    name: str
    job_role: str
    score: Optional[int] = None
    label: Optional[str] = None
    level: Optional[str] = None
    last_reading_at: Optional[datetime] = None
    shift_minutes: Optional[int] = None
    minutes_since_reading: Optional[int] = None

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    score: int
    created_at: datetime
    acknowledged: bool

    class Config:
        from_attributes = True
