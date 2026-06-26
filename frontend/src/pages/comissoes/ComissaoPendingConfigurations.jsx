export default function ComissaoPendingConfigurations({
  configuracoesParaSalvar,
  onRemove,
  onSaveAll,
  progressoSalvamento,
  salvando,
}) {
  if (configuracoesParaSalvar.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 border rounded-lg p-4">
      <h4 className="font-semibold mb-3">
        Configurações a Salvar ({configuracoesParaSalvar.length})
      </h4>
      <div className="space-y-2 max-h-40 overflow-y-auto">
        {configuracoesParaSalvar.map((config, index) => (
          <div
            key={`${config.tipo}-${config.referencia_id}-${index}`}
            className="flex items-center justify-between bg-gray-50 p-2 rounded text-sm"
          >
            <div>
              <span className="font-medium">{config.nome}</span>
              <span className="text-gray-500 ml-2">
                (
                {config.tipo_calculo === "percentual"
                  ? `${config.percentual}%`
                  : `Lucro ${config.percentual}%`}
                )
              </span>
            </div>
            <button onClick={() => onRemove(index)} className="text-red-600 hover:text-red-800">
              ✕
            </button>
          </div>
        ))}
      </div>
      <button
        onClick={onSaveAll}
        disabled={salvando}
        className={`w-full py-2 rounded mt-4 text-white ${
          salvando ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
        }`}
      >
        {salvando ? (
          <span>
            ⏳ Salvando {progressoSalvamento.atual}/{progressoSalvamento.total}...
          </span>
        ) : (
          "💾 Salvar Todas as Configurações"
        )}
      </button>
    </div>
  );
}
