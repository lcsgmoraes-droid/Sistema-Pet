import CampanhasConfigBirthdaySection from "./CampanhasConfigBirthdaySection";
import CampanhasConfigDestaqueSection from "./CampanhasConfigDestaqueSection";
import CampanhasConfigInactivitySection from "./CampanhasConfigInactivitySection";
import CampanhasConfigSchedulerHeader from "./CampanhasConfigSchedulerHeader";

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
      <CampanhasConfigSchedulerHeader />

      {schedulerConfigLoading && (
        <div className="text-center py-12 text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
          <p className="text-sm">Carregando configuracoes...</p>
        </div>
      )}

      {schedulerConfig && !schedulerConfigLoading && (
        <div className="space-y-4">
          <CampanhasConfigBirthdaySection
            schedulerConfig={schedulerConfig}
            setSchedulerConfig={setSchedulerConfig}
          />
          <CampanhasConfigInactivitySection
            schedulerConfig={schedulerConfig}
            setSchedulerConfig={setSchedulerConfig}
          />
          <CampanhasConfigDestaqueSection
            schedulerConfig={schedulerConfig}
            setSchedulerConfig={setSchedulerConfig}
          />

          <div className="flex justify-end">
            <button
              onClick={handleSalvarSchedulerConfig}
              disabled={salvarDesabilitado}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {schedulerConfigSalvando
                ? "Salvando..."
                : "\u{1F4BE} Salvar Configuracoes"}
            </button>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-xs text-amber-700">
              {"\u26A0\uFE0F"} <strong>Atencao:</strong> Os horarios aqui salvos
              sao registrados no sistema. O scheduler usara os novos valores a
              partir do proximo reinicio do servidor. Para aplicar imediatamente
              em producao, avise o suporte tecnico.
            </p>
          </div>
        </div>
      )}

      {!schedulerConfig && !schedulerConfigLoading && (
        <div className="bg-white rounded-xl border shadow-sm p-6 text-center">
          <p className="text-sm text-gray-500 mb-2">
            Nao foi possivel carregar as configuracoes.
          </p>
          <p className="text-xs text-gray-400">
            Certifique-se de que as campanhas padrao foram inicializadas
            (botao &quot;Inicializar Campanhas&quot; na aba Campanhas).
          </p>
        </div>
      )}
    </div>
  );
}
