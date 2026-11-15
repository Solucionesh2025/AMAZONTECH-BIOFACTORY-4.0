from datetime import date, datetime, timezone

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now():
    return datetime.now(timezone.utc)


class TenantMixin:
    """Toda tabla de negocio pertenece a una empresa (aislamiento multiempresa)."""
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    ruc: Mapped[str | None] = mapped_column(String(30))
    country: Mapped[str] = mapped_column(String(60), default="Perú")
    currency: Mapped[str] = mapped_column(String(8), default="PEN")
    weight_unit: Mapped[str] = mapped_column(String(8), default="kg")
    sale_price_per_kg: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Plant(TenantMixin, Base):
    __tablename__ = "plants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(200))


class User(TenantMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id"))


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class FruitType(TenantMixin, Base):
    __tablename__ = "fruit_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Parámetros CONFIGURABLES de simulación (no son valores industriales certificados)
    pulp_yield_pct: Mapped[float] = mapped_column(Float, default=50.0)
    seed_pct: Mapped[float] = mapped_column(Float, default=20.0)
    peel_pct: Mapped[float] = mapped_column(Float, default=20.0)
    wash_loss_pct: Mapped[float] = mapped_column(Float, default=2.0)
    notes: Mapped[str | None] = mapped_column(Text)


class Supplier(TenantMixin, Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(150))


class Lot(TenantMixin, Base):
    __tablename__ = "lots"
    __table_args__ = (UniqueConstraint("company_id", "lot_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_number: Mapped[str] = mapped_column(String(40), index=True)
    fruit_id: Mapped[int] = mapped_column(ForeignKey("fruit_types.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id"))
    received_on: Mapped[date] = mapped_column(Date, default=date.today)
    weight_kg: Mapped[float] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String(15), default="A")
    condition: Mapped[str] = mapped_column(String(20), default="óptimo")
    notes: Mapped[str | None] = mapped_column(Text)


class PulpingRecord(TenantMixin, Base):
    __tablename__ = "pulping_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    recorded_on: Mapped[date] = mapped_column(Date, default=date.today)
    initial_kg: Mapped[float] = mapped_column(Float)
    pulp_kg: Mapped[float] = mapped_column(Float)
    seed_kg: Mapped[float] = mapped_column(Float, default=0)
    peel_kg: Mapped[float] = mapped_column(Float, default=0)
    other_kg: Mapped[float] = mapped_column(Float, default=0)
    yield_pct: Mapped[float] = mapped_column(Float, default=0)


class FreezingRecord(TenantMixin, Base):
    __tablename__ = "freezing_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    recorded_on: Mapped[date] = mapped_column(Date, default=date.today)
    product_type: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(10))  # IQF | PULPA
    temp_c: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="en_proceso")
    alert: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_message: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AlertRule(TenantMixin, Base):
    """Límites configurables por empresa/proceso. No son normas sanitarias universales."""
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(10))
    max_temp_c: Mapped[float | None] = mapped_column(Float)
    max_duration_min: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PackagingRecord(TenantMixin, Base):
    __tablename__ = "packaging_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    recorded_on: Mapped[date] = mapped_column(Date, default=date.today)
    bag_grams: Mapped[int] = mapped_column(Integer)
    units: Mapped[int] = mapped_column(Integer)
    rejected_units: Mapped[int] = mapped_column(Integer, default=0)
    total_kg: Mapped[float] = mapped_column(Float, default=0)
    bags_used: Mapped[int] = mapped_column(Integer, default=0)


class InventoryItem(TenantMixin, Base):
    __tablename__ = "inventory_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(15), default="kg")
    min_stock: Mapped[float] = mapped_column(Float, default=0)
    lot_number: Mapped[str | None] = mapped_column(String(40))


class InventoryMovement(TenantMixin, Base):
    __tablename__ = "inventory_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[float] = mapped_column(Float)
    lot_number: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(200))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class CostEntry(TenantMixin, Base):
    __tablename__ = "cost_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)
    incurred_on: Mapped[date] = mapped_column(Date, default=date.today)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"))
    description: Mapped[str | None] = mapped_column(String(200))


class Machine(TenantMixin, Base):
    __tablename__ = "machines"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    station: Mapped[str] = mapped_column(String(30))
    capacity_kg_h: Mapped[float] = mapped_column(Float, default=100)
    status: Mapped[str] = mapped_column(String(20), default="operativa")
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id"))


class TelemetryReading(TenantMixin, Base):
    """Lecturas de sensores. simulated=True mientras no haya hardware real conectado."""
    __tablename__ = "telemetry_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(60), index=True)
    sensor_type: Mapped[str] = mapped_column(String(30))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(10))
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now)


class ActivityLog(TenantMixin, Base):
    __tablename__ = "activity_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(300))


class Notification(TenantMixin, Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(String(300))
    level: Mapped[str] = mapped_column(String(10), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
