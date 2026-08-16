import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[schemas.LocationOut])
def list_locations(db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    return db.query(models.Location).order_by(models.Location.name).all()


@router.get("/public", response_model=list[schemas.LocationOut])
def list_locations_public(db: Session = Depends(get_db)):
    """Unauthenticated listing so a kiosk can be configured with a location
    without needing a staff login on the kiosk device itself. Only exposes
    name/type/key, nothing about students."""
    return db.query(models.Location).order_by(models.Location.name).all()


@router.post("", response_model=schemas.LocationOut)
def create_location(payload: schemas.LocationCreate, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    loc = models.Location(
        name=payload.name,
        location_type=payload.location_type,
        kiosk_key=secrets.token_urlsafe(16),
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db), _=Depends(security.get_current_user)):
    loc = db.query(models.Location).get(location_id)
    if loc:
        db.delete(loc)
        db.commit()
    return {"ok": True}
