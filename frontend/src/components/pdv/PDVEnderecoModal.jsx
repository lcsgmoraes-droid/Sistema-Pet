import { X } from "lucide-react";

export default function PDVEnderecoModal({
  enderecoAtual,
  loadingCep,
  onBuscarCep,
  onClose,
  onChange,
  onSalvar,
}) {
  if (!enderecoAtual) {
    return null;
  }

  const atualizarCampo = (campo, valor) => {
    onChange({
      ...enderecoAtual,
      [campo]: valor,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
          <h3 className="text-xl font-bold text-gray-900">
            Adicionar Novo Endereço ao Cliente
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Endereço *
              </label>
              <select
                value={enderecoAtual.tipo}
                onChange={(e) => atualizarCampo("tipo", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="entrega">📦 Entrega</option>
                <option value="cobranca">💰 Cobrança</option>
                <option value="comercial">🏢 Comercial</option>
                <option value="residencial">🏠 Residencial</option>
                <option value="trabalho">📍 Trabalho</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Apelido (opcional)
              </label>
              <input
                type="text"
                value={enderecoAtual.apelido}
                onChange={(e) => atualizarCampo("apelido", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="Ex: Casa da mãe, Escritório, Loja"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CEP *
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={enderecoAtual.cep}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, "");
                    const formatted =
                      value.length > 5
                        ? `${value.slice(0, 5)}-${value.slice(5, 8)}`
                        : value;
                    atualizarCampo("cep", formatted);
                  }}
                  onBlur={(e) => onBuscarCep(e.target.value)}
                  maxLength="9"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  placeholder="00000-000"
                />
                {loadingCep && (
                  <div className="absolute right-2 top-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Endereço *
              </label>
              <input
                type="text"
                value={enderecoAtual.endereco}
                onChange={(e) => atualizarCampo("endereco", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="Rua, Avenida, etc."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número
              </label>
              <input
                type="text"
                value={enderecoAtual.numero}
                onChange={(e) => atualizarCampo("numero", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="123"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Complemento
              </label>
              <input
                type="text"
                value={enderecoAtual.complemento}
                onChange={(e) => atualizarCampo("complemento", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="Apto, Bloco, Sala..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bairro
              </label>
              <input
                type="text"
                value={enderecoAtual.bairro}
                onChange={(e) => atualizarCampo("bairro", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="Centro, Jardim..."
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cidade *
              </label>
              <input
                type="text"
                value={enderecoAtual.cidade}
                onChange={(e) => atualizarCampo("cidade", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="São Paulo"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estado
              </label>
              <input
                type="text"
                value={enderecoAtual.estado}
                onChange={(e) => atualizarCampo("estado", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                maxLength="2"
                placeholder="SP"
              />
            </div>
          </div>

          <p className="text-xs text-gray-500">* Campos obrigatórios</p>
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onSalvar}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Salvar Endereço
          </button>
        </div>
      </div>
    </div>
  );
}
