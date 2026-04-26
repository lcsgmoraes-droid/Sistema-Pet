import { RefreshCw, Settings } from "lucide-react";

export default function ConfiguracoesHeader({ onReload }) {
  return (
    <div className="flex items-center gap-3">
      <div className="p-2 bg-blue-100 rounded-lg">
        <Settings size={24} className="text-blue-600" />
      </div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configurações - Módulo Veterinário</h1>
        <p className="text-gray-500 text-sm">Gerencie o modelo operacional e os veterinários parceiros.</p>
      </div>
      <button
        onClick={onReload}
        className="ml-auto p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        title="Recarregar"
      >
        <RefreshCw size={18} />
      </button>
    </div>
  );
}
