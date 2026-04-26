import { Plus, Search } from "lucide-react";

export default function MedicamentosToolbar({ busca, onBuscaChange, onNovo }) {
  return (
    <div className="flex gap-3">
      <div className="relative flex-1">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={busca}
          onChange={(event) => onBuscaChange(event.target.value)}
          placeholder="Buscar por nome, comercial ou principio ativo..."
          className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-300"
        />
      </div>
      <button
        type="button"
        onClick={onNovo}
        className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
      >
        <Plus size={14} />
        Adicionar
      </button>
    </div>
  );
}
