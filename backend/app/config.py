"""
Central configuration for the attendance backend.

NOTE ON PRIVACY / COMPLIANCE:
This system stores biometric identifiers (face embeddings) for minors.
Before running this against real students, confirm with your school's
administration/legal counsel that you have:
  - Written parental/guardian consent (and student assent where applicable)
    for biometric data collection, per state biometric privacy laws
    (e.g. Illinois BIPA, Texas CUBI, Washington's biometric law) and
    student-records law (FERPA in the US).
  - A documented data retention & deletion policy (see ConsentRecord model
    and the /students/{id} DELETE endpoint, which purges embeddings).
  - Encryption at rest for the database file and enrollment photos in
    any real deployment (this prototype uses local SQLite/disk for
    simplicity - swap for an encrypted volume / managed DB in production).
"""
import os
import secrets
from pydantic_settings import BaseSettings


def _resolve_database_url() -> str:
    # Railway (and most PaaS providers) inject a plain DATABASE_URL when you
    # attach a Postgres plugin; fall back to our own prefixed var, then to a
    # local SQLite file for plain `uvicorn app.main:app` runs.
    url = os.environ.get("DATABASE_URL") or os.environ.get("ATTENDANCE_DATABASE_URL") or "sqlite:///./attendance.db"
    # SQLAlchemy 2.x dropped support for the legacy "postgres://" scheme that
    # Railway/Heroku-style providers still hand out.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _resolve_secret_key() -> str:
    key = os.environ.get("ATTENDANCE_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if key:
        return key
    # No key configured: generate one for this process so the app still boots,
    # but warn loudly since it means every restart invalidates admin sessions.
    # Set ATTENDANCE_SECRET_KEY as a real environment variable in any
    # deployment that should keep people logged in across restarts.
    print(
        "WARNING: no ATTENDANCE_SECRET_KEY/SECRET_KEY set - generating a random one for this "
        "process. Admin sessions will be invalidated on every restart. Set a fixed "
        "ATTENDANCE_SECRET_KEY environment variable to fix this."
    )
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    app_name: str = "School Attendance System"
    database_url: str = _resolve_database_url()
    secret_key: str = _resolve_secret_key()
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hour admin session

    # Face matching: cosine similarity threshold for SFace embeddings.
    # SFace's official recommended threshold for cosine similarity is ~0.363
    # for a reasonable FAR; we default a bit higher (stricter) for a school
    # setting where false-accepts matter more than convenience.
    face_match_threshold: float = 0.42

    # Minimum seconds between two logged scans for the same student at the
    # same location, to avoid duplicate log spam from a lingering face.
    dedupe_window_seconds: int = 120

    # Attendance status cutoffs, in minutes after a class's scheduled start.
    late_after_minutes: int = 10

    enrollments_dir: str = os.path.join(os.path.dirname(__file__), "static", "enrollments")
    ml_models_dir: str = os.path.join(os.path.dirname(__file__), "ml_models")

    # Only used the very first time the app boots against an empty database
    # (see the startup hook in main.py) -- set these as real environment
    # variables on any deployment reachable from the public internet, rather
    # than relying on the auto-generated fallback password.
    admin_password: str | None = os.environ.get("ATTENDANCE_ADMIN_PASSWORD")
    teacher_password: str | None = os.environ.get("ATTENDANCE_TEACHER_PASSWORD")

    class Config:
        env_prefix = "ATTENDANCE_"


settings = Settings()
os.makedirs(settings.enrollments_dir, exist_ok=True)
