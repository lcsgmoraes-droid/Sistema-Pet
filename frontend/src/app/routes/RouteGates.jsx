import { Link, Navigate } from "react-router-dom";
import ModuloBloqueado from "../../components/ModuloBloqueado";
import { useAuth } from "../../contexts/AuthContext";
import { useModulos } from "../../contexts/ModulosContext";
import { isMobileViewport, isVeterinarioProfile } from "../../utils/veterinarioPerfil";

export function DefaultProtectedHomeRedirect() {
  const { user } = useAuth();
  const destino =
    isMobileViewport() && isVeterinarioProfile(user) ? "/veterinario/agenda" : "/dashboard";
  return <Navigate to={destino} replace />;
}

export function ModuleGate({ modulo, children }) {
  return <ModuloBloqueado modulo={modulo}>{children}</ModuloBloqueado>;
}

export function ResourceGate({ recurso, children }) {
  const { recursosAtivos, recursoAtivo } = useModulos();

  if (recursosAtivos === null) return <div className="min-h-[240px]" aria-hidden="true" />;
  if (recursoAtivo(recurso)) return children;

  return (
    <div className="flex min-h-[240px] items-center justify-center p-6">
      <div className="max-w-md rounded-xl border border-slate-200 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Recurso indisponível no plano atual
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          A entrada por XML não está incluída no plano desta empresa.
        </p>
        <Link className="mt-4 inline-block text-indigo-600 dark:text-indigo-300" to="/meu-plano">
          Ver meu plano
        </Link>
      </div>
    </div>
  );
}
