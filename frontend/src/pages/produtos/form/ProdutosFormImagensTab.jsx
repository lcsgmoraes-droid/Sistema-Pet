import { TabContent } from "../../../components/ResponsiveTabs";
import { resolveMediaUrl } from "../../../utils/mediaUrl";

export default function ProdutosFormImagensTab({
  handleDeleteImagem,
  handleSetPrincipal,
  handleUploadImagem,
  imagens,
  uploadingImage,
}) {
  return (
    <TabContent>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Imagens do Produto</h2>

          <label className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition cursor-pointer">
            {uploadingImage ? "Enviando..." : "+ Adicionar Imagem"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleUploadImagem}
              disabled={uploadingImage}
              className="hidden"
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
                  alt={img.descricao || "Imagem do produto"}
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
                      onClick={() => handleSetPrincipal(img.id)}
                      className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                      title="Definir como principal"
                    >
                      ⭐ Principal
                    </button>
                  )}

                  <button
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
            <strong>Dica:</strong> A primeira imagem marcada como "Principal" será exibida na
            listagem de produtos. Formatos aceitos: JPG, PNG, WebP (max. 10MB) com otimizacao
            automatica e thumbnail.
          </p>
        </div>
      </div>
    </TabContent>
  );
}
