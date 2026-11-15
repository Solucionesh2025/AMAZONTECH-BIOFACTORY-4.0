const BASE = (import.meta.env.VITE_API_URL || "") + "/api";
const KEY = "bf_token";

export const getToken = () => localStorage.getItem(KEY);
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY));

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => (onUnauthorized = fn);

function message(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((d) => `${(d.loc || []).slice(1).join(".") || "dato"}: ${d.msg.replace("Value error, ", "")}`).join(" · ");
  return `Error ${status}`;
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && t) onUnauthorized();
  if (!res.ok) throw new Error(message(data.detail, res.status));
  return data;
}
