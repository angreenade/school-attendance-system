"""
Reusable demo-data seeding, shared by the standalone `seed.py` dev script and
the auto-seed-on-first-boot hook in `main.py` for cloud deployments.

`run_seed(db, wipe=...)`:
  - wipe=True  (used by `python3 seed.py`): clears existing rows first --
    convenient for local dev, destructive, never called automatically.
  - wipe=False (used by the startup hook): assumes the DB is already empty
    and just inserts -- the startup hook only calls this once, guarded by
    an AdminUser count check, so a redeploy never wipes real data.
"""
import datetime as dt
import random
import secrets

import numpy as np
from sqlalchemy.orm import Session

from . import models
from .security import hash_password

WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

FIRST_NAMES = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Lily", "Mason", "Grace", "Owen",
               "Ella", "Lucas", "Nora", "Aiden", "Ivy", "Caleb", "Sofia", "Jack"]
LAST_NAMES = ["Johnson", "Garcia", "Kim", "Patel", "Rossi", "Nguyen", "Smith", "Brown", "Davis",
              "Cohen", "Martin", "Lee", "Clark", "Walker", "Young", "King", "Wright", "Adams"]

LOCATION_DEFS = [
    ("Room 101", "classroom"),
    ("Room 204", "classroom"),
    ("Library Study Room", "study_room"),
    ("Main Entrance", "entrance"),
]

CLASS_DEFS = [
    ("Algebra II - Section A", "Room 101", "Mr. Chen", "08:00", "Mon,Tue,Wed,Thu,Fri"),
    ("Chemistry - Section B", "Room 204", "Ms. Rivera", "09:15", "Mon,Wed,Fri"),
    ("World History", "Room 101", "Mr. Okafor", "10:30", "Tue,Thu"),
    ("Study Hall", "Library Study Room", "Ms. Patel", "13:00", "Mon,Tue,Wed,Thu,Fri"),
]


def run_seed(db: Session, wipe: bool = True, admin_password: str | None = None, teacher_password: str | None = None) -> dict:
    random.seed(42)
    np.random.seed(42)

    if wipe:
        for table in [models.AttendanceLog, models.Enrollment, models.ConsentRecord, models.Student,
                      models.ClassSection, models.Location, models.AdminUser]:
            db.query(table).delete()
        db.commit()

    admin = models.AdminUser(
        username="admin",
        hashed_password=hash_password(admin_password or "admin123"),
        full_name="School Administrator",
        role="admin",
    )
    db.add(admin)
    teacher = models.AdminUser(
        username="teacher",
        hashed_password=hash_password(teacher_password or "teacher123"),
        full_name="Ms. Rivera",
        role="teacher",
    )
    db.add(teacher)
    db.commit()

    locations = {}
    for name, ltype in LOCATION_DEFS:
        loc = models.Location(name=name, location_type=ltype, kiosk_key=secrets.token_urlsafe(16))
        db.add(loc)
        locations[name] = loc
    db.commit()

    sections = {}
    for name, loc_name, teacher_name, start, days in CLASS_DEFS:
        section = models.ClassSection(
            name=name, term="Winter Term 2026", teacher_name=teacher_name,
            location_id=locations[loc_name].id, scheduled_start=start, scheduled_days=days,
        )
        db.add(section)
        sections[name] = section
    db.commit()

    students = []
    for i, (fn, ln) in enumerate(zip(FIRST_NAMES, LAST_NAMES), start=1):
        student = models.Student(
            student_id=f"STU{1000 + i}", first_name=fn, last_name=ln,
            grade=random.choice(["9", "10", "11", "12"]), homeroom=random.choice(["101", "204"]),
            active=True,
            # Synthetic embedding placeholder -- real students need a real photo enrolled
            # via POST /api/students/{id}/enroll-photo before the kiosk will recognize them.
            face_embedding=np.random.RandomState(i).normal(size=128).astype(np.float32).tobytes(),
        )
        db.add(student)
        db.flush()
        db.add(models.ConsentRecord(
            student_id=student.id, consent_given=True, guardian_name=f"Guardian of {fn} {ln}",
            consent_date=dt.datetime.utcnow() - dt.timedelta(days=90), notes="Demo consent record (seeded).",
        ))
        students.append(student)
    db.commit()

    section_list = list(sections.values())
    for student in students:
        for section in random.sample(section_list, k=random.randint(2, 4)):
            db.add(models.Enrollment(student_id=student.id, class_section_id=section.id))
    db.commit()

    term_start = dt.date.today() - dt.timedelta(weeks=7)
    today = dt.date.today()
    log_count = 0
    day = term_start
    enroll_map = {s.id: [e.class_section_id for e in s.enrollments] for s in students}

    while day <= today:
        weekday = WEEKDAY_ABBR[day.weekday()]
        for section in section_list:
            if weekday not in section.scheduled_days.split(","):
                continue
            hh, mm = [int(p) for p in section.scheduled_start.split(":")]
            scheduled_dt = dt.datetime.combine(day, dt.time(hh, mm))
            enrolled_students = [s for s in students if section.id in enroll_map[s.id]]
            for student in enrolled_students:
                if random.random() > 0.90:
                    continue
                if random.random() < 0.12:
                    offset_minutes = random.randint(11, 25)
                else:
                    offset_minutes = random.randint(-4, 9)
                ts = scheduled_dt + dt.timedelta(minutes=offset_minutes)
                status = "late" if offset_minutes > 10 else "on_time"
                db.add(models.AttendanceLog(
                    student_id=student.id, location_id=section.location_id, class_section_id=section.id,
                    timestamp=ts, status=status, match_confidence=round(random.uniform(0.46, 0.81), 3),
                ))
                log_count += 1
        day += dt.timedelta(days=1)
    db.commit()

    return {
        "students": len(students),
        "class_sections": len(section_list),
        "locations": len(locations),
        "attendance_logs": log_count,
    }
