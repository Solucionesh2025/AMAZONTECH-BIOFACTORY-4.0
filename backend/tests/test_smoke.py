import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import seed  # noqa: E402

seed.run()
client = TestClient(app)


def login(email, pw="Demo2026!"):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_required():
    assert client.get("/api/lots").status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@demo.biofactory", "password": "mala"}).status_code == 401


def test_dashboard_and_yield_formula():
    h = login("admin@demo.biofactory")
    d = client.get("/api/dashboard?days=7", headers=h).json()
    assert len(d["series"]) == 7 and d["demo_data"] is True
    assert d["period"]["received_kg"] > 0
    fruit = client.get("/api/fruits", headers=h).json()[0]
    lot = client.post("/api/lots", headers=h, json={"fruit_id": fruit["id"], "weight_kg": 100}).json()
    assert lot["lot_number"].startswith("L-")
    p = client.post("/api/pulping", headers=h, json={"lot_id": lot["id"], "initial_kg": 100, "pulp_kg": 55,
                                                     "seed_kg": 20, "peel_kg": 15, "other_kg": 5}).json()
    assert p["yield_pct"] == 55.0
    bad = client.post("/api/pulping", headers=h, json={"lot_id": lot["id"], "initial_kg": 100, "pulp_kg": 90,
                                                       "seed_kg": 20})
    assert bad.status_code == 422


def test_roles():
    fruit = client.get("/api/fruits", headers=login("admin@demo.biofactory")).json()[0]
    h = login("almacen@demo.biofactory")
    assert client.post("/api/lots", headers=h, json={"fruit_id": fruit["id"], "weight_kg": 10}).status_code == 403
    assert client.get("/api/users", headers=login("operador@demo.biofactory")).status_code == 403
    assert client.get("/api/admin/companies", headers=login("admin@demo.biofactory")).status_code == 403
    assert client.get("/api/admin/companies", headers=login("superadmin@amazontech.demo")).status_code == 200


def test_tenant_isolation():
    r = client.post("/api/auth/register-company", json={"company_name": "Otra Empresa SAC", "admin_name": "Beto",
                                                        "email": "beto@otra.com", "password": "ClaveSegura1"})
    assert r.status_code == 201
    h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/lots", headers=h2).json() == []
    assert client.get("/api/fruits", headers=h2).json() == []
    lot_id = client.get("/api/lots", headers=login("admin@demo.biofactory")).json()[0]["id"]
    assert client.get(f"/api/lots/{lot_id}", headers=h2).status_code == 404
    # no puede referenciar un fruto de otra empresa
    fruit_id = client.get("/api/fruits", headers=login("admin@demo.biofactory")).json()[0]["id"]
    assert client.post("/api/lots", headers=h2, json={"fruit_id": fruit_id, "weight_kg": 5}).status_code == 422


def test_freezing_routes_and_alerts():
    h = login("operador@demo.biofactory")
    lot = client.get("/api/lots", headers=h).json()[0]["id"]
    base = {"lot_id": lot, "temp_c": -33, "duration_min": 120}
    assert client.post("/api/freezing", headers=h, json={**base, "method": "IQF", "product_type": "pulpa"}).status_code == 422
    assert client.post("/api/freezing", headers=h, json={**base, "method": "PULPA", "product_type": "fruto_entero"}).status_code == 422
    ok = client.post("/api/freezing", headers=h, json={**base, "method": "IQF", "product_type": "fruto_trozado"}).json()
    assert ok["alert"] is False
    hot = client.post("/api/freezing", headers=h, json={**base, "temp_c": -10, "method": "IQF", "product_type": "fruto_entero"}).json()
    assert hot["alert"] is True and hot["status"] == "alerta"


def test_inventory_and_traceability():
    h = login("almacen@demo.biofactory")
    items = client.get("/api/inventory/items", headers=h).json()
    it = next(i for i in items if i["category"] == "bolsas")
    r = client.post("/api/inventory/movements", headers=h, json={"item_id": it["id"], "kind": "salida", "quantity": 10 ** 6})
    assert r.status_code == 409
    assert client.post("/api/inventory/movements", headers=h, json={"item_id": it["id"], "kind": "entrada", "quantity": 100}).status_code == 201
    assert len(client.get("/api/inventory/low-stock", headers=h).json()) >= 1
    ln = client.get("/api/lots", headers=h).json()[0]["lot_number"]
    t = client.get(f"/api/traceability/{ln}", headers=h).json()
    assert t["lot"]["lot_number"] == ln and t["pulping"]


def test_costs_simulation_password_reset():
    h = login("gerente@demo.biofactory")
    s = client.get("/api/costs-summary?days=14", headers=h).json()
    assert s["total_cost"] > 0 and s["cost_per_kg"] > 0
    be = client.post("/api/costs/break-even", headers=h, json={"fixed_costs": 1000, "variable_cost_per_kg": 8, "price_per_kg": 18}).json()
    assert be["break_even_kg"] == 100.0
    fid = client.get("/api/fruits", headers=h).json()[0]["id"]
    for route in ("PULPA", "IQF"):
        sim = client.post("/api/simulation/run", headers=h, json={"fruit_id": fid, "input_kg": 500, "route": route}).json()
        assert sim["simulated"] and sim["totals"]["packaged_kg"] > 0 and len(sim["stages"]) >= 5
    big = client.post("/api/simulation/run", headers=h, json={"fruit_id": fid, "input_kg": 50000}).json()
    assert big["alerts"]
    r = client.post("/api/auth/forgot-password", json={"email": "operador@demo.biofactory"}).json()
    assert client.post("/api/auth/reset-password", json={"token": r["dev_token"], "new_password": "NuevaClave123"}).status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": r["dev_token"], "new_password": "OtraClave123"}).status_code == 400
    login("operador@demo.biofactory", "NuevaClave123")
