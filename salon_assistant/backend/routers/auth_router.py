from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import User
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentifizierung"])


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    salon_id: Optional[int] = None
    is_superadmin: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    salon_id: Optional[int]
    is_superadmin: bool

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username, User.active == True).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch"
        )
    token = create_token(user.id, user.salon_id, user.is_superadmin)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Altes Passwort falsch")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Passwort geändert"}


# Nur Super-Admin darf Benutzer anlegen
@router.post("/users", response_model=UserResponse)
def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nur Super-Admins dürfen Benutzer anlegen")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Benutzername bereits vergeben")
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        salon_id=data.salon_id,
        is_superadmin=data.is_superadmin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Kein Zugriff")
    return db.query(User).filter(User.active == True).all()


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Kein Zugriff")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    user.active = False
    db.commit()
    return {"message": "Benutzer deaktiviert"}
