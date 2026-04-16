"""Demo-Daten für Entwicklung und Präsentation."""
from database import SessionLocal, init_db
from models import Salon, Hairdresser, Service


def seed():
    init_db()
    db = SessionLocal()

    existing = db.query(Salon).first()
    if existing:
        print("Demo-Daten bereits vorhanden.")
        db.close()
        return

    salon = Salon(
        name="Salon Bella",
        phone="+49 30 12345678",
        address="Musterstraße 1, 10115 Berlin",
        email="info@salon-bella.de",
        twilio_phone_number="+49301234567",
        opening_time="09:00",
        closing_time="19:00",
        slot_duration_minutes=15
    )
    db.add(salon)
    db.flush()

    hairdressers_data = [
        {"name": "Maria Schmidt", "specialization": "Colorierung, Balayage"},
        {"name": "Thomas Müller", "specialization": "Herrenschnitte, Bartpflege"},
        {"name": "Lisa Wagner", "specialization": "Brautfrisuren, Hochsteckfrisuren"},
        {"name": "Kevin Braun", "specialization": "Afro, Locken"},
    ]
    for hd in hairdressers_data:
        db.add(Hairdresser(salon_id=salon.id, **hd))

    services_data = [
        {"name": "Damenhaarschnitt", "description": "Waschen, Schneiden, Föhnen", "duration_minutes": 60, "price": 45.00},
        {"name": "Herrenhaarschnitt", "description": "Waschen, Schneiden, Föhnen", "duration_minutes": 30, "price": 25.00},
        {"name": "Colorierung", "description": "Vollcolorierung inkl. Pflege", "duration_minutes": 90, "price": 75.00},
        {"name": "Balayage", "description": "Handgemachte Aufhellung", "duration_minutes": 120, "price": 120.00},
        {"name": "Strähnen", "description": "Highlights mit Folie", "duration_minutes": 90, "price": 85.00},
        {"name": "Dauerwelle", "description": "Klassische oder Volumen-Dauerwelle", "duration_minutes": 120, "price": 95.00},
        {"name": "Bartpflege", "description": "Bart schneiden und formen", "duration_minutes": 20, "price": 15.00},
        {"name": "Haarpflege-Kur", "description": "Intensive Haarpflege-Behandlung", "duration_minutes": 30, "price": 25.00},
        {"name": "Brautfrisur", "description": "Aufsteckfrisur für besondere Anlässe", "duration_minutes": 90, "price": 150.00},
        {"name": "Kinder-Haarschnitt", "description": "Für Kinder bis 12 Jahre", "duration_minutes": 30, "price": 18.00},
    ]
    for sd in services_data:
        db.add(Service(salon_id=salon.id, **sd))

    db.commit()
    db.close()
    print(f"Demo-Daten erstellt: Salon '{salon.name}' mit {len(hairdressers_data)} Friseuren und {len(services_data)} Dienstleistungen.")


if __name__ == "__main__":
    seed()
