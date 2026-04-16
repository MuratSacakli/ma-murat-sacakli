import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Salon, Hairdresser, Service, CallSession
from services.ai_assistant import get_ai_response, get_greeting
from services.booking_service import (
    create_appointment_from_booking,
    format_confirmation_message,
    format_conflict_message
)
from config import settings

router = APIRouter(prefix="/calls", tags=["Telefonanrufe"])

TWIML_GATHER = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="de-DE" voice="Polly.Vicki">{message}</Say>
    <Gather input="speech" language="de-DE" speechTimeout="auto" action="{action_url}" method="POST">
        <Say language="de-DE" voice="Polly.Vicki">Bitte sprechen Sie jetzt.</Say>
    </Gather>
    <Redirect>{action_url}</Redirect>
</Response>"""

TWIML_SAY_HANGUP = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="de-DE" voice="Polly.Vicki">{message}</Say>
    <Hangup/>
</Response>"""

TWIML_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="de-DE" voice="Polly.Vicki">Es tut mir leid, es ist ein technischer Fehler aufgetreten. Bitte rufen Sie später erneut an.</Say>
    <Hangup/>
</Response>"""


def get_salon_by_twilio_number(db: Session, twilio_number: str) -> Salon:
    return db.query(Salon).filter(
        Salon.twilio_phone_number == twilio_number,
        Salon.active == True
    ).first()


@router.post("/incoming")
async def handle_incoming_call(
    request: Request,
    db: Session = Depends(get_db)
):
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

        session = CallSession(
            call_sid=call_sid,
            salon_id=salon.id,
            caller_phone=caller,
            conversation_history=json.dumps([]),
            booking_data=json.dumps({})
        )
        db.add(session)
        db.commit()

        greeting = get_greeting(salon.name)
        action_url = f"{settings.BASE_URL}/calls/respond/{call_sid}"
        twiml = TWIML_GATHER.format(message=greeting, action_url=action_url)
        return Response(content=twiml, media_type="application/xml")

    except Exception:
        return Response(content=TWIML_ERROR, media_type="application/xml")


@router.post("/respond/{call_sid}")
async def handle_speech_response(
    call_sid: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        speech_result = form_data.get("SpeechResult", "")

        session = db.query(CallSession).filter(CallSession.call_sid == call_sid).first()
        if not session:
            return Response(content=TWIML_ERROR, media_type="application/xml")

        salon = db.query(Salon).filter(Salon.id == session.salon_id).first()
        hairdressers = db.query(Hairdresser).filter(
            Hairdresser.salon_id == salon.id,
            Hairdresser.active == True
        ).all()
        services = db.query(Service).filter(
            Service.salon_id == salon.id,
            Service.active == True
        ).all()

        conversation_history = json.loads(session.conversation_history)
        booking_data = json.loads(session.booking_data)

        conversation_history.append({"role": "user", "content": speech_result})

        ai_response, booking_complete = get_ai_response(
            conversation_history=conversation_history,
            salon=salon,
            hairdressers=hairdressers,
            services=services,
            booking_data=booking_data
        )

        conversation_history.append({"role": "assistant", "content": ai_response})
        action_url = f"{settings.BASE_URL}/calls/respond/{call_sid}"

        if booking_complete:
            appointment = create_appointment_from_booking(db, salon.id, booking_complete)

            if appointment:
                hairdresser = next(
                    (h for h in hairdressers if h.id == appointment.hairdresser_id), None
                )
                hairdresser_name = hairdresser.name if hairdresser else booking_complete.get("hairdresser_name", "")
                confirmation = format_confirmation_message(appointment, hairdresser_name)

                session.status = "completed"
                session.ended_at = datetime.utcnow()
                session.conversation_history = json.dumps(conversation_history)
                db.commit()

                twiml = TWIML_SAY_HANGUP.format(message=confirmation)
                return Response(content=twiml, media_type="application/xml")
            else:
                conflict_msg = format_conflict_message()
                ai_response = conflict_msg
                booking_data = {}

        session.conversation_history = json.dumps(conversation_history)
        session.booking_data = json.dumps(booking_data)
        db.commit()

        twiml = TWIML_GATHER.format(message=ai_response, action_url=action_url)
        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        return Response(content=TWIML_ERROR, media_type="application/xml")


@router.get("/sessions")
def list_call_sessions(salon_id: int = None, db: Session = Depends(get_db)):
    query = db.query(CallSession)
    if salon_id:
        query = query.filter(CallSession.salon_id == salon_id)
    return query.order_by(CallSession.created_at.desc()).limit(50).all()
