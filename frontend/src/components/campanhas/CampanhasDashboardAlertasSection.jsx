export default function CampanhasDashboardAlertasSection({
  dashboard,
  onAbrirEnvioInativos,
  onAbrirAba,
}) {
  if (!dashboard.alertas) return null;

  return (
    <div className="space-y-3">
      <h2 className="font-semibold text-gray-800">
        {"\u26A0\uFE0F"} Alertas do Dia
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            dias: 30,
            count: dashboard.alertas.inativos_30d,
            label: "\u{1F634} Clientes sem compra ha +30 dias",
            colors: "bg-orange-50 border-orange-200",
            textColor: "text-orange-700",
          },
          {
            dias: 60,
            count: dashboard.alertas.inativos_60d,
            label: "\u{1F6A8} Clientes sem compra ha +60 dias",
            colors: "bg-red-50 border-red-200",
            textColor: "text-red-700",
          },
        ].map(({ dias, count, label, colors, textColor }) => (
          <div
            key={dias}
            className={`rounded-xl border p-4 ${
              count > 0 ? colors : "bg-gray-50 border-gray-200"
            }`}
          >
            <p
              className={`text-3xl font-bold ${
                count > 0 ? textColor : "text-gray-400"
              }`}
            >
              {count}
            </p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
            {count > 0 && (
              <button
                onClick={() => onAbrirEnvioInativos(dias)}
                className="mt-2 text-xs font-medium text-white bg-orange-500 hover:bg-orange-600 px-3 py-1 rounded-lg transition-colors"
              >
                {"\u2709\uFE0F"} Enviar e-mail de reativacao
              </button>
            )}
          </div>
        ))}
        <div
          className={`rounded-xl border p-4 ${
            dashboard.alertas.total_sorteios_pendentes > 0
              ? "bg-yellow-50 border-yellow-200"
              : "bg-gray-50 border-gray-200"
          }`}
        >
          <p
            className={`text-3xl font-bold ${
              dashboard.alertas.total_sorteios_pendentes > 0
                ? "text-yellow-700"
                : "text-gray-400"
            }`}
          >
            {dashboard.alertas.total_sorteios_pendentes}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {"\u{1F3B2}"} Sorteio(s) nao executado(s)
          </p>
        </div>
      </div>

      {dashboard.alertas.sorteios_pendentes?.length > 0 && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-yellow-50">
            <p className="text-sm font-medium text-yellow-800">
              {"\u{1F3B2}"} Sorteios Pendentes
            </p>
          </div>
          <div className="divide-y">
            {dashboard.alertas.sorteios_pendentes.map((s) => (
              <div
                key={s.id}
                className="px-4 py-3 flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{s.name}</p>
                  <p className="text-xs text-gray-500">
                    Status: {s.status}
                    {s.draw_date
                      ? ` - Data: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`
                      : ""}
                  </p>
                </div>
                <button
                  onClick={() => onAbrirAba("sorteios")}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Ver sorteio {"\u2192"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {dashboard.alertas?.total_brindes_pendentes > 0 && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-amber-50 flex items-center justify-between">
            <p className="text-sm font-medium text-amber-800">
              {"\u{1F381}"} Brindes Pendentes de Retirada (
              {dashboard.alertas.total_brindes_pendentes})
            </p>
            <button
              onClick={() => onAbrirAba("cupons")}
              className="text-xs text-blue-600 hover:underline"
            >
              Ver cupons {"\u2192"}
            </button>
          </div>
          <div className="divide-y">
            {dashboard.alertas.brindes_pendentes.slice(0, 5).map((b, i) => (
              <div
                key={i}
                className="px-4 py-3 flex items-start justify-between gap-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {b.nome_cliente}
                  </p>
                  <p className="text-xs text-gray-500">
                    {b.categoria === "maior_gasto"
                      ? "\u{1F4B0} Maior Gasto"
                      : b.categoria === "mais_compras"
                        ? "\u{1F6D2} Mais Compras"
                        : b.categoria}
                    {b.periodo ? ` - ${b.periodo}` : ""}
                  </p>
                  {b.mensagem && (
                    <p className="text-xs text-amber-700 mt-0.5 truncate">
                      {b.mensagem}
                    </p>
                  )}
                </div>
                {b.retirar_ate && (
                  <span className="text-xs text-gray-400 shrink-0">
                    ate {new Date(b.retirar_ate).toLocaleDateString("pt-BR")}
                  </span>
                )}
              </div>
            ))}
            {dashboard.alertas.total_brindes_pendentes > 5 && (
              <div className="px-4 py-2 text-xs text-gray-400 text-center">
                +{dashboard.alertas.total_brindes_pendentes - 5} mais
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
