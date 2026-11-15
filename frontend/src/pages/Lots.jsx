import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Icon from "../components/Icon";
import { Empty, Field, Panel, fmt, fmtDate, useToast } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const blank = () => ({ fruit_id: "", supplier_id: "", received_on: today(), weight_kg: "", quality: "A", condition: "óptimo", notes: "", lot_number: "" });

export default function Lots() {
  const toast = useToast();
  const [lots, setLots] = useState([]);
  const [fruits, setFruits] = useState([]);
  const [sups, setSups] = useState([]);
  const [f, setF] = useState(blank());
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [supForm, setSupForm] = useState(null);

  const load = () => Promise.all([api("/lots"), api("/fruits"), api("/suppliers")])
    .then(([l, fr, s]) => { setLots(l); setFruits(fr); setSups(s); }).catch((e) => toast(e.message, "err"));
  useEffect(() => { load(); }, []);

  const fname = useMemo(() => Object.fromEntries(fruits.map((x) => [x.id, x.name])), [fruits]);
  const sname = useMemo(() => Object.fromEntries(sups.map((x) => [x.id, x.name])), [sups]);
  const rows = lots.filter((l) => !q || `${l.lot_number} ${fname[l.fruit_id] || ""} ${sname[l.supplier_id] || ""}`.toLowerCase().includes(q.toLowerCase()));
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function save(e) {
    e.preventDefault(); setBusy(true);
    try {
      const body = { ...f, fruit_id: +f.fruit_id, supplier_id: f.supplier_id ? +f.supplier_id : null,
                     weight_kg: +f.weight_kg, lot_number: f.lot_number.trim() || null, notes: f.notes.trim() || null };
      const lot = await api("/lots", { method: "POST", body });
      toast(`Lote ${lot.lot_number} registrado.`); setF(blank()); load();
    } catch (err) { toast(err.message, "err"); } finally { setBusy(false); }
  }
  async function remove(l) {
    if (!confirm(`¿Eliminar el lote ${l.lot_number}?`)) return;
    try { await api(`/lots/${l.id}`, { method: "DELETE" }); toast("Lote eliminado."); load(); }
    catch (err) { toast(err.message, "err"); }
  }
  async function addSupplier(e) {
    e.preventDefault();
    try {
      const s = await api("/suppliers", { method: "POST", body: { name: supForm.name, location: supForm.location || null } });
      toast(`Proveedor ${s.name} agregado.`); setSupForm(null); await load(); setF((x) => ({ ...x, supplier_id: String(s.id) }));
    } catch (err) { toast(err.message, "err"); }
  }

  return (
    <>
      <div className="page-h"><h1>Recepción de fruta</h1></div>
      <Panel title="Registrar recepción">
        <form className="form-grid" onSubmit={save}>
          <Field label="Fruto"><select required value={f.fruit_id} onChange={set("fruit_id")}>
            <option value="">Selecciona…</option>{fruits.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field>
          <Field label="Proveedor">
            <select value={f.supplier_id} onChange={set("supplier_id")}>
              <option value="">Sin proveedor</option>{sups.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
            <button type="button" className="link" onClick={() => setSupForm({ name: "", location: "" })}>+ Nuevo proveedor</button>
          </Field>
          <Field label="Fecha de recepción"><input type="date" required value={f.received_on} onChange={set("received_on")} /></Field>
          <Field label="Peso recibido (kg)"><input type="number" required min="0.01" step="0.01" value={f.weight_kg} onChange={set("weight_kg")} /></Field>
          <Field label="Calidad"><select value={f.quality} onChange={set("quality")}>
            <option value="A">A</option><option value="B">B</option><option value="C">C</option><option value="rechazado">Rechazado</option></select></Field>
          <Field label="Estado de la materia prima"><select value={f.condition} onChange={set("condition")}>
            <option>óptimo</option><option>aceptable</option><option>deficiente</option></select></Field>
          <Field label="Número de lote" hint="Déjalo vacío para generarlo automáticamente."><input maxLength={40} value={f.lot_number} onChange={set("lot_number")} /></Field>
          <Field label="Observaciones"><input value={f.notes} onChange={set("notes")} /></Field>
          <div className="form-actions"><button className="primary" disabled={busy}>{busy ? "Guardando…" : "Registrar lote"}</button></div>
        </form>
        {supForm && (
          <form className="inline-form" onSubmit={addSupplier}>
            <input required placeholder="Nombre del proveedor" value={supForm.name} onChange={(e) => setSupForm({ ...supForm, name: e.target.value })} />
            <input placeholder="Ubicación" value={supForm.location} onChange={(e) => setSupForm({ ...supForm, location: e.target.value })} />
            <button className="primary sm">Guardar proveedor</button>
            <button type="button" className="ghost sm" onClick={() => setSupForm(null)}>Cancelar</button>
          </form>
        )}
      </Panel>

      <Panel title={`Lotes recibidos (${rows.length})`} actions={<input className="filter" placeholder="Filtrar por lote, fruto o proveedor" value={q} onChange={(e) => setQ(e.target.value)} />}>
        {rows.length === 0 ? <Empty>No hay lotes que coincidan. Registra la primera recepción arriba.</Empty> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Lote</th><th>Fecha</th><th>Fruto</th><th>Proveedor</th><th className="n">Peso (kg)</th><th>Calidad</th><th>Estado</th><th /></tr></thead>
            <tbody>{rows.slice(0, 100).map((l) => (
              <tr key={l.id}>
                <td><strong>{l.lot_number}</strong>{l.is_demo && <span className="tag demo sm">DEMO</span>}</td>
                <td>{fmtDate(l.received_on)}</td><td>{fname[l.fruit_id]}</td><td>{sname[l.supplier_id] || "—"}</td>
                <td className="n">{fmt(l.weight_kg)}</td><td><span className={`q q-${l.quality}`}>{l.quality}</span></td><td>{l.condition}</td>
                <td><button className="icon-btn" aria-label={`Eliminar lote ${l.lot_number}`} onClick={() => remove(l)}><Icon name="trash" size={17} /></button></td>
              </tr>))}</tbody>
          </table></div>
        )}
      </Panel>
    </>
  );
}
