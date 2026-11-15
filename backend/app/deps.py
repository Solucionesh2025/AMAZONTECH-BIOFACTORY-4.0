import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)

ROLES = ["superadmin", "company_admin", "manager", "supervisor", "operator", "warehouse"]

PERMISSIONS = {
    "superadmin": {"*"},
    "company_admin": {"*"},
    "manager": {"read", "write_ops", "write_inventory", "write_costs", "manage_settings", "reports"},
    "supervisor": {"read", "write_ops", "write_inventory", "reports"},
    "operator": {"read", "write_ops"},
    "warehouse": {"read", "write_inventory"},
}


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "No autenticado")
    try:
        data = decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido o expirado")
    user = db.get(User, int(data["sub"]))
    if not user or not user.active:
        raise HTTPException(401, "Usuario inactivo o inexistente")
    return user


def require(perm: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        perms = PERMISSIONS.get(user.role, set())
        if "*" not in perms and perm not in perms:
            raise HTTPException(403, "Tu rol no tiene permiso para esta acción")
        return user
    return checker


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Acceso restringido")
        return user
    return checker
