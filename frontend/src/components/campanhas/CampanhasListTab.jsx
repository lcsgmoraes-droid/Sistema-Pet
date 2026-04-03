const FALLBACK_TIPO = {
  color: "bg-gray-100 text-gray-700",
  emoji: "📋",
};

export default function CampanhasListTab({
  campanhas,
  loadingCampanhas,
  campanhaEditando,
  arquivando,
  toggling,
  salvandoParams,
  tipoLabels,
  userCreatableTypes,
  formatarParams,
  renderFormCampaign,
  onNovaCampanha,
  onAbrirEdicao,
  onFecharEdicao,
  onArquivarCampanha,
  onToggleCampanha,
  onSalvarParametros,
}) {
  const campanhasVisiveis = campanhas.filter(
    (campanha) => campanha.campaign_type !== "ranking_monthly",
  );

  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Campanhas Cadastradas</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {campanhasVisiveis.length} campanha(s)
          </span>
          <button
            onClick={onNovaCampanha}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
          >
            + Nova Campanha
          </button>
        </div>
      </div>

      {loadingCampanhas ? (
        <div className="p-8 text-center text-gray-400">
          Carregando campanhas...
        </div>
      ) : campanhas.length === 0 ? (
        <div className="p-8 text-center text-gray-400">
          <p className="text-2xl mb-2">🎪</p>
          <p>Nenhuma campanha cadastrada ainda.</p>
        </div>
      ) : (
        <div className="divide-y">
          {campanhasVisiveis.map((campanha) => {
            const tipo = tipoLabels[campanha.campaign_type] || {
              ...FALLBACK_TIPO,
              label: campanha.campaign_type,
            };
            const ativa = campanha.status === "active";
            const editando = campanhaEditando === campanha.id;

            return (
              <div key={campanha.id} className="px-6 py-4">
                <div className="flex items-center gap-4">
                  <div className="text-2xl">{tipo.emoji}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">
                        {campanha.name}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${tipo.color}`}
                      >
                        {tipo.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5 truncate">
                      {formatarParams(campanha.campaign_type, campanha.params)}
                    </p>
                  </div>

                  <button
                    onClick={() =>
                      editando
                        ? onFecharEdicao()
                        : onAbrirEdicao(campanha)
                    }
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                  >
                    {editando ? "Cancelar" : "⚙️ Configurar"}
                  </button>

                  {userCreatableTypes.has(campanha.campaign_type) && (
                    <button
                      onClick={() => onArquivarCampanha(campanha)}
                      disabled={arquivando === campanha.id}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
                      title="Arquivar campanha"
                    >
                      {arquivando === campanha.id ? "..." : "🗑️"}
                    </button>
                  )}

                  <button
                    onClick={() => onToggleCampanha(campanha)}
                    disabled={toggling === campanha.id}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors min-w-[100px] disabled:opacity-50 ${
                      ativa
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {toggling === campanha.id
                      ? "..."
                      : ativa
                        ? "✅ Ativa"
                        : "⏸️ Pausada"}
                  </button>
                </div>

                {editando && (
                  <div className="mt-4 bg-blue-50 rounded-xl p-4 border border-blue-200">
                    <p className="text-xs font-semibold text-blue-700 mb-3">
                      ⚙️ Parâmetros —{" "}
                      {tipoLabels[campanha.campaign_type]?.label ||
                        campanha.campaign_type}
                    </p>
                    {renderFormCampaign(campanha)}
                    <button
                      onClick={() => onSalvarParametros(campanha)}
                      disabled={salvandoParams}
                      className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {salvandoParams ? "Salvando..." : "💾 Salvar Parâmetros"}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
