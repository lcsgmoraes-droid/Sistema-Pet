import { Plus, Stethoscope } from "lucide-react";

export default function DashboardHeader({ exportando, onExportar, onNovaConsulta }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <div className="shrink-0 rounded-xl bg-blue-100 p-2">
          <Stethoscope size={24} className="text-blue-600" />
        </div>
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-gray-800 sm:text-2xl">Painel Veterinário</h1>
          <p className="text-sm text-gray-500">Visão geral do dia</p>
        </div>
      </div>
      <div className="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-2">
        <button
          onClick={onExportar}
          disabled={exportando}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-60"
        >
          {exportando ? "Exportando..." : "Exportar relatório (CSV)"}
        </button>
        <button
          onClick={onNovaConsulta}
          className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <Plus size={16} />
          Nova consulta
        </button>
      </div>
    </div>
  );
}
