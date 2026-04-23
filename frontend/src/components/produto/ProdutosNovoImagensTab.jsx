import { resolveMediaUrl } from '../../utils/mediaUrl';

export default function ProdutosNovoImagensTab({
  handleDeleteImagem,
  handleSetPrincipal,
  handleUploadImagem,
  imagens,
  isEdicao,
  uploadingImage,
}) {
  if (!isEdicao) {
    return (
      <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <p className="mt-2 text-sm text-gray-600">Salve o produto primeiro para adicionar imagens</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Imagens do Produto</h3>

        <label className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer">
          {uploadingImage ? 'Enviando...' : '+ Adicionar Imagens'}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleUploadImagem}
            disabled={uploadingImage}
            className="hidden"
            multiple
          />
        </label>
      </div>

      {imagens.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">📷 Nenhuma imagem cadastrada</p>
          <p className="text-sm">Clique em "Adicionar Imagem" para enviar fotos do produto</p>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {imagens.map((img) => (
            <div key={img.id} className="relative group border rounded-lg overflow-hidden">
              <img
                src={resolveMediaUrl(img.thumbnail_url || img.url)}
                alt="Imagem do produto"
                className="w-full h-48 object-cover"
              />

              {img.e_principal && (
                <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                  Principal
                </div>
              )}

              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                {!img.e_principal && (
                  <button
                    type="button"
                    onClick={() => handleSetPrincipal(img.id)}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    title="Definir como principal"
                  >
                    ⭐ Principal
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => handleDeleteImagem(img.id)}
                  className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                  title="Excluir"
                >
                  🗑️ Excluir
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Dica:</strong> A primeira imagem marcada como "Principal" será exibida na listagem de produtos.
          Formatos aceitos: JPG, PNG, WebP (máx. 10MB). O sistema converte para WebP e gera miniaturas automaticamente.
        </p>
      </div>
    </div>
  );
}
