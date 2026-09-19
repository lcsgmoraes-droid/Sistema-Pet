import { FiPlusCircle, FiRefreshCw, FiUsers } from "react-icons/fi";
import { Link } from "react-router-dom";

export default function OpsTenantsHeader({ loading, onRefresh }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
          <FiUsers className="h-5 w-5" />
          Gestao de tenants
        </div>
        <h1 className="mt-1 text-2xl font-bold text-slate-950">Clientes e catalogo base</h1>
        <p className="mt-1 text-sm text-slate-500">
          Visao operacional dos tenants e comando controlado para copiar o cadastro base da loja
          Lucas.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Link
          to="/ops/grupos-comerciais/onboarding"
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 hover:bg-blue-100"
        >
          <FiPlusCircle className="h-4 w-4" />
          Novo grupo comercial (onboarding assistido)
        </Link>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiRefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </button>
      </div>
    </div>
  );
}
