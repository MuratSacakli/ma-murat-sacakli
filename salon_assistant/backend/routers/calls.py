import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Salon, Hairdresser, Service, CallSession, Customer
from services.ai_assistant import get_ai_response, get_greeting
from services.booking_service import (
    create_appointment_from_booking,
    format_confirmation_message,
    format_conflict_message
)
from config import settings

router = APIRouter(prefix="/calls", tags=["Telefonanrufe"])

LANG_VOICE = {
    "de": ("de-DE", "Polly.Vicki"),
    "en": ("en-US", "Polly.Joanna"),
    "tr": ("tr-TR", "Polly.Filiz"),
}

TWIML_GATHER = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{lang}" voice="{voice}">{message}</Say>
    <Gather input="speech" language="{lang}" speechTimeout="auto" action="{action_url}" method="POST">
    </Gather>
    <Redirect>{action_url}</Redirect>
</Response>"""

TWIML_SAY_HANGUP = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{lang}" voice="{voice}">{message}</Say>
    <Hangup/>
</Response>"""

TWIML_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="de-DE" voice="Polly.Vicki">Es tut mir leid, es ist ein technischer Fehler aufgetreten. Bitte rufen Sie später erneut an.</Say>
    <Hangup/>
</Response>"""


def find_customer_by_phone(db: Session, salon_id: int, phone: str) -> Customer:
    import re as _re
    digits = _re.sub(r'[^\d+]', '', phone)
    customers = db.query(Customer).filter(Customer.salon_id == salon_id).all()
    for c in customers:
        if _re.sub(r'[^\d+]', '', c.phone) == digits:
            return c
    return None


def upsert_customer(db: Session, salon_id: int, booking_data: dict, language: str) -> Customer:
    phone = booking_data.get("customer_phone", "").strip().replace(" ", "")
    name = booking_data.get("customer_name", "")
    if not phone or not name:
        return None

    customer = find_customer_by_phone(db, salon_id, phone)
    if customer:
        customer.visit_count += 1
        customer.last_visit = datetime.utcnow()
        customer.preferred_language = language
    else:
        customer = Customer(
            salon_id=salon_id,
            name=name,
            phone=phone,
            preferred_language=language,
            visit_count=1,
            last_visit=datetime.utcnow()
        )
        db.add(customer)
    db.commit()
    return customer


def make_twiml_gather(message: str, action_url: str, language: str) -> str:
    lang_code, voice = LANG_VOICE.get(language, LANG_VOICE["de"])
    return TWIML_GATHER.format(
        lang=lang_code, voice=voice,
        message=message, action_url=action_url
    )


def make_twiml_hangup(message: str, language: str) -> str:
    lang_code, voice = LANG_VOICE.get(language, LANG_VOICE["de"])
    return TWIML_SAY_HANGUP.format(lang=lang_code, voice=voice, message=message)


def get_salon_by_twilio_number(db: Session, twilio_number: str) -> Salon:
    return db.query(Salon).filter(
        Salon.twilio_phone_number == twilio_number,
        Salon.active == True
    ).first()


@router.post("/incoming")
async def handle_incoming_call(request: Request, db: Session = Depends(get_db)):
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "unknown")
        caller = form_data.get("From", "unknown")
        called = form_data.get("To", "")

        salon = get_salon_by_twilio_number(db, called)
        if not salon:
            salon = db.query(Salon).filter(Salon.active == True).first()
        if not salon:
            return Response(content=TWIML_ERROR, media_type="application/xml")

        customer = find_customer_by_phone(db, salon.id, caller)
        language = customer.preferred_language if customer else "de"

        session = CallSession(
            call_sid=call_sid,
            salon_id=salon.id,
            customer_id=customer.id if customer else None,
            caller_phone=caller,
            detected_language=language,
            conversation_history=json.dumps([]),
            booking_data=json.dumps({})
        )
        db.add(session)
        db.commit()

        greeting = get_greeting(salon.name, customer=customer, language=language)
        action_url = f"{settings.BASE_URL}/calls/respond/{call_sid}"
        twiml = make_twiml_gather(greeting, action_url, language)
        return Response(content=twiml, media_type="application/xml")

    except Exception:
        return Response(content=TWIML_ERROR, media_type="application/xml")


@router.post("/respond/{call_sid}")
async def handle_speech_response(call_sid: str, request: Request, db: Session = Depends(get_db)):
    try:
        form_data = await request.form()
        speech_result = form_data.get("SpeechResult", "")

        session = db.query(CallSession).filter(CallSession.call_sid == call_sid).first()
        if not session:
            return Response(content=TWIML_ERROR, media_type="application/xml")

        salon = db.query(Salon).filter(Salon.id == session.salon_id).first()
        hairdressers = db.query(Hairdresser).filter(
            Hairdresser.salon_id == salon.id, Hairdresser.active == True
        ).all()
        services = db.query(Service).filter(
            Service.salon_id == salon.id, Service.active == True
        ).all()
        customer = db.query(Customer).filter(Customer.id == session.customer_id).first() if session.customer_id else None

        conversation_history = json.loads(session.conversation_history)
        booking_data = json.loads(session.booking_data)
        language = session.detected_language or "de"

        conversation_history.append({"role": "user", "content": speech_result})

        ai_response, booking_complete = get_ai_response(
            conversation_history=conversation_history,
            salon=salon,
            hairdressers=hairdressers,
            services=services,
            booking_data=booking_data,
            customer=customer
        )

        conversation_history.append({"role": "assistant", "content": ai_response})
        action_url = f"{settings.BASE_URL}/calls/respond/{call_sid}"

        if booking_complete:
            detected_lang = booking_complete.get("detected_language", language)
            session.detected_language = detected_lang
            language = detected_lang

            appointment = create_appointment_from_booking(db, salon.id, booking_complete)
            if appointment:
                upsert_customer(db, salon.id, booking_complete, detected_lang)

                hairdresser = next((h for h in hairdressers if h.id == appointment.hairdresser_id), None)
                hairdresser_name = hairdresser.name if hairdresser else booking_complete.get("hairdresser_name", "")
                confirmation = format_confirmation_message(appointment, hairdresser_name, detected_lang)

                session.status = "completed"
                session.ended_at = datetime.utcnow()
                session.conversation_history = json.dumps(conversation_history)
                db.commit()

                twiml = make_twiml_hangup(confirmation, detected_lang)
                return Response(content=twiml, media_type="application/xml")
            else:
                ai_response = format_conflict_message(language)
                booking_data = {}

        session.conversation_history = json.dumps(conversation_history)
        session.booking_data = json.dumps(booking_data)
        db.commit()

        twiml = make_twiml_gather(ai_response, action_url, language)
        return Response(content=twiml, media_type="application/xml")

    except Exception:
        return Response(content=TWIML_ERROR, media_type="application/xml")


@router.get("/sessions")
def list_call_sessions(salon_id: int = None, db: Session = Depends(get_db)):
    query = db.query(CallSession)
    if salon_id:
        query = query.filter(CallSession.salon_id == salon_id)
    return query.order_by(CallSession.created_at.desc()).limit(50).all()
