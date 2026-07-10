import { Cake, Gift, PawPrint, UserRound } from "lucide-react";

export default function CampanhasDashboardAniversariosCard({ dashboard }) {
  const aniversarios = dashboard.aniversarios_hoje || [];

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-2 border-b border-slate-200 bg-rose-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Cake className="text-rose-700" size={20} aria-hidden="true" />
          <h2 className="font-semibold text-gray-900">Aniversarios de hoje</h2>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-semibold text-rose-700">
          <Gift size={14} aria-hidden="true" />
          {dashboard.total_aniversarios} aniversario(s)
        </span>
      </div>

      {aniversarios.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-gray-400">Nenhum aniversario hoje.</div>
      ) : (
        <div className="divide-y divide-slate-200">
          {aniversarios.map((aniversario, index) => {
            const Icon = aniversario.tipo === "pet" ? PawPrint : UserRound;

            return (
              <div
                key={`${aniversario.nome}-${index}`}
                className="flex items-center gap-3 px-5 py-3"
              >
                <span className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-rose-700">
                  <Icon size={18} aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-gray-900">{aniversario.nome}</p>
                  <p className="text-xs text-gray-500">
                    {aniversario.tipo === "pet" ? "Pet" : "Cliente"}
                    {aniversario.idade ? ` - ${aniversario.idade} ano(s)` : ""}
                  </p>
                </div>
                <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700">
                  Hoje
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
