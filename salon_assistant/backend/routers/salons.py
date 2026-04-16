from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Salon, Hairdresser, Service, User
from schemas import SalonCreate, SalonUpdate, SalonResponse, HairdresserResponse, ServiceResponse
from auth import get_current_user, require_salon_access

router = APIRouter(prefix="/api/salons", tags=["Salons"])


@router.get("/", response_model=List[SalonResponse])
def list_salons(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_superadmin:
        return db.query(Salon).filter(Salon.active == True).all()
    return db.query(Salon).filter(Salon.id == current_user.salon_id, Salon.active == True).all()


@router.post("/", response_model=SalonResponse)
def create_salon(salon: SalonCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins dürfen Salons erstellen")
    db_salon = Salon(**salon.model_dump())
    db.add(db_salon)
    db.commit()
    db.refresh(db_salon)
    return db_salon


@router.get("/{salon_id}", response_model=SalonResponse)
def get_salon(salon_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon nicht gefunden")
    return salon


@router.put("/{salon_id}", response_model=SalonResponse)
def update_salon(salon_id: int, salon_update: SalonUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon nicht gefunden")
    for field, value in salon_update.model_dump(exclude_none=True).items():
        setattr(salon, field, value)
    db.commit()
    db.refresh(salon)
    return salon


@router.delete("/{salon_id}")
def delete_salon(salon_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins dürfen Salons löschen")
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon nicht gefunden")
    salon.active = False
    db.commit()
    return {"message": "Salon deaktiviert"}


@router.get("/{salon_id}/hairdressers", response_model=List[HairdresserResponse])
def get_salon_hairdressers(salon_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    return db.query(Hairdresser).filter(Hairdresser.salon_id == salon_id, Hairdresser.active == True).all()


@router.get("/{salon_id}/services", response_model=List[ServiceResponse])
def get_salon_services(salon_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    return db.query(Service).filter(Service.salon_id == salon_id, Service.active == True).all()
