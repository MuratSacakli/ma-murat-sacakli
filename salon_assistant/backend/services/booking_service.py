from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Appointment, Hairdresser, Service, Salon


def find_hairdresser_by_name(db: Session, salon_id: int, name: str) -> Optional[Hairdresser]:
    hairdressers = db.query(Hairdresser).filter(
        Hairdresser.salon_id == salon_id,
        Hairdresser.active == True
    ).all()
    name_lower = name.lower().strip()
    for h in hairdressers:
        if name_lower in h.name.lower() or h.name.lower() in name_lower:
            return h
    return None


def find_services_by_names(db: Session, salon_id: int, service_names: list) -> list:
    all_services = db.query(Service).filter(
        Service.salon_id == salon_id,
        Service.active == True
    ).all()
    matched = []
    for name in service_names:
        name_lower = name.lower().strip()
        for s in all_services:
            if name_lower in s.name.lower() or s.name.lower() in name_lower:
                if s not in matched:
                    matched.append(s)
    return matched


def is_slot_available(db: Session, hairdresser_id: int, start_time: datetime, end_time: datetime) -> bool:
    conflict = db.query(Appointment).filter(
        Appointment.hairdresser_id == hairdresser_id,
        Appointment.status != "cancelled",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time
    ).first()
    return conflict is None


def create_appointment_from_booking(db: Session, salon_id: int, booking_data: dict) -> Optional[Appointment]:
    hairdresser = find_hairdresser_by_name(db, salon_id, booking_data.get("hairdresser_name", ""))
    if not hairdresser:
        return None

    services = find_services_by_names(db, salon_id, booking_data.get("services", []))
    if not services:
        return None

    date_str = booking_data.get("date", "")
    time_str = booking_data.get("time", "")
    try:
        start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None

    total_duration = sum(s.duration_minutes for s in services)
    total_price = sum(s.price for s in services)
    end_time = start_time + timedelta(minutes=total_duration)

    if not is_slot_available(db, hairdresser.id, start_time, end_time):
        return None

    service_names = ", ".join(s.name for s in services)
    appointment = Appointment(
        salon_id=salon_id,
        hairdresser_id=hairdresser.id,
        customer_name=booking_data.get("customer_name", ""),
        customer_phone=booking_data.get("customer_phone", ""),
        services=service_names,
        start_time=start_time,
        end_time=end_time,
        total_price=total_price,
        total_duration_minutes=total_duration,
        status="confirmed",
        booked_via="phone"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def format_confirmation_message(appointment: Appointment, hairdresser_name: str) -> str:
    date_str = appointment.start_time.strftime("%A, den %d.%m.%Y")
    time_str = appointment.start_time.strftime("%H:%M")
    return (
        f"Perfekt! Ich habe Ihren Termin erfolgreich gebucht. "
        f"{date_str} um {time_str} Uhr bei {hairdresser_name} "
        f"für {appointment.services}. "
        f"Gesamtpreis: {appointment.total_price:.2f} Euro. "
        f"Wir freuen uns auf Ihren Besuch, {appointment.customer_name}! Auf Wiederhören."
    )


def format_conflict_message() -> str:
    return (
        "Leider ist dieser Termin bereits vergeben. "
        "Möchten Sie einen anderen Zeitpunkt wählen?"
    )
