from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Hairdresser
from schemas import HairdresserCreate, HairdresserUpdate, HairdresserResponse

router = APIRouter(prefix="/api/hairdressers", tags=["Friseure"])


@router.post("/", response_model=HairdresserResponse)
def create_hairdresser(hairdresser: HairdresserCreate, db: Session = Depends(get_db)):
    db_hairdresser = Hairdresser(**hairdresser.model_dump())
    db.add(db_hairdresser)
    db.commit()
    db.refresh(db_hairdresser)
    return db_hairdresser


@router.get("/{hairdresser_id}", response_model=HairdresserResponse)
def get_hairdresser(hairdresser_id: int, db: Session = Depends(get_db)):
    hairdresser = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not hairdresser:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    return hairdresser


@router.put("/{hairdresser_id}", response_model=HairdresserResponse)
def update_hairdresser(hairdresser_id: int, update: HairdresserUpdate, db: Session = Depends(get_db)):
    hairdresser = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not hairdresser:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(hairdresser, field, value)
    db.commit()
    db.refresh(hairdresser)
    return hairdresser


@router.delete("/{hairdresser_id}")
def delete_hairdresser(hairdresser_id: int, db: Session = Depends(get_db)):
    hairdresser = db.query(Hairdresser).filter(Hairdresser.id == hairdresser_id).first()
    if not hairdresser:
        raise HTTPException(status_code=404, detail="Friseur nicht gefunden")
    hairdresser.active = False
    db.commit()
    return {"message": "Friseur deaktiviert"}
