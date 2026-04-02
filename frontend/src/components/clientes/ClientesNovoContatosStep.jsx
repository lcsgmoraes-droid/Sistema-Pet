const ClientesNovoContatosStep = ({
  formData,
  setFormData,
  setShowDuplicadoWarning,
  setClienteDuplicado,
}) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Contatos
      </h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Celular *
        </label>
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
        />
      </div>

      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="text-sm text-gray-700">
          Este número é WhatsApp?
        </span>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={formData.celular_whatsapp === true}
              onChange={() =>
                setFormData({ ...formData, celular_whatsapp: true })
              }
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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Telefone fixo
        </label>
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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          E-mail
        </label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) =>
            setFormData({ ...formData, email: e.target.value })
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="email@exemplo.com"
        />
      </div>
    </div>
  );
};

export default ClientesNovoContatosStep;
