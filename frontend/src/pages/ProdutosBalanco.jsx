import ProdutosBalancoFiltros from "../components/produtoBalanco/ProdutosBalancoFiltros";
import ProdutosBalancoPaginacao from "../components/produtoBalanco/ProdutosBalancoPaginacao";
import ProdutosBalancoTabela from "../components/produtoBalanco/ProdutosBalancoTabela";
import { useProdutosBalancoPage } from "../hooks/useProdutosBalancoPage";

export default function ProdutosBalanco() {
  const {
    atualizarFiltro,
    atualizarInput,
    aplicarFiltrosServidor,
    carregando,
    filtros,
    fimItem,
    fornecedores,
    inicioItem,
    inputRefs,
    inputs,
    marcas,
    onInputKeyDown,
    paginaAtual,
    produtosPaginados,
    setPaginaAtual,
    submetendo,
    destacados,
    totalItens,
    totalPaginas,
  } = useProdutosBalancoPage();

  if (carregando) {
    return (
      <div className="p-6">
        <div className="text-gray-500">Carregando tela de balanco...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Balanco de Estoque</h1>
        <p className="text-sm text-blue-800 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 mt-2 inline-block leading-relaxed">
          Nesta tela, digite os valores em Entrada, Saida ou Balanco e pressione{" "}
          <span className="mx-1 inline-flex items-center rounded-md border border-blue-300 bg-white px-2 py-0.5 text-xs font-semibold text-blue-700 align-middle">
            TAB
          </span>{" "}
          para lancar automaticamente e ir para o proximo produto. O destaque verde mostra os
          itens ja lancados e permanece na tela ate voce clicar em Atualizar lista.
        </p>
      </div>

      <ProdutosBalancoFiltros
        filtros={filtros}
        fornecedores={fornecedores}
        marcas={marcas}
        onAtualizarFiltro={atualizarFiltro}
        onAplicarFiltros={aplicarFiltrosServidor}
      />

      <ProdutosBalancoPaginacao
        fimItem={fimItem}
        inicioItem={inicioItem}
        onPaginaAnterior={() => setPaginaAtual((prev) => Math.max(1, prev - 1))}
        onPaginaProxima={() => setPaginaAtual((prev) => Math.min(totalPaginas, prev + 1))}
        paginaAtual={paginaAtual}
        totalItens={totalItens}
        totalPaginas={totalPaginas}
      />

      <ProdutosBalancoTabela
        destacados={destacados}
        inputRefs={inputRefs}
        inputs={inputs}
        onAtualizarInput={atualizarInput}
        onInputKeyDown={onInputKeyDown}
        produtos={produtosPaginados}
        submetendo={submetendo}
      />

      <ProdutosBalancoPaginacao
        fimItem={fimItem}
        inicioItem={inicioItem}
        onPaginaAnterior={() => setPaginaAtual((prev) => Math.max(1, prev - 1))}
        onPaginaProxima={() => setPaginaAtual((prev) => Math.min(totalPaginas, prev + 1))}
        paginaAtual={paginaAtual}
        totalItens={totalItens}
        totalPaginas={totalPaginas}
      />
    </div>
  );
}
