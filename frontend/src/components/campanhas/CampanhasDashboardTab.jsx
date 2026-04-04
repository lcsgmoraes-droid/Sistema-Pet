import { formatBRL } from "../../utils/formatters";

function DashboardMetricCard({
  value,
  label,
  className = "text-blue-700",
  extra,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
      <p className={`text-3xl font-bold ${className}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
      {extra}
    </div>
  );
}

export default function CampanhasDashboardTab({
  loadingDashboard,
  dashboard,
  onAbrirEnvioInativos,
  onAbrirAba,
}) {
  if (loadingDashboard) {
    return (
      <div className="p-8 text-center text-gray-400">
        Carregando dashboard...
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="p-8 text-center text-gray-400">
        Erro ao carregar dashboard.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <DashboardMetricCard
          value={dashboard.campanhas_ativas?.total ?? dashboard.campanhas_ativas}
          label="\u{1F4E2} Campanhas ativas"
          extra={
            dashboard.campanhas_ativas?.nomes?.length > 0 ? (
              <div className="mt-2 text-left space-y-0.5">
                {dashboard.campanhas_ativas.nomes.map((nome, i) => (
                  <p key={i} className="text-xs text-gray-600 truncate">
                    • {nome}
                  </p>
                ))}
              </div>
            ) : null
          }
        />
        <DashboardMetricCard
          value={dashboard.cupons_emitidos_hoje}
          label="\u{1F39F}\uFE0F Cupons emitidos hoje"
          className="text-green-700"
        />
        <DashboardMetricCard
          value={dashboard.cupons_usados_hoje}
          label="\u2705 Cupons usados hoje"
          className="text-orange-700"
        />
        <DashboardMetricCard
          value={`R$ ${formatBRL(dashboard.saldo_passivo_cashback || 0)}`}
          label="\u{1F4B0} Saldo passivo (cashback)"
          className="text-2xl text-purple-700"
        />
        <div
          className={`rounded-xl border shadow-sm p-4 text-center ${
            dashboard.proximos_eventos?.dias_ate_fim_mes <= 3
              ? "bg-yellow-50 border-yellow-300"
              : "bg-white"
          }`}
        >
          <p
            className={`text-3xl font-bold ${
              dashboard.proximos_eventos?.dias_ate_fim_mes <= 3
                ? "text-yellow-700"
                : "text-indigo-700"
            }`}
          >
            {dashboard.proximos_eventos?.dias_ate_fim_mes ?? "-"}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {"\u{1F31F}"}{" "}
            {dashboard.proximos_eventos?.dias_ate_fim_mes === 0
              ? "Ultimo dia - calcule o destaque!"
              : "dia(s) p/ Destaque Mensal"}
          </p>
        </div>
        {(dashboard.cupons_expirados_hoje ?? 0) > 0 && (
          <div className="bg-red-50 rounded-xl border border-red-200 shadow-sm p-4 text-center">
            <p className="text-3xl font-bold text-red-700">
              {dashboard.cupons_expirados_hoje}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {"\u23F0"} Cupons expiram hoje
            </p>
          </div>
        )}
        <DashboardMetricCard
          value={dashboard.cupons_ativos_total ?? 0}
          label="\u{1F4E6} Cupons ativos no total"
          className="text-teal-700"
        />
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-pink-50 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">
            {"\u{1F382}"} Aniversarios de Hoje
          </h2>
          <span className="text-sm text-pink-600 font-medium">
            {dashboard.total_aniversarios} aniversario(s)
          </span>
        </div>
        {dashboard.aniversarios_hoje.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">
            Nenhum aniversario hoje.
          </div>
        ) : (
          <div className="divide-y">
            {dashboard.aniversarios_hoje.map((a, i) => (
              <div key={i} className="px-6 py-3 flex items-center gap-3">
                <span className="text-xl">
                  {a.tipo === "pet" ? "\u{1F415}" : "\u{1F464}"}
                </span>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{a.nome}</p>
                  <p className="text-xs text-gray-500">
                    {a.tipo === "pet" ? "Pet" : "Cliente"}
                    {a.idade ? ` • ${a.idade} ano(s)` : ""}
                  </p>
                </div>
                <span className="text-xs bg-pink-100 text-pink-700 px-2 py-0.5 rounded-full">
                  {"\u{1F382}"} Hoje!
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {dashboard.alertas && (
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
                      <p className="text-sm font-medium text-gray-900">
                        {s.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        Status: {s.status}
                        {s.draw_date
                          ? ` • Data: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`
                          : ""}
                      </p>
                    </div>
                    <button
                      onClick={() => onAbrirAba("sorteios")}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Ver sorteio →
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
                  Ver cupons →
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
                        {b.periodo ? ` • ${b.periodo}` : ""}
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
      )}

      {dashboard.proximos_eventos && (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-800">
            {"\u{1F4C5}"} Proximos Eventos
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b bg-pink-50 flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-800">
                  {"\u{1F382}"} Aniversarios Amanha
                </p>
                <span className="text-xs text-pink-600 font-medium">
                  {dashboard.proximos_eventos.total_aniversarios_amanha} pessoa(s)
                </span>
              </div>
              {dashboard.proximos_eventos.aniversarios_amanha.length === 0 ? (
                <div className="px-4 py-4 text-xs text-gray-400 text-center">
                  Nenhum aniversario amanha.
                </div>
              ) : (
                <div className="divide-y">
                  {dashboard.proximos_eventos.aniversarios_amanha.map((a, i) => (
                    <div key={i} className="px-4 py-2.5 flex items-center gap-2">
                      <span>{a.tipo === "pet" ? "\u{1F415}" : "\u{1F464}"}</span>
                      <span className="text-sm text-gray-800">{a.nome}</span>
                      <span className="ml-auto text-xs text-gray-400">
                        {a.tipo === "pet" ? "Pet" : "Cliente"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-3">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-4">
                <span className="text-3xl">{"\u{1F31F}"}</span>
                <div>
                  <p className="font-semibold text-amber-900">
                    Destaque Mensal
                  </p>
                  <p className="text-sm text-amber-700">
                    {dashboard.proximos_eventos.dias_ate_fim_mes === 0
                      ? "Hoje e o ultimo dia do mes!"
                      : `Faltam ${dashboard.proximos_eventos.dias_ate_fim_mes} dia(s) para o fim do mes`}
                  </p>
                </div>
              </div>

              {dashboard.proximos_eventos.sorteios_esta_semana?.length > 0 && (
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <div className="px-4 py-3 border-b bg-yellow-50">
                    <p className="text-sm font-medium text-gray-800">
                      {"\u{1F3B2}"} Sorteios Esta Semana
                    </p>
                  </div>
                  <div className="divide-y">
                    {dashboard.proximos_eventos.sorteios_esta_semana.map((s) => (
                      <div
                        key={s.id}
                        className="px-4 py-2.5 flex items-center justify-between"
                      >
                        <span className="text-sm text-gray-800">{s.name}</span>
                        <span className="text-xs text-gray-500">
                          {s.draw_date
                            ? new Date(s.draw_date).toLocaleDateString("pt-BR")
                            : "-"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
