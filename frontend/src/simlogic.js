// Lógica pura del simulador: convierte la respuesta de /simulation/run en una línea de tiempo animable.
export const TRANSIT_MIN = 4;   // minutos simulados que tarda el producto entre estaciones
export const AMBIENT_C = 20;    // temperatura ambiente de partida (simulada)
const SLOT_OF = { recepcion: 0, lavado_seleccion: 1, despulpadora: 2, troceado: 2, congelamiento: 3, empacadora: 4, almacen_frigorifico: 5 };
const clamp = (v) => Math.max(0, Math.min(1, v));

export function slotLabels(route, iqfProduct) {
  return [
    "Recepción de frutos",
    "Lavado y selección",
    route === "PULPA" ? "Despulpadora" : iqfProduct === "fruto_trozado" ? "Troceado" : "Sin troceado (fruto entero)",
    route === "PULPA" ? "Congelamiento de pulpa" : "Congelamiento IQF",
    "Empaque y sellado",
    "Almacén frigorífico",
  ];
}

export function buildTimeline(sim) {
  const segs = [];
  let t = 0;
  sim.stages.forEach((s, i) => {
    if (i > 0) {
      const prev = sim.stages[i - 1];
      segs.push({ type: "transit", from: SLOT_OF[prev.station], to: SLOT_OF[s.station], start: t, end: t + TRANSIT_MIN, mass: prev.output_kg });
      t += TRANSIT_MIN;
    }
    const d = Math.max(s.duration_min, 0.1);
    segs.push({ type: "stage", slot: SLOT_OF[s.station], stage: s, start: t, end: t + d });
    t += d;
  });
  return { segs, total: t };
}

export function tempAt(target, p) {
  return AMBIENT_C + (target - AMBIENT_C) * (1 - Math.exp(-3 * p));
}

export function snapshot(sim, tl, t) {
  const rows = tl.segs.filter((s) => s.type === "stage").map((seg) => {
    const p = clamp((t - seg.start) / (seg.end - seg.start));
    const status = t < seg.start ? "espera" : t >= seg.end ? "completado" : "proceso";
    const s = seg.stage;
    let temp = null;
    if (s.temp_c != null && status !== "espera") temp = status === "completado" ? s.temp_c : tempAt(s.temp_c, p);
    return { ...s, slot: seg.slot, progress: p, status, temp_now: temp,
             capacityAlert: s.status === "alerta_capacidad" && t >= seg.start };
  });
  let where = { slot: 0, pos: 0, mass: sim.input_kg, kind: "espera" };
  for (const seg of tl.segs) {
    if (t < seg.start) break;
    const p = clamp((t - seg.start) / (seg.end - seg.start));
    if (seg.type === "stage") {
      const s = seg.stage;
      where = { slot: seg.slot, pos: seg.slot, mass: s.input_kg + (s.output_kg - s.input_kg) * p, kind: p >= 1 ? "reposo" : "proceso" };
    } else {
      where = { slot: seg.to, pos: seg.from + (seg.to - seg.from) * p, mass: seg.mass, kind: p >= 1 ? "reposo" : "transito" };
    }
  }
  const pack = rows.find((r) => r.station === "empacadora");
  const store = rows.find((r) => r.station === "almacen_frigorifico");
  const active = rows.find((r) => r.status === "proceso" && r.temp_now != null);
  return {
    rows, where,
    lossKg: Math.max(0, sim.input_kg - where.mass),
    unitsGood: pack ? Math.round(sim.totals.packages_good * pack.progress) : 0,
    storedKg: store ? store.output_kg * store.progress : 0,
    activeTemp: active ? { value: active.temp_now, label: active.label } : null,
    alerts: rows.filter((r) => r.capacityAlert).map((r) => `${r.label}: ${r.alert}`),
    done: t >= tl.total,
  };
}

export const fmtClock = (min) => `${Math.floor(min / 60)} h ${String(Math.floor(min % 60)).padStart(2, "0")} min`;
