from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Meta(ORM):
    id: int
    created_at: datetime
    is_demo: bool


# ---------- Auth / usuarios ----------
Role = Literal["superadmin", "company_admin", "manager", "supervisor", "operator", "warehouse"]


class RegisterCompanyIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=64)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=64)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: str
    active: bool
    company_id: int
    plant_id: int | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=64)
    role: Role = "operator"
    plant_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    active: bool | None = None
    plant_id: int | None = None


class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    ruc: str | None = None
    country: str = "Perú"
    currency: str = Field(default="PEN", max_length=8)
    weight_unit: Literal["kg", "lb", "g"] = "kg"
    sale_price_per_kg: float = Field(default=0, ge=0)


class CompanyOut(CompanyIn, ORM):
    id: int
    is_demo: bool


# ---------- Maestros ----------
class PlantIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    location: str | None = None


class PlantOut(PlantIn, Meta):
    pass


class FruitIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    pulp_yield_pct: float = Field(ge=0, le=100)
    seed_pct: float = Field(ge=0, le=100)
    peel_pct: float = Field(ge=0, le=100)
    wash_loss_pct: float = Field(default=2.0, ge=0, le=50)
    notes: str | None = None

    @model_validator(mode="after")
    def balance(self):
        if self.pulp_yield_pct + self.seed_pct + self.peel_pct > 100.0001:
            raise ValueError("pulpa + semilla + cáscara no puede superar 100 %")
        return self


class FruitOut(FruitIn, Meta):
    pass


class SupplierIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    contact: str | None = None
    location: str | None = None


class SupplierOut(SupplierIn, Meta):
    pass


class MachineIn(BaseModel):
    name: str
    station: Literal["recepcion", "lavado_seleccion", "despulpadora", "congelamiento",
                     "empacadora", "almacen_frigorifico"]
    capacity_kg_h: float = Field(gt=0)
    status: Literal["operativa", "mantenimiento", "detenida"] = "operativa"
    plant_id: int | None = None


class MachineOut(MachineIn, Meta):
    pass


# ---------- Producción ----------
class LotIn(BaseModel):
    lot_number: str | None = Field(default=None, max_length=40)
    fruit_id: int
    supplier_id: int | None = None
    plant_id: int | None = None
    received_on: date = Field(default_factory=date.today)
    weight_kg: float = Field(gt=0)
    quality: Literal["A", "B", "C", "rechazado"] = "A"
    condition: Literal["óptimo", "aceptable", "deficiente"] = "óptimo"
    notes: str | None = None


class LotOut(LotIn, Meta):
    lot_number: str


class PulpingIn(BaseModel):
    lot_id: int
    recorded_on: date = Field(default_factory=date.today)
    initial_kg: float = Field(gt=0)
    pulp_kg: float = Field(ge=0)
    seed_kg: float = Field(default=0, ge=0)
    peel_kg: float = Field(default=0, ge=0)
    other_kg: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def mass_balance(self):
        total = self.pulp_kg + self.seed_kg + self.peel_kg + self.other_kg
        if total > self.initial_kg * 1.001:
            raise ValueError("La suma de pulpa, semillas, cáscaras y otros supera el peso inicial")
        return self


class PulpingOut(PulpingIn, Meta):
    yield_pct: float


FreezeMethod = Literal["IQF", "PULPA"]
ProductType = Literal["fruto_entero", "fruto_trozado", "pulpa"]


class FreezingIn(BaseModel):
    lot_id: int
    recorded_on: date = Field(default_factory=date.today)
    product_type: ProductType
    method: FreezeMethod
    temp_c: float = Field(ge=-100, le=60)
    duration_min: int = Field(gt=0, le=10000)
    status: Literal["en_proceso", "completado", "alerta"] = "en_proceso"
    notes: str | None = None

    @model_validator(mode="after")
    def route(self):
        if self.method == "IQF" and self.product_type == "pulpa":
            raise ValueError("IQF aplica a fruto entero o trozado; la pulpa usa ruta PULPA")
        if self.method == "PULPA" and self.product_type != "pulpa":
            raise ValueError("La ruta PULPA solo aplica al producto 'pulpa'")
        return self


class FreezingOut(FreezingIn, Meta):
    alert: bool
    alert_message: str | None


class AlertRuleIn(BaseModel):
    method: FreezeMethod
    max_temp_c: float | None = Field(default=None, ge=-100, le=60)
    max_duration_min: int | None = Field(default=None, gt=0)
    active: bool = True


class AlertRuleOut(AlertRuleIn, Meta):
    pass


class PackagingIn(BaseModel):
    lot_id: int
    recorded_on: date = Field(default_factory=date.today)
    bag_grams: int = Field(gt=0, le=50000)
    units: int = Field(ge=0)
    rejected_units: int = Field(default=0, ge=0)


class PackagingOut(PackagingIn, Meta):
    total_kg: float
    bags_used: int


# ---------- Inventario / costos ----------
InvCategory = Literal["fruta_fresca", "pulpa", "congelado", "envases", "bolsas",
                      "etiquetas", "insumos", "producto_terminado"]


class InventoryItemIn(BaseModel):
    category: InvCategory
    name: str = Field(min_length=2, max_length=150)
    quantity: float = Field(default=0, ge=0)
    unit: str = Field(default="kg", max_length=15)
    min_stock: float = Field(default=0, ge=0)
    lot_number: str | None = None


class InventoryItemOut(InventoryItemIn, Meta):
    pass


class MovementIn(BaseModel):
    item_id: int
    kind: Literal["entrada", "salida"]
    quantity: float = Field(gt=0)
    lot_number: str | None = None
    reason: str | None = Field(default=None, max_length=200)


class MovementOut(MovementIn, Meta):
    user_id: int | None


CostCategory = Literal["materia_prima", "mano_obra", "electricidad", "agua",
                       "empaque", "mantenimiento", "transporte", "otros"]


class CostIn(BaseModel):
    category: CostCategory
    amount: float = Field(gt=0)
    incurred_on: date = Field(default_factory=date.today)
    lot_id: int | None = None
    description: str | None = None


class CostOut(CostIn, Meta):
    pass


class BreakEvenIn(BaseModel):
    fixed_costs: float = Field(ge=0)
    variable_cost_per_kg: float = Field(ge=0)
    price_per_kg: float = Field(gt=0)


# ---------- Simulación ----------
class SimulationIn(BaseModel):
    fruit_id: int
    input_kg: float = Field(gt=0, le=1_000_000)
    route: Literal["IQF", "PULPA"] = "PULPA"
    iqf_product: Literal["fruto_entero", "fruto_trozado"] = "fruto_entero"
    bag_grams: int = Field(default=500, gt=0)
    reject_rate_pct: float = Field(default=1.0, ge=0, le=100)
    shift_hours: float = Field(default=8, gt=0)
    capacity_kg_h: dict[str, float] = Field(default_factory=dict)  # override por estación
    freeze_temp_c: float | None = None  # valor de simulación configurable


class TelemetryIn(BaseModel):
    device_id: str = Field(max_length=60)
    sensor_type: Literal["temperatura", "peso", "humedad"]
    value: float
    unit: str = Field(max_length=10)
    simulated: bool = True
