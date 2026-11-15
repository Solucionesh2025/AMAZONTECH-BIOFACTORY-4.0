import { createContext, useCallback, useContext, useState } from "react";

const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((text, kind = "ok") => {
    const id = Math.random();
    setItems((x) => [...x, { id, text, kind }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((i) => <div key={i.id} className={`toast ${i.kind}`}>{i.text}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

export const Field = ({ label, children, hint }) => (
  <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>
);

export const Panel = ({ title, actions, children, className = "" }) => (
  <section className={`panel ${className}`}>
    {(title || actions) && <header className="panel-h"><h2>{title}</h2><div>{actions}</div></header>}
    {children}
  </section>
);

export const Stat = ({ label, value, unit, tone = "", sub }) => (
  <div className={`stat ${tone}`}>
    <span className="stat-l">{label}</span>
    <strong>{value ?? "—"}{value != null && unit ? <em>{unit}</em> : null}</strong>
    {sub && <small>{sub}</small>}
  </div>
);

export const Empty = ({ children }) => <p className="empty">{children}</p>;

export const fmt = (n, d = 1) => (n == null ? "—" : Number(n).toLocaleString("es-PE", { maximumFractionDigits: d }));
export const fmtDate = (s) => new Date(s + "T00:00:00").toLocaleDateString("es-PE", { day: "2-digit", month: "short" });
