import { useState } from "react";
import { BarChart3, Download } from "lucide-react";
import ModuleTabs from "../../components/ui/ModuleTabs";
import AnaliseProdutoEspecifico from "./AnaliseProdutoEspecifico";
import AnaliseProdutosFiltros from "./AnaliseProdutosFiltros";
import { CurvaAbcProdutos, GruposProdutos, VisaoGeralProdutos } from "./AnaliseProdutosViews";
import useAnaliseProdutos from "./useAnaliseProdutos";

const ABAS = [
  { id: "geral", label: "Visão geral" },
  { id: "abc", label: "Curva ABC" },
  { id: "grupos", label: "Grupos" },
  { id: "produto", label: "Produto específico" },
];

export default function AnaliseProdutosPage() {
  const [aba, setAba] = useState("geral");
  const analise = useAnaliseProdutos();

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-start gap-3">
          <span className="rounded-2xl bg-blue-100 p-3 text-blue-700">
            <BarChart3 className="h-6 w-6" aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
              Análise de Produtos
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Acompanhe desempenho de venda, ranking, Curva ABC, grupos e o histórico detalhado de
              cada produto.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={analise.exportarCsv}
          disabled={analise.carregando}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Exportar produtos do filtro
        </button>
      </header>

      <AnaliseProdutosFiltros
        catalogos={analise.catalogos}
        periodoAtivo={analise.periodoAtivo}
        filtros={analise.filtrosForm}
        onPeriodoChange={analise.escolherPeriodo}
        onChange={analise.atualizarFiltro}
        onSubmit={analise.aplicarFiltros}
        onLimpar={analise.limparFiltros}
      />

      <div className="rounded-2xl border border-slate-200 bg-white px-4 pt-2 shadow-sm">
        <ModuleTabs
          active={aba}
          onChange={setAba}
          tabs={ABAS}
          ariaLabel="Seções da análise de produtos"
        />
      </div>

      {analise.carregando && aba !== "produto" ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-14 text-center text-sm text-slate-500 shadow-sm">
          Calculando indicadores, rankings e Curva ABC...
        </div>
      ) : (
        <>
          {aba === "geral" && <VisaoGeralProdutos dados={analise.dados} />}
          {aba === "abc" && <CurvaAbcProdutos produtos={analise.dados.produtos} />}
          {aba === "grupos" && <GruposProdutos produtos={analise.dados.produtos} />}
          {aba === "produto" && (
            <AnaliseProdutoEspecifico
              produtoSelecionado={analise.produtoSelecionado}
              dadosProduto={analise.dadosProduto}
              carregando={analise.carregandoProduto}
              filtrosAplicados={analise.filtrosAplicados}
              pagina={analise.paginaProduto}
              onSelecionar={analise.selecionarProduto}
              onLimpar={analise.limparProduto}
              onPaginaChange={analise.setPaginaProduto}
            />
          )}
        </>
      )}

      <p className="pb-4 text-center text-xs text-slate-500">
        Lucro e margem são estimativas: usam o custo atual cadastrado do produto, não o custo
        histórico de cada venda.
      </p>
    </div>
  );
}
