"""Fábrica de routers CRUD con aislamiento por empresa, permisos por rol y bitácora."""
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .deps import require
from .models import User
from .services import log_activity


def crud_router(prefix: str, tag: str, Model, In, Out, write_perm: str,
                fk: dict | None = None, before_save: Callable | None = None,
                after_save: Callable | None = None) -> APIRouter:
    fk = fk or {}
    entity = Model.__tablename__
    r = APIRouter(prefix=prefix, tags=[tag])

    def get_owned(db: Session, user: User, obj_id: int):
        obj = db.scalar(select(Model).where(Model.id == obj_id, Model.company_id == user.company_id))
        if not obj:
            raise HTTPException(404, "Registro no encontrado")
        return obj

    def prepare(db: Session, user: User, values: dict) -> dict:
        for field, M in fk.items():
            v = values.get(field)
            if v is not None and not db.scalar(
                    select(M.id).where(M.id == v, M.company_id == user.company_id)):
                raise HTTPException(422, f"{field} no existe en tu empresa")
        if before_save:
            values = before_save(db, user, values) or values
        return values

    @r.get("", response_model=list[Out])
    def list_(limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
              user: User = Depends(require("read")), db: Session = Depends(get_db)):
        stmt = (select(Model).where(Model.company_id == user.company_id)
                .order_by(Model.id.desc()).limit(limit).offset(offset))
        return db.scalars(stmt).all()

    @r.get("/{obj_id}", response_model=Out)
    def get_(obj_id: int, user: User = Depends(require("read")), db: Session = Depends(get_db)):
        return get_owned(db, user, obj_id)

    @r.post("", response_model=Out, status_code=201)
    def create(data: In, user: User = Depends(require(write_perm)), db: Session = Depends(get_db)):  # type: ignore
        values = prepare(db, user, data.model_dump())
        obj = Model(company_id=user.company_id, **values)
        db.add(obj)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Registro duplicado o inválido")
        log_activity(db, user, "crear", entity, obj.id)
        if after_save:
            after_save(db, user, obj)
        db.commit()
        return obj

    @r.put("/{obj_id}", response_model=Out)
    def update(obj_id: int, data: In, user: User = Depends(require(write_perm)),  # type: ignore
               db: Session = Depends(get_db)):
        obj = get_owned(db, user, obj_id)
        for k, v in prepare(db, user, data.model_dump()).items():
            setattr(obj, k, v)
        log_activity(db, user, "editar", entity, obj.id)
        if after_save:
            after_save(db, user, obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Registro duplicado o inválido")
        return obj

    @r.delete("/{obj_id}", status_code=204)
    def delete(obj_id: int, user: User = Depends(require(write_perm)), db: Session = Depends(get_db)):
        obj = get_owned(db, user, obj_id)
        db.delete(obj)
        log_activity(db, user, "eliminar", entity, obj_id)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "No se puede eliminar: tiene registros asociados")

    return r
