import { formatarMoeda } from "../../api/produtos";
import { formatarData } from "./transferenciaParceiroUtils";

export default function BaixaLoteTransferenciaLista({
  items,
  aplicacoes,
  onToggleAplicacao,
  onAtualizarValorAplicacao,
}) {
  if (!items?.length) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600">
        Nenhuma transferencia em aberto encontrada para essa pessoa nos filtros atuais.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-4 py-3">Baixar</th>
            <th className="px-4 py-3">Transferencia</th>
            <th className="px-4 py-3 text-right">Saldo</th>
            <th className="px-4 py-3 text-right">Valor aplicado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => {
            const contaId = item.conta_receber_id;
            const valorAplicado = aplicacoes?.[contaId] || "";
            const marcado = valorAplicado !== "";

            return (
              <tr key={contaId}>
                <td className="px-4 py-3 align-top">
                  <input
                    type="checkbox"
                    checked={marcado}
                    onChange={(event) => onToggleAplicacao(item, event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                </td>
                <td className="px-4 py-3 align-top">
                  <p className="text-sm font-semibold text-slate-900">
                    {item.documento || `Transferencia #${contaId}`}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Emissao: {formatarData(item.data_emissao)} | Vencimento:{" "}
                    {formatarData(item.data_vencimento)}
                  </p>
                </td>
                <td className="px-4 py-3 text-right align-top text-sm font-semibold text-amber-700">
                  {formatarMoeda(item.saldo_aberto)}
                </td>
                <td className="px-4 py-3 align-top">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={valorAplicado}
                    onChange={(event) => onAtualizarValorAplicacao(contaId, event.target.value)}
                    className="ml-auto block w-32 rounded-lg border border-slate-300 px-3 py-2 text-right text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
