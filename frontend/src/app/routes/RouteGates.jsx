import { Navigate } from "react-router-dom";
import ModuloBloqueado from "../../components/ModuloBloqueado";
import { useAuth } from "../../contexts/AuthContext";
import { isMobileViewport, isVeterinarioProfile } from "../../utils/veterinarioPerfil";

export function DefaultProtectedHomeRedirect() {
  const { user } = useAuth();
  const destino =
    isMobileViewport() && isVeterinarioProfile(user) ? "/veterinario/agenda" : "/lembretes";
  return <Navigate to={destino} replace />;
}

export function ModuleGate({ modulo, children }) {
  return <ModuloBloqueado modulo={modulo}>{children}</ModuloBloqueado>;
}
