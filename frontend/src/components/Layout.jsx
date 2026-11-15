import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { ROLE_LABELS, useAuth } from "../auth";
import Icon from "./Icon";

const NAV = [
  { to: "/", label: "Panel principal", icon: "dash", end: true },
  { to: "/recepcion", label: "Recepción de fruta", icon: "truck" },
  { to: "/simulador", label: "Simulador de línea", icon: "play" },
  { to: "/despulpado", label: "Control de despulpado", icon: "drop" },
];

function useOutside(ref, fn) {
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && fn();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [ref, fn]);
}

function SearchBox() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const ref = useRef(null);
  const nav = useNavigate();
  useOutside(ref, () => setRes(null));
  useEffect(() => {
    if (q.trim().length < 2) return setRes(null);
    const t = setTimeout(() => api(`/search?q=${encodeURIComponent(q.trim())}`).then(setRes).catch(() => setRes(null)), 250);
    return () => clearTimeout(t);
  }, [q]);
  const total = res ? Object.values(res).flat().length : 0;
  const go = (path) => { setRes(null); setQ(""); nav(path); };
  return (
    <div className="search" ref={ref}>
      <Icon name="search" size={18} />
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar lote, proveedor, fruto o insumo" aria-label="Buscar" />
      {res && (
        <div className="drop">
          {total === 0 && <p className="empty">Sin resultados para “{q}”.</p>}
          {res.lots.map((x) => <button key={"l" + x.id} onClick={() => go("/recepcion")}>Lote {x.lot_number}<small>{x.weight_kg} kg</small></button>)}
          {res.suppliers.map((x) => <button key={"s" + x.id} onClick={() => go("/recepcion")}>Proveedor: {x.name}</button>)}
          {res.fruits.map((x) => <button key={"f" + x.id} onClick={() => go("/despulpado")}>Fruto: {x.name}</button>)}
          {res.inventory.map((x) => <button key={"i" + x.id} onClick={() => go("/")}>Inventario: {x.name}<small>{x.quantity} {x.unit}</small></button>)}
        </div>
      )}
    </div>
  );
}

function Bell() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useOutside(ref, () => setOpen(false));
  const load = () => api("/notifications").then(setItems).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, []);
  const unread = items.filter((i) => !i.read).length;
  const readAll = () => api("/notifications/read-all", { method: "POST" }).then(load);
  return (
    <div className="bell" ref={ref}>
      <button className="icon-btn" onClick={() => setOpen(!open)} aria-label={`Notificaciones, ${unread} sin leer`}>
        <Icon name="bell" />{unread > 0 && <span className="badge">{unread}</span>}
      </button>
      {open && (
        <div className="drop right">
          <div className="drop-h"><strong>Notificaciones</strong>{unread > 0 && <button className="link" onClick={readAll}>Marcar como leídas</button>}</div>
          {items.length === 0 && <p className="empty">No tienes notificaciones.</p>}
          {items.slice(0, 12).map((n) => (
            <div key={n.id} className={`note ${n.level} ${n.read ? "read" : ""}`}>{n.message}</div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <aside className={`side ${open ? "open" : ""}`}>
        <div className="brand">
          <span className="mark"><Icon name="leaf" size={22} /></span>
          <div><strong>BIOFACTORY 4.0</strong><small>AMAZONTECH</small></div>
        </div>
        <nav onClick={() => setOpen(false)}>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav">
              <Icon name={n.icon} />{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="me">
          <strong>{user.full_name}</strong>
          <small>{ROLE_LABELS[user.role]}</small>
          <button className="ghost" onClick={signOut}><Icon name="out" size={16} /> Cerrar sesión</button>
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <div className="main">
        <header className="top">
          <button className="icon-btn menu" onClick={() => setOpen(true)} aria-label="Abrir menú"><Icon name="menu" /></button>
          <SearchBox />
          <Bell />
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
