export default function CampanhasDashboardProximosEventosSection({ dashboard }) {
  if (!dashboard.proximos_eventos) return null;

  return (
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
              <p className="font-semibold text-amber-900">Destaque Mensal</p>
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
  );
}
