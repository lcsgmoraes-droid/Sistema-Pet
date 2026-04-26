import { Filter, Search } from "lucide-react";

export default function ConsultasFiltros({ busca, filtroStatus, onBuscaChange, onStatusChange }) {
  return (
    <div className="flex flex-wrap gap-3">
      <div className="relative flex-1 min-w-[200px]">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por codigo, pet, veterinario, motivo ou diagnostico..."
          value={busca}
          onChange={(event) => onBuscaChange(event.target.value)}
          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>
      <div className="relative">
        <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <select
          value={filtroStatus}
          onChange={(event) => onStatusChange(event.target.value)}
          className="pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white appearance-none"
        >
          <option value="">Todos os status</option>
          <option value="aberta">Aberta</option>
          <option value="finalizada">Finalizada</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>
    </div>
  );
}
