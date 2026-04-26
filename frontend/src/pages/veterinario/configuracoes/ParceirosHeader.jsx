import { ChevronDown, ChevronUp, Link2, Plus } from "lucide-react";

export default function ParceirosHeader({ mostrarForm, onToggleForm, totalParceiros }) {
  return (
    <div className="flex items-center justify-between p-5 border-b border-gray-100">
      <div className="flex items-center gap-2">
        <Link2 size={20} className="text-blue-500" />
        <h2 className="text-lg font-semibold text-gray-900">Veterinarios Parceiros</h2>
        <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          {totalParceiros}
        </span>
      </div>
      <button
        onClick={onToggleForm}
        className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
      >
        <Plus size={16} />
        Vincular parceiro
        {mostrarForm ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
    </div>
  );
}
