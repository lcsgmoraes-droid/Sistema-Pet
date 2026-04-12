const ClientesNovoPaginationControls = ({
  loading,
  totalRegistros,
  paginaAtual,
  registrosPorPagina,
  setRegistrosPorPagina,
  setPaginaAtual,
  variant = "top",
}) => {
  if (loading || totalRegistros <= 0) return null;

  const totalPaginas = Math.ceil(totalRegistros / registrosPorPagina);
  const containerClass =
    variant === "top"
      ? "px-4 py-3 bg-gray-50 border border-gray-200 rounded-t-lg flex items-center justify-between mb-0"
      : "px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between";

  const pages = Array.from({ length: Math.min(totalPaginas, 5) }, (_, i) => {
    if (totalPaginas <= 5) return i + 1;
    if (paginaAtual <= 3) return i + 1;
    if (paginaAtual >= totalPaginas - 2) return totalPaginas - 4 + i;
    return paginaAtual - 2 + i;
  });

  return (
    <div className={containerClass}>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">
          Mostrando {(paginaAtual - 1) * registrosPorPagina + 1} a{" "}
          {Math.min(paginaAtual * registrosPorPagina, totalRegistros)} de{" "}
          {totalRegistros} pessoas
        </span>
        <select
          value={registrosPorPagina}
          onChange={(e) => {
            setRegistrosPorPagina(Number(e.target.value));
            setPaginaAtual(1);
          }}
          className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        >
          <option value={10}>10 por pagina</option>
          <option value={20}>20 por pagina</option>
          <option value={30}>30 por pagina</option>
          <option value={50}>50 por pagina</option>
          <option value={100}>100 por pagina</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setPaginaAtual(1)}
          disabled={paginaAtual === 1}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Primeira
        </button>
        <button
          onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
          disabled={paginaAtual === 1}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Anterior
        </button>

        <div className="flex items-center gap-1">
          {pages.map((pageNum) => (
            <button
              key={pageNum}
              onClick={() => setPaginaAtual(pageNum)}
              className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                paginaAtual === pageNum
                  ? "bg-purple-600 text-white"
                  : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {pageNum}
            </button>
          ))}
        </div>

        <button
          onClick={() =>
            setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas))
          }
          disabled={paginaAtual === totalPaginas}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Proxima
        </button>
        <button
          onClick={() => setPaginaAtual(totalPaginas)}
          disabled={paginaAtual === totalPaginas}
          className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Ultima
        </button>
      </div>
    </div>
  );
};

export default ClientesNovoPaginationControls;
