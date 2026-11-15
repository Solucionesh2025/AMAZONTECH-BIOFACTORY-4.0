import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../components/ui";

const STATIONS = ["Recepción", "Lavado", "Despulpado", "Congelamiento", "Empaque", "Almacén frío"];

function Line() {
  return (
    <div className="line" aria-hidden="true">
      <div className="belt"><span className="item" /></div>
      <ol>{STATIONS.map((s) => <li key={s}><i />{s}</li>)}</ol>
    </div>
  );
}

export default function Auth() {
  const { login, register } = useAuth();
  const toast = useToast();
  const [mode, setMode] = useState("login"); // login | register | forgot | reset
  const [f, setF] = useState({ email: "", password: "", company_name: "", admin_name: "", token: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      if (mode === "login") await login(f.email, f.password);
      else if (mode === "register")
        await register({ company_name: f.company_name, admin_name: f.admin_name, email: f.email, password: f.password });
      else if (mode === "forgot") {
        const r = await api("/auth/forgot-password", { method: "POST", body: { email: f.email } });
        toast(r.message);
        if (r.dev_token) { setF({ ...f, token: r.dev_token }); toast("Modo desarrollo: el código se completó automáticamente.", "warn"); }
        setMode("reset");
      } else {
        await api("/auth/reset-password", { method: "POST", body: { token: f.token, new_password: f.password } });
        toast("Contraseña actualizada. Ya puedes iniciar sesión.");
        setF({ ...f, password: "", token: "" }); setMode("login");
      }
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const titles = { login: "Inicia sesión", register: "Registra tu empresa", forgot: "Recupera tu contraseña", reset: "Crea una contraseña nueva" };
  return (
    <div className="auth">
      <section className="auth-hero">
        <div>
          <h1>BIOFACTORY 4.0</h1>
          <p>Controla tu línea de procesamiento de frutos amazónicos, desde la recepción hasta la cámara fría.</p>
        </div>
        <Line />
        <small>Desarrollado por AMAZONTECH</small>
      </section>
      <form className="auth-form" onSubmit={submit}>
        <h2>{titles[mode]}</h2>
        {mode === "register" && (<>
          <label className="field"><span>Nombre de la empresa</span><input required minLength={2} value={f.company_name} onChange={set("company_name")} /></label>
          <label className="field"><span>Tu nombre</span><input required minLength={2} value={f.admin_name} onChange={set("admin_name")} /></label>
        </>)}
        {mode !== "reset" && <label className="field"><span>Correo</span><input type="email" required autoComplete="email" value={f.email} onChange={set("email")} /></label>}
        {mode === "reset" && <label className="field"><span>Código de recuperación</span><input required value={f.token} onChange={set("token")} /></label>}
        {mode !== "forgot" && (
          <label className="field"><span>{mode === "reset" ? "Nueva contraseña" : "Contraseña"}</span>
            <input type="password" required minLength={mode === "login" ? 1 : 8} maxLength={64} autoComplete={mode === "login" ? "current-password" : "new-password"} value={f.password} onChange={set("password")} />
            {mode !== "login" && <small>Mínimo 8 caracteres.</small>}
          </label>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "Procesando…" : { login: "Entrar", register: "Crear empresa", forgot: "Enviar instrucciones", reset: "Guardar contraseña" }[mode]}
        </button>
        <div className="auth-links">
          {mode === "login" && (<>
            <button type="button" className="link" onClick={() => setMode("register")}>Registrar mi empresa</button>
            <button type="button" className="link" onClick={() => setMode("forgot")}>Olvidé mi contraseña</button>
          </>)}
          {mode !== "login" && <button type="button" className="link" onClick={() => { setError(""); setMode("login"); }}>Volver a iniciar sesión</button>}
        </div>
        {mode === "login" && (
          <p className="demo-hint">Empresa de demostración: <code>admin@demo.biofactory</code> · clave <code>Demo2026!</code>
            <button type="button" className="link" onClick={() => setF({ ...f, email: "admin@demo.biofactory", password: "Demo2026!" })}>Usar estos datos</button></p>
        )}
      </form>
    </div>
  );
}
