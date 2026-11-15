from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..crud import crud_router
from ..database import get_db
from ..deps import require
from ..models import (AlertRule, FreezingRecord, FruitType, InventoryItem, InventoryMovement,
                      Lot, Machine, Notification, PackagingRecord, Plant, PulpingRecord,
                      Supplier, User)
from ..schemas import (AlertRuleIn, AlertRuleOut, FreezingIn, FreezingOut, FruitIn, FruitOut,
                       InventoryItemIn, InventoryItemOut, LotIn, LotOut, MachineIn, MachineOut,
                       MovementIn, MovementOut, PackagingIn, PackagingOut, PlantIn, PlantOut,
                       PulpingIn, PulpingOut, SupplierIn, SupplierOut)
from ..services import log_activity, notify

router = APIRouter()


# ---- hooks ----
def lot_before(db: Session, user: User, v: dict):
    if not v.get("lot_number"):
        prefix = f"L-{v['received_on']:%Y%m%d}-"
        n = db.scalar(select(func.count(Lot.id)).where(
            Lot.company_id == user.company_id, Lot.lot_number.like(prefix + "%"))) or 0
        v["lot_number"] = f"{prefix}{n + 1:03d}"
    return v


def pulping_before(db: Session, user: User, v: dict):
    v["yield_pct"] = round(v["pulp_kg"] / v["initial_kg"] * 100, 2)  # Rendimiento = pulpa/inicial × 100
    return v


def packaging_before(db: Session, user: User, v: dict):
    v["total_kg"] = round(v["units"] * v["bag_grams"] / 1000, 3)
    v["bags_used"] = v["units"] + v["rejected_units"]
    return v


def freezing_before(db: Session, user: User, v: dict):
    msgs = []
    rule = db.scalar(select(AlertRule).where(AlertRule.company_id == user.company_id,
                                             AlertRule.method == v["method"], AlertRule.active == True))  # noqa: E712
    if rule:
        if rule.max_temp_c is not None and v["temp_c"] > rule.max_temp_c:
            msgs.append(f"Temperatura {v['temp_c']} °C por encima del límite configurado ({rule.max_temp_c} °C)")
        if rule.max_duration_min is not None and v["duration_min"] > rule.max_duration_min:
            msgs.append(f"Tiempo {v['duration_min']} min por encima del límite configurado ({rule.max_duration_min} min)")
    v["alert"] = bool(msgs)
    v["alert_message"] = "; ".join(msgs) or None
    if msgs:
        v["status"] = "alerta"
    return v


def freezing_after(db: Session, user: User, obj: FreezingRecord):
    if obj.alert:
        notify(db, user.company_id, f"Alerta de congelamiento (lote #{obj.lot_id}): {obj.alert_message}", "warning")


router.include_router(crud_router("/plants", "plantas", Plant, PlantIn, PlantOut, "manage_settings"))
router.include_router(crud_router("/fruits", "frutos", FruitType, FruitIn, FruitOut, "manage_settings"))
router.include_router(crud_router("/suppliers", "proveedores", Supplier, SupplierIn, SupplierOut, "write_ops"))
router.include_router(crud_router("/machines", "máquinas", Machine, MachineIn, MachineOut, "manage_settings",
                                  fk={"plant_id": Plant}))
router.include_router(crud_router("/lots", "recepción", Lot, LotIn, LotOut, "write_ops",
                                  fk={"fruit_id": FruitType, "supplier_id": Supplier, "plant_id": Plant},
                                  before_save=lot_before))
router.include_router(crud_router("/pulping", "despulpado", PulpingRecord, PulpingIn, PulpingOut, "write_ops",
                                  fk={"lot_id": Lot}, before_save=pulping_before))
router.include_router(crud_router("/freezing", "congelamiento", FreezingRecord, FreezingIn, FreezingOut,
                                  "write_ops", fk={"lot_id": Lot}, before_save=freezing_before,
                                  after_save=freezing_after))
router.include_router(crud_router("/alert-rules", "congelamiento", AlertRule, AlertRuleIn, AlertRuleOut,
                                  "manage_settings"))
router.include_router(crud_router("/packaging", "empaque", PackagingRecord, PackagingIn, PackagingOut,
                                  "write_ops", fk={"lot_id": Lot}, before_save=packaging_before))
router.include_router(crud_router("/inventory/items", "inventario", InventoryItem, InventoryItemIn,
                                  InventoryItemOut, "write_inventory"))


# ---- Inventario: movimientos y stock mínimo ----
@router.post("/inventory/movements", response_model=MovementOut, status_code=201, tags=["inventario"])
def move(data: MovementIn, user: User = Depends(require("write_inventory")), db: Session = Depends(get_db)):
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == data.item_id,
                                                  InventoryItem.company_id == user.company_id))
    if not item:
        raise HTTPException(404, "Ítem no encontrado")
    delta = data.quantity if data.kind == "entrada" else -data.quantity
    if item.quantity + delta < 0:
        raise HTTPException(409, f"Stock insuficiente: disponible {item.quantity} {item.unit}")
    item.quantity = round(item.quantity + delta, 4)
    mv = InventoryMovement(company_id=user.company_id, user_id=user.id, **data.model_dump())
    db.add(mv)
    db.flush()
    log_activity(db, user, data.kind, "inventory_items", item.id, f"{data.quantity} {item.unit}")
    if item.min_stock and item.quantity <= item.min_stock:
        notify(db, user.company_id, f"Stock mínimo alcanzado: {item.name} ({item.quantity} {item.unit})", "warning")
    db.commit()
    return mv


@router.get("/inventory/movements", response_model=list[MovementOut], tags=["inventario"])
def movements(item_id: int | None = None, lot_number: str | None = None,
              limit: int = Query(200, le=1000), user: User = Depends(require("read")),
              db: Session = Depends(get_db)):
    stmt = select(InventoryMovement).where(InventoryMovement.company_id == user.company_id)
    if item_id:
        stmt = stmt.where(InventoryMovement.item_id == item_id)
    if lot_number:
        stmt = stmt.where(InventoryMovement.lot_number == lot_number)
    return db.scalars(stmt.order_by(InventoryMovement.id.desc()).limit(limit)).all()


@router.get("/inventory/low-stock", response_model=list[InventoryItemOut], tags=["inventario"])
def low_stock(user: User = Depends(require("read")), db: Session = Depends(get_db)):
    return db.scalars(select(InventoryItem).where(
        InventoryItem.company_id == user.company_id, InventoryItem.min_stock > 0,
        InventoryItem.quantity <= InventoryItem.min_stock)).all()


# ---- Trazabilidad por lote ----
@router.get("/traceability/{lot_number}", tags=["inventario"])
def traceability(lot_number: str, user: User = Depends(require("read")), db: Session = Depends(get_db)):
    cid = user.company_id
    lot = db.scalar(select(Lot).where(Lot.company_id == cid, Lot.lot_number == lot_number))
    if not lot:
        raise HTTPException(404, "Lote no encontrado")

    def rows(M, **kw):
        return [LotOut.model_validate(x).model_dump() if M is Lot else x for x in
                db.scalars(select(M).where(M.company_id == cid, **kw)).all()]

    return {
        "lot": LotOut.model_validate(lot),
        "fruit": FruitOut.model_validate(db.get(FruitType, lot.fruit_id)),
        "supplier": SupplierOut.model_validate(db.get(Supplier, lot.supplier_id)) if lot.supplier_id else None,
        "pulping": [PulpingOut.model_validate(x) for x in db.scalars(
            select(PulpingRecord).where(PulpingRecord.lot_id == lot.id, PulpingRecord.company_id == cid))],
        "freezing": [FreezingOut.model_validate(x) for x in db.scalars(
            select(FreezingRecord).where(FreezingRecord.lot_id == lot.id, FreezingRecord.company_id == cid))],
        "packaging": [PackagingOut.model_validate(x) for x in db.scalars(
            select(PackagingRecord).where(PackagingRecord.lot_id == lot.id, PackagingRecord.company_id == cid))],
        "inventory_movements": [MovementOut.model_validate(x) for x in db.scalars(
            select(InventoryMovement).where(InventoryMovement.lot_number == lot_number,
                                            InventoryMovement.company_id == cid))],
    }


# ---- Buscador general ----
@router.get("/search", tags=["general"])
def search(q: str = Query(min_length=2, max_length=60), user: User = Depends(require("read")),
           db: Session = Depends(get_db)):
    cid, like = user.company_id, f"%{q}%"
    return {
        "lots": [{"id": x.id, "lot_number": x.lot_number, "weight_kg": x.weight_kg} for x in db.scalars(
            select(Lot).where(Lot.company_id == cid, or_(Lot.lot_number.ilike(like), Lot.notes.ilike(like))).limit(10))],
        "suppliers": [{"id": x.id, "name": x.name} for x in db.scalars(
            select(Supplier).where(Supplier.company_id == cid, Supplier.name.ilike(like)).limit(10))],
        "fruits": [{"id": x.id, "name": x.name} for x in db.scalars(
            select(FruitType).where(FruitType.company_id == cid, FruitType.name.ilike(like)).limit(10))],
        "inventory": [{"id": x.id, "name": x.name, "quantity": x.quantity, "unit": x.unit} for x in db.scalars(
            select(InventoryItem).where(InventoryItem.company_id == cid, InventoryItem.name.ilike(like)).limit(10))],
    }


# ---- Notificaciones y bitácora ----
@router.get("/notifications", tags=["general"])
def notifications(user: User = Depends(require("read")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.company_id == user.company_id)
                      .order_by(Notification.id.desc()).limit(50)).all()
    return [{"id": n.id, "message": n.message, "level": n.level, "read": n.read,
             "created_at": n.created_at} for n in rows]


@router.post("/notifications/read-all", tags=["general"])
def read_all(user: User = Depends(require("read")), db: Session = Depends(get_db)):
    for n in db.scalars(select(Notification).where(Notification.company_id == user.company_id,
                                                    Notification.read == False)):  # noqa: E712
        n.read = True
    db.commit()
    return {"ok": True}


@router.get("/activity", tags=["general"])
def activity(limit: int = Query(100, le=500), user: User = Depends(require("reports")),
             db: Session = Depends(get_db)):
    from ..models import ActivityLog
    rows = db.scalars(select(ActivityLog).where(ActivityLog.company_id == user.company_id)
                      .order_by(ActivityLog.id.desc()).limit(limit)).all()
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "entity": a.entity,
             "entity_id": a.entity_id, "detail": a.detail, "created_at": a.created_at} for a in rows]
