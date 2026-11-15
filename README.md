# BIOFACTORY 4.0 — AMAZONTECH

Plataforma web multiempresa para gestionar, simular y monitorear una línea agroindustrial de frutos amazónicos
(camu camu, aguaje, cocona, arazá, maracuyá…).

> **Estado: Etapa 1 (backend) completa y probada · Etapa 2a (frontend) entregada:** login/registro/recuperación,
> panel con gráficos, recepción y control de despulpado. + **simulador animado de la línea** (rutas IQF y pulpa, iniciar/pausar/reiniciar, velocidad, alertas de capacidad, temperaturas simuladas). Siguen en la 2b: congelamiento, empaque,
> inventario, costos, reportes y sostenibilidad.
> Todos los datos de ejemplo están marcados como **DEMOSTRACIÓN**. Los parámetros de rendimiento, temperaturas y
> límites son **configurables y de simulación**: no son valores industriales certificados ni normas sanitarias.

## Arquitectura

```
biofactory/
├── docker-compose.yml        # PostgreSQL (+ Mosquitto MQTT para la Etapa 3)
├── db/schema.sql             # DDL PostgreSQL generado desde los modelos
├── backend/                  # FastAPI + SQLAlchemy 2 + JWT
│   ├── app/
│   │   ├── main.py           # app, CORS, routers
│   │   ├── config.py         # variables de entorno (.env)
│   │   ├── database.py       # engine / sesión
│   │   ├── models.py         # tablas; TenantMixin => company_id en todo
│   │   ├── schemas.py        # validaciones Pydantic
│   │   ├── security.py       # bcrypt + JWT + tokens de recuperación (hash SHA-256)
│   │   ├── deps.py           # usuario actual y permisos por rol
│   │   ├── crud.py           # fábrica CRUD: aislamiento por empresa + bitácora
│   │   ├── services.py       # actividad y notificaciones
│   │   ├── seed.py           # empresa DEMOSTRACIÓN
│   │   ├── export_sql.py     # genera db/schema.sql
│   │   └── routers/{auth,operations,analytics}.py
│   └── tests/test_smoke.py   # 7 pruebas de extremo a extremo
└── frontend/                 # React + Vite + Recharts (Etapa 2)
```

**Multiempresa:** cada fila lleva `company_id`; toda consulta filtra por la empresa del token y las claves
foráneas se validan contra la misma empresa (no se puede referenciar datos ajenos).

**Roles:** `superadmin`, `company_admin`, `manager`, `supervisor`, `operator`, `warehouse`
(matriz en `app/deps.py`).

## Ejecutar localmente

```bash
# 1) Base de datos
docker compose up -d db

# 2) Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # cambia SECRET_KEY
python -m app.seed --reset                             # crea tablas + datos DEMOSTRACIÓN
uvicorn app.main:app --reload
# Documentación interactiva: http://localhost:8000/docs

# 3) Pruebas (usan SQLite temporal)
python -m pytest -q
```

Sin Docker: en `.env` usa `DATABASE_URL=sqlite:///./biofactory.db`.

**Usuarios demo** (clave `Demo2026!`, solo demostración): `admin@demo.biofactory`, `gerente@demo.biofactory`,
`supervisor@demo.biofactory`, `operador@demo.biofactory`, `almacen@demo.biofactory`, `superadmin@amazontech.demo`.

## Frontend (React + Vite + Recharts)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy automático de /api → http://localhost:8000)
npm run build      # versión de producción en dist/
```

Requiere el backend corriendo (ver arriba). Páginas actuales: Panel principal, Recepción de fruta,
Simulador de línea, Control de despulpado; además búsqueda general, notificaciones y cierre de sesión.

## API (prefijo `/api`)

| Módulo | Endpoints |
|---|---|
| Auth | `POST /auth/register-company`, `/auth/login`, `/auth/logout`, `GET /auth/me`, `/auth/forgot-password`, `/auth/reset-password` |
| Usuarios / empresa | `GET/POST /users`, `PATCH /users/{id}`, `GET/PUT /company`, `GET /admin/companies` (superadmin) |
| Maestros | CRUD `/plants`, `/fruits`, `/suppliers`, `/machines` |
| Recepción | CRUD `/lots` (lote autogenerado `L-AAAAMMDD-NNN`) |
| Despulpado | CRUD `/pulping` (rendimiento = pulpa/inicial × 100, con balance de masa), `GET /yield-report` |
| Congelamiento | CRUD `/freezing` (rutas **IQF** vs **PULPA** validadas), CRUD `/alert-rules` (límites configurables) |
| Empaque | CRUD `/packaging` (kg totales y bolsas usadas automáticos) |
| Inventario | CRUD `/inventory/items`, `POST/GET /inventory/movements`, `GET /inventory/low-stock`, `GET /traceability/{lote}` |
| Costos | CRUD `/costs`, `GET /costs-summary`, `POST /costs/break-even` |
| Panel | `GET /dashboard?days=1|7|30` |
| Simulador | `POST /simulation/run` (balance de masa por estación, tiempos, alertas de capacidad) |
| Sostenibilidad | `GET /sustainability` |
| Monitoreo | `POST /telemetry/ingest`, `GET /telemetry`, `GET /telemetry/simulated` (marcado `simulated: true`) |
| General | `GET /search?q=`, `GET /notifications`, `POST /notifications/read-all`, `GET /activity` |

**Integración industrial (Etapa 3):** convención de tópicos MQTT
`biofactory/{company_id}/{plant_id}/{device_id}/{sensor_type}`; un puente MQTT→`/telemetry/ingest`
reemplazará los datos simulados sin cambiar el modelo.

## Hoja de ruta
- **Etapa 2b:** simulador animado de la línea, congelamiento con gráficas de temperatura, empaque, inventario, costos y rentabilidad, sostenibilidad, administración de usuarios y perfil de empresa.
- **Etapa 3:** reportes PDF/Excel, puente MQTT, Alembic, envío real de correo, límite de intentos de login, despliegue.

## Seguridad
Contraseñas con bcrypt; JWT con expiración; tokens de recuperación guardados solo como hash y de un solo uso;
`DEV_MODE=false` en producción; cambiar `SECRET_KEY`; servir tras HTTPS.
