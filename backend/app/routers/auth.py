from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require, require_roles
from ..models import (ActivityLog, Company, FruitType, AlertRule, PasswordReset,
                      Notification, User)
from ..schemas import (CompanyIn, CompanyOut, ForgotIn, LoginIn, RegisterCompanyIn,
                       ResetIn, TokenOut, UserCreate, UserOut, UserUpdate)
from ..security import (create_access_token, hash_password, hash_reset_token,
                        new_reset_token, verify_password)
from ..services import log_activity

router = APIRouter()


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id, user.company_id, user.role),
                    user=UserOut.model_validate(user))


@router.post("/auth/register-company", response_model=TokenOut, status_code=201, tags=["auth"])
def register_company(data: RegisterCompanyIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Ese correo ya está registrado")
    if db.scalar(select(Company).where(Company.name == data.company_name)):
        raise HTTPException(409, "Ya existe una empresa con ese nombre")
    company = Company(name=data.company_name)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, email=data.email.lower(), full_name=data.admin_name,
                password_hash=hash_password(data.password), role="company_admin")
    db.add(user)
    # Reglas de alerta iniciales SIN límites: cada empresa debe configurarlos según su normativa
    db.add_all([AlertRule(company_id=company.id, method="IQF", active=False),
                AlertRule(company_id=company.id, method="PULPA", active=False)])
    db.flush()
    log_activity(db, user, "registro", "companies", company.id)
    db.commit()
    return _token(user)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Credenciales incorrectas")
    log_activity(db, user, "login", "users", user.id)
    db.commit()
    return _token(user)


@router.post("/auth/logout", tags=["auth"])
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # JWT sin estado: el cliente descarta el token. Se registra el evento.
    log_activity(db, user, "logout", "users", user.id)
    db.commit()
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/auth/forgot-password", tags=["auth"])
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    resp: dict = {"ok": True, "message": "Si el correo existe, recibirás instrucciones."}
    if user and user.active:
        raw, hashed = new_reset_token()
        db.add(PasswordReset(user_id=user.id, token_hash=hashed,
                             expires_at=datetime.utcnow() + timedelta(minutes=settings.reset_token_minutes)))
        db.commit()
        # TODO etapa 3: enviar por SMTP. En modo desarrollo se devuelve para poder probar el flujo.
        if settings.dev_mode:
            resp["dev_token"] = raw
    return resp


@router.post("/auth/reset-password", tags=["auth"])
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    pr = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == hash_reset_token(data.token)))
    if not pr or pr.used or pr.expires_at < datetime.utcnow():
        raise HTTPException(400, "Token inválido o vencido")
    user = db.get(User, pr.user_id)
    user.password_hash = hash_password(data.new_password)
    pr.used = True
    db.commit()
    return {"ok": True}


# ---------- Administración de usuarios de la empresa ----------
@router.get("/users", response_model=list[UserOut], tags=["usuarios"])
def list_users(user: User = Depends(require("manage_users")), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.company_id == user.company_id).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201, tags=["usuarios"])
def create_user(data: UserCreate, user: User = Depends(require("manage_users")),
                db: Session = Depends(get_db)):
    if data.role == "superadmin" and user.role != "superadmin":
        raise HTTPException(403, "Solo un superadministrador puede crear otro")
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Ese correo ya está registrado")
    new = User(company_id=user.company_id, email=data.email.lower(), full_name=data.full_name,
               password_hash=hash_password(data.password), role=data.role, plant_id=data.plant_id)
    db.add(new)
    db.flush()
    log_activity(db, user, "crear", "users", new.id, f"rol={new.role}")
    db.commit()
    return new


@router.patch("/users/{user_id}", response_model=UserOut, tags=["usuarios"])
def update_user(user_id: int, data: UserUpdate, user: User = Depends(require("manage_users")),
                db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(User.id == user_id, User.company_id == user.company_id))
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    if data.role == "superadmin" and user.role != "superadmin":
        raise HTTPException(403, "Solo un superadministrador puede asignar ese rol")
    if target.id == user.id and (data.active is False or (data.role and data.role != user.role)):
        raise HTTPException(400, "No puedes desactivarte ni cambiar tu propio rol")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(target, k, v)
    log_activity(db, user, "editar", "users", target.id)
    db.commit()
    return target


# ---------- Perfil de empresa ----------
@router.get("/company", response_model=CompanyOut, tags=["empresa"])
def get_company(user: User = Depends(require("read")), db: Session = Depends(get_db)):
    return db.get(Company, user.company_id)


@router.put("/company", response_model=CompanyOut, tags=["empresa"])
def update_company(data: CompanyIn, user: User = Depends(require("manage_settings")),
                   db: Session = Depends(get_db)):
    company = db.get(Company, user.company_id)
    for k, v in data.model_dump().items():
        setattr(company, k, v)
    log_activity(db, user, "editar", "companies", company.id)
    db.commit()
    return company


# ---------- Panel superadministrador ----------
@router.get("/admin/companies", tags=["admin"])
def admin_companies(user: User = Depends(require_roles("superadmin")), db: Session = Depends(get_db)):
    out = []
    for c in db.scalars(select(Company).order_by(Company.id)).all():
        n = len(db.scalars(select(User.id).where(User.company_id == c.id)).all())
        out.append({"id": c.id, "name": c.name, "is_demo": c.is_demo, "users": n,
                    "created_at": c.created_at})
    return out
