import { formatarMoeda } from "../../api/produtos";
import ProductIdentity from "../../components/ui/ProductIdentity";
import { formatarDataHora, formatarQuantidade } from "./produtosRelatorioFormatters";

function obterBadgeTipo(tipo) {
  const tipoLower = String(tipo || "").toLowerCase();

  if (tipoLower === "entrada") return "bg-emerald-100 text-emerald-700";
  if (tipoLower === "transferencia") return "bg-blue-100 text-blue-700";
  return "bg-rose-100 text-rose-700";
}

export default function ProdutosRelatorioMovimentacoesTable({
  dadosMovimentacoes,
  loadingMovimentacoes,
  inicioItemMovimentacoes,
  fimItemMovimentacoes,
  paginaAtualMovimentacoes,
  totalPaginasMovimentacoes,
  exportando,
  onExportarCsv,
  onPaginaChange,
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Movimentacoes filtradas</h3>
          <p className="mt-1 text-sm text-gray-600">
            Historico operacional paginado para manter a tela leve mesmo com muitos registros.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
            Exibindo {inicioItemMovimentacoes}-{fimItemMovimentacoes} de{" "}
            {dadosMovimentacoes.total_registros}
          </span>
          <button
            type="button"
            onClick={onExportarCsv}
            disabled={exportando || dadosMovimentacoes.total_registros === 0}
            className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {exportando ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </div>

      {loadingMovimentacoes ? (
        <div className="px-5 py-8 text-center text-sm text-gray-500">
          Carregando movimentacoes...
        </div>
      ) : dadosMovimentacoes.movimentacoes.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-gray-500">
          Nenhuma movimentacao encontrada com o filtro atual.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Lancamento
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Produto
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Tipo / motivo
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Entrada
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Saida
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Estoque apos
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Valor
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Usuario
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {dadosMovimentacoes.movimentacoes.map((mov) => (
                  <tr key={mov.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 text-sm text-gray-700">
                      <p className="font-medium text-gray-900">
                        {formatarDataHora(mov.data_completa)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {mov.numero_pedido || "Sem documento"}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-sm text-gray-700">
                      <div className="flex flex-wrap items-center gap-2">
                        <ProductIdentity
                          product={mov}
                          nameClassName="font-semibold text-gray-900"
                          codeClassName="text-xs text-gray-500"
                        />
                        {mov.em_promocao && (
                          <span
                            className="rounded-full bg-cyan-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan-700"
                            title={mov.promocao_origem || "Venda por preco promocional ativo"}
                          >
                            Promo
                          </span>
                        )}
                      </div>
                      {mov.em_promocao && (
                        <p className="mt-1 text-xs font-medium text-cyan-700">
                          {mov.promocao_origem || "Preco promocional ativo"}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-3 text-sm text-gray-700">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${obterBadgeTipo(mov.tipo)}`}
                      >
                        {mov.tipo || "-"}
                      </span>
                      <p className="mt-2 text-xs text-gray-500">
                        {mov.motivo_label || "Sem motivo informado"}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-emerald-700">
                      {mov.entrada != null ? formatarQuantidade(mov.entrada) : "-"}
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-rose-700">
                      {mov.saida != null ? formatarQuantidade(mov.saida) : "-"}
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-medium text-gray-900">
                      {formatarQuantidade(mov.estoque)}
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-medium text-gray-900">
                      {formatarMoeda(mov.valor_total)}
                    </td>
                    <td className="px-5 py-3 text-sm text-gray-700">{mov.usuario || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-gray-600">
              Pagina {paginaAtualMovimentacoes} de {totalPaginasMovimentacoes || 1}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => onPaginaChange((prev) => Math.max(prev - 1, 1))}
                disabled={paginaAtualMovimentacoes <= 1}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                type="button"
                onClick={() =>
                  onPaginaChange((prev) =>
                    totalPaginasMovimentacoes > 0
                      ? Math.min(prev + 1, totalPaginasMovimentacoes)
                      : prev,
                  )
                }
                disabled={
                  totalPaginasMovimentacoes === 0 ||
                  paginaAtualMovimentacoes >= totalPaginasMovimentacoes
                }
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
