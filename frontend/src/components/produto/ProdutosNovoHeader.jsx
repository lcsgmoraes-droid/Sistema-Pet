export default function ProdutosNovoHeader({ formData, isEdicao, onVoltar }) {
  return (
    <div className="mb-6">
      <div className="flex justify-between items-start">
        <div>
          <button
            onClick={onVoltar}
            className="text-blue-600 hover:text-blue-800 mb-2 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Voltar
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEdicao ? 'Editar Produto' : 'Novo Produto'}
          </h1>
          {isEdicao && formData.codigo && (
            <div className="mt-3 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-700">SKU:</span>
                <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-lg font-mono">
                  {formData.codigo}
                </span>
              </div>
              {formData.nome && (
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-700">Descrição:</span>
                  <span className="text-gray-600">{formData.nome}</span>
                </div>
              )}
            </div>
          )}
        </div>
        <a
          href="/cadastros/categorias"
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 border border-blue-200 flex items-center gap-2 text-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Gerenciar Categorias
        </a>
      </div>
    </div>
  );
}
