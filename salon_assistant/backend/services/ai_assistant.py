import json
import re
from datetime import datetime, timedelta
from typing import Optional
import anthropic
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Du bist ein freundlicher Telefonassistent für einen Friseursalon.
Du sprichst ausschließlich Deutsch und hilfst Kunden dabei, Termine zu buchen.

Deine Aufgaben:
1. Begrüße den Kunden herzlich mit dem Salonnamen
2. Frage nach dem gewünschten Friseur (nenne die verfügbaren Namen)
3. Frage nach der gewünschten Dienstleistung (nenne die verfügbaren Dienstleistungen mit Preisen)
4. Frage nach dem Wunschtermin (Datum und Uhrzeit)
5. Frage nach dem Namen und der Telefonnummer des Kunden
6. Bestätige die Buchung

Wichtige Regeln:
- Sei immer freundlich und professionell
- Sprich natürlich, wie ein echter Mitarbeiter
- Halte Antworten kurz und klar (max. 3 Sätze)
- Wenn du Informationen sammelst, extrahiere sie präzise
- Bei Unklarheiten frage freundlich nach
- Das heutige Datum ist {today}

Salon-Informationen:
{salon_info}

Verfügbare Friseure:
{hairdressers}

Verfügbare Dienstleistungen:
{services}

Gesammelte Buchungsdaten bisher:
{booking_data}

Wenn alle Buchungsdaten vollständig sind (Friseur, Dienstleistung(en), Datum+Uhrzeit, Kundenname, Kundennummer),
gib am Ende deiner Antwort EXAKT diesen JSON-Block aus (in keinem anderen Format):
BOOKING_COMPLETE:{{
  "hairdresser_name": "Name des Friseurs",
  "services": ["Dienstleistung 1", "Dienstleistung 2"],
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "customer_name": "Kundenname",
  "customer_phone": "Telefonnummer"
}}"""


def build_system_prompt(salon, hairdressers, services, booking_data: dict) -> str:
    salon_info = f"Name: {salon.name}\nAdresse: {salon.address or 'nicht angegeben'}\nÖffnungszeiten: {salon.opening_time} - {salon.closing_time} Uhr"

    hairdressers_text = "\n".join([
        f"- {h.name}" + (f" (Spezialisierung: {h.specialization})" if h.specialization else "")
        for h in hairdressers
    ]) or "Keine Friseure verfügbar"

    services_text = "\n".join([
        f"- {s.name}: {s.price:.2f}€, Dauer: {s.duration_minutes} Min."
        + (f" ({s.description})" if s.description else "")
        for s in services
    ]) or "Keine Dienstleistungen verfügbar"

    booking_summary = json.dumps(booking_data, ensure_ascii=False, indent=2) if booking_data else "Noch keine Daten gesammelt"

    return SYSTEM_PROMPT.format(
        today=datetime.now().strftime("%A, %d.%m.%Y"),
        salon_info=salon_info,
        hairdressers=hairdressers_text,
        services=services_text,
        booking_data=booking_summary
    )


def extract_booking_from_response(response_text: str) -> Optional[dict]:
    match = re.search(r'BOOKING_COMPLETE:(\{.*?\})', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def clean_response_for_speech(response_text: str) -> str:
    cleaned = re.sub(r'BOOKING_COMPLETE:\{.*?\}', '', response_text, flags=re.DOTALL)
    return cleaned.strip()


def get_ai_response(
    conversation_history: list,
    salon,
    hairdressers: list,
    services: list,
    booking_data: dict
) -> tuple[str, Optional[dict]]:
    system_prompt = build_system_prompt(salon, hairdressers, services, booking_data)

    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=conversation_history
    )

    full_response = response.content[0].text
    booking_complete = extract_booking_from_response(full_response)
    speech_text = clean_response_for_speech(full_response)

    return speech_text, booking_complete


def get_greeting(salon_name: str) -> str:
    return (
        f"Guten Tag! Sie sind verbunden mit dem Friseursalon {salon_name}. "
        f"Ich bin Ihr digitaler Buchungsassistent. "
        f"Wie kann ich Ihnen helfen? Möchten Sie einen Termin vereinbaren?"
    )
