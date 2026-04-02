function ProdutosBalancoPaginacao({
  fimItem,
  inicioItem,
  onPaginaAnterior,
  onPaginaProxima,
  paginaAtual,
  totalItens,
  totalPaginas,
}) {
  return (
    <>
      <div className="flex items-center justify-between text-sm text-gray-500 px-1">
        <span>
          Mostrando {inicioItem} a {fimItem} de {totalItens} produtos
        </span>
        <span>20 por pagina</span>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onPaginaAnterior}
          disabled={paginaAtual <= 1}
          className="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 disabled:opacity-50"
        >
          Anterior
        </button>
        <span className="text-sm text-gray-500">
          Pagina {Math.min(paginaAtual, totalPaginas)} de {totalPaginas}
        </span>
        <button
          type="button"
          onClick={onPaginaProxima}
          disabled={paginaAtual >= totalPaginas}
          className="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 disabled:opacity-50"
        >
          Proxima
        </button>
      </div>
    </>
  );
}

export default ProdutosBalancoPaginacao;
