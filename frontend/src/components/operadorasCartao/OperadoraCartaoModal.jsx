import { AlertCircle, Eye, EyeOff, Save, X } from "lucide-react";
import { ICONES_DISPONIVEIS } from "./operadorasCartaoUtils";

function OperadoraCartaoModal({
  erro,
  formData,
  modalAberto,
  mostrarToken,
  onClose,
  onSubmit,
  onToggleMostrarToken,
  operadoraSelecionada,
  setErro,
  setFormData,
}) {
  if (!modalAberto) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
          <h2 className="text-xl font-bold text-gray-900">
            {operadoraSelecionada ? "Editar Operadora" : "Nova Operadora"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-6">
          {erro && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span className="text-sm text-red-700">{erro}</span>
            </div>
          )}

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Informacoes Basicas</h3>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome da Operadora *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => {
                    setErro("");
                    setFormData({ ...formData, nome: e.target.value });
                  }}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Stone, Cielo, Rede"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Codigo (sigla)</label>
                <input
                  type="text"
                  value={formData.codigo}
                  onChange={(e) => setFormData({ ...formData, codigo: e.target.value.toUpperCase() })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  placeholder="Ex: STONE, CIELO"
                  maxLength={50}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Maximo de Parcelas *
                </label>
                <input
                  type="number"
                  value={formData.max_parcelas}
                  onChange={(e) =>
                    setFormData({ ...formData, max_parcelas: parseInt(e.target.value, 10) || 1 })
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="1"
                  max="24"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Entre 1 e 24 parcelas</p>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.padrao}
                    onChange={(e) => setFormData({ ...formData, padrao: e.target.checked })}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Operadora Padrao</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.ativo}
                    onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Ativo</span>
                </label>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Interface</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Cor</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={formData.cor}
                    onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                    className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={formData.cor}
                    onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    placeholder="#00A868"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Icone</label>
                <div className="flex flex-wrap gap-2">
                  {ICONES_DISPONIVEIS.map((icone) => (
                    <button
                      key={icone}
                      type="button"
                      onClick={() => setFormData({ ...formData, icone })}
                      className={`w-10 h-10 rounded flex items-center justify-center text-xl transition-colors ${
                        formData.icone === icone
                          ? "bg-blue-100 ring-2 ring-blue-500"
                          : "bg-gray-100 hover:bg-gray-200"
                      }`}
                    >
                      {icone}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Integracao API (Opcional)</h3>

            <label className="flex items-center gap-2 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.api_enabled}
                onChange={(e) => setFormData({ ...formData, api_enabled: e.target.checked })}
                className="w-4 h-4 text-blue-600"
              />
              <span className="text-sm font-medium text-gray-700">Habilitar integracao via API</span>
            </label>

            {formData.api_enabled && (
              <div className="space-y-4 pl-6 border-l-2 border-blue-200">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Endpoint da API
                  </label>
                  <input
                    type="url"
                    value={formData.api_endpoint}
                    onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    placeholder="https://api.operadora.com/v1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Token de Acesso
                  </label>
                  <div className="relative">
                    <input
                      type={mostrarToken ? "text" : "password"}
                      value={formData.api_token_encrypted}
                      onChange={(e) =>
                        setFormData({ ...formData, api_token_encrypted: e.target.value })
                      }
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="Token sera criptografado ao salvar"
                    />
                    <button
                      type="button"
                      onClick={onToggleMostrarToken}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {mostrarToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors"
            >
              <Save className="w-4 h-4" />
              {operadoraSelecionada ? "Salvar Alteracoes" : "Criar Operadora"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default OperadoraCartaoModal;
