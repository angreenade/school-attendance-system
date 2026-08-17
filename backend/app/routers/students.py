import datetime as dt
import os
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..database import get_db
from ..face_engine import face_engine, embedding_to_bytes

router = APIRouter(prefix="/api/students", tags=["students"])


def _to_out(student: models.Student) -> schemas.StudentOut:
    consent_given = bool(student.consent and student.consent.consent_given)
    return schemas.StudentOut(
        id=student.id,
        student_id=student.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        grade=student.grade,
        homeroom=student.homeroom,
        photo_path=student.photo_path,
        active=student.active,
        is_enrolled_for_recognition=student.is_enrolled_for_recognition,
        consent_given=consent_given,
    )


@router.get("", response_model=list[schemas.StudentOut])
def list_students(
    q: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(security.get_current_user),
):
    query = db.query(models.Student)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.Student.first_name.ilike(like))
            | (models.Student.last_name.ilike(like))
            | (models.Student.student_id.ilike(like))
        )
    return [_to_out(s) for s in query.order_by(models.Student.last_name).all()]


@router.post("", response_model=schemas.StudentOut)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    if db.query(models.Student).filter(models.Student.student_id == payload.student_id).first():
        raise HTTPException(status_code=400, detail="A student with that school ID already exists")

    student = models.Student(
        student_id=payload.student_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        grade=payload.grade,
        homeroom=payload.homeroom,
    )
    db.add(student)
    db.flush()

    consent = models.ConsentRecord(
        student_id=student.id,
        consent_given=payload.consent_given,
        guardian_name=payload.guardian_name,
        consent_date=dt.datetime.utcnow() if payload.consent_given else None,
    )
    db.add(consent)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.put("/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    student = db.query(models.Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    """Fully purges a student's record, including their biometric embedding and
    enrollment photo -- required to honor data-deletion requests."""
    student = db.query(models.Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.photo_path:
        full_path = os.path.join(settings.enrollments_dir, os.path.basename(student.photo_path))
        if os.path.exists(full_path):
            os.remove(full_path)
    db.delete(student)
    db.commit()
    return {"ok": True}


@router.post("/{student_id}/enroll-photo", response_model=schemas.StudentOut)
async def enroll_photo(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(security.get_current_user),
):
    """Uploads a clear reference photo of the student's face, computes and
    stores their face embedding. Requires guardian consent to be on file."""
    student = db.query(models.Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not (student.consent and student.consent.consent_given):
        raise HTTPException(
            status_code=403,
            detail="No parental/guardian consent on file for this student. Record consent before enrolling biometric data.",
        )

    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not read uploaded image")

    faces = face_engine.all_face_embeddings(image)
    if len(faces) == 0:
        raise HTTPException(status_code=400, detail="No face detected in the photo. Use a clear, front-facing photo.")
    if len(faces) > 1:
        raise HTTPException(status_code=400, detail="Multiple faces detected. Upload a photo with only this student.")

    embedding = faces[0].embedding

    filename = f"{uuid.uuid4().hex}.jpg"
    save_path = os.path.join(settings.enrollments_dir, filename)
    cv2.imwrite(save_path, image)

    if student.photo_path:
        old_path = os.path.join(settings.enrollments_dir, os.path.basename(student.photo_path))
        if os.path.exists(old_path):
            os.remove(old_path)

    student.photo_path = f"/static/enrollments/{filename}"
    student.face_embedding = embedding_to_bytes(embedding)
    db.commit()
    db.refresh(student)
    return _to_out(student)
