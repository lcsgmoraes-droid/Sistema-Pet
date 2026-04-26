export default function ConsultasPaginacao({ pagina, setPagina, totalPaginas }) {
  if (totalPaginas <= 1) return null;

  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-gray-400">
        Mostrando pagina {pagina} de {totalPaginas}
      </p>
      <div className="flex gap-2">
        <button
          disabled={pagina <= 1}
          onClick={() => setPagina((valor) => valor - 1)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >
          Anterior
        </button>
        <button
          disabled={pagina >= totalPaginas}
          onClick={() => setPagina((valor) => valor + 1)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >
          Proxima
        </button>
      </div>
    </div>
  );
}
