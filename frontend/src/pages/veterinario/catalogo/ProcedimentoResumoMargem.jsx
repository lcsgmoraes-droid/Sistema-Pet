import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";

export default function ProcedimentoResumoMargem({ resumoMargem }) {
  const { custoEstimadoForm, margemEstimadaForm, margemPercentualForm, precoSugeridoForm } = resumoMargem;

  return (
    <div className="grid gap-3 border-t border-gray-200 pt-3 md:grid-cols-3">
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Preco</p>
        <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(precoSugeridoForm)}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo estimado</p>
        <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(custoEstimadoForm)}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem estimada</p>
        <p className={`text-sm font-semibold ${margemEstimadaForm < 0 ? "text-red-600" : "text-emerald-700"}`}>
          {formatMoneyBRL(margemEstimadaForm)}
        </p>
        <p className="text-[11px] text-gray-400">{formatPercent(margemPercentualForm)}</p>
      </div>
    </div>
  );
}
