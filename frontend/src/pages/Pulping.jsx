import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Empty, Field, Panel, fmt, fmtDate, useToast } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const blank = () => ({ lot_id: "", recorded_on: today(), initial_kg: "", pulp_kg: "", seed_kg: "", peel_kg: "", other_kg: "" });
const n = (v) => (v === "" || v == null ? 0 : +v);

export default function Pulping() {
  const toast = useToast();
  const [recs, setRecs] = useState([]);
  const [lots, setLots] = useState([]);
  const [fruits, setFruits] = useState([]);
  const [rep, setRep] = useState([]);
  const [f, setF] = useState(blank());
  const [busy, setBusy] = useState(false);

  const load = () => Promise.all([api("/pulping"), api("/lots"), api("/fruits"), api("/yield-report?days=30")])
    .then(([r, l, fr, y]) => { setRecs(r); setLots(l); setFruits(fr); setRep(y); })
    .catch((e) => toast(e.message, "err"));
  useEffect(() => { load(); }, []);

  const fname = useMemo(() => Object.fromEntries(fruits.map((x) => [x.id, x.name])), [fruits]);
  const lotInfo = useMemo(() => Object.fromEntries(lots.map((l) => [l.id, l])), [lots]);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const pickLot = (e) => {
    const l = lotInfo[e.target.value];
    setF({ ...f, lot_id: e.target.value, initial_kg: l ? String(l.weight_kg) : f.initial_kg });
  };

  const total = n(f.pulp_kg) + n(f.seed_kg) + n(f.peel_kg) + n(f.other_kg);
  const init = n(f.initial_kg);
  const yieldPct = init > 0 ? (n(f.pulp_kg) / init) * 100 : null;
  const over = init > 0 && total > init * 1.001;
  const unaccounted = init > 0 ? init - total : null;

  async function save(e) {
    e.preventDefault();
    if (over) return toast("La suma de pulpa, semillas, cáscaras y otros supera el peso inicial.", "err");
    setBusy(true);
    try {
      const r = await api("/pulping", { method: "POST", body: { lot_id: +f.lot_id, recorded_on: f.recorded_on,
        initial_kg: init, pulp_kg: n(f.pulp_kg), seed_kg: n(f.seed_kg), peel_kg: n(f.peel_kg), other_kg: n(f.other_kg) } });
      toast(`Despulpado guardado. Rendimiento: ${fmt(r.yield_pct, 2)} %`); setF(blank()); load();
    } catch (err) { toast(err.message, "err"); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="page-h"><h1>Control de despulpado</h1></div>
      <div className="grid2 wide-left">
        <Panel title="Registrar despulpado">
          <form className="form-grid one" onSubmit={save}>
            <Field label="Lote"><select required value={f.lot_id} onChange={pickLot}>
              <option value="">Selecciona un lote…</option>
              {lots.map((l) => <option key={l.id} value={l.id}>{l.lot_number} · {fname[l.fruit_id]} · {fmt(l.weight_kg)} kg</option>)}</select></Field>
            <Field label="Fecha"><input type="date" required value={f.recorded_on} onChange={set("recorded_on")} /></Field>
            <Field label="Peso inicial (kg)"><input type="number" required min="0.01" step="0.01" value={f.initial_kg} onChange={set("initial_kg")} /></Field>
            <Field label="Peso de pulpa (kg)"><input type="number" required min="0" step="0.01" value={f.pulp_kg} onChange={set("pulp_kg")} /></Field>
            <Field label="Peso de semillas (kg)"><input type="number" min="0" step="0.01" value={f.seed_kg} onChange={set("seed_kg")} /></Field>
            <Field label="Peso de cáscaras (kg)"><input type="number" min="0" step="0.01" value={f.peel_kg} onChange={set("peel_kg")} /></Field>
            <Field label="Otros residuos (kg)"><input type="number" min="0" step="0.01" value={f.other_kg} onChange={set("other_kg")} /></Field>
            <div className={`calc ${over ? "bad" : ""}`} aria-live="polite">
              <span>Rendimiento = pulpa ÷ peso inicial × 100</span>
              <strong>{yieldPct == null ? "—" : `${fmt(yieldPct, 2)} %`}</strong>
              {unaccounted != null && <small>{over ? `La suma excede el peso inicial en ${fmt(-unaccounted, 2)} kg.` : `Sin contabilizar: ${fmt(unaccounted, 2)} kg`}</small>}
            </div>
            <div className="form-actions"><button className="primary" disabled={busy || over}>{busy ? "Guardando…" : "Guardar despulpado"}</button></div>
          </form>
        </Panel>

        <Panel title="Rendimiento por fruto (últimos 30 días)">
          {rep.length === 0 ? <Empty>Aún no hay registros de despulpado.</Empty> : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={rep} margin={{ left: -10, right: 8, top: 8 }}>
                <CartesianGrid stroke="#E3EAE7" vertical={false} />
                <XAxis dataKey="fruit" tick={{ fontSize: 12 }} /><YAxis unit="%" tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => `${v} %`} /><Legend />
                <Bar name="Rendimiento de pulpa" dataKey="yield_pct" fill="#10B981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <Panel title="Distribución de masa por fruto (kg)">
        {rep.length === 0 ? <Empty>Sin datos todavía.</Empty> : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={rep} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid stroke="#E3EAE7" vertical={false} />
              <XAxis dataKey="fruit" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip /><Legend />
              <Bar name="Pulpa" dataKey="pulp_kg" stackId="a" fill="#10B981" />
              <Bar name="Semillas" dataKey="seed_kg" stackId="a" fill="#0E5A43" />
              <Bar name="Cáscaras" dataKey="peel_kg" stackId="a" fill="#F28C28" />
              <Bar name="Otros" dataKey="other_kg" stackId="a" fill="#8A9792" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Panel>

      <Panel title="Historial de despulpado">
        {recs.length === 0 ? <Empty>No hay registros.</Empty> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Fecha</th><th>Lote</th><th>Fruto</th><th className="n">Inicial</th><th className="n">Pulpa</th><th className="n">Semillas</th><th className="n">Cáscaras</th><th className="n">Otros</th><th className="n">Rend. %</th></tr></thead>
            <tbody>{recs.slice(0, 60).map((r) => {
              const l = lotInfo[r.lot_id];
              return (<tr key={r.id}><td>{fmtDate(r.recorded_on)}</td><td>{l?.lot_number || `#${r.lot_id}`}</td><td>{l ? fname[l.fruit_id] : "—"}</td>
                <td className="n">{fmt(r.initial_kg)}</td><td className="n">{fmt(r.pulp_kg)}</td><td className="n">{fmt(r.seed_kg)}</td>
                <td className="n">{fmt(r.peel_kg)}</td><td className="n">{fmt(r.other_kg)}</td><td className="n"><strong>{fmt(r.yield_pct, 2)}</strong></td></tr>);
            })}</tbody>
          </table></div>
        )}
      </Panel>
    </>
  );
}
