import { Cake, CalendarDays, Dice5, Sparkles } from "lucide-react";

export default function CampanhasDashboardProximosEventosSection({ dashboard }) {
  if (!dashboard.proximos_eventos) return null;

  const proximos = dashboard.proximos_eventos;

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Proximos eventos</h2>
        <p className="text-sm text-gray-500">Datas importantes para acao de campanhas.</p>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-rose-50 px-5 py-3">
            <div className="flex items-center gap-2">
              <Cake className="text-rose-700" size={18} aria-hidden="true" />
              <p className="text-sm font-semibold text-gray-900">Aniversarios amanha</p>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-rose-700">
              {proximos.total_aniversarios_amanha} pessoa(s)
            </span>
          </div>
          {proximos.aniversarios_amanha.length === 0 ? (
            <div className="px-5 py-5 text-center text-sm text-gray-400">
              Nenhum aniversario amanha.
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {proximos.aniversarios_amanha.map((aniversario, index) => (
                <div
                  key={`${aniversario.nome}-${index}`}
                  className="flex items-center gap-3 px-5 py-3"
                >
                  <span className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-rose-700">
                    <CalendarDays size={16} aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
                    {aniversario.nome}
                  </span>
                  <span className="text-xs text-gray-400">
                    {aniversario.tipo === "pet" ? "Pet" : "Cliente"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
            <div className="flex items-start gap-3">
              <span className="rounded-lg border border-amber-200 bg-white p-2 text-amber-700">
                <Sparkles size={20} aria-hidden="true" />
              </span>
              <div>
                <p className="font-semibold text-amber-900">Destaque mensal</p>
                <p className="mt-1 text-sm text-amber-800">
                  {proximos.dias_ate_fim_mes === 0
                    ? "Hoje e o ultimo dia do mes."
                    : `Faltam ${proximos.dias_ate_fim_mes} dia(s) para o fim do mes.`}
                </p>
              </div>
            </div>
          </div>

          {proximos.sorteios_esta_semana?.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center gap-2 border-b border-slate-200 bg-amber-50 px-5 py-3">
                <Dice5 className="text-amber-800" size={18} aria-hidden="true" />
                <p className="text-sm font-semibold text-gray-900">Sorteios esta semana</p>
              </div>
              <div className="divide-y divide-slate-200">
                {proximos.sorteios_esta_semana.map((sorteio) => (
                  <div
                    key={sorteio.id}
                    className="flex items-center justify-between gap-3 px-5 py-3"
                  >
                    <span className="min-w-0 truncate text-sm font-medium text-gray-900">
                      {sorteio.name}
                    </span>
                    <span className="shrink-0 text-xs text-gray-500">
                      {sorteio.draw_date
                        ? new Date(sorteio.draw_date).toLocaleDateString("pt-BR")
                        : "-"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
