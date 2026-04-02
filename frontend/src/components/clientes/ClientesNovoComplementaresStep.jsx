const ClientesNovoComplementaresStep = ({
  formData,
  setFormData,
  enderecosAdicionais,
  abrirModalEndereco,
  removerEndereco,
}) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Informacoes complementares
      </h3>

      <div className="border-b pb-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="text-md font-semibold text-gray-800">
              Enderecos Adicionais
            </h4>
            <p className="text-sm text-gray-600">
              Cadastre multiplos enderecos para entrega, cobranca, etc.
            </p>
          </div>
          <button
            type="button"
            onClick={() => abrirModalEndereco()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            Adicionar Endereco
          </button>
        </div>

        {enderecosAdicionais.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
            {enderecosAdicionais.map((endereco, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          endereco.tipo === "entrega"
                            ? "bg-blue-100 text-blue-800"
                            : endereco.tipo === "cobranca"
                              ? "bg-green-100 text-green-800"
                              : endereco.tipo === "comercial"
                                ? "bg-purple-100 text-purple-800"
                                : endereco.tipo === "residencial"
                                  ? "bg-orange-100 text-orange-800"
                                  : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {endereco.tipo === "entrega"
                          ? "Entrega"
                          : endereco.tipo === "cobranca"
                            ? "Cobranca"
                            : endereco.tipo === "comercial"
                              ? "Comercial"
                              : endereco.tipo === "residencial"
                                ? "Residencial"
                                : "Trabalho"}
                      </span>
                      <span className="text-xs font-medium text-gray-500">
                        +{index + 1}
                      </span>
                    </div>
                    {endereco.apelido && (
                      <p className="text-sm font-semibold text-gray-900 mb-1">
                        {endereco.apelido}
                      </p>
                    )}
                    <p className="text-sm text-gray-700">
                      {endereco.endereco}, {endereco.numero}
                      {endereco.complemento && ` - ${endereco.complemento}`}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {endereco.bairro}, {endereco.cidade}/{endereco.estado}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      CEP: {endereco.cep}
                    </p>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <button
                      type="button"
                      onClick={() => abrirModalEndereco(index)}
                      className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Editar"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                    <button
                      type="button"
                      onClick={() => removerEndereco(index)}
                      className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Excluir"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 text-sm">
            <svg
              className="w-12 h-12 mx-auto mb-2 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Nenhum endereco adicional cadastrado
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Marcacoes / Tags
        </label>
        <input
          type="text"
          value={formData.tags}
          onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="Ex: Bom pagador, Cliente fiel, VIP"
        />
        <p className="text-xs text-gray-500 mt-1">
          Separe por virgula para multiplas tags
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Observacoes
        </label>
        <textarea
          value={formData.observacoes}
          onChange={(e) =>
            setFormData({
              ...formData,
              observacoes: e.target.value,
            })
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          rows="4"
          placeholder="Informacoes adicionais sobre o cliente..."
        />
      </div>
    </div>
  );
};

export default ClientesNovoComplementaresStep;
