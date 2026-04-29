from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Hairdresser, User
from schemas import HairdresserCreate, HairdresserUpdate, HairdresserResponse
from auth import get_current_user, require_salon_access

router = APIRouter(prefix="/api/hairdressers", tags=["Friseure"])


@router.post("/", response_model=HairdresserResponse)
def create_hairdresser(hairdresser: HairdresserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(hairdresser.salon_id, current_user)
    db_hairdresser = Hairdresser(**hairdresser.model_dump())
    db.add(db_hairdresser)
    db.commit()
    db.refresh(db_hairdresser)
    return db_hairdresser


@router.get("/{hairdresser_id}", response_model=HairdresserResponse)
def get_hairdresser(hairdresser_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    require_salon_access(h.salon_id, current_user)
    return h


@router.put("/{hairdresser_id}", response_model=HairdresserResponse)
def update_hairdresser(hairdresser_id: int, update: HairdresserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    require_salon_access(h.salon_id, current_user)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(h, field, value)
    db.commit()
    db.refresh(h)
    return h


@router.delete("/{hairdresser_id}")
def delete_hairdresser(hairdresser_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    require_salon_access(h.salon_id, current_user)
    h.active = False
    db.commit()
    return {"message": "Friseur deaktiviert"}
