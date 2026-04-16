from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Customer, User
from schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from auth import get_current_user, require_salon_access

router = APIRouter(prefix="/api/customers", tags=["Kunden"])


@router.get("/", response_model=List[CustomerResponse])
def list_customers(salon_id: int, search: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    query = db.query(Customer).filter(Customer.salon_id == salon_id)
    if search:
        query = query.filter(Customer.name.ilike(f"%{search}%") | Customer.phone.ilike(f"%{search}%"))
    return query.order_by(Customer.name).all()


@router.post("/", response_model=CustomerResponse)
def create_customer(customer: CustomerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(customer.salon_id, current_user)
    existing = db.query(Customer).filter(Customer.salon_id == customer.salon_id, Customer.phone == customer.phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Kunde mit dieser Telefonnummer bereits vorhanden")
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/by-phone", response_model=CustomerResponse)
def get_customer_by_phone(salon_id: int, phone: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(salon_id, current_user)
    import re as _re
    digits = _re.sub(r'[^\d+]', '', phone)
    for c in db.query(Customer).filter(Customer.salon_id == salon_id).all():
        if _re.sub(r'[^\d+]', '', c.phone) == digits:
            return c
    raise HTTPException(status_code=404, detail="Kunde nicht gefunden")


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    require_salon_access(c.salon_id, current_user)
    return c


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, update: CustomerUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    require_salon_access(c.salon_id, current_user)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    require_salon_access(c.salon_id, current_user)
    db.delete(c)
    db.commit()
    return {"message": "Kunde gelöscht"}
