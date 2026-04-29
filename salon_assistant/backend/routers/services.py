from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Service, User
from schemas import ServiceCreate, ServiceUpdate, ServiceResponse
from auth import get_current_user, require_salon_access

router = APIRouter(prefix="/api/services", tags=["Dienstleistungen"])


@router.post("/", response_model=ServiceResponse)
def create_service(service: ServiceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(service.salon_id, current_user)
    db_service = Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Dienstleistung nicht gefunden")
    require_salon_access(s.salon_id, current_user)
    return s


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, update: ServiceUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Dienstleistung nicht gefunden")
    require_salon_access(s.salon_id, current_user)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{service_id}")
def delete_service(service_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Dienstleistung nicht gefunden")
    require_salon_access(s.salon_id, current_user)
    s.active = False
    db.commit()
    return {"message": "Dienstleistung deaktiviert"}
