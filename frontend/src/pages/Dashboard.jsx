import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Empty, Panel, Stat, fmt, fmtDate } from "../components/ui";

const PERIODS = [{ d: 1, l: "Hoy" }, { d: 7, l: "Semana" }, { d: 30, l: "Mes" }];
const C = { green: "#0E5A43", emerald: "#10B981", orange: "#F28C28", gray: "#5B6B66" };

export default function Dashboard() {
  const [days, setDays] = useState(7);
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    setErr("");
    api(`/dashboard?days=${days}`).then(setD).catch((e) => setErr(e.message));
  }, [days]);

  if (err) return <p className="form-error">{err}</p>;
  if (!d) return <p className="empty">Cargando panel…</p>;
  const cur = d.currency;
  const series = d.series.map((s) => ({ ...s, label: fmtDate(s.date) }));
  const t = d.today, p = d.period;

  return (
    <>
      <div className="page-h">
        <div>
          <h1>Panel principal</h1>
          {d.demo_data && <span className="tag demo">Datos de DEMOSTRACIÓN</span>}
        </div>
        <div className="seg" role="group" aria-label="Periodo">
          {PERIODS.map((x) => <button key={x.d} className={days === x.d ? "on" : ""} onClick={() => setDays(x.d)}>{x.l}</button>)}
        </div>
      </div>

      <div className="stats">
        <Stat label="Fruta recibida hoy" value={fmt(t.received_kg)} unit=" kg" />
        <Stat label="Pulpa obtenida hoy" value={fmt(t.pulp_kg)} unit=" kg" tone="emerald" />
        <Stat label="Rendimiento de despulpado hoy" value={fmt(t.yield_pct)} unit=" %" sub="pulpa / peso inicial" />
        <Stat label="Residuos hoy" value={fmt(t.waste_kg)} unit=" kg" />
        <Stat label="Empaques hoy" value={fmt(t.packages, 0)} unit=" und" tone="orange" />
        <Stat label="Registros de congelamiento hoy" value={fmt(t.frozen_records, 0)} />
        <Stat label="Inventario disponible" value={fmt(d.inventory.total_kg_available)} unit=" kg"
              sub={`${d.inventory.low_stock} ítem(s) en stock mínimo`} tone={d.inventory.low_stock ? "orange" : ""} />
        <Stat label={`Costo de producción (${PERIODS.find((x) => x.d === days).l.toLowerCase()})`} value={fmt(p.production_cost, 0)} unit={` ${cur}`}
              sub={`Ventas estimadas: ${fmt(p.estimated_sales, 0)} ${cur}`} />
      </div>

      <div className="grid2">
        <Panel title="Producción diaria (kg)">
          {series.every((s) => !s.received_kg) ? <Empty>Aún no hay recepciones en este periodo.</Empty> : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={series} margin={{ left: -10, right: 8, top: 8 }}>
                <CartesianGrid stroke="#E3EAE7" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
                <Tooltip /><Legend />
                <Area name="Fruta recibida" dataKey="received_kg" stroke={C.green} fill={C.green} fillOpacity={0.15} />
                <Area name="Pulpa" dataKey="pulp_kg" stroke={C.emerald} fill={C.emerald} fillOpacity={0.25} />
                <Area name="Residuos" dataKey="waste_kg" stroke={C.orange} fill={C.orange} fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title={`Costos diarios (${cur})`}>
          {series.every((s) => !s.costs) ? <Empty>Registra costos para verlos aquí.</Empty> : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={series} margin={{ left: -10, right: 8, top: 8 }}>
                <CartesianGrid stroke="#E3EAE7" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
                <Tooltip /><Bar name="Costos" dataKey="costs" fill={C.gray} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <Panel title={`Resumen del periodo (${days} día${days > 1 ? "s" : ""})`}>
        <dl className="kv">
          <div><dt>Fruta recibida</dt><dd>{fmt(p.received_kg)} kg</dd></div>
          <div><dt>Pulpa</dt><dd>{fmt(p.pulp_kg)} kg</dd></div>
          <div><dt>Rendimiento medio</dt><dd>{fmt(p.yield_pct)} %</dd></div>
          <div><dt>Producto empacado</dt><dd>{fmt(p.packaged_kg)} kg · {fmt(p.packages, 0)} und</dd></div>
          <div><dt>Alertas de congelamiento</dt><dd>{p.freezing_alerts}</dd></div>
          <div><dt>Ventas estimadas</dt><dd>{fmt(p.estimated_sales, 0)} {cur}</dd></div>
        </dl>
      </Panel>
    </>
  );
}
