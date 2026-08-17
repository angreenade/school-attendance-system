from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("", response_model=list[schemas.ClassSectionOut])
def list_classes(db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    return db.query(models.ClassSection).order_by(models.ClassSection.name).all()


@router.post("", response_model=schemas.ClassSectionOut)
def create_class(payload: schemas.ClassSectionCreate, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    section = models.ClassSection(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.post("/{class_id}/enroll/{student_id}")
def enroll_student(class_id: int, student_id: int, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    section = db.query(models.ClassSection).get(class_id)
    student = db.query(models.Student).get(student_id)
    if not section or not student:
        raise HTTPException(status_code=404, detail="Class or student not found")

    existing = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.class_section_id == class_id, models.Enrollment.student_id == student_id)
        .first()
    )
    if existing:
        return {"ok": True, "already_enrolled": True}

    db.add(models.Enrollment(class_section_id=class_id, student_id=student_id))
    db.commit()
    return {"ok": True}


@router.delete("/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    section = db.query(models.ClassSection).get(class_id)
    if section:
        db.delete(section)
        db.commit()
    return {"ok": True}
