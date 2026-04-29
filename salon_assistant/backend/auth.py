"""JWT + Passwort-Hashing komplett mit Python-Bordmitteln."""
import hmac
import hashlib
import base64
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
from config import settings

TOKEN_EXPIRE_HOURS = 8
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + '=' * (padding % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return f"pbkdf2${salt}${h}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        expected = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260000).hex()
        return hmac.compare_digest(expected, h)
    except Exception:
        return False


def create_token(user_id: int, salon_id: Optional[int], is_superadmin: bool) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    expire = (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp()
    payload = _b64url(json.dumps({
        "sub": str(user_id),
        "salon_id": salon_id,
        "superadmin": is_superadmin,
        "exp": expire
    }).encode())
    sig_input = f"{header}.{payload}".encode()
    sig = _b64url(hmac.new(settings.SECRET_KEY.encode(), sig_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def decode_token(token: str) -> dict:
    try:
        header, payload, sig = token.split(".")
        sig_input = f"{header}.{payload}".encode()
        expected = _b64url(hmac.new(settings.SECRET_KEY.encode(), sig_input, hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = json.loads(_b64url_decode(payload))
        if data["exp"] < datetime.utcnow().timestamp():
            raise ValueError("expired")
        return data
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ungültig oder abgelaufen")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    user = db.query(User).filter(User.id == int(payload["sub"]), User.active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Benutzer nicht gefunden")
    return user


def require_salon_access(salon_id: int, current_user: User):
    if current_user.is_superadmin:
        return
    if current_user.salon_id != salon_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf diesen Salon")
