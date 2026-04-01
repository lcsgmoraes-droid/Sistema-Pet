export default function ProdutosNovoStatusBanners({
  isEdicao,
  onAbrirPredecessor,
  onAbrirSucessor,
  predecessorInfo,
  sucessorInfo,
}) {
  if (!isEdicao || (!predecessorInfo && !sucessorInfo)) {
    return null;
  }

  return (
    <>
      {predecessorInfo && (
        <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-5 rounded-lg shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg className="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  Este produto e continuacao de outro
                </h3>
              </div>
              <p className="text-sm text-gray-700 mb-3">
                Este produto substitui:{' '}
                <button
                  type="button"
                  onClick={onAbrirPredecessor}
                  className="font-bold text-blue-700 hover:text-blue-900 hover:underline"
                >
                  {predecessorInfo.codigo} - {predecessorInfo.nome}
                </button>
              </p>
              {predecessorInfo.motivo_descontinuacao && (
                <div className="bg-white/70 rounded-md px-3 py-2 text-sm">
                  <span className="font-medium text-gray-700">Motivo da substituicao:</span>{' '}
                  <span className="text-gray-900">{predecessorInfo.motivo_descontinuacao}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {sucessorInfo && (
        <div className="mb-6 bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-500 p-5 rounded-lg shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg className="w-7 h-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  Este produto foi descontinuado
                </h3>
              </div>
              <p className="text-sm text-gray-700 mb-3">
                Descontinuado em{' '}
                <span className="font-semibold">
                  {new Date(sucessorInfo.data_descontinuacao).toLocaleDateString('pt-BR')}
                </span>
              </p>
              <p className="text-sm text-gray-700 mb-3">
                Substituido por:{' '}
                <button
                  type="button"
                  onClick={onAbrirSucessor}
                  className="font-bold text-red-700 hover:text-red-900 hover:underline"
                >
                  {sucessorInfo.codigo} - {sucessorInfo.nome}
                </button>
              </p>
              {sucessorInfo.motivo_descontinuacao && (
                <div className="bg-white/70 rounded-md px-3 py-2 text-sm">
                  <span className="font-medium text-gray-700">Motivo:</span>{' '}
                  <span className="text-gray-900">{sucessorInfo.motivo_descontinuacao}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
