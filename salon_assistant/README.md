# Salon Buchungsassistent

Ein KI-gestützter Telefonassistent für Friseursalons. Kunden rufen an, sprechen mit einer KI auf Deutsch und buchen automatisch Termine.

## Funktionen

- **KI-Telefonassistent**: Nimmt Anrufe entgegen, versteht Sprache, bucht Termine vollautomatisch
- **Multi-Salon**: Verwaltung mehrerer Salons mit einer Installation
- **Web-Dashboard**: Termine, Friseure und Dienstleistungen verwalten
- **Anruf-Protokoll**: Alle Gespräche einsehbar inkl. Verlauf
- **Konflikterkennung**: Doppelbuchungen werden automatisch verhindert

## Technologie

| Komponente | Technologie |
|---|---|
| Backend | FastAPI (Python) |
| KI-Assistent | Claude claude-sonnet-4-6 (Anthropic) |
| Telefonie | Twilio Voice API |
| Datenbank | SQLite (Produktion: PostgreSQL) |
| Frontend | HTML/CSS/JS (kein Framework) |

## Installation

### 1. Abhängigkeiten installieren

```bash
cd salon_assistant
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# .env bearbeiten und API-Keys eintragen
```

### 3. Demo-Daten laden (optional)

```bash
cd backend
python seed_data.py
```

### 4. Server starten

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Dashboard: http://localhost:8000

## Twilio-Konfiguration

1. Twilio-Account erstellen: https://www.twilio.com
2. Telefonnummer kaufen (deutsche Nummer)
3. In Twilio-Console: Webhook für "Wenn ein Anruf eingeht" konfigurieren:
   - URL: `https://ihre-domain.de/calls/incoming`
   - Methode: HTTP POST
4. Für lokale Entwicklung: [ngrok](https://ngrok.com) verwenden

```bash
ngrok http 8000
# URL aus ngrok als BASE_URL in .env eintragen
```

## Gesprächsablauf

```
Kunde ruft an
    ↓
"Willkommen beim Salon Bella, ich bin Ihr digitaler Assistent..."
    ↓
"Welchen Friseur wünschen Sie? Wir haben: Maria, Thomas, Lisa..."
    ↓
"Welche Dienstleistung? Haarschnitt 45€, Colorierung 75€..."
    ↓
"Wann soll der Termin sein? Datum und Uhrzeit bitte."
    ↓
"Ihr Name und Telefonnummer bitte."
    ↓
"Ihr Termin ist gebucht! Montag 14:00 Uhr bei Maria..."
    ↓
Termin erscheint im Dashboard
```

## API-Endpunkte

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | /api/salons/ | Alle Salons |
| POST | /api/salons/ | Salon erstellen |
| GET | /api/salons/{id}/hairdressers | Friseure eines Salons |
| GET | /api/salons/{id}/services | Dienstleistungen eines Salons |
| GET | /api/appointments/ | Termine (mit Filtern) |
| POST | /api/appointments/ | Termin erstellen |
| POST | /api/appointments/availability | Freie Slots abfragen |
| POST | /calls/incoming | Twilio Webhook (eingehender Anruf) |
| POST | /calls/respond/{call_sid} | Twilio Webhook (Spracherkennung) |

Interaktive API-Dokumentation: http://localhost:8000/docs
