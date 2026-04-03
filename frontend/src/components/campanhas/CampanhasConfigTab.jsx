export default function CampanhasConfigTab({
  schedulerConfigLoading,
  schedulerConfig,
  setSchedulerConfig,
  onSalvarSchedulerConfig = null,
  schedulerConfigSalvando,
}) {
  const handleSalvarSchedulerConfig =
    typeof onSalvarSchedulerConfig === "function"
      ? onSalvarSchedulerConfig
      : () => {};
  const salvarDesabilitado =
    schedulerConfigSalvando || typeof onSalvarSchedulerConfig !== "function";

  return (

        <div className="space-y-6">
          {/* Header */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-1">
              ⚙️ Configurações de Envio
            </h2>
            <p className="text-xs text-gray-500">
              Defina os horários em que o sistema envia as mensagens automáticas
              de cada campanha.
            </p>
          </div>

          {/* Loading */}
          {schedulerConfigLoading && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando configurações...</p>
            </div>
          )}

          {/* Formulário */}
          {schedulerConfig && !schedulerConfigLoading && (
            <div className="space-y-4">
              {/* Card: Aniversários */}
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-2xl">🎂</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de Aniversário
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviadas todos os dias para aniversariantes do dia
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-600 w-44">
                    Hora de envio:
                  </label>
                  <select
                    value={schedulerConfig.birthday_send_hour}
                    onChange={(e) =>
                      setSchedulerConfig({
                        ...schedulerConfig,
                        birthday_send_hour: Number(e.target.value),
                      })
                    }
                    className="border rounded-lg px-3 py-2 text-sm"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {String(i).padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Card: Inatividade */}
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-2xl">😴</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de Reativação (Clientes Inativos)
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviadas uma vez por semana para clientes sem compras há
                      muito tempo
                    </p>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-gray-600 w-44">
                      Dia da semana:
                    </label>
                    <select
                      value={schedulerConfig.inactivity_day_of_week}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          inactivity_day_of_week: e.target.value,
                        })
                      }
                      className="border rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="mon">Segunda-feira</option>
                      <option value="tue">Terça-feira</option>
                      <option value="wed">Quarta-feira</option>
                      <option value="thu">Quinta-feira</option>
                      <option value="fri">Sexta-feira</option>
                      <option value="sat">Sábado</option>
                      <option value="sun">Domingo</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-gray-600 w-44">
                      Hora de envio:
                    </label>
                    <select
                      value={schedulerConfig.inactivity_send_hour}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          inactivity_send_hour: Number(e.target.value),
                        })
                      }
                      className="border rounded-lg px-3 py-2 text-sm"
                    >
                      {Array.from({ length: 24 }, (_, i) => (
                        <option key={i} value={i}>
                          {String(i).padStart(2, "0")}:00
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Auto-envio do Destaque Mensal */}
              <div className="border rounded-xl p-5">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">🏅</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Auto-envio do Destaque Mensal
                    </h3>
                    <p className="text-xs text-gray-500">
                      Calcula e envia automaticamente o cupom ao vencedor do mês
                      no dia 1 às 08:00
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={schedulerConfig.auto_destaque_mensal ?? false}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          auto_destaque_mensal: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-sm text-gray-700">
                      Ativar envio automático do Destaque Mensal
                    </span>
                  </label>
                  {schedulerConfig.auto_destaque_mensal && (
                    <div className="flex flex-col sm:flex-row gap-4 pl-6">
                      <div className="flex items-center gap-3">
                        <label className="text-sm text-gray-600 w-44">
                          Valor do cupom (R$):
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={
                            schedulerConfig.auto_destaque_coupon_value ?? 50
                          }
                          onChange={(e) =>
                            setSchedulerConfig({
                              ...schedulerConfig,
                              auto_destaque_coupon_value:
                                parseFloat(e.target.value) || 0,
                            })
                          }
                          className="border rounded-lg px-3 py-2 text-sm w-28"
                        />
                      </div>
                      <div className="flex items-center gap-3">
                        <label className="text-sm text-gray-600 w-44">
                          Validade (dias):
                        </label>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={
                            schedulerConfig.auto_destaque_coupon_days ?? 10
                          }
                          onChange={(e) =>
                            setSchedulerConfig({
                              ...schedulerConfig,
                              auto_destaque_coupon_days:
                                parseInt(e.target.value, 10) || 10,
                            })
                          }
                          className="border rounded-lg px-3 py-2 text-sm w-28"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Botão salvar */}
              <div className="flex justify-end">
                <button
                  onClick={handleSalvarSchedulerConfig}
                  disabled={salvarDesabilitado}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {schedulerConfigSalvando
                    ? "Salvando..."
                    : "💾 Salvar Configurações"}
                </button>
              </div>

              {/* Nota informativa */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-xs text-amber-700">
                  ⚠️ <strong>Atenção:</strong> Os horários aqui salvos são
                  registrados no sistema. O scheduler usará os novos valores a
                  partir do próximo reinício do servidor. Para aplicar
                  imediatamente em produção, avise o suporte técnico.
                </p>
              </div>
            </div>
          )}

          {/* Estado vazio */}
          {!schedulerConfig && !schedulerConfigLoading && (
            <div className="bg-white rounded-xl border shadow-sm p-6 text-center">
              <p className="text-sm text-gray-500 mb-2">
                Não foi possível carregar as configurações.
              </p>
              <p className="text-xs text-gray-400">
                Certifique-se de que as campanhas padrão foram inicializadas
                (botão &quot;Inicializar Campanhas&quot; na aba Campanhas).
              </p>
            </div>
          )}
        </div>
  );
}
