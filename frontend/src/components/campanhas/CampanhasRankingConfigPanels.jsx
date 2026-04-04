function toggleFlag(setRankingConfig, key) {
  setRankingConfig((prev) =>
    prev ? { ...prev, [key]: !prev[key] } : prev,
  );
}

export default function CampanhasRankingConfigPanels({
  rankingConfig,
  setRankingConfig,
  rankingConfigLoading,
  salvarRankingConfig,
  rankingConfigSalvando,
  rankLabels,
  formatBRL,
}) {
  return (
    <>
      <div className="bg-white rounded-xl border shadow-sm">
        <button
          className="w-full px-6 py-4 flex items-center justify-between text-left"
          onClick={() => toggleFlag(setRankingConfig, "_aberto")}
        >
          <span className="font-semibold text-gray-800">
            Configurar criterios de ranking
          </span>
          <span className="text-gray-400 text-sm">
            {rankingConfig?._aberto ? "Fechar" : "Expandir"}
          </span>
        </button>
        {rankingConfig?._aberto && (
          <div className="px-6 pb-6 space-y-4">
            {rankingConfigLoading ? (
              <div className="text-center text-gray-400 py-4">Carregando...</div>
            ) : !rankingConfig ? (
              <div className="text-center text-gray-400 py-4">
                Nao foi possivel carregar.
              </div>
            ) : (
              <>
                <p className="text-xs text-gray-500">
                  O cliente precisa atingir <strong>todos</strong> os criterios
                  de um nivel para alcanca-lo.
                </p>
                {[
                  { key: "silver", label: "Prata" },
                  { key: "gold", label: "Ouro" },
                  { key: "diamond", label: "Platina" },
                  { key: "platinum", label: "Diamante" },
                ].map(({ key, label }) => (
                  <div key={key} className="border rounded-xl p-4 space-y-2">
                    <p className="font-medium text-gray-700">{label}</p>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Gasto minimo (R$)
                        </label>
                        <input
                          type="number"
                          value={rankingConfig[`${key}_min_spent`] ?? ""}
                          onChange={(e) =>
                            setRankingConfig((prev) => ({
                              ...prev,
                              [`${key}_min_spent`]: e.target.value,
                            }))
                          }
                          className="w-full border rounded-lg px-3 py-2 text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Compras minimas
                        </label>
                        <input
                          type="number"
                          value={rankingConfig[`${key}_min_purchases`] ?? ""}
                          onChange={(e) =>
                            setRankingConfig((prev) => ({
                              ...prev,
                              [`${key}_min_purchases`]: e.target.value,
                            }))
                          }
                          className="w-full border rounded-lg px-3 py-2 text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Meses ativos minimos
                        </label>
                        <input
                          type="number"
                          value={rankingConfig[`${key}_min_months`] ?? ""}
                          onChange={(e) =>
                            setRankingConfig((prev) => ({
                              ...prev,
                              [`${key}_min_months`]: e.target.value,
                            }))
                          }
                          className="w-full border rounded-lg px-3 py-2 text-sm"
                        />
                      </div>
                    </div>
                  </div>
                ))}
                <div className="flex justify-end">
                  <button
                    onClick={salvarRankingConfig}
                    disabled={rankingConfigSalvando}
                    className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 disabled:opacity-50"
                  >
                    {rankingConfigSalvando ? "Salvando..." : "Salvar criterios"}
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border shadow-sm">
        <button
          className="w-full px-6 py-4 flex items-center justify-between text-left"
          onClick={() => toggleFlag(setRankingConfig, "_beneficios_aberto")}
        >
          <span className="font-semibold text-gray-800">
            Beneficios por nivel
          </span>
          <span className="text-gray-400 text-sm">
            {rankingConfig?._beneficios_aberto ? "Fechar" : "Expandir"}
          </span>
        </button>
        {rankingConfig?._beneficios_aberto && (
          <div className="px-6 pb-6 space-y-4">
            {["bronze", "silver", "gold", "diamond", "platinum"].map((key) => {
              const rankLabel = rankLabels[key];
              return (
                <div key={key} className="border rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${rankLabel.color} ${rankLabel.border}`}
                    >
                      {rankLabel.emoji} {rankLabel.label}
                    </span>
                  </div>
                  <textarea
                    rows={2}
                    value={rankingConfig?.[`${key}_benefits`] ?? ""}
                    onChange={(e) =>
                      setRankingConfig((prev) => ({
                        ...prev,
                        [`${key}_benefits`]: e.target.value,
                      }))
                    }
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder={`Beneficios para ${rankLabel.label.toLowerCase()}`}
                  />
                  <div className="grid grid-cols-3 gap-3 text-sm text-gray-500">
                    <div>
                      Gasto minimo:{" "}
                      {rankingConfig
                        ? `R$ ${formatBRL(rankingConfig[`${key}_min_spent`] ?? 0)}`
                        : "..."}
                    </div>
                    <div>
                      Compras minimas:{" "}
                      {rankingConfig?.[`${key}_min_purchases`] ?? "..."}
                    </div>
                    <div>
                      Meses ativos:{" "}
                      {rankingConfig?.[`${key}_min_months`] ?? "..."}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
