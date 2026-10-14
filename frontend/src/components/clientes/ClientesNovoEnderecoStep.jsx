const ClientesNovoEnderecoStep = ({ formData, setFormData, buscarCep, loadingCep, cepError }) => {
  const temEndereco = [formData.cep, formData.endereco, formData.bairro].some((value) =>
    String(value ?? "").trim(),
  );

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Endereco</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">CEP</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={formData.cep}
            onChange={(e) => {
              const cep = e.target.value;
              setFormData({ ...formData, cep });
              if (cep.replace(/\D/g, "").length === 8) {
                buscarCep(cep);
              }
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="00000-000"
            maxLength="9"
          />
          <button
            type="button"
            onClick={() => buscarCep(formData.cep)}
            disabled={loadingCep}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {loadingCep ? "Buscando..." : "Buscar"}
          </button>
        </div>
        {cepError && <p className="text-xs text-red-500 mt-1">{cepError}</p>}
        <p className="text-xs text-gray-500 mt-1">
          Digite o CEP para preencher o endereco automaticamente
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Endereco</label>
        <input
          type="text"
          value={formData.endereco}
          onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="Rua, Avenida..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="cliente-numero-endereco"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Numero{temEndereco ? " *" : ""}
          </label>
          <input
            id="cliente-numero-endereco"
            type="text"
            value={formData.numero}
            onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="123 ou S/N"
            required={temEndereco}
            aria-describedby="cliente-numero-endereco-ajuda"
          />
          <p id="cliente-numero-endereco-ajuda" className="text-xs text-gray-500 mt-1">
            Se não houver número, informe S/N ou sem número.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Complemento</label>
          <input
            type="text"
            value={formData.complemento}
            onChange={(e) =>
              setFormData({
                ...formData,
                complemento: e.target.value,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="Apto, Bloco..."
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Bairro</label>
        <input
          type="text"
          value={formData.bairro}
          onChange={(e) => setFormData({ ...formData, bairro: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cidade</label>
          <input
            type="text"
            value={formData.cidade}
            onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
          <input
            type="text"
            value={formData.estado}
            onChange={(e) => setFormData({ ...formData, estado: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            maxLength="2"
            placeholder="SP"
          />
        </div>
      </div>
    </div>
  );
};

export default ClientesNovoEnderecoStep;
