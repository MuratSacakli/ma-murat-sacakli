"""
Liest Konfiguration zur Laufzeit:
Priorität: Datenbank (Dashboard) > .env-Datei
"""
from sqlalchemy.orm import Session


def get_runtime_config(db: Session) -> dict:
    from models import SystemSettings
    from config import settings as env

    s = db.query(SystemSettings).filter(SystemSettings.id == 1).first()

    def pick(db_val, env_val):
        return db_val if db_val else env_val

    return {
        "anthropic_api_key":  pick(s.anthropic_api_key if s else None,  env.ANTHROPIC_API_KEY),
        "claude_model":       pick(s.claude_model       if s else None,  env.CLAUDE_MODEL),
        "twilio_account_sid": pick(s.twilio_account_sid if s else None,  env.TWILIO_ACCOUNT_SID),
        "twilio_auth_token":  pick(s.twilio_auth_token  if s else None,  env.TWILIO_AUTH_TOKEN),
        "twilio_phone_number":pick(s.twilio_phone_number if s else None, env.TWILIO_PHONE_NUMBER),
        "base_url":           pick(s.base_url            if s else None, env.BASE_URL),
    }
