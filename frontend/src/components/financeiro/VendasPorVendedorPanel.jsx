import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import BuscaProdutoMultiplo from "../v2/BuscaProdutoMultiplo/BuscaProdutoMultiplo";
import useVendasGruposProdutos from "./useVendasGruposProdutos";
import VendasGruposProdutosPanel from "./VendasGruposProdutosPanel";
import { formatMoneyBRL } from "../../utils/formatters";
import { exportarPlanilhasExcel } from "./vendasFinanceiro/vendasFinanceiroExcel";
import {
  agruparVendasPorVendedor,
  opcoesProdutosVendas,
  planilhasVendasPorVendedor,
} from "./vendasPorVendedorRelatorio";

const formatarQuantidade = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });

export default function VendasPorVendedorPanel({ vendas, dataInicio, dataFim, formatarData }) {
  const [vendedorSelecionado, setVendedorSelecionado] = useState("");
  const [produtosSelecionados, setProdutosSelecionados] = useState([]);
  const [exportando, setExportando] = useState("");
  const controleGrupos = useVendasGruposProdutos({
    dataInicio,
    dataFim,
    vendedorSelecionado,
    produtosSelecionados,
    setProdutosSelecionados,
  });
  const produtos = useMemo(() => {
    const porId = new Map(opcoesProdutosVendas(vendas).map((opcao) => [opcao.value, opcao]));
    for (const salvo of controleGrupos.gruposSalvos) {
      for (const item of salvo.produtos || []) {
        const value = String(item.id);
        // Relatórios históricos podem omitir o código; o grupo traz o cadastro atual.
        const produto = { ...porId.get(value)?.produto, ...item };
        porId.set(value, {
          value,
          label: `${produto.nome}${produto.codigo ? ` (${produto.codigo})` : ""}`,
          produto,
        });
      }
    }
    return [...porId.values()].sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
  }, [vendas, controleGrupos.gruposSalvos]);
  const produto = produtosSelecionados.length
    ? {
        label:
          (!controleGrupos.grupoAlterado && controleGrupos.grupo?.nome) ||
          produtos
            .filter((opcao) => produtosSelecionados.includes(opcao.value))
            .map((opcao) => opcao.label)
            .join(", ") ||
          "Produtos selecionados",
      }
    : null;
  const filtrandoProduto = produtosSelecionados.length > 0;
  const grupos = useMemo(
    () => agruparVendasPorVendedor(vendas, produtosSelecionados),
    [vendas, produtosSelecionados],
  );
  const opcoes = useMemo(
    () =>
      agruparVendasPorVendedor(vendas).map((grupo) => ({
        value: grupo.chave,
        label: grupo.vendedor,
      })),
    [vendas],
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
  const quantidadeProdutos = gruposVisiveis.reduce(
    (total, grupo) => total + grupo.quantidadeProdutos,
    0,
  );

  const exportar = async (formato) => {
    if (!gruposVisiveis.length) {
      toast.error("Não há vendas para exportar nesse período.");
      return;
    }
    setExportando(formato);
    try {
      const periodo = { inicio: dataInicio, fim: dataFim };
      const nome = `vendas_por_vendedor_${filtrandoProduto ? "produtos_" : ""}${dataInicio}_${dataFim}`;
      if (formato === "pdf") {
        const { criarPdfVendasPorVendedor } = await import("./vendasPorVendedorPdf");
        const pdf = await criarPdfVendasPorVendedor({
          grupos: gruposVisiveis,
          periodo,
          produto,
          vendedor:
            opcoes.find((opcao) => opcao.value === vendedorSelecionado)?.label ||
            "Todos os vendedores",
        });
        pdf.save(`${nome}.pdf`);
      } else {
        await exportarPlanilhasExcel(
          planilhasVendasPorVendedor(gruposVisiveis, periodo, produto),
          `${nome}.xlsx`,
        );
      }
      toast.success("Relatório por vendedor exportado.");
    } catch (error) {
      console.error("Erro ao exportar vendas por vendedor:", error);
      toast.error("Não foi possível exportar o relatório.");
    } finally {
      setExportando("");
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
          <div className="flex flex-wrap gap-2">
            <BotaoInteracao
              onClick={() => exportar("pdf")}
              disabled={Boolean(exportando) || !gruposVisiveis.length}
            >
              {exportando === "pdf" ? "Gerando PDF..." : "Exportar PDF"}
            </BotaoInteracao>
            <BotaoInteracao
              onClick={() => exportar("excel")}
              disabled={Boolean(exportando) || !gruposVisiveis.length}
            >
              {exportando === "excel" ? "Exportando..." : "Exportar Excel"}
            </BotaoInteracao>
          </div>
        </div>
        <div className="mt-4 grid max-w-3xl gap-4 sm:grid-cols-2">
          <BuscaProdutoMultiplo
            id="relatorio-produto-vendedor"
            label="Produtos"
            value={produtosSelecionados}
            onChange={setProdutosSelecionados}
            opcoes={produtos}
            help="Selecione vários produtos por nome ou código. Inclui o catálogo e os produtos vendidos no período."
          />
          <InputCombobox
            id="relatorio-vendedor"
            label="Vendedor"
            placeholder="Todos os vendedores"
            value={vendedorSelecionado}
            onChange={setVendedorSelecionado}
            opcoes={opcoes}
          />
        </div>
        <VendasGruposProdutosPanel
          controle={controleGrupos}
          produtosSelecionados={produtosSelecionados}
          vendedorSelecionado={vendedorSelecionado}
        />
        <p className="mt-4 text-sm text-slate-700 dark:text-slate-200">
          {quantidade} venda(s)
          {filtrandoProduto &&
            ` · Quantidade do produto: ${formatarQuantidade(quantidadeProdutos)}`}
          {` · ${filtrandoProduto ? "Valor bruto do produto" : "Total vendido"}: ${formatMoneyBRL(valorTotal)}`}
        </p>
        {filtrandoProduto && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Somente os itens do produto selecionado. Valor bruto antes de descontos e taxas, sem
            abater devoluções. Vendas canceladas não entram.
          </p>
        )}
      </div>

      {filtrandoProduto && gruposVisiveis.length > 0 && (
        <div className="overflow-x-auto rounded-lg bg-white shadow dark:bg-slate-900">
          <table className="w-full min-w-[520px] text-left text-sm">
            <caption className="px-4 py-3 text-left font-semibold text-slate-800 dark:text-slate-100">
              Resumo por vendedor · {produto?.label}
            </caption>
            <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              <tr>
                <th scope="col" className="px-4 py-2">
                  Vendedor
                </th>
                <th scope="col" className="px-4 py-2 text-right">
                  Vendas
                </th>
                <th scope="col" className="px-4 py-2 text-right">
                  Quantidade
                </th>
                <th scope="col" className="px-4 py-2 text-right">
                  Valor bruto do produto
                </th>
              </tr>
            </thead>
            <tbody className="divide-y text-slate-700 dark:divide-slate-700 dark:text-slate-200">
              {gruposVisiveis.map((grupo) => (
                <tr key={grupo.chave}>
                  <th scope="row" className="px-4 py-3 font-medium">
                    {grupo.vendedor}
                  </th>
                  <td className="px-4 py-3 text-right">{grupo.quantidade}</td>
                  <td className="px-4 py-3 text-right">
                    {formatarQuantidade(grupo.quantidadeProdutos)}
                  </td>
                  <td className="px-4 py-3 text-right">{formatMoneyBRL(grupo.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {gruposVisiveis.length === 0 ? (
        <p className="rounded-lg bg-white p-6 text-slate-600 shadow dark:bg-slate-900 dark:text-slate-300">
          Nenhuma venda encontrada para os filtros selecionados nesse período.
        </p>
      ) : (
        gruposVisiveis.map((grupo) => (
          <div
            key={grupo.chave}
            className="overflow-x-auto rounded-lg bg-white shadow dark:bg-slate-900"
          >
            <div className="flex flex-wrap justify-between gap-2 border-b p-4 dark:border-slate-700">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100">{grupo.vendedor}</h3>
              <span className="text-sm text-slate-700 dark:text-slate-200">
                {grupo.quantidade} venda(s)
                {filtrandoProduto &&
                  ` · Quantidade: ${formatarQuantidade(grupo.quantidadeProdutos)}`}
                {` · ${filtrandoProduto ? "Valor bruto: " : ""}${formatMoneyBRL(grupo.total)}`}
              </span>
            </div>
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <tr>
                  <th className="px-4 py-2">Data</th>
                  <th className="px-4 py-2">Venda</th>
                  <th className="px-4 py-2">Cliente</th>
                  <th className="px-4 py-2">Produtos e quantidades</th>
                  <th className="px-4 py-2 text-right">
                    {filtrandoProduto ? "Valor bruto do produto" : "Total"}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-slate-700">
                {grupo.vendas.map((venda) => (
                  <tr key={venda.id} className="text-slate-700 dark:text-slate-200">
                    <td className="whitespace-nowrap px-4 py-3">
                      {formatarData(venda.data_venda)}
                    </td>
                    <td className="px-4 py-3">{venda.numero_venda}</td>
                    <td className="px-4 py-3">{venda.cliente_nome}</td>
                    <td className="px-4 py-3">
                      {(venda.itens || []).length
                        ? venda.itens.map((item, indice) => (
                            <div key={`${venda.id}-${item.venda_item_id || indice}`}>
                              {item.produto_nome} · {formatarQuantidade(item.quantidade)}
                            </div>
                          ))
                        : "Sem itens"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {formatMoneyBRL(venda.total_relatorio)}
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
