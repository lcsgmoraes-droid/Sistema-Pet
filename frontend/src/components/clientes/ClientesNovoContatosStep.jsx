const ClientesNovoContatosStep = ({
  formData,
  setFormData,
  setShowDuplicadoWarning,
  setClienteDuplicado,
}) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Contatos</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Celular *</label>
        <input
          type="text"
          value={formData.celular}
          onChange={(e) => {
            setFormData({ ...formData, celular: e.target.value });
            setShowDuplicadoWarning(false);
            setClienteDuplicado(null);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="(00) 00000-0000"
          required={formData.tipo_cadastro === "cliente"}
        />
        {formData.tipo_cadastro === "cliente" && (
          <p className="mt-1 text-xs text-gray-500">
            Obrigatorio para clientes do app, e-commerce e loja fisica.
          </p>
        )}
      </div>

      <div className="rounded-lg border border-gray-200 p-3 space-y-3">
        <div>
          <h4 className="text-sm font-semibold text-gray-900">Celulares adicionais</h4>
          <p className="text-xs text-gray-500">
            Cadastre o celular da mãe, irmã ou de outra pessoa. No PDV, esse número encontra o
            cadastro principal e seus benefícios.
          </p>
        </div>
        {(formData.contatos_adicionais || []).map((contato, index) => (
          <div key={index} className="flex flex-wrap items-center gap-2">
            <input
              type="tel"
              aria-label={`Celular adicional ${index + 1}`}
              value={contato.numero}
              onChange={(e) => {
                const contatos = [...formData.contatos_adicionais];
                contatos[index] = { ...contato, numero: e.target.value };
                setFormData({ ...formData, contatos_adicionais: contatos });
              }}
              className="min-w-[170px] flex-1 rounded-lg border border-gray-300 px-3 py-2"
              placeholder="(00) 00000-0000"
              maxLength={50}
            />
            <input
              type="text"
              aria-label={`Vínculo do celular adicional ${index + 1}`}
              value={contato.vinculo}
              onChange={(e) => {
                const contatos = [...formData.contatos_adicionais];
                contatos[index] = { ...contato, vinculo: e.target.value };
                setFormData({ ...formData, contatos_adicionais: contatos });
              }}
              className="min-w-[130px] flex-1 rounded-lg border border-gray-300 px-3 py-2"
              placeholder="Mãe, irmã, pai..."
              maxLength={60}
            />
            <button
              type="button"
              onClick={() =>
                setFormData({
                  ...formData,
                  contatos_adicionais: formData.contatos_adicionais.filter((_, i) => i !== index),
                })
              }
              className="rounded-lg px-3 py-2 text-sm text-red-700 hover:bg-red-50"
            >
              Remover
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            setFormData({
              ...formData,
              contatos_adicionais: [
                ...(formData.contatos_adicionais || []),
                { numero: "", vinculo: "" },
              ],
            })
          }
          className="rounded-lg border border-blue-300 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
        >
          + Adicionar celular
        </button>
      </div>

      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="text-sm text-gray-700">Este número é WhatsApp?</span>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={formData.celular_whatsapp === true}
              onChange={() => setFormData({ ...formData, celular_whatsapp: true })}
              className="text-blue-600"
            />
            <span className="text-sm">Sim</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={formData.celular_whatsapp === false}
              onChange={() =>
                setFormData({
                  ...formData,
                  celular_whatsapp: false,
                })
              }
              className="text-blue-600"
            />
            <span className="text-sm">Não</span>
          </label>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Telefone fixo</label>
        <input
          type="text"
          value={formData.telefone}
          onChange={(e) => {
            setFormData({ ...formData, telefone: e.target.value });
            setShowDuplicadoWarning(false);
            setClienteDuplicado(null);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="(00) 0000-0000"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="email@exemplo.com"
        />
      </div>
    </div>
  );
};

export default ClientesNovoContatosStep;
