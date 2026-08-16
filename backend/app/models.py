import datetime as dt

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class AdminUser(Base):
    """Staff account (admin or teacher) able to log into the dashboard."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="admin")  # admin | teacher
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Location(Base):
    """A physical scanning point: a classroom door, a study room, a building entrance."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    location_type = Column(String(32), nullable=False, default="classroom")  # classroom | study_room | entrance
    kiosk_key = Column(String(64), unique=True, nullable=False)  # simple shared secret the kiosk presents
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    attendance_logs = relationship("AttendanceLog", back_populates="location")


class ClassSection(Base):
    """A scheduled class/section, tied to a default location and a term."""

    __tablename__ = "class_sections"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)  # e.g. "Chemistry 101 - Section B"
    term = Column(String(64), nullable=False, default="Winter Term")
    teacher_name = Column(String(128), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    scheduled_start = Column(String(5), nullable=False, default="08:00")  # "HH:MM" 24h
    scheduled_days = Column(String(32), nullable=False, default="Mon,Tue,Wed,Thu,Fri")

    location = relationship("Location")
    enrollments = relationship("Enrollment", back_populates="class_section", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    student_id = Column(String(32), unique=True, nullable=False, index=True)  # school-issued ID
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    grade = Column(String(16), nullable=True)
    homeroom = Column(String(64), nullable=True)
    photo_path = Column(String(255), nullable=True)
    # 128-d SFace embedding stored as raw float32 bytes; NULL until enrolled.
    face_embedding = Column(LargeBinary, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendance_logs = relationship("AttendanceLog", back_populates="student", cascade="all, delete-orphan")
    consent = relationship("ConsentRecord", back_populates="student", uselist=False, cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_enrolled_for_recognition(self) -> bool:
        return self.face_embedding is not None


class Enrollment(Base):
    """Many-to-many: which students belong to which class sections."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "class_section_id", name="uq_student_class"),)

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=False)

    student = relationship("Student", back_populates="enrollments")
    class_section = relationship("ClassSection", back_populates="enrollments")


class AttendanceLog(Base):
    """One row per successful face-recognition scan."""

    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True)
    timestamp = Column(DateTime, default=dt.datetime.utcnow, index=True)
    status = Column(String(16), nullable=False, default="on_time")  # on_time | late
    match_confidence = Column(Float, nullable=False)  # cosine similarity score at match time

    student = relationship("Student", back_populates="attendance_logs")
    location = relationship("Location", back_populates="attendance_logs")
    class_section = relationship("ClassSection")


class ConsentRecord(Base):
    """Tracks parental/guardian consent for biometric data collection per student.

    Required before enrolling a student's face embedding in most jurisdictions.
    """

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    consent_given = Column(Boolean, default=False)
    guardian_name = Column(String(128), nullable=True)
    consent_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    student = relationship("Student", back_populates="consent")
