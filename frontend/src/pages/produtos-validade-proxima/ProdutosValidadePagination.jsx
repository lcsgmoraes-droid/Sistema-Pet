export default function ProdutosValidadePagination({ controller }) {
  const { dados, fimItem, inicioItem, loading, paginaAtual, totalPaginas } = controller;

  return (
    <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="text-sm text-gray-600">
        {dados.total > 0
          ? `Mostrando ${inicioItem}-${fimItem} de ${dados.total} lote(s).`
          : "Nenhum lote para exibir."}
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => controller.setPaginaAtual((prev) => Math.max(prev - 1, 1))}
          disabled={paginaAtual <= 1 || loading}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Anterior
        </button>
        <span className="text-sm text-gray-600">
          Pagina {paginaAtual} de {Math.max(totalPaginas, 1)}
        </span>
        <button
          type="button"
          onClick={() =>
            controller.setPaginaAtual((prev) => Math.min(prev + 1, Math.max(totalPaginas, 1)))
          }
          disabled={loading || paginaAtual >= totalPaginas}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Proxima
        </button>
      </div>
    </div>
  );
}
