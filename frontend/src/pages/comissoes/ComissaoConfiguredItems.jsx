import { COMMISSION_ITEM_ICONS } from "./comissoesConstants";

export default function ComissaoConfiguredItems({ configuracao, onRemoveConfig, onSelectItem }) {
  const configuredItems = Object.entries(configuracao);

  if (configuredItems.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 border rounded-lg p-3 bg-green-50">
      <h4 className="text-sm font-semibold text-green-800 mb-2">
        ✅ Itens Já Configurados ({configuredItems.length})
      </h4>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {configuredItems.map(([key, config]) => (
          <div
            key={key}
            className="w-full flex items-center justify-between text-xs bg-white p-2 rounded hover:bg-gray-50 transition-colors group"
          >
            <button
              onClick={() =>
                onSelectItem(config.tipo, config.referencia_id, config.nome_item || "Item")
              }
              className="flex-1 flex items-center gap-2 text-left"
            >
              {config.tipo === "geral" ? (
                <span className="font-semibold text-blue-700">Todos</span>
              ) : (
                COMMISSION_ITEM_ICONS[config.tipo]
              )}
              <span className="text-gray-700">{config.nome_item || "Item"}</span>
              <span className="text-green-600 font-medium ml-auto">
                {config.tipo_calculo === "percentual"
                  ? `${config.percentual}%`
                  : `Lucro ${config.percentual}%`}
              </span>
            </button>
            <button
              onClick={() => onRemoveConfig(key, config)}
              className="ml-2 text-red-600 hover:text-red-800 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>
      <p className="text-xs text-green-700 mt-2 italic">💡 Clique em um item para editar</p>
    </div>
  );
}
