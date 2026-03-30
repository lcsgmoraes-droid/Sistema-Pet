import { Plus, Star, X } from "lucide-react";

export default function PDVOportunidadesSidebar({
  aberto,
  opportunities,
  onClose,
  onAdicionar,
  onAlternativa,
  onIgnorar,
}) {
  if (!aberto) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute top-0 right-0 w-80 h-full bg-gray-50 border-l border-gray-300 shadow-lg flex flex-col animate-in slide-in-from-right duration-200">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-300 bg-white">
          <div className="flex items-center gap-2">
            <Star className="w-4 h-4 text-gray-600" />
            <h2 className="text-sm font-medium text-gray-700">Oportunidades</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            type="button"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {opportunities.slice(0, 5).map((opp) => (
            <div
              key={opp.id}
              className="p-3 bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors"
            >
              <h3 className="text-xs font-medium text-gray-900 mb-1">
                {opp.titulo}
              </h3>
              <p className="text-xs text-gray-700 mb-2 leading-relaxed">
                {opp.descricao_curta}
              </p>

              <div className="flex items-center justify-between gap-2 text-xs mt-2">
                <button
                  onClick={() => onAdicionar(opp)}
                  className="flex items-center gap-1 text-green-500 hover:text-green-600 transition-colors whitespace-nowrap font-medium"
                  title="Adicionar ao carrinho"
                  type="button"
                >
                  <Plus className="w-3 h-3" />
                  <span>Adicionar</span>
                </button>
                <button
                  onClick={() => onAlternativa(opp)}
                  className="text-orange-600 hover:text-orange-700 transition-colors whitespace-nowrap flex-1 text-center font-medium"
                  title="Ver alternativa"
                  type="button"
                >
                  Alternativa
                </button>
                <button
                  onClick={() => onIgnorar(opp)}
                  className="flex items-center gap-1 text-red-500 hover:text-red-600 transition-colors whitespace-nowrap font-medium"
                  title="Ignorar sugestão"
                  type="button"
                >
                  <span>Ignorar</span>
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}

          {opportunities.length === 0 && (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <p className="text-xs">Nenhuma oportunidade disponível</p>
            </div>
          )}
        </div>

        <div className="px-4 py-2 border-t border-gray-200 bg-white">
          <p className="text-[10px] text-gray-400 text-center">
            {opportunities.length > 0
              ? `${Math.min(opportunities.length, 6)} oportunidades`
              : ""}
          </p>
        </div>
      </div>
    </div>
  );
}
