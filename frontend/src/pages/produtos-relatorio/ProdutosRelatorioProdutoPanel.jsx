import ProductIdentity from "../../components/ui/ProductIdentity";
import { formatarData, formatarQuantidade } from "./produtosRelatorioFormatters";
import ProdutosRelatorioCurvaVendas30Dias from "./ProdutosRelatorioCurvaVendas30Dias";
import ProdutosRelatorioHistoricoVendas from "./ProdutosRelatorioHistoricoVendas";
import ProdutosRelatorioJanelaVendaCard from "./ProdutosRelatorioJanelaVendaCard";
import ProdutosRelatorioResumoCard from "./ProdutosRelatorioResumoCard";

function ProdutosRelatorioProdutoVazio() {
  return (
    <div className="rounded-3xl border border-dashed border-blue-200 bg-blue-50 p-8 text-center shadow-sm">
      <h2 className="text-xl font-semibold text-blue-900">
        Selecione um produto para enxergar o padrao de venda
      </h2>
      <p className="mx-auto mt-3 max-w-3xl text-sm text-blue-800">
        O objetivo principal desta tela agora e apoiar a compra. Busque o item por nome, SKU, codigo
        ou codigo de barras para ver o giro nos ultimos 7, 15, 30, 60 e 90 dias, alem do historico
        recente de vendas.
      </p>
    </div>
  );
}

export default function ProdutosRelatorioProdutoPanel({
  produtoSelecionado,
  dadosProduto,
  loadingResumoProduto,
  janelasOrdenadas,
  periodoAtivoDias,
  curva30Dias,
  totalPaginasHistorico,
  exportando,
  onEditarProduto,
  onExportarCsv,
  onPaginaHistoricoChange,
}) {
  if (!produtoSelecionado) {
    return <ProdutosRelatorioProdutoVazio />;
  }

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-bold text-gray-900">
                <ProductIdentity
                  product={dadosProduto?.produto || produtoSelecionado}
                  name={dadosProduto?.produto?.nome || produtoSelecionado.nome}
                  nameClassName="text-gray-900"
                  codeClassName="text-xs font-medium text-gray-500"
                />
              </h2>
              {dadosProduto?.produto?.categoria_nome && (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  {dadosProduto.produto.categoria_nome}
                </span>
              )}
              {dadosProduto?.produto?.marca_nome && (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  {dadosProduto.produto.marca_nome}
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onEditarProduto}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
            >
              Editar produto
            </button>
            <button
              type="button"
              onClick={onExportarCsv}
              disabled={exportando}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {exportando ? "Exportando..." : "Exportar movimentacoes"}
            </button>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ProdutosRelatorioResumoCard
            titulo="Estoque atual"
            valor={formatarQuantidade(dadosProduto?.produto?.estoque_atual)}
            descricao={`Minimo: ${formatarQuantidade(dadosProduto?.produto?.estoque_minimo)}`}
            destaque="blue"
          />
          <ProdutosRelatorioResumoCard
            titulo="Cobertura estimada"
            valor={
              dadosProduto?.resumo?.ruptura_ativa
                ? "Ruptura"
                : dadosProduto?.resumo?.cobertura_estimada_dias != null
                  ? `${formatarQuantidade(dadosProduto.resumo.cobertura_estimada_dias)} dias`
                  : "Sem base"
            }
            descricao={
              dadosProduto?.resumo?.ruptura_ativa
                ? "Estoque zerado/negativo; cobertura tratada como 0."
                : "Calculado pela media diaria dos ultimos 30 dias."
            }
            destaque={dadosProduto?.resumo?.ruptura_ativa ? "rose" : "amber"}
          />
          <ProdutosRelatorioResumoCard
            titulo="Media diaria 30 dias"
            valor={formatarQuantidade(dadosProduto?.resumo?.media_diaria_30)}
            descricao={`Vendidos 30 dias: ${formatarQuantidade(
              dadosProduto?.resumo?.quantidade_vendida_30,
            )}`}
            destaque="emerald"
          />
          <ProdutosRelatorioResumoCard
            titulo="Ultima venda"
            valor={formatarData(dadosProduto?.resumo?.ultima_venda?.data_venda)}
            descricao={
              dadosProduto?.resumo?.dias_sem_vender != null
                ? `${dadosProduto.resumo.dias_sem_vender} dia(s) sem vender`
                : "Sem historico de venda"
            }
            destaque="violet"
          />
        </div>
      </div>

      {loadingResumoProduto ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">
          Carregando historico comercial do produto...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            {janelasOrdenadas.map((janela) => (
              <ProdutosRelatorioJanelaVendaCard
                key={janela.dias}
                janela={janela}
                ativa={periodoAtivoDias === janela.dias}
              />
            ))}
          </div>

          {curva30Dias.length > 0 && <ProdutosRelatorioCurvaVendas30Dias pontos={curva30Dias} />}

          <ProdutosRelatorioHistoricoVendas
            dadosProduto={dadosProduto}
            totalPaginasHistorico={totalPaginasHistorico}
            onPaginaChange={onPaginaHistoricoChange}
          />
        </>
      )}
    </div>
  );
}
