"""Datos de DEMOSTRACIÓN (ficticios). Uso: python -m app.seed [--reset]"""
import random
import sys
from datetime import date, timedelta

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import (AlertRule, Company, CostEntry, FreezingRecord, FruitType, InventoryItem,
                     Lot, Machine, Notification, PackagingRecord, Plant, PulpingRecord,
                     Supplier, User)
from .security import hash_password

DEMO_NAME = "Planta Demo Amazonía (DEMOSTRACIÓN)"
DEMO_PASSWORD = "Demo2026!"  # solo para la empresa de demostración


def run(reset: bool = False):
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    rnd = random.Random(42)
    with SessionLocal() as db:
        if db.scalar(select(Company).where(Company.name == DEMO_NAME)):
            print("La empresa de demostración ya existe. Usa --reset para recrearla.")
            return
        # Plataforma + superadmin
        plat = Company(name="AMAZONTECH (Plataforma)", is_demo=False)
        db.add(plat); db.flush()
        db.add(User(company_id=plat.id, email="superadmin@amazontech.demo", full_name="Superadmin AMAZONTECH",
                    password_hash=hash_password(DEMO_PASSWORD), role="superadmin"))
        # Empresa demo
        c = Company(name=DEMO_NAME, ruc="00000000000 (DEMO)", country="Perú", currency="PEN",
                    sale_price_per_kg=18.0, is_demo=True)
        db.add(c); db.flush()
        cid = c.id
        plant = Plant(company_id=cid, name="Planta Iquitos 1 (DEMOSTRACIÓN)", location="Iquitos, Loreto", is_demo=True)
        db.add(plant); db.flush()
        for email, name, role in [
            ("admin@demo.biofactory", "Ana Admin (DEMO)", "company_admin"),
            ("gerente@demo.biofactory", "Gabriel Gerente (DEMO)", "manager"),
            ("supervisor@demo.biofactory", "Sofía Supervisora (DEMO)", "supervisor"),
            ("operador@demo.biofactory", "Oscar Operador (DEMO)", "operator"),
            ("almacen@demo.biofactory", "Alma Almacén (DEMO)", "warehouse")]:
            db.add(User(company_id=cid, email=email, full_name=name, role=role,
                        password_hash=hash_password(DEMO_PASSWORD), plant_id=plant.id, is_demo=True))
        # Frutos: parámetros ficticios de demostración (pulpa, semilla, cáscara, merma de lavado)
        fruit_defs = [("Camu camu", 55, 25, 12, 2), ("Aguaje", 30, 45, 20, 2), ("Cocona", 70, 15, 10, 2),
                      ("Arazá", 65, 15, 15, 2), ("Maracuyá", 35, 12, 45, 2)]
        fruits = []
        for n, p, s, k, w in fruit_defs:
            f = FruitType(company_id=cid, name=n, pulp_yield_pct=p, seed_pct=s, peel_pct=k,
                          wash_loss_pct=w, notes="Parámetros de DEMOSTRACIÓN, ajustables", is_demo=True)
            db.add(f); fruits.append(f)
        sups = [Supplier(company_id=cid, name=n, location=l, contact="000-000-000 (DEMO)", is_demo=True)
                for n, l in [("Asociación Río Nanay (DEMO)", "Nanay"), ("Cooperativa Ucayali Verde (DEMO)", "Pucallpa"),
                             ("Agricultor Juan Pérez (DEMO)", "Iquitos")]]
        db.add_all(sups)
        db.add_all([AlertRule(company_id=cid, method="IQF", max_temp_c=-30, max_duration_min=240, is_demo=True),
                    AlertRule(company_id=cid, method="PULPA", max_temp_c=-22, max_duration_min=360, is_demo=True)])
        for nm, st, cap in [("Lavadora DEMO-01", "lavado_seleccion", 500), ("Despulpadora DEMO-01", "despulpadora", 300),
                            ("Túnel IQF DEMO-01", "congelamiento", 250), ("Empacadora DEMO-01", "empacadora", 200),
                            ("Cámara fría DEMO-01", "almacen_frigorifico", 5000)]:
            db.add(Machine(company_id=cid, name=nm, station=st, capacity_kg_h=cap, plant_id=plant.id, is_demo=True))
        db.flush()

        today, seq = date.today(), 0
        for back in range(14, -1, -1):
            day = today - timedelta(days=back)
            for _ in range(2):
                seq += 1
                f = rnd.choice(fruits)
                kg = round(rnd.uniform(200, 600), 1)
                lot = Lot(company_id=cid, lot_number=f"L-{day:%Y%m%d}-{seq:03d}", fruit_id=f.id,
                          supplier_id=rnd.choice(sups).id, plant_id=plant.id, received_on=day, weight_kg=kg,
                          quality=rnd.choice(["A", "A", "B"]), condition="óptimo", notes="DEMOSTRACIÓN", is_demo=True)
                db.add(lot); db.flush()
                init = kg * (1 - f.wash_loss_pct / 100)
                pulp = round(init * f.pulp_yield_pct / 100 * rnd.uniform(0.93, 1.05), 2)
                seed = round(init * f.seed_pct / 100 * rnd.uniform(0.95, 1.05), 2)
                peel = round(init * f.peel_pct / 100 * rnd.uniform(0.95, 1.05), 2)
                other = max(0.0, round(init - pulp - seed - peel, 2))
                db.add(PulpingRecord(company_id=cid, lot_id=lot.id, recorded_on=day, initial_kg=round(init, 2),
                                     pulp_kg=pulp, seed_kg=seed, peel_kg=peel, other_kg=other,
                                     yield_pct=round(pulp / init * 100, 2), is_demo=True))
                iqf = seq % 2 == 0
                temp = round(rnd.uniform(-34, -31) if iqf else rnd.uniform(-27, -24), 1)
                alert = seq == 9
                if alert:
                    temp = -20.0
                db.add(FreezingRecord(company_id=cid, lot_id=lot.id, recorded_on=day,
                                      product_type="fruto_entero" if iqf else "pulpa", method="IQF" if iqf else "PULPA",
                                      temp_c=temp, duration_min=rnd.randint(90, 220),
                                      status="alerta" if alert else "completado", alert=alert,
                                      alert_message="Temperatura -20.0 °C por encima del límite configurado (-22.0 °C) [DEMO]" if alert else None,
                                      is_demo=True))
                bag = rnd.choice([250, 500, 1000])
                packable = (pulp if not iqf else init * 0.99)
                units = int(packable * 1000 // bag)
                rej = max(0, round(units * 0.01))
                db.add(PackagingRecord(company_id=cid, lot_id=lot.id, recorded_on=day, bag_grams=bag, units=units - rej,
                                       rejected_units=rej, total_kg=round((units - rej) * bag / 1000, 3),
                                       bags_used=units, is_demo=True))
                db.add(CostEntry(company_id=cid, category="materia_prima", amount=round(kg * 3.5, 2), incurred_on=day,
                                 lot_id=lot.id, description="Compra de fruta (DEMO)", is_demo=True))
            for cat, amt in [("mano_obra", 240), ("electricidad", 95), ("agua", 28), ("empaque", 60)]:
                db.add(CostEntry(company_id=cid, category=cat, amount=amt * rnd.uniform(0.9, 1.1), incurred_on=day,
                                 description="DEMOSTRACIÓN", is_demo=True))
            if day.weekday() == 0:
                db.add(CostEntry(company_id=cid, category="mantenimiento", amount=150, incurred_on=day, is_demo=True))
                db.add(CostEntry(company_id=cid, category="transporte", amount=120, incurred_on=day, is_demo=True))
        for cat, nm, q, u, mn in [("fruta_fresca", "Fruta fresca (varios) DEMO", 900, "kg", 200),
                                  ("pulpa", "Pulpa procesada DEMO", 650, "kg", 150),
                                  ("congelado", "Fruta IQF DEMO", 480, "kg", 100),
                                  ("envases", "Envases de 1 kg DEMO", 1200, "unid", 500),
                                  ("bolsas", "Bolsas 500 g DEMO", 400, "unid", 500),
                                  ("etiquetas", "Etiquetas DEMO", 3000, "unid", 1000),
                                  ("insumos", "Guantes y desinfectante DEMO", 40, "unid", 20),
                                  ("producto_terminado", "Producto terminado DEMO", 1100, "kg", 300)]:
            db.add(InventoryItem(company_id=cid, category=cat, name=nm, quantity=q, unit=u, min_stock=mn, is_demo=True))
        db.add(Notification(company_id=cid, level="warning", is_demo=True,
                            message="Stock mínimo alcanzado: Bolsas 500 g DEMO (400 unid)"))
        db.add(Notification(company_id=cid, level="info", is_demo=True,
                            message="Bienvenido a BIOFACTORY 4.0. Estos son datos de DEMOSTRACIÓN."))
        db.commit()
        print(f"Demo lista. Usuarios (clave {DEMO_PASSWORD}): admin@demo.biofactory, gerente@, supervisor@, "
              "operador@, almacen@demo.biofactory; superadmin@amazontech.demo")


if __name__ == "__main__":
    run("--reset" in sys.argv)
