from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import BillingConfig, CallSession, Salon, User
from auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["Abrechnung"])


class BillingConfigUpdate(BaseModel):
    price_per_minute_eur: Optional[float] = None
    price_per_1k_tokens_eur: Optional[float] = None
    min_billing_minutes: Optional[float] = None


class BillingConfigResponse(BaseModel):
    price_per_minute_eur: float
    price_per_1k_tokens_eur: float
    min_billing_minutes: float
    currency: str
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _get_or_create_config(db: Session) -> BillingConfig:
    cfg = db.query(BillingConfig).filter(BillingConfig.id == 1).first()
    if not cfg:
        cfg = BillingConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _usage_query(db: Session, salon_id: int = None, month: str = None):
    q = db.query(CallSession)
    if salon_id:
        q = q.filter(CallSession.salon_id == salon_id)
    if month:
        y, m = map(int, month.split("-"))
        q = q.filter(
            func.strftime('%Y', CallSession.created_at) == str(y),
            func.strftime('%m', CallSession.created_at) == f"{m:02d}"
        )
    return q


# ─── Preiskonfiguration (nur Super-Admin) ─────────────────────────────────────
@router.get("/config", response_model=BillingConfigResponse)
def get_billing_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_or_create_config(db)


@router.put("/config", response_model=BillingConfigResponse)
def update_billing_config(update: BillingConfigUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins dürfen Preise konfigurieren")
    cfg = _get_or_create_config(db)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(cfg, field, value)
    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    return cfg


# ─── Nutzungsübersicht eines Salons ──────────────────────────────────────────
@router.get("/usage/{salon_id}")
def get_salon_usage(
    salon_id: int,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin and current_user.salon_id != salon_id:
        raise HTTPException(status_code=403, detail="Kein Zugriff")

    cfg = _get_or_create_config(db)
    sessions = _usage_query(db, salon_id=salon_id, month=month).all()

    total_minutes = sum((s.billed_minutes or 0) for s in sessions)
    total_tokens_in = sum((s.tokens_input or 0) for s in sessions)
    total_tokens_out = sum((s.tokens_output or 0) for s in sessions)
    total_tokens = total_tokens_in + total_tokens_out
    total_calls = len(sessions)
    completed = sum(1 for s in sessions if s.status == "completed")

    cost_minutes = total_minutes * cfg.price_per_minute_eur
    cost_tokens = (total_tokens / 1000) * cfg.price_per_1k_tokens_eur
    total_cost = cost_minutes + cost_tokens

    return {
        "salon_id": salon_id,
        "month": month or "all",
        "total_calls": total_calls,
        "completed_bookings": completed,
        "total_minutes": round(total_minutes, 2),
        "total_tokens_input": total_tokens_in,
        "total_tokens_output": total_tokens_out,
        "total_tokens": total_tokens,
        "cost_minutes_eur": round(cost_minutes, 4),
        "cost_tokens_eur": round(cost_tokens, 4),
        "total_cost_eur": round(total_cost, 4),
        "price_per_minute": cfg.price_per_minute_eur,
        "currency": cfg.currency,
    }


# ─── Übersicht ALLER Salons (nur Super-Admin) ─────────────────────────────────
@router.get("/overview")
def get_billing_overview(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins")

    cfg = _get_or_create_config(db)
    salons = db.query(Salon).filter(Salon.active == True).all()
    rows = []

    for salon in salons:
        sessions = _usage_query(db, salon_id=salon.id, month=month).all()
        mins = sum((s.billed_minutes or 0) for s in sessions)
        tokens = sum((s.tokens_input or 0) + (s.tokens_output or 0) for s in sessions)
        cost = mins * cfg.price_per_minute_eur + (tokens / 1000) * cfg.price_per_1k_tokens_eur
        rows.append({
            "salon_id": salon.id,
            "salon_name": salon.name,
            "calls": len(sessions),
            "minutes": round(mins, 2),
            "tokens": tokens,
            "cost_eur": round(cost, 4),
        })

    grand_total = sum(r["cost_eur"] for r in rows)
    return {
        "month": month or "all",
        "price_per_minute": cfg.price_per_minute_eur,
        "price_per_1k_tokens": cfg.price_per_1k_tokens_eur,
        "currency": cfg.currency,
        "salons": rows,
        "grand_total_eur": round(grand_total, 4),
    }


# ─── Einzelne Anrufe eines Salons ─────────────────────────────────────────────
@router.get("/calls/{salon_id}")
def get_call_details(
    salon_id: int,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin and current_user.salon_id != salon_id:
        raise HTTPException(status_code=403, detail="Kein Zugriff")

    cfg = _get_or_create_config(db)
    sessions = _usage_query(db, salon_id=salon_id, month=month).order_by(CallSession.created_at.desc()).limit(200).all()

    return [{
        "call_sid": s.call_sid,
        "date": s.created_at.isoformat(),
        "caller": s.caller_phone,
        "status": s.status,
        "duration_sec": s.duration_seconds or 0,
        "billed_min": round(s.billed_minutes or 0, 2),
        "tokens_in": s.tokens_input or 0,
        "tokens_out": s.tokens_output or 0,
        "cost_eur": round(
            (s.billed_minutes or 0) * cfg.price_per_minute_eur +
            ((s.tokens_input or 0) + (s.tokens_output or 0)) / 1000 * cfg.price_per_1k_tokens_eur,
            4
        ),
    } for s in sessions]
