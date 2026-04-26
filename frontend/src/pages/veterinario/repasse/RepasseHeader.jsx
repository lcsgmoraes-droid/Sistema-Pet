import { DollarSign, RefreshCw } from "lucide-react";

export default function RepasseHeader({ carregando, onAtualizar }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-sky-100 rounded-xl">
          <DollarSign size={22} className="text-sky-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Fechamento de Repasse</h1>
          <p className="text-sm text-gray-500">Controle de recebimento dos lancamentos veterinarios</p>
        </div>
      </div>
      <button
        onClick={onAtualizar}
        disabled={carregando}
        className="flex items-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 px-3 py-2 rounded-lg text-sm transition-colors disabled:opacity-60"
      >
        <RefreshCw size={14} className={carregando ? "animate-spin" : ""} />
        Atualizar
      </button>
    </div>
  );
}
