import { useEffect, useMemo, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Empty, Field, Panel, Stat, fmt, useToast } from "../components/ui";
import { buildTimeline, fmtClock, slotLabels, snapshot, tempAt } from "../simlogic";

const BASE = 3; // minutos simulados por segundo real a velocidad 1x
const SPEEDS = [1, 5, 10, 30, 60];
const X0 = 95, DX = 162; // posiciones de estaciones en el SVG
const STATUS_TXT = { espera: "En espera", proceso: "En proceso", completado: "Completado" };

function Plant({ sim, snap, labels, machines }) {
  const rows = Object.fromEntries((snap?.rows || []).map((r) => [r.slot, r]));
  return (
    <div className="plant-wrap">
      <svg className="plant" viewBox="0 0 1000 250" role="img" aria-label="Esquema animado de la planta">
        <line x1={X0} y1="120" x2={X0 + DX * 5} y2="120" className="belt-line" />
        {labels.map((label, i) => {
          const r = rows[i];
          const skipped = sim && !r;
          const st = !sim ? "idle" : skipped ? "skipped" : r.capacityAlert ? "alert" : r.status;
          const cx = X0 + DX * i;
          const m = machines[i];
          return (
            <g key={i} className={`st st-${st}`}>
              <rect x={cx - 62} y="68" width="124" height="104" rx="8" />
              <text x={cx} y="92" className="st-name" textAnchor="middle">
                {label.length > 17 ? [label.slice(0, label.lastIndexOf(" ", 17)), label.slice(label.lastIndexOf(" ", 17) + 1)].map((t, k) => <tspan key={k} x={cx} dy={k ? 14 : 0}>{t}</tspan>) : label}
              </text>
              <text x={cx} y="138" className="st-state" textAnchor="middle">
                {skipped ? "Omitida en esta ruta" : r ? (r.capacityAlert ? "Alerta de capacidad" : STATUS_TXT[r.status]) : "Listo"}
              </text>
              {r && <rect x={cx - 50} y="156" width="100" height="6" rx="3" className="bar-bg" />}
              {r && <rect x={cx - 50} y="156" width={100 * r.progress} height="6" rx="3" className="bar-fg" />}
              {r?.temp_now != null && <text x={cx} y="196" textAnchor="middle" className="st-temp">{fmt(r.temp_now)} °C</text>}
              {m && <text x={cx} y="220" textAnchor="middle" className={`st-machine ${m.status !== "operativa" ? "bad" : ""}`}>{m.name}{m.status !== "operativa" ? ` (${m.status})` : ""}</text>}
            </g>
          );
        })}
        {snap && (
          <g className="lot" transform={`translate(${X0 + DX * snap.where.pos}, 120)`}>
            <rect x="-9" y="-9" width="18" height="18" rx="4" className={snap.where.kind === "proceso" ? "pulse" : ""} />
            <text y="-52" textAnchor="middle">{fmt(snap.where.mass)} kg</text>
          </g>
        )}
      </svg>
    </div>
  );
}

export default function Simulator() {
  const toast = useToast();
  const [fruits, setFruits] = useState([]);
  const [machines, setMachines] = useState([]);
  const [p, setP] = useState({ fruit_id: "", input_kg: 500, route: "PULPA", iqf_product: "fruto_entero", bag: "500", bag_custom: 750, reject: 1, shift: 8, freeze: "" });
  const [sim, setSim] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | running | paused | done
  const [t, setT] = useState(0);
  const [speed, setSpeed] = useState(10);
  const [hist, setHist] = useState([]);
  const [busy, setBusy] = useState(false);
  const tRef = useRef(0);
  const lastPush = useRef(-99);
  const histRef = useRef([]);

  useEffect(() => {
    Promise.all([api("/fruits"), api("/machines")]).then(([f, m]) => {
      setFruits(f); setMachines(m);
      if (f.length) setP((x) => ({ ...x, fruit_id: String(f[0].id) }));
    }).catch((e) => toast(e.message, "err"));
  }, []);

  const tl = useMemo(() => (sim ? buildTimeline(sim) : null), [sim]);
  const snap = useMemo(() => (sim && tl ? snapshot(sim, tl, t) : null), [sim, tl, t]);
  const labels = slotLabels(sim?.route ?? p.route, sim ? p.iqf_product : p.iqf_product);
  const machBySlot = useMemo(() => {
    const keys = ["recepcion", "lavado_seleccion", "despulpadora", "congelamiento", "empacadora", "almacen_frigorifico"];
    return keys.map((k) => machines.find((m) => m.station === k));
  }, [machines]);

  // bucle de animación
  useEffect(() => {
    if (status !== "running" || !tl) return;
    let last = performance.now(), raf;
    const tick = (now) => {
      const dt = Math.min((now - last) / 1000, 0.25); last = now;
      tRef.current = Math.min(tl.total, tRef.current + dt * speed * BASE);
      const s = snapshot(sim, tl, tRef.current);
      if (s.activeTemp && tRef.current - lastPush.current >= 4) {
        lastPush.current = tRef.current;
        histRef.current = [...histRef.current, { h: +(tRef.current / 60).toFixed(2), temp: +s.activeTemp.value.toFixed(1) }];
        setHist(histRef.current);
      }
      setT(tRef.current);
      if (tRef.current >= tl.total) { setStatus("done"); return; }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [status, speed, tl, sim]);

  const locked = status === "running" || status === "paused";
  const set = (k) => (e) => setP({ ...p, [k]: e.target.value });

  async function start() {
    if (status === "paused") return setStatus("running");
    setBusy(true);
    try {
      const cap = {};
      machBySlot.forEach((m) => { if (m) cap[m.station] = m.capacity_kg_h; });
      const body = {
        fruit_id: +p.fruit_id, input_kg: +p.input_kg, route: p.route, iqf_product: p.iqf_product,
        bag_grams: +(p.bag === "custom" ? p.bag_custom : p.bag), reject_rate_pct: +p.reject, shift_hours: +p.shift,
        capacity_kg_h: cap, ...(p.freeze !== "" ? { freeze_temp_c: +p.freeze } : {}),
      };
      const r = await api("/simulation/run", { method: "POST", body });
      tRef.current = 0; lastPush.current = -99; histRef.current = []; setHist([]); setT(0);
      setSim(r); setStatus("running");
      machBySlot.filter((m) => m && m.status !== "operativa").forEach((m) => toast(`${m.name} está en estado “${m.status}”. Revisa antes de producir.`, "warn"));
    } catch (err) { toast(err.message, "err"); } finally { setBusy(false); }
  }
  const pause = () => setStatus("paused");
  const reset = () => { tRef.current = 0; histRef.current = []; setHist([]); setT(0); setSim(null); setStatus("idle"); };

  const tot = sim?.totals;
  return (
    <>
      <div className="page-h">
        <div><h1>Simulador de línea de producción</h1><span className="tag demo">SIMULACIÓN · parámetros configurables</span></div>
      </div>

      <Panel title="Configuración">
        <div className="form-grid">
          <Field label="Tipo de fruto"><select disabled={locked} value={p.fruit_id} onChange={set("fruit_id")}>
            {fruits.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></Field>
          <Field label="Materia prima (kg)"><input type="number" disabled={locked} min="1" max="1000000" value={p.input_kg} onChange={set("input_kg")} /></Field>
          <Field label="Ruta de procesamiento"><select disabled={locked} value={p.route} onChange={set("route")}>
            <option value="PULPA">Pulpa (despulpado)</option>
            <option value="IQF">IQF (entero o trozado)</option></select></Field>
          {p.route === "IQF" && (
            <Field label="Presentación IQF"><select disabled={locked} value={p.iqf_product} onChange={set("iqf_product")}>
              <option value="fruto_entero">Fruto entero</option><option value="fruto_trozado">Fruto trozado</option></select></Field>)}
          <Field label="Presentación de empaque"><select disabled={locked} value={p.bag} onChange={set("bag")}>
            <option value="250">Bolsa de 250 g</option><option value="500">Bolsa de 500 g</option><option value="1000">Bolsa de 1 kg</option><option value="custom">Personalizada…</option></select></Field>
          {p.bag === "custom" && <Field label="Gramos por bolsa"><input type="number" disabled={locked} min="1" value={p.bag_custom} onChange={set("bag_custom")} /></Field>}
          <Field label="Rechazo en empaque (%)"><input type="number" disabled={locked} min="0" max="100" step="0.1" value={p.reject} onChange={set("reject")} /></Field>
          <Field label="Horas del turno" hint="Se alerta si una estación necesita más horas."><input type="number" disabled={locked} min="1" step="0.5" value={p.shift} onChange={set("shift")} /></Field>
          <Field label="Temperatura de congelamiento (°C)" hint="Vacío = valor de simulación por defecto."><input type="number" disabled={locked} step="0.5" placeholder="Por defecto" value={p.freeze} onChange={set("freeze")} /></Field>
        </div>
        <p className="note-line">{p.route === "IQF"
          ? "IQF congela fruto entero o trozado de forma individual; no se aplica a pulpa."
          : "La pulpa se obtiene en la despulpadora y se congela por separado, no por IQF."} Las capacidades se toman de las máquinas registradas en tu planta cuando existen.</p>
        <div className="sim-controls">
          <button className="primary" onClick={start} disabled={busy || status === "running" || !p.fruit_id || !(p.input_kg > 0)}>
            {busy ? "Preparando…" : status === "paused" ? "REANUDAR" : "INICIAR SIMULACIÓN"}</button>
          <button className="ghost dark" onClick={pause} disabled={status !== "running"}>PAUSAR</button>
          <button className="ghost dark" onClick={reset} disabled={status === "idle"}>REINICIAR</button>
          <div className="speed" role="group" aria-label="Velocidad de simulación"><span>Velocidad</span>
            {SPEEDS.map((s) => <button key={s} className={speed === s ? "on" : ""} onClick={() => setSpeed(s)}>{s}×</button>)}</div>
        </div>
      </Panel>

      <Panel title="Planta" actions={sim && <span className={`state-pill ${status}`}>{{ running: "En marcha", paused: "En pausa", done: "Completada" }[status]}</span>}>
        <Plant sim={sim} snap={snap} labels={labels} machines={machBySlot} />
        {!sim && <Empty>Elige el fruto, la cantidad y la ruta, y pulsa INICIAR SIMULACIÓN.</Empty>}
      </Panel>

      {sim && snap && (
        <>
          <div className="stats">
            <Stat label="Tiempo simulado" value={fmtClock(t)} sub={`de ${fmtClock(tl.total)}`} />
            <Stat label="Masa en proceso" value={fmt(snap.where.mass)} unit=" kg" tone="emerald" />
            <Stat label="Pérdidas y subproductos acumulados" value={fmt(snap.lossKg)} unit=" kg" />
            <Stat label="Producción acumulada" value={fmt(snap.unitsGood, 0)} unit=" bolsas" tone="orange"
                  sub={`${fmt(snap.unitsGood * (sim.totals.packaged_kg / Math.max(tot.packages_good, 1)))} kg empacados`} />
          </div>

          <div className="grid2">
            <Panel title="Alertas">
              {snap.alerts.length === 0 && !snap.done ? <Empty>Sin alertas de capacidad por ahora.</Empty> : (
                <ul className="alerts">
                  {snap.alerts.map((a, i) => <li key={i} className="warn">{a}</li>)}
                  {snap.done && <li className="ok">Simulación completada: {fmt(tot.packages_good, 0)} bolsas buenas, {fmt(tot.packages_rejected, 0)} rechazadas, {fmt(tot.packaged_kg)} kg ({fmt(tot.overall_yield_pct)} % de la materia prima).</li>}
                </ul>)}
            </Panel>
            <Panel title="Temperatura del equipo activo (simulada)">
              {hist.length < 2 ? <Empty>Se mostrará cuando la fruta o pulpa llegue al congelamiento.</Empty> : (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={hist} margin={{ left: -10, right: 8, top: 8 }}>
                    <CartesianGrid stroke="#E3EAE7" vertical={false} />
                    <XAxis dataKey="h" unit=" h" tick={{ fontSize: 12 }} /><YAxis unit="°" tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v) => `${v} °C`} labelFormatter={(l) => `${l} h`} />
                    <Line dataKey="temp" stroke="#10B981" dot={false} strokeWidth={2} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>)}
            </Panel>
          </div>

          <Panel title="Estado por estación">
            <div className="table-wrap"><table>
              <thead><tr><th>Estación</th><th>Estado</th><th className="n">Entrada (kg)</th><th className="n">Salida (kg)</th><th className="n">Pérdida (kg)</th><th className="n">Duración</th><th className="n">Capacidad (kg/h)</th><th className="n">Temp.</th></tr></thead>
              <tbody>{snap.rows.map((r) => (
                <tr key={r.station} className={r.status === "proceso" ? "row-active" : ""}>
                  <td><strong>{r.label}</strong>{r.note && <div className="sub">{r.note}</div>}</td>
                  <td><span className={`chip ${r.capacityAlert ? "alert" : r.status}`}>{r.capacityAlert ? "Alerta de capacidad" : STATUS_TXT[r.status]}</span></td>
                  <td className="n">{fmt(r.input_kg)}</td><td className="n">{fmt(r.output_kg)}</td><td className="n">{fmt(r.loss_kg)}</td>
                  <td className="n">{fmtClock(r.duration_min)}</td><td className="n">{fmt(r.capacity_kg_h, 0)}</td>
                  <td className="n">{r.temp_now != null ? `${fmt(r.temp_now)} °C` : "—"}</td></tr>))}</tbody>
            </table></div>
          </Panel>
          <p className="disclaimer">{sim.disclaimer}</p>
        </>
      )}
    </>
  );
}
