export default function ProdutosNovoHeader({ formData, isClone, isEdicao, onClonar, onVoltar }) {
  const titulo = isClone ? 'Clonar Produto' : isEdicao ? 'Editar Produto' : 'Novo Produto';

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
            {titulo}
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
          {isClone && (
            <p className="mt-2 text-sm text-gray-600">
              Revise os dados copiados e informe um novo SKU/codigo antes de salvar.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isEdicao && onClonar && (
            <button
              type="button"
              onClick={onClonar}
              className="px-4 py-2 bg-slate-50 text-slate-700 rounded-lg hover:bg-slate-100 border border-slate-200 flex items-center gap-2 text-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Clonar Produto
            </button>
          )}
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
    </div>
  );
}
