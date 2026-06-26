import { formatarMoeda } from "../../api/produtos";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import SaleReference from "../../components/ui/SaleReference";
import { formatarData, formatarQuantidade } from "./produtosRelatorioFormatters";

export default function ProdutosRelatorioHistoricoVendas({
  dadosProduto,
  totalPaginasHistorico,
  onPaginaChange,
}) {
  const historico = dadosProduto?.historico_vendas || [];
  const paginaAtual = dadosProduto?.historico_page || 1;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Historico recente de vendas do produto
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Veja quando vendeu, para quem e em qual quantidade dentro do periodo selecionado.
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          {dadosProduto?.historico_total || 0} registro(s)
        </span>
      </div>

      {historico.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-gray-500">
          Nenhuma venda do produto encontrada neste recorte.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Data
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Venda
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Cliente
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Qtd
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Preco unit
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Total
                  </th>
                  <th className="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {historico.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 text-sm text-gray-700">
                      {formatarData(item.data_venda)}
                    </td>
                    <td className="px-5 py-3 text-sm font-medium text-gray-900">
                      <div className="flex flex-wrap items-center gap-2">
                        <SaleReference
                          value={item.numero_venda || item.venda_id}
                          showPrefix={false}
                          empty={<span>-</span>}
                        />
                        {item.em_promocao && (
                          <span
                            className="rounded-full bg-cyan-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan-700"
                            title={item.promocao_origem || "Venda por preco promocional ativo"}
                          >
                            Promo
                          </span>
                        )}
                      </div>
                      {item.em_promocao && (
                        <p className="mt-1 text-xs font-medium text-cyan-700">
                          {item.promocao_origem || "Preco promocional ativo"}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-3 text-sm text-gray-700">
                      <CustomerIdentity
                        fallback="Sem cliente"
                        nameClassName="font-medium text-gray-700"
                        record={item}
                      />
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">
                      {formatarQuantidade(item.quantidade)}
                    </td>
                    <td className="px-5 py-3 text-right text-sm text-gray-700">
                      {formatarMoeda(item.preco_unitario)}
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">
                      {formatarMoeda(item.subtotal)}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                        {item.status || "-"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-gray-600">
              Pagina {paginaAtual} de {totalPaginasHistorico || 1}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => onPaginaChange((prev) => Math.max(prev - 1, 1))}
                disabled={paginaAtual <= 1}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                type="button"
                onClick={() =>
                  onPaginaChange((prev) =>
                    totalPaginasHistorico > 0 ? Math.min(prev + 1, totalPaginasHistorico) : prev,
                  )
                }
                disabled={totalPaginasHistorico === 0 || paginaAtual >= totalPaginasHistorico}
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
