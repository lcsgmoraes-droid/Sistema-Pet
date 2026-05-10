import { Calendar } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import { actionButtonClasses } from "../ui/actionStyles";

export default function DiasUteisResumoPanel({
  adicionarFeriadoCustomizado,
  configDiasUteis,
  feriadosCustomizados,
  formatarData,
  formatarMoeda,
  mostrarConfigFeriados,
  novoFeriadoData,
  novoFeriadoNome,
  removerFeriadoCustomizado,
  resumoDiasPeriodo,
  setConfigDiasUteis,
  setMostrarConfigFeriados,
  setNovoFeriadoData,
  setNovoFeriadoNome,
}) {
  return (
    <div className="mb-6 rounded-lg border border-blue-100 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">
            Dias uteis e media operacional
          </h3>
          <p className="text-sm text-gray-500">
            Configure se sabado entra na media. Feriado com faturamento vira dia util automaticamente.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
            <input
              type="checkbox"
              checked={configDiasUteis.considerarSabadoDiaUtil}
              onChange={(event) =>
                setConfigDiasUteis((prev) => ({
                  ...prev,
                  considerarSabadoDiaUtil: event.target.checked,
                }))
              }
              className="h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
            />
            Sabado conta como dia util
          </label>
          <ActionButton
            icon={Calendar}
            intent="edit"
            onClick={() => setMostrarConfigFeriados((prev) => !prev)}
            size="sm"
            tone="soft"
          >
            Configurar feriados
          </ActionButton>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-xl bg-slate-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Dias uteis
          </div>
          <div className="mt-1 text-2xl font-bold text-slate-900">
            {resumoDiasPeriodo.diasUteis}
          </div>
          <div className="text-xs text-slate-500">
            {resumoDiasPeriodo.totalDias} dia(s) no periodo
          </div>
        </div>
        <div className="rounded-xl bg-emerald-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
            Dias trabalhados
          </div>
          <div className="mt-1 text-2xl font-bold text-emerald-700">
            {resumoDiasPeriodo.diasTrabalhados}
          </div>
          <div className="text-xs text-emerald-600">
            Dia util com venda registrada
          </div>
        </div>
        <div className="rounded-xl bg-amber-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Dias uteis sem venda
          </div>
          <div className="mt-1 text-2xl font-bold text-amber-700">
            {resumoDiasPeriodo.diasUteisSemVenda}
          </div>
          <div className="text-xs text-amber-700">
            Fora fins de semana/feriados
          </div>
        </div>
        <div className="rounded-xl bg-blue-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Media por dia util
          </div>
          <div className="mt-1 text-2xl font-bold text-blue-700">
            {formatarMoeda(resumoDiasPeriodo.mediaDiaUtil)}
          </div>
          <div className="text-xs text-blue-700">
            {resumoDiasPeriodo.feriados} feriado(s),{" "}
            {resumoDiasPeriodo.finsDeSemana} fim(ns) de semana
          </div>
        </div>
      </div>

      {mostrarConfigFeriados && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
            <input
              type="date"
              value={novoFeriadoData}
              onChange={(event) => setNovoFeriadoData(event.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <input
              type="text"
              value={novoFeriadoNome}
              onChange={(event) => setNovoFeriadoNome(event.target.value)}
              placeholder="Nome do feriado local, municipal ou data sem expediente"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <button
              type="button"
              onClick={adicionarFeriadoCustomizado}
              className={actionButtonClasses({
                intent: "create",
                tone: "solid",
                size: "sm",
              })}
            >
              Salvar feriado
            </button>
          </div>

          {feriadosCustomizados.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {feriadosCustomizados.map((feriado) => (
                <span
                  key={feriado.data}
                  className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm"
                >
                  {formatarData(feriado.data)} - {feriado.nome}
                  <button
                    type="button"
                    onClick={() => removerFeriadoCustomizado(feriado.data)}
                    className="text-rose-600 hover:text-rose-700"
                  >
                    remover
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
