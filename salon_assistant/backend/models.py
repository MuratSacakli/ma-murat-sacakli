from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Time
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Salon(Base):
    __tablename__ = "salons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(String(500))
    email = Column(String(200))
    twilio_phone_number = Column(String(50), unique=True)
    opening_time = Column(String(5), default="09:00")
    closing_time = Column(String(5), default="18:00")
    slot_duration_minutes = Column(Integer, default=30)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hairdressers = relationship("Hairdresser", back_populates="salon", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="salon", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="salon", cascade="all, delete-orphan")
    call_sessions = relationship("CallSession", back_populates="salon", cascade="all, delete-orphan")


class Hairdresser(Base):
    __tablename__ = "hairdressers"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String(200), nullable=False)
    specialization = Column(String(500))
    active = Column(Boolean, default=True)

    salon = relationship("Salon", back_populates="hairdressers")
    appointments = relationship("Appointment", back_populates="hairdresser")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False, default=30)
    price = Column(Float, nullable=False)
    active = Column(Boolean, default=True)

    salon = relationship("Salon", back_populates="services")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    hairdresser_id = Column(Integer, ForeignKey("hairdressers.id"), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    services = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_price = Column(Float)
    total_duration_minutes = Column(Integer)
    status = Column(String(50), default="confirmed")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    booked_via = Column(String(50), default="phone")

    salon = relationship("Salon", back_populates="appointments")
    hairdresser = relationship("Hairdresser", back_populates="appointments")


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=True)
    call_sid = Column(String(200), unique=True, nullable=False)
    caller_phone = Column(String(50))
    conversation_history = Column(Text, default="[]")
    booking_data = Column(Text, default="{}")
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    salon = relationship("Salon", back_populates="call_sessions")
