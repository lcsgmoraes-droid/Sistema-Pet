export default function CampanhasConfigDestaqueSection({
  schedulerConfig,
  setSchedulerConfig,
}) {
  return (
    <div className="border rounded-xl p-5 bg-white shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{"\u{1F3C5}"}</span>
        <div>
          <h3 className="font-medium text-gray-800">
            Auto-envio do Destaque Mensal
          </h3>
          <p className="text-xs text-gray-500">
            Calcula e envia automaticamente o cupom ao vencedor do mes no dia 1
            as 08:00
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
            Ativar envio automatico do Destaque Mensal
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
                value={schedulerConfig.auto_destaque_coupon_value ?? 50}
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
                value={schedulerConfig.auto_destaque_coupon_days ?? 10}
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
  );
}
