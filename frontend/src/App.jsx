import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Lots from "./pages/Lots";
import Pulping from "./pages/Pulping";
import Simulator from "./pages/Simulator";

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="boot">Cargando BIOFACTORY 4.0…</div>;
  if (!user) return <Routes><Route path="*" element={<Auth />} /></Routes>;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="recepcion" element={<Lots />} />
        <Route path="despulpado" element={<Pulping />} />
        <Route path="simulador" element={<Simulator />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
