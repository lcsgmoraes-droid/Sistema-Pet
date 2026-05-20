import { Filter, Search } from "lucide-react";

export default function ConsultasFiltros({ busca, filtroStatus, onBuscaChange, onStatusChange }) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
      <div className="relative min-w-0">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por codigo, pet, veterinario, motivo ou diagnostico..."
          value={busca}
          onChange={(event) => onBuscaChange(event.target.value)}
          className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>
      <div className="relative min-w-0">
        <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <select
          value={filtroStatus}
          onChange={(event) => onStatusChange(event.target.value)}
          className="w-full appearance-none rounded-lg border border-gray-200 bg-white py-2 pl-8 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
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
