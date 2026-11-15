import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud import crud_router
from ..database import get_db
from ..deps import require
from ..models import (Company, CostEntry, FreezingRecord, FruitType, InventoryItem, Lot,
                      PackagingRecord, PulpingRecord, TelemetryReading, User)
from ..schemas import (BreakEvenIn, CostIn, CostOut, SimulationIn, TelemetryIn)
from ..services import log_activity

router = APIRouter()
router.include_router(crud_router("/costs", "costos", CostEntry, CostIn, CostOut, "write_costs",
                                  fk={"lot_id": Lot}))

# Costos variables vs fijos: clasificación por defecto (ajustable en etapas siguientes)
VARIABLE = {"materia_prima", "mano_obra", "electricidad", "agua", "empaque", "transporte"}


def _period(days: int):
    end = date.today()
    return end - timedelta(days=days - 1), end


@router.get("/dashboard", tags=["panel"])
def dashboard(days: int = Query(7, ge=1, le=365), user: User = Depends(require("read")),
              db: Session = Depends(get_db)):
    cid = user.company_id
    start, end = _period(days)
    company = db.get(Company, cid)
    days_map = {start + timedelta(i): defaultdict(float) for i in range(days)}

    lots = db.scalars(select(Lot).where(Lot.company_id == cid, Lot.received_on >= start)).all()
    pulp = db.scalars(select(PulpingRecord).where(PulpingRecord.company_id == cid,
                                                  PulpingRecord.recorded_on >= start)).all()
    pack = db.scalars(select(PackagingRecord).where(PackagingRecord.company_id == cid,
                                                    PackagingRecord.recorded_on >= start)).all()
    frz = db.scalars(select(FreezingRecord).where(FreezingRecord.company_id == cid,
                                                  FreezingRecord.recorded_on >= start)).all()
    costs = db.scalars(select(CostEntry).where(CostEntry.company_id == cid,
                                               CostEntry.incurred_on >= start)).all()
    for l in lots:
        if l.received_on in days_map: days_map[l.received_on]["received_kg"] += l.weight_kg
    for p in pulp:
        d = days_map.get(p.recorded_on)
        if d is not None:
            d["initial_kg"] += p.initial_kg
            d["pulp_kg"] += p.pulp_kg
            d["waste_kg"] += p.seed_kg + p.peel_kg + p.other_kg
    for k in pack:
        if k.recorded_on in days_map:
            days_map[k.recorded_on]["packaged_kg"] += k.total_kg
            days_map[k.recorded_on]["packages"] += k.units
    for c in costs:
        if c.incurred_on in days_map: days_map[c.incurred_on]["costs"] += c.amount

    series = [{"date": d.isoformat(), **{k: round(v, 2) for k, v in vals.items()}}
              for d, vals in sorted(days_map.items())]
    sums = defaultdict(float)
    for s in series:
        for k, v in s.items():
            if k != "date": sums[k] += v
    tdy = days_map[end]
    inv = db.scalars(select(InventoryItem).where(InventoryItem.company_id == cid)).all()
    low = [i for i in inv if i.min_stock and i.quantity <= i.min_stock]
    return {
        "period_days": days, "currency": company.currency, "demo_data": bool(company.is_demo),
        "today": {"received_kg": round(tdy["received_kg"], 2), "pulp_kg": round(tdy["pulp_kg"], 2),
                  "yield_pct": round(tdy["pulp_kg"] / tdy["initial_kg"] * 100, 2) if tdy["initial_kg"] else None,
                  "waste_kg": round(tdy["waste_kg"], 2), "packages": int(tdy["packages"]),
                  "frozen_records": sum(1 for f in frz if f.recorded_on == end)},
        "period": {"received_kg": round(sums["received_kg"], 2), "pulp_kg": round(sums["pulp_kg"], 2),
                   "yield_pct": round(sums["pulp_kg"] / sums["initial_kg"] * 100, 2) if sums["initial_kg"] else None,
                   "waste_kg": round(sums["waste_kg"], 2), "packaged_kg": round(sums["packaged_kg"], 2),
                   "packages": int(sums["packages"]), "frozen_records": len(frz),
                   "freezing_alerts": sum(1 for f in frz if f.alert),
                   "production_cost": round(sums["costs"], 2),
                   "estimated_sales": round(sums["packaged_kg"] * company.sale_price_per_kg, 2)},
        "inventory": {"items": len(inv), "low_stock": len(low),
                      "total_kg_available": round(sum(i.quantity for i in inv if i.unit == "kg"), 2)},
        "series": series,
    }


@router.get("/costs-summary", tags=["costos"])
def costs_summary(days: int = Query(30, ge=1, le=365), user: User = Depends(require("read")),
                  db: Session = Depends(get_db)):
    cid = user.company_id
    start, _ = _period(days)
    company = db.get(Company, cid)
    costs = db.scalars(select(CostEntry).where(CostEntry.company_id == cid, CostEntry.incurred_on >= start)).all()
    packed = sum(p.total_kg for p in db.scalars(select(PackagingRecord).where(
        PackagingRecord.company_id == cid, PackagingRecord.recorded_on >= start)))
    by_cat: dict[str, float] = defaultdict(float)
    for c in costs:
        by_cat[c.category] += c.amount
    total = sum(by_cat.values())
    variable = sum(v for k, v in by_cat.items() if k in VARIABLE)
    fixed = total - variable
    price = company.sale_price_per_kg
    cost_kg = total / packed if packed else None
    var_kg = variable / packed if packed else None
    revenue = packed * price
    return {
        "currency": company.currency, "period_days": days, "kg_packaged": round(packed, 2),
        "by_category": {k: round(v, 2) for k, v in by_cat.items()},
        "total_cost": round(total, 2), "variable_cost": round(variable, 2), "fixed_cost": round(fixed, 2),
        "cost_per_kg": round(cost_kg, 3) if cost_kg else None,
        "sale_price_per_kg": price, "estimated_revenue": round(revenue, 2),
        "contribution_margin_per_kg": round(price - var_kg, 3) if var_kg is not None else None,
        "estimated_profit": round(revenue - total, 2),
        "break_even_kg": (round(fixed / (price - var_kg), 1)
                          if var_kg is not None and price > var_kg else None),
        "note": "Estimaciones a partir de los costos y precios configurados por la empresa.",
    }


@router.post("/costs/break-even", tags=["costos"])
def break_even(data: BreakEvenIn, user: User = Depends(require("read"))):
    margin = data.price_per_kg - data.variable_cost_per_kg
    if margin <= 0:
        return {"viable": False, "message": "El precio no cubre el costo variable por kg."}
    kg = data.fixed_costs / margin
    return {"viable": True, "contribution_margin_per_kg": round(margin, 3),
            "break_even_kg": round(kg, 1), "break_even_revenue": round(kg * data.price_per_kg, 2)}


@router.get("/yield-report", tags=["despulpado"])
def yield_report(days: int = Query(30, ge=1, le=365), user: User = Depends(require("reports")),
                 db: Session = Depends(get_db)):
    start, _ = _period(days)
    rows = db.execute(select(PulpingRecord, Lot, FruitType).join(Lot, PulpingRecord.lot_id == Lot.id)
                      .join(FruitType, Lot.fruit_id == FruitType.id)
                      .where(PulpingRecord.company_id == user.company_id,
                             PulpingRecord.recorded_on >= start)).all()
    agg: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for p, _, f in rows:
        a = agg[f.name]
        a["initial_kg"] += p.initial_kg; a["pulp_kg"] += p.pulp_kg; a["seed_kg"] += p.seed_kg
        a["peel_kg"] += p.peel_kg; a["other_kg"] += p.other_kg; a["records"] += 1
    return [{"fruit": k, **{kk: round(vv, 2) for kk, vv in v.items()},
             "yield_pct": round(v["pulp_kg"] / v["initial_kg"] * 100, 2) if v["initial_kg"] else None}
            for k, v in agg.items()]


@router.get("/sustainability", tags=["sostenibilidad"])
def sustainability(days: int = Query(30, ge=1, le=365), user: User = Depends(require("read")),
                   db: Session = Depends(get_db)):
    start, _ = _period(days)
    cid = user.company_id
    p = db.scalars(select(PulpingRecord).where(PulpingRecord.company_id == cid,
                                               PulpingRecord.recorded_on >= start)).all()
    init = sum(x.initial_kg for x in p)
    waste = sum(x.seed_kg + x.peel_kg + x.other_kg for x in p)
    pulp = sum(x.pulp_kg for x in p)
    energy = sum(c.amount for c in db.scalars(select(CostEntry).where(
        CostEntry.company_id == cid, CostEntry.incurred_on >= start, CostEntry.category == "electricidad")))
    water = sum(c.amount for c in db.scalars(select(CostEntry).where(
        CostEntry.company_id == cid, CostEntry.incurred_on >= start, CostEntry.category == "agua")))
    recs = []
    if init and waste / init > 0.4:
        recs.append("Más del 40 % de la materia prima sale como residuo: evalúa valorizar semillas y cáscaras "
                    "(compostaje, alimentación animal, extractos), previa validación técnica y normativa.")
    recs.append("Registra consumo real de energía (kWh) y agua (m³) por lote para medir mejoras; "
                "hoy solo se dispone de su costo monetario.")
    return {"raw_material_used_kg": round(init, 2), "utilization_pct": round(pulp / init * 100, 2) if init else None,
            "waste_kg": round(waste, 2), "waste_pct": round(waste / init * 100, 2) if init else None,
            "energy_cost": round(energy, 2), "water_cost": round(water, 2),
            "recommendations": recs,
            "disclaimer": "Indicadores calculados con los registros ingresados; no constituyen certificación ambiental."}


# ---------------- Simulador de línea ----------------
DEFAULT_CAP = {"recepcion": 800, "lavado_seleccion": 500, "despulpadora": 300, "troceado": 400,
               "congelamiento": 250, "empacadora": 200, "almacen_frigorifico": 5000}
# Valores de SIMULACIÓN (configurables), no parámetros sanitarios ni industriales certificados.
SIM_TEMP = {"IQF": -35.0, "PULPA": -25.0, "ALMACEN": -18.0}


@router.post("/simulation/run", tags=["simulador"])
def simulate(data: SimulationIn, user: User = Depends(require("read")), db: Session = Depends(get_db)):
    fruit = db.scalar(select(FruitType).where(FruitType.id == data.fruit_id, FruitType.company_id == user.company_id))
    if not fruit:
        raise HTTPException(404, "Fruto no encontrado")
    cap = {**DEFAULT_CAP, **data.capacity_kg_h}
    stages, mass = [], data.input_kg
    freeze_t = data.freeze_temp_c if data.freeze_temp_c is not None else SIM_TEMP[data.route]

    def add(key, label, kg_in, kg_out, temp=None, note=None, loss_detail=None):
        hours = kg_in / cap[key]
        alert = hours > data.shift_hours
        stages.append({"station": key, "label": label, "input_kg": round(kg_in, 2),
                       "output_kg": round(kg_out, 2), "loss_kg": round(kg_in - kg_out, 2),
                       "duration_min": round(hours * 60, 1), "capacity_kg_h": cap[key],
                       "temp_c": temp, "status": "alerta_capacidad" if alert else "ok",
                       "alert": (f"Se requieren {hours:.1f} h; el turno configurado es de {data.shift_hours} h"
                                 if alert else None), "note": note})

    add("recepcion", "Recepción de frutos", mass, mass)
    out = mass * (1 - fruit.wash_loss_pct / 100)
    add("lavado_seleccion", "Lavado y selección", mass, out, note=f"Pérdida configurada: {fruit.wash_loss_pct} %")
    mass = out
    if data.route == "PULPA":
        pulp = mass * fruit.pulp_yield_pct / 100
        add("despulpadora", "Despulpadora", mass, pulp,
            note=f"Pulpa {fruit.pulp_yield_pct}%, semilla {fruit.seed_pct}%, cáscara {fruit.peel_pct}% (parámetros configurables)")
        mass = pulp
        product = "pulpa"
        add("congelamiento", "Congelamiento de pulpa", mass, mass, temp=freeze_t,
            note="Ruta PULPA: congelamiento de pulpa envasada/en bloque, distinto del IQF")
    else:
        product = data.iqf_product
        if product == "fruto_trozado":
            cut = mass * 0.97
            add("troceado", "Troceado", mass, cut, note="Pérdida de troceado de simulación: 3 %")
            mass = cut
        add("congelamiento", "Congelamiento IQF", mass, mass * 0.995, temp=freeze_t,
            note="Ruta IQF: fruto entero o trozado congelado individualmente (merma de simulación 0,5 %)")
        mass *= 0.995
    units = int(mass * 1000 // data.bag_grams)
    rejected = math.ceil(units * data.reject_rate_pct / 100)
    good = units - rejected
    packed_kg = good * data.bag_grams / 1000
    add("empacadora", "Empaque y sellado", mass, packed_kg,
        note=f"{units} bolsas de {data.bag_grams} g; {rejected} rechazadas")
    add("almacen_frigorifico", "Almacén frigorífico", packed_kg, packed_kg, temp=SIM_TEMP["ALMACEN"])
    return {"simulated": True, "fruit": fruit.name, "route": data.route, "product": product,
            "input_kg": data.input_kg, "stages": stages,
            "totals": {"packages_total": units, "packages_rejected": rejected, "packages_good": good,
                       "packaged_kg": round(packed_kg, 2),
                       "overall_yield_pct": round(packed_kg / data.input_kg * 100, 2),
                       "packaging_material_units": units,
                       "total_duration_min": round(sum(s["duration_min"] for s in stages), 1)},
            "alerts": [s["alert"] for s in stages if s["alert"]],
            "disclaimer": "SIMULACIÓN con parámetros configurables. No representa resultados industriales "
                          "certificados ni límites sanitarios; valídelos con su proceso y normativa."}


# ---------------- Telemetría (Módulo 12) ----------------
@router.post("/telemetry/ingest", status_code=201, tags=["monitoreo"])
def ingest(data: TelemetryIn, user: User = Depends(require("write_ops")), db: Session = Depends(get_db)):
    """Punto de entrada para el futuro puente MQTT/PLC → API (etapa 3)."""
    db.add(TelemetryReading(company_id=user.company_id, **data.model_dump()))
    db.commit()
    return {"ok": True}


@router.get("/telemetry", tags=["monitoreo"])
def telemetry(limit: int = Query(100, le=1000), user: User = Depends(require("read")),
              db: Session = Depends(get_db)):
    rows = db.scalars(select(TelemetryReading).where(TelemetryReading.company_id == user.company_id)
                      .order_by(TelemetryReading.id.desc()).limit(limit)).all()
    return [{"device_id": r.device_id, "sensor_type": r.sensor_type, "value": r.value,
             "unit": r.unit, "simulated": r.simulated, "ts": r.ts} for r in rows]


@router.get("/telemetry/simulated", tags=["monitoreo"])
def telemetry_simulated(points: int = Query(30, ge=1, le=300), user: User = Depends(require("read"))):
    """Datos SIMULADOS (simulated=true) para la primera versión: caminata aleatoria por sensor."""
    rng = random.Random()
    devices = [("congelador-01", "temperatura", "°C", -30.0, 1.2), ("camara-01", "temperatura", "°C", -18.0, 0.5),
               ("balanza-01", "peso", "kg", 250.0, 4.0)]
    now = datetime.utcnow()
    out = []
    for dev, kind, unit, base, jitter in devices:
        v = base
        for i in range(points):
            v += rng.uniform(-jitter, jitter) * 0.5 + (base - v) * 0.1
            out.append({"device_id": dev, "sensor_type": kind, "value": round(v, 2), "unit": unit,
                        "simulated": True, "ts": (now - timedelta(minutes=points - i)).isoformat()})
    return {"simulated": True, "mqtt_topic_convention": "biofactory/{company_id}/{plant_id}/{device_id}/{sensor_type}",
            "readings": out}
