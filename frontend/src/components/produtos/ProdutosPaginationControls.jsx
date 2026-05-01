import React from "react";

export default function ProdutosPaginationControls({
  itensPorPagina,
  onChangeItensPorPagina,
  onIrParaPagina,
  onIrParaPrimeiraPagina,
  onIrParaUltimaPagina,
  onPaginaAnterior,
  onProximaPagina,
  paginaAtual,
  totalItens,
  totalPaginas,
}) {
  if (totalItens <= 0) return null;

  const paginaInicial =
    totalPaginas <= 5
      ? 1
      : paginaAtual <= 3
        ? 1
        : paginaAtual >= totalPaginas - 2
          ? totalPaginas - 4
          : paginaAtual - 2;

  const paginasVisiveis = Array.from(
    { length: Math.min(totalPaginas, 5) },
    (_, index) => paginaInicial + index,
  );

  return (
    <div className="flex w-full flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-4">
        <span className="text-sm text-gray-600">
          Mostrando {(paginaAtual - 1) * itensPorPagina + 1} a{" "}
          {Math.min(paginaAtual * itensPorPagina, totalItens)} de {totalItens} produtos
        </span>
        <select
          value={itensPorPagina}
          onChange={(event) => onChangeItensPorPagina(event.target.value)}
          className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value={10}>10 por pagina</option>
          <option value={20}>20 por pagina</option>
          <option value={30}>30 por pagina</option>
          <option value={50}>50 por pagina</option>
          <option value={100}>100 por pagina</option>
        </select>
      </div>

      <div className="flex items-center justify-between gap-2 md:justify-end">
        <button
          onClick={onIrParaPrimeiraPagina}
          disabled={paginaAtual === 1}
          className="hidden px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed sm:inline-flex"
        >
          Primeira
        </button>
        <button
          onClick={onPaginaAnterior}
          disabled={paginaAtual === 1}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Anterior
        </button>

        <span className="text-sm font-medium text-gray-600 sm:hidden">
          {paginaAtual}/{Math.max(totalPaginas, 1)}
        </span>

        <div className="hidden items-center gap-1 sm:flex">
          {paginasVisiveis.map((pageNum) => (
            <button
              key={pageNum}
              onClick={() => onIrParaPagina(pageNum)}
              className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                paginaAtual === pageNum
                  ? "bg-blue-600 text-white"
                  : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {pageNum}
            </button>
          ))}
        </div>

        <button
          onClick={onProximaPagina}
          disabled={paginaAtual === totalPaginas}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Proxima
        </button>
        <button
          onClick={onIrParaUltimaPagina}
          disabled={paginaAtual === totalPaginas}
          className="hidden px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed sm:inline-flex"
        >
          Ultima
        </button>
      </div>
    </div>
  );
}
