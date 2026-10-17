import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import { formatMoneyBRL } from "../../utils/formatters";
import { exportarPlanilhasExcel } from "./vendasFinanceiro/vendasFinanceiroExcel";
import {
  agruparVendasPorVendedor,
  planilhasVendasPorVendedor,
} from "./vendasPorVendedorRelatorio";

export default function VendasPorVendedorPanel({ vendas, dataInicio, dataFim, formatarData }) {
  const [vendedorSelecionado, setVendedorSelecionado] = useState("");
  const [exportando, setExportando] = useState(false);
  const grupos = useMemo(() => agruparVendasPorVendedor(vendas), [vendas]);
  const opcoes = useMemo(
    () => grupos.map((grupo) => ({ value: grupo.chave, label: grupo.vendedor })),
    [grupos],
  );
  useEffect(() => {
    if (vendedorSelecionado && !opcoes.some((opcao) => opcao.value === vendedorSelecionado)) {
      setVendedorSelecionado("");
    }
  }, [opcoes, vendedorSelecionado]);
  const gruposVisiveis = useMemo(
    () => grupos.filter((grupo) => !vendedorSelecionado || grupo.chave === vendedorSelecionado),
    [grupos, vendedorSelecionado],
  );
  const quantidade = gruposVisiveis.reduce((total, grupo) => total + grupo.quantidade, 0);
  const valorTotal = gruposVisiveis.reduce((total, grupo) => total + grupo.total, 0);

  const exportar = async () => {
    if (!gruposVisiveis.length) {
      toast.error("Não há vendas para exportar nesse período.");
      return;
    }
    setExportando(true);
    try {
      await exportarPlanilhasExcel(
        planilhasVendasPorVendedor(gruposVisiveis, { inicio: dataInicio, fim: dataFim }),
        `vendas_por_vendedor_${dataInicio}_${dataFim}.xlsx`,
      );
      toast.success("Relatório por vendedor exportado.");
    } catch (error) {
      console.error("Erro ao exportar vendas por vendedor:", error);
      toast.error("Não foi possível exportar o relatório.");
    } finally {
      setExportando(false);
    }
  };

  return (
    <section className="space-y-5">
      <div className="rounded-lg bg-white p-4 shadow dark:bg-slate-900">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              Vendas por vendedor
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              De {formatarData(dataInicio)} até {formatarData(dataFim)}, em todos os canais. O
              vendedor é o indicado na venda, independentemente da comissão.
            </p>
          </div>
          <BotaoInteracao onClick={exportar} disabled={exportando || !gruposVisiveis.length}>
            {exportando ? "Exportando..." : "Exportar Excel"}
          </BotaoInteracao>
        </div>
        <div className="mt-4 max-w-sm">
          <InputCombobox
            id="relatorio-vendedor"
            label="Vendedor"
            placeholder="Todos os vendedores"
            value={vendedorSelecionado}
            onChange={setVendedorSelecionado}
            opcoes={opcoes}
          />
        </div>
        <p className="mt-4 text-sm text-slate-700 dark:text-slate-200">
          {quantidade} venda(s) · Total vendido: {formatMoneyBRL(valorTotal)}
        </p>
      </div>

      {gruposVisiveis.length === 0 ? (
        <p className="rounded-lg bg-white p-6 text-slate-600 shadow dark:bg-slate-900 dark:text-slate-300">
          Nenhuma venda encontrada nesse período.
        </p>
      ) : (
        gruposVisiveis.map((grupo) => (
          <div key={grupo.chave} className="overflow-x-auto rounded-lg bg-white shadow dark:bg-slate-900">
            <div className="flex flex-wrap justify-between gap-2 border-b p-4 dark:border-slate-700">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100">{grupo.vendedor}</h3>
              <span className="text-sm text-slate-700 dark:text-slate-200">
                {grupo.quantidade} venda(s) · {formatMoneyBRL(grupo.total)}
              </span>
            </div>
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <tr>
                  <th className="px-4 py-2">Data</th>
                  <th className="px-4 py-2">Venda</th>
                  <th className="px-4 py-2">Cliente</th>
                  <th className="px-4 py-2">Produtos e quantidades</th>
                  <th className="px-4 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-slate-700">
                {grupo.vendas.map((venda) => (
                  <tr key={venda.id} className="text-slate-700 dark:text-slate-200">
                    <td className="whitespace-nowrap px-4 py-3">{formatarData(venda.data_venda)}</td>
                    <td className="px-4 py-3">{venda.numero_venda}</td>
                    <td className="px-4 py-3">{venda.cliente_nome}</td>
                    <td className="px-4 py-3">
                      {(venda.itens || []).length
                        ? venda.itens.map((item, indice) => (
                            <div key={`${venda.id}-${item.venda_item_id || indice}`}>
                              {item.produto_nome} ·{" "}
                              {Number(item.quantidade || 0).toLocaleString("pt-BR", {
                                maximumFractionDigits: 3,
                              })}{" "}
                              un.
                            </div>
                          ))
                        : "Sem itens"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {formatMoneyBRL(venda.total_venda)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </section>
  );
}
