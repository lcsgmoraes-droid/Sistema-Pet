import { Plus, Stethoscope } from "lucide-react";

export default function DashboardHeader({ exportando, onExportar, onNovaConsulta }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-xl">
          <Stethoscope size={24} className="text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Painel Veterinário</h1>
          <p className="text-sm text-gray-500">Visão geral do dia</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onExportar}
          disabled={exportando}
          className="bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
        >
          {exportando ? "Exportando..." : "Exportar relatório (CSV)"}
        </button>
        <button
          onClick={onNovaConsulta}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Nova consulta
        </button>
      </div>
    </div>
  );
}
