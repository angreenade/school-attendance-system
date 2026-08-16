import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: str
    role: str


# ---------- Location ----------

class LocationCreate(BaseModel):
    name: str
    location_type: str = "classroom"


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location_type: str
    kiosk_key: str


# ---------- Class Section ----------

class ClassSectionCreate(BaseModel):
    name: str
    term: str = "Winter Term"
    teacher_name: Optional[str] = None
    location_id: Optional[int] = None
    scheduled_start: str = "08:00"
    scheduled_days: str = "Mon,Tue,Wed,Thu,Fri"


class ClassSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    term: str
    teacher_name: Optional[str]
    location_id: Optional[int]
    scheduled_start: str
    scheduled_days: str


# ---------- Student ----------

class StudentCreate(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    grade: Optional[str] = None
    homeroom: Optional[str] = None
    guardian_name: Optional[str] = None
    consent_given: bool = False


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: str
    first_name: str
    last_name: str
    grade: Optional[str]
    homeroom: Optional[str]
    photo_path: Optional[str]
    active: bool
    is_enrolled_for_recognition: bool
    consent_given: bool = False


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    grade: Optional[str] = None
    homeroom: Optional[str] = None
    active: Optional[bool] = None


# ---------- Attendance ----------

class ScanRequest(BaseModel):
    location_kiosk_key: str
    image_base64: str  # data URL or raw base64 JPEG/PNG of the captured frame


class ScanResult(BaseModel):
    matched: bool
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    location_name: Optional[str] = None
    timestamp: Optional[dt.datetime] = None
    status: Optional[str] = None  # on_time | late
    confidence: Optional[float] = None
    message: str
    duplicate: bool = False


class AttendanceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    student_name: str
    student_school_id: str
    location_id: int
    location_name: str
    class_section_id: Optional[int]
    class_section_name: Optional[str]
    timestamp: dt.datetime
    status: str
    match_confidence: float


class DailyStat(BaseModel):
    date: dt.date
    on_time: int
    late: int
    total: int


class SummaryStats(BaseModel):
    total_scans: int
    unique_students: int
    on_time_rate: float
    late_rate: float
    daily: list[DailyStat]
