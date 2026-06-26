import { FiRefreshCw, FiUsers } from "react-icons/fi";

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
  );
}
