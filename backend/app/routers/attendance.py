import csv
import datetime as dt
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..database import get_db
from ..face_engine import face_engine, decode_base64_image, bytes_to_embedding

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _find_current_class_section(db: Session, location_id: int, now: dt.datetime) -> models.ClassSection | None:
    """Best-effort match of 'what class is happening right now at this location',
    used to decide on-time vs late. Falls back to None (no class context) if
    nothing is scheduled, in which case the scan is just logged as on_time."""
    today_abbr = WEEKDAY_ABBR[now.weekday()]
    sections = (
        db.query(models.ClassSection)
        .filter(models.ClassSection.location_id == location_id)
        .all()
    )
    best = None
    best_delta = None
    for section in sections:
        if today_abbr not in [d.strip() for d in section.scheduled_days.split(",")]:
            continue
        try:
            hh, mm = [int(p) for p in section.scheduled_start.split(":")]
        except ValueError:
            continue
        scheduled_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        delta = (now - scheduled_dt).total_seconds() / 60.0
        # Consider it "current" if within a 90-minute window after the scheduled start
        # (covers a typical period length) and not before the start.
        if 0 <= delta <= 90:
            if best_delta is None or delta < best_delta:
                best = section
                best_delta = delta
    return best


def _status_for(section: models.ClassSection | None, now: dt.datetime) -> str:
    if section is None:
        return "on_time"
    hh, mm = [int(p) for p in section.scheduled_start.split(":")]
    scheduled_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    minutes_late = (now - scheduled_dt).total_seconds() / 60.0
    return "late" if minutes_late > settings.late_after_minutes else "on_time"


@router.post("/scan", response_model=schemas.ScanResult)
def scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    """Called by the kiosk. No staff auth required -- kiosks authenticate with
    their per-location kiosk_key instead, since this endpoint runs unattended
    at a classroom door."""
    location = db.query(models.Location).filter(models.Location.kiosk_key == payload.location_kiosk_key).first()
    if not location:
        raise HTTPException(status_code=401, detail="Unknown or invalid kiosk key")

    try:
        image = decode_base64_image(payload.image_base64)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image data")

    detected = face_engine.largest_face_embedding(image)
    if detected is None:
        return schemas.ScanResult(matched=False, message="No face detected in frame")

    candidates = [
        (s.id, bytes_to_embedding(s.face_embedding))
        for s in db.query(models.Student).filter(models.Student.active == True, models.Student.face_embedding.isnot(None)).all()  # noqa: E712
    ]
    student_db_id, score = face_engine.find_best_match(detected.embedding, candidates)

    if student_db_id is None:
        return schemas.ScanResult(matched=False, message="Face not recognized", confidence=round(max(score, 0), 3))

    student = db.query(models.Student).get(student_db_id)
    now = dt.datetime.utcnow()

    recent = (
        db.query(models.AttendanceLog)
        .filter(
            models.AttendanceLog.student_id == student.id,
            models.AttendanceLog.location_id == location.id,
            models.AttendanceLog.timestamp >= now - dt.timedelta(seconds=settings.dedupe_window_seconds),
        )
        .order_by(models.AttendanceLog.timestamp.desc())
        .first()
    )
    if recent:
        return schemas.ScanResult(
            matched=True,
            student_id=student.student_id,
            student_name=student.full_name,
            location_name=location.name,
            timestamp=recent.timestamp,
            status=recent.status,
            confidence=round(score, 3),
            message=f"Welcome back, {student.first_name} (already recorded)",
            duplicate=True,
        )

    section = _find_current_class_section(db, location.id, now)
    status_value = _status_for(section, now)

    log = models.AttendanceLog(
        student_id=student.id,
        location_id=location.id,
        class_section_id=section.id if section else None,
        timestamp=now,
        status=status_value,
        match_confidence=round(score, 3),
    )
    db.add(log)
    db.commit()

    return schemas.ScanResult(
        matched=True,
        student_id=student.student_id,
        student_name=student.full_name,
        location_name=location.name,
        timestamp=now,
        status=status_value,
        confidence=round(score, 3),
        message=f"Welcome, {student.first_name}!",
    )


def _apply_filters(
    query,
    date_from: dt.date | None,
    date_to: dt.date | None,
    student_id: int | None,
    location_id: int | None,
    status: str | None,
    class_section_id: int | None,
):
    if date_from:
        query = query.filter(models.AttendanceLog.timestamp >= dt.datetime.combine(date_from, dt.time.min))
    if date_to:
        query = query.filter(models.AttendanceLog.timestamp <= dt.datetime.combine(date_to, dt.time.max))
    if student_id:
        query = query.filter(models.AttendanceLog.student_id == student_id)
    if location_id:
        query = query.filter(models.AttendanceLog.location_id == location_id)
    if status:
        query = query.filter(models.AttendanceLog.status == status)
    if class_section_id:
        query = query.filter(models.AttendanceLog.class_section_id == class_section_id)
    return query


@router.get("", response_model=list[schemas.AttendanceLogOut])
def list_attendance(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    student_id: int | None = None,
    location_id: int | None = None,
    status: str | None = None,
    class_section_id: int | None = None,
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
    _=Depends(security.get_current_user),
):
    query = db.query(models.AttendanceLog).order_by(models.AttendanceLog.timestamp.desc())
    query = _apply_filters(query, date_from, date_to, student_id, location_id, status, class_section_id)
    rows = query.limit(limit).all()
    return [
        schemas.AttendanceLogOut(
            id=r.id,
            student_id=r.student_id,
            student_name=r.student.full_name,
            student_school_id=r.student.student_id,
            location_id=r.location_id,
            location_name=r.location.name,
            class_section_id=r.class_section_id,
            class_section_name=r.class_section.name if r.class_section else None,
            timestamp=r.timestamp,
            status=r.status,
            match_confidence=r.match_confidence,
        )
        for r in rows
    ]


@router.get("/export.csv")
def export_csv(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    student_id: int | None = None,
    location_id: int | None = None,
    status: str | None = None,
    class_section_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(security.get_current_user),
):
    query = db.query(models.AttendanceLog).order_by(models.AttendanceLog.timestamp.desc())
    query = _apply_filters(query, date_from, date_to, student_id, location_id, status, class_section_id)
    rows = query.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Timestamp (UTC)", "Student ID", "Student Name", "Location", "Class", "Status", "Confidence"])
    for r in rows:
        writer.writerow([
            r.timestamp.isoformat(),
            r.student.student_id,
            r.student.full_name,
            r.location.name,
            r.class_section.name if r.class_section else "",
            r.status,
            r.match_confidence,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_export_{dt.date.today().isoformat()}.csv"},
    )


@router.get("/stats/summary", response_model=schemas.SummaryStats)
def stats_summary(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    location_id: int | None = None,
    class_section_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(security.get_current_user),
):
    query = db.query(models.AttendanceLog)
    query = _apply_filters(query, date_from, date_to, None, location_id, None, class_section_id)
    rows = query.all()

    total = len(rows)
    unique_students = len({r.student_id for r in rows})
    on_time = sum(1 for r in rows if r.status == "on_time")
    late = sum(1 for r in rows if r.status == "late")

    by_day: dict[dt.date, dict[str, int]] = {}
    for r in rows:
        d = r.timestamp.date()
        by_day.setdefault(d, {"on_time": 0, "late": 0})
        by_day[d][r.status] = by_day[d].get(r.status, 0) + 1

    daily = [
        schemas.DailyStat(date=d, on_time=v["on_time"], late=v["late"], total=v["on_time"] + v["late"])
        for d, v in sorted(by_day.items())
    ]

    return schemas.SummaryStats(
        total_scans=total,
        unique_students=unique_students,
        on_time_rate=round(on_time / total, 4) if total else 0.0,
        late_rate=round(late / total, 4) if total else 0.0,
        daily=daily,
    )
