from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from auth import get_current_user
from models import User
from models import SystemSettings

router = APIRouter(prefix="/api/settings", tags=["Systemeinstellungen"])

CLAUDE_MODELS = [
    {"id": "claude-sonnet-4-6",         "label": "Claude Sonnet 4.6 — Standard (empfohlen)"},
    {"id": "claude-opus-4-7",           "label": "Claude Opus 4.7 — Leistungsstark"},
    {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 — Schnell & günstig"},
]


class SettingsUpdate(BaseModel):
    anthropic_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    base_url: Optional[str] = None


class SettingsResponse(BaseModel):
    anthropic_api_key_set: bool
    anthropic_api_key_preview: str
    claude_model: str
    twilio_account_sid: str
    twilio_auth_token_set: bool
    twilio_phone_number: str
    base_url: str
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _get_or_create(db: Session) -> SystemSettings:
    s = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not s:
        s = SystemSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _mask(value: str) -> str:
    if not value:
        return ""
    return value[:6] + "••••••••" + value[-4:] if len(value) > 10 else "••••••••"


@router.get("/", response_model=SettingsResponse)
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_or_create(db)
    from config import settings as env_settings
    return SettingsResponse(
        anthropic_api_key_set=bool(s.anthropic_api_key or env_settings.ANTHROPIC_API_KEY),
        anthropic_api_key_preview=_mask(s.anthropic_api_key or env_settings.ANTHROPIC_API_KEY),
        claude_model=s.claude_model or env_settings.CLAUDE_MODEL,
        twilio_account_sid=s.twilio_account_sid or env_settings.TWILIO_ACCOUNT_SID or "",
        twilio_auth_token_set=bool(s.twilio_auth_token or env_settings.TWILIO_AUTH_TOKEN),
        twilio_phone_number=s.twilio_phone_number or env_settings.TWILIO_PHONE_NUMBER or "",
        base_url=s.base_url or env_settings.BASE_URL or "",
        updated_at=s.updated_at
    )


@router.put("/")
def update_settings(update: SettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins dürfen Systemeinstellungen ändern")
    s = _get_or_create(db)
    for field, value in update.model_dump(exclude_none=True).items():
        if value != "":
            setattr(s, field, value)
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Einstellungen gespeichert"}


@router.get("/models")
def list_models():
    return CLAUDE_MODELS


@router.post("/test-connection")
def test_connection(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.runtime_config import get_runtime_config
    cfg = get_runtime_config(db)
    results = {}

    # Anthropic test
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])
        client.messages.create(
            model=cfg["claude_model"],
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}]
        )
        results["anthropic"] = {"ok": True, "message": "Verbindung erfolgreich"}
    except Exception as e:
        results["anthropic"] = {"ok": False, "message": str(e)[:120]}

    # Twilio test
    try:
        from twilio.rest import Client
        client = Client(cfg["twilio_account_sid"], cfg["twilio_auth_token"])
        client.api.accounts(cfg["twilio_account_sid"]).fetch()
        results["twilio"] = {"ok": True, "message": "Verbindung erfolgreich"}
    except Exception as e:
        results["twilio"] = {"ok": False, "message": str(e)[:120]}

    return results
