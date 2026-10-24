import { formatarMoeda } from "../../api/produtos";
import { formatarQuantidade } from "./produtosRelatorioFormatters";
import ProdutosRelatorioFiltros from "./ProdutosRelatorioFiltros";
import ProdutosRelatorioHeader from "./ProdutosRelatorioHeader";
import ProdutosRelatorioMovimentacoesTable from "./ProdutosRelatorioMovimentacoesTable";
import ProdutosRelatorioProdutoPanel from "./ProdutosRelatorioProdutoPanel";
import ProdutosRelatorioResumoCard from "./ProdutosRelatorioResumoCard";
import useProdutosRelatorioController from "./useProdutosRelatorioController";

export default function ProdutosRelatorioPage() {
  const relatorio = useProdutosRelatorioController();

  return (
    <div className="space-y-6 p-6">
      <ProdutosRelatorioHeader onVoltar={relatorio.voltarParaProdutos} />

      <ProdutosRelatorioFiltros
        periodoSelecionado={relatorio.periodoSelecionado}
        filtrosForm={relatorio.filtrosForm}
        erroQuantidade={relatorio.erroQuantidade}
        produtoSelecionado={relatorio.produtoSelecionado}
        buscaProduto={relatorio.buscaProduto}
        sugestoesProdutos={relatorio.sugestoesProdutos}
        dropdownAberto={relatorio.dropdownAberto}
        loadingBuscaProduto={relatorio.loadingBuscaProduto}
        buscaRef={relatorio.buscaRef}
        onSubmit={relatorio.aplicarFiltros}
        onPeriodoChange={relatorio.handlePeriodoChange}
        onDataInicioChange={relatorio.alterarDataInicio}
        onDataFimChange={relatorio.alterarDataFim}
        onFiltroChange={relatorio.atualizarFiltro}
        onBuscaProdutoChange={relatorio.alterarBuscaProduto}
        onBuscaProdutoFocus={relatorio.focarBuscaProduto}
        onLimparBuscaProduto={relatorio.limparBuscaProduto}
        onSelecionarProduto={relatorio.selecionarProduto}
        onLimparProduto={relatorio.limparProduto}
        onLimparFiltros={relatorio.limparFiltros}
      />

      {relatorio.filtrosAplicados.quantidade_operador && (
        <div
          className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-3 text-sm text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-100"
          role="status"
        >
          <p className="font-semibold">
            Quantidade filtrada:{" "}
            {
              { acima_de: "acima de", abaixo_de: "abaixo de", igual_a: "igual a" }[
                relatorio.filtrosAplicados.quantidade_operador
              ]
            }{" "}
            {formatarQuantidade(
              String(relatorio.filtrosAplicados.quantidade_valor).replace(",", "."),
            )}{" "}
            {relatorio.dadosProduto?.produto?.unidade ||
              relatorio.produtoSelecionado?.unidade ||
              "(unidade do produto)"}{" "}
            por item vendido ou movimentação.
          </p>
          <p className="mt-1">
            Totais, vendas, gráfico e exportação seguem este filtro. O estoque atual é o saldo
            total; a cobertura estimada considera apenas as vendas filtradas.
          </p>
        </div>
      )}

      <ProdutosRelatorioProdutoPanel
        produtoSelecionado={relatorio.produtoSelecionado}
        dadosProduto={relatorio.dadosProduto}
        loadingResumoProduto={relatorio.loadingResumoProduto}
        janelasOrdenadas={relatorio.janelasOrdenadas}
        periodoAtivoDias={relatorio.periodoAtivoDias}
        curva30Dias={relatorio.curva30Dias}
        totalPaginasHistorico={relatorio.totalPaginasHistorico}
        exportando={relatorio.exportando}
        onEditarProduto={relatorio.editarProdutoSelecionado}
        onExportarCsv={relatorio.exportarCsv}
        onPaginaHistoricoChange={relatorio.setPaginaHistoricoVendas}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <ProdutosRelatorioResumoCard
          titulo="Total de entradas"
          valor={formatarQuantidade(relatorio.dadosMovimentacoes.totais.total_entradas)}
          descricao="Somatorio de entradas dentro do filtro atual."
          destaque="emerald"
        />
        <ProdutosRelatorioResumoCard
          titulo="Total de saidas"
          valor={formatarQuantidade(relatorio.dadosMovimentacoes.totais.total_saidas)}
          descricao="Somatorio de saidas dentro do filtro atual."
          destaque="rose"
        />
        <ProdutosRelatorioResumoCard
          titulo="Valor movimentado"
          valor={formatarMoeda(relatorio.dadosMovimentacoes.totais.valor_total)}
          descricao="Baseado no valor total das movimentacoes filtradas."
          destaque="blue"
        />
      </div>

      <ProdutosRelatorioMovimentacoesTable
        dadosMovimentacoes={relatorio.dadosMovimentacoes}
        loadingMovimentacoes={relatorio.loadingMovimentacoes}
        inicioItemMovimentacoes={relatorio.inicioItemMovimentacoes}
        fimItemMovimentacoes={relatorio.fimItemMovimentacoes}
        paginaAtualMovimentacoes={relatorio.paginaAtualMovimentacoes}
        totalPaginasMovimentacoes={relatorio.totalPaginasMovimentacoes}
        exportando={relatorio.exportando}
        onExportarCsv={relatorio.exportarCsv}
        onPaginaChange={relatorio.setPaginaMovimentacoes}
      />
    </div>
  );
}
