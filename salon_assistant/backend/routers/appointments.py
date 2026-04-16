from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Appointment, Hairdresser, User
from schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AvailabilityRequest
from auth import get_current_user, require_salon_access

router = APIRouter(prefix="/api/appointments", tags=["Termine"])


@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    salon_id: Optional[int] = None,
    hairdresser_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)
    # Salon-Nutzer sehen nur ihre eigenen Termine
    effective_salon = salon_id if current_user.is_superadmin else current_user.salon_id
    if effective_salon:
        query = query.filter(Appointment.salon_id == effective_salon)
    if hairdresser_id:
        query = query.filter(Appointment.hairdresser_id == hairdresser_id)
    if date_from:
        query = query.filter(Appointment.start_time >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Appointment.start_time <= datetime.fromisoformat(date_to))
    if status:
        query = query.filter(Appointment.status == status)
    return query.order_by(Appointment.start_time).all()


@router.post("/", response_model=AppointmentResponse)
def create_appointment(appointment: AppointmentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_salon_access(appointment.salon_id, current_user)
    conflict = db.query(Appointment).filter(
        Appointment.hairdresser_id == appointment.hairdresser_id,
        Appointment.status != "cancelled",
        Appointment.start_time < appointment.end_time,
        Appointment.end_time > appointment.start_time
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="Zeitkonflikt: Friseur ist zu dieser Zeit bereits gebucht")
    db_appointment = Appointment(**appointment.model_dump())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    require_salon_access(a.salon_id, current_user)
    return a


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(appointment_id: int, update: AppointmentUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    require_salon_access(a.salon_id, current_user)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(a, field, value)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{appointment_id}")
def cancel_appointment(appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    require_salon_access(a.salon_id, current_user)
    a.status = "cancelled"
    db.commit()
    return {"message": "Termin storniert"}


@router.post("/availability")
def get_available_slots(request: AvailabilityRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from models import Salon
    require_salon_access(request.salon_id, current_user)
    salon = db.query(Salon).filter(Salon.id == request.salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon nicht gefunden")
    target_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    open_h, open_m = map(int, salon.opening_time.split(":"))
    close_h, close_m = map(int, salon.closing_time.split(":"))
    slot_start = datetime(target_date.year, target_date.month, target_date.day, open_h, open_m)
    closing = datetime(target_date.year, target_date.month, target_date.day, close_h, close_m)
    slot_duration = timedelta(minutes=request.duration_minutes)
    booked = db.query(Appointment).filter(
        Appointment.hairdresser_id == request.hairdresser_id,
        Appointment.status != "cancelled",
        Appointment.start_time >= slot_start,
        Appointment.start_time < closing
    ).all()
    booked_ranges = [(a.start_time, a.end_time) for a in booked]
    available_slots = []
    while slot_start + slot_duration <= closing:
        slot_end = slot_start + slot_duration
        if not any(not (slot_end <= b_start or slot_start >= b_end) for b_start, b_end in booked_ranges):
            available_slots.append({"start": slot_start.isoformat(), "end": slot_end.isoformat(), "display": slot_start.strftime("%H:%M")})
        slot_start += timedelta(minutes=salon.slot_duration_minutes)
    return {"date": request.date, "available_slots": available_slots}
