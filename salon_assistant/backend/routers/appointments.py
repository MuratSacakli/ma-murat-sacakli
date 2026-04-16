from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Appointment, Hairdresser, Service
from schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AvailabilityRequest

router = APIRouter(prefix="/api/appointments", tags=["Termine"])


@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    salon_id: Optional[int] = None,
    hairdresser_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)
    if salon_id:
        query = query.filter(Appointment.salon_id == salon_id)
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
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db)):
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
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(appointment_id: int, update: AppointmentUpdate, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(appointment, field, value)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}")
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    appointment.status = "cancelled"
    db.commit()
    return {"message": "Termin storniert"}


@router.post("/availability")
def get_available_slots(request: AvailabilityRequest, db: Session = Depends(get_db)):
    from models import Salon
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
        conflict = any(
            not (slot_end <= b_start or slot_start >= b_end)
            for b_start, b_end in booked_ranges
        )
        if not conflict:
            available_slots.append({
                "start": slot_start.isoformat(),
                "end": slot_end.isoformat(),
                "display": slot_start.strftime("%H:%M")
            })
        slot_start += timedelta(minutes=salon.slot_duration_minutes)

    return {"date": request.date, "available_slots": available_slots}
