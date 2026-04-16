import json
import re
from datetime import datetime
from typing import Optional
import anthropic
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

LANG_LABELS = {
    "de": {"customer": "Kunde", "assistant": "Assistent"},
    "en": {"customer": "Customer", "assistant": "Assistant"},
    "tr": {"customer": "Müşteri",  "assistant": "Asistan"},
}

SYSTEM_PROMPT = """You are a friendly phone assistant for a hair salon. You MUST respond in the language the customer is speaking.

Supported languages: German (de), English (en), Turkish (tr).
- If the customer speaks German → respond in German
- If the customer speaks English → respond in English
- If the customer speaks Turkish → respond in Turkish

You naturally handle names from all backgrounds:
Arabic (Mohamed, Fatima, Omar...), Turkish (Murat, Ayşe, Yusuf...),
Albanian (Arben, Blerim, Shqipe...), Bosnian (Amir, Amira, Haris...),
German (Thomas, Maria, Klaus...) and all other names.
Always spell back names exactly as given — never change or Germanize them.

Your tasks:
1. Greet the customer. If they are a returning customer, greet them by name and mention their last visit.
2. Ask which hairdresser they prefer (list available names)
3. Ask which service(s) they want (list services with prices)
4. Ask for preferred date and time
5. If new customer: ask for their name and phone number
6. Confirm the booking

Rules:
- Always friendly and natural, like a real employee
- Keep answers short (max 3 sentences)
- Today is {today}

Salon information:
{salon_info}

Available hairdressers:
{hairdressers}

Available services:
{services}

Returning customer info (if known):
{customer_info}

Booking data collected so far:
{booking_data}

When ALL booking data is complete (hairdresser, service(s), date+time, customer name, customer phone),
output EXACTLY this JSON at the end of your response — no other format:
BOOKING_COMPLETE:{{"hairdresser_name": "...", "services": ["..."], "date": "YYYY-MM-DD", "time": "HH:MM", "customer_name": "...", "customer_phone": "...", "detected_language": "de|en|tr"}}"""


def build_system_prompt(salon, hairdressers, services, booking_data: dict, customer=None) -> str:
    salon_info = (
        f"Name: {salon.name}\n"
        f"Address: {salon.address or 'not specified'}\n"
        f"Opening hours: {salon.opening_time} - {salon.closing_time}"
    )

    hairdressers_text = "\n".join([
        f"- {h.name}" + (f" (specialization: {h.specialization})" if h.specialization else "")
        for h in hairdressers
    ]) or "No hairdressers available"

    services_text = "\n".join([
        f"- {s.name}: {s.price:.2f}€, duration: {s.duration_minutes} min"
        + (f" ({s.description})" if s.description else "")
        for s in services
    ]) or "No services available"

    if customer:
        last_visit = customer.last_visit.strftime("%d.%m.%Y") if customer.last_visit else "first visit"
        pref_lang = {"de": "German", "en": "English", "tr": "Turkish"}.get(customer.preferred_language, "German")
        customer_info = (
            f"Name: {customer.name}\n"
            f"Phone: {customer.phone}\n"
            f"Visits: {customer.visit_count}\n"
            f"Last visit: {last_visit}\n"
            f"Preferred language: {pref_lang}\n"
            + (f"Notes: {customer.notes}" if customer.notes else "")
        )
    else:
        customer_info = "New customer (not yet in database)"

    booking_summary = json.dumps(booking_data, ensure_ascii=False, indent=2) if booking_data else "No data collected yet"

    return SYSTEM_PROMPT.format(
        today=datetime.now().strftime("%A, %d.%m.%Y"),
        salon_info=salon_info,
        hairdressers=hairdressers_text,
        services=services_text,
        customer_info=customer_info,
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
    return re.sub(r'BOOKING_COMPLETE:\{.*?\}', '', response_text, flags=re.DOTALL).strip()


def get_ai_response(
    conversation_history: list,
    salon,
    hairdressers: list,
    services: list,
    booking_data: dict,
    customer=None
) -> tuple[str, Optional[dict]]:
    system_prompt = build_system_prompt(salon, hairdressers, services, booking_data, customer)

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


def get_greeting(salon_name: str, customer=None, language: str = "de") -> str:
    if customer:
        greetings = {
            "de": f"Guten Tag, {customer.name}! Schön, dass Sie sich wieder bei {salon_name} melden. Wie kann ich Ihnen helfen?",
            "en": f"Hello, {customer.name}! Great to hear from you again at {salon_name}. How can I help you?",
            "tr": f"Merhaba, {customer.name}! {salon_name}'ı tekrar aradığınız için teşekkürler. Size nasıl yardımcı olabilirim?",
        }
    else:
        greetings = {
            "de": f"Guten Tag! Sie sind verbunden mit dem Friseursalon {salon_name}. Ich bin Ihr digitaler Buchungsassistent. Wie kann ich Ihnen helfen? Sie können auch auf Englisch oder Türkisch sprechen.",
            "en": f"Hello! You've reached {salon_name}. I'm your digital booking assistant. How can I help you today?",
            "tr": f"Merhaba! {salon_name}'ı aradınız. Ben dijital rezervasyon asistanınızım. Size nasıl yardımcı olabilirim?",
        }
    return greetings.get(language, greetings["de"])
