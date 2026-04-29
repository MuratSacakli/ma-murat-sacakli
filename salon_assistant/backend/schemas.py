from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class SalonBase(BaseModel):
    name: str
    phone: str
    address: Optional[str] = None
    email: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    opening_time: str = "09:00"
    closing_time: str = "18:00"
    slot_duration_minutes: int = 30


class SalonCreate(SalonBase):
    pass


class SalonUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    active: Optional[bool] = None


class SalonResponse(SalonBase):
    id: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HairdresserBase(BaseModel):
    name: str
    specialization: Optional[str] = None


class HairdresserCreate(HairdresserBase):
    salon_id: int


class HairdresserUpdate(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    active: Optional[bool] = None


class HairdresserResponse(HairdresserBase):
    id: int
    salon_id: int
    active: bool

    class Config:
        from_attributes = True


class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float


class ServiceCreate(ServiceBase):
    salon_id: int


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int
    salon_id: int
    active: bool

    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    customer_name: str
    customer_phone: str
    services: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    salon_id: int
    hairdresser_id: int
    total_price: Optional[float] = None
    total_duration_minutes: Optional[int] = None


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: int
    salon_id: int
    hairdresser_id: int
    total_price: Optional[float] = None
    total_duration_minutes: Optional[int] = None
    status: str
    created_at: datetime
    booked_via: str

    class Config:
        from_attributes = True


class AvailabilityRequest(BaseModel):
    salon_id: int
    hairdresser_id: int
    date: str
    duration_minutes: int


class CustomerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    preferred_language: str = "de"
    preferred_hairdresser_id: Optional[int] = None
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    salon_id: int


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_hairdresser_id: Optional[int] = None
    notes: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: int
    salon_id: int
    visit_count: int
    created_at: datetime
    last_visit: Optional[datetime] = None

    class Config:
        from_attributes = True
