export default function PetDetalhesNovoExameForm({
  novoExame,
  onSalvar,
  salvandoExame,
  setNovoExame,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="text-lg font-semibold text-gray-900">Novo exame</h3>
      <input
        type="text"
        value={novoExame.nome}
        onChange={(e) => setNovoExame((prev) => ({ ...prev, nome: e.target.value }))}
        placeholder="Nome do exame"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
      />
      <div className="grid grid-cols-2 gap-3">
        <select
          value={novoExame.tipo}
          onChange={(e) => setNovoExame((prev) => ({ ...prev, tipo: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        >
          <option value="laboratorial">Laboratorial</option>
          <option value="imagem">Imagem</option>
          <option value="citologia">Citologia</option>
          <option value="outro">Outro</option>
        </select>
        <input
          type="date"
          value={novoExame.data_solicitacao}
          onChange={(e) => setNovoExame((prev) => ({ ...prev, data_solicitacao: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
      </div>
      <input
        type="text"
        value={novoExame.laboratorio}
        onChange={(e) => setNovoExame((prev) => ({ ...prev, laboratorio: e.target.value }))}
        placeholder="LaboratÃ³rio ou clÃ­nica"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
      />
      <textarea
        value={novoExame.observacoes}
        onChange={(e) => setNovoExame((prev) => ({ ...prev, observacoes: e.target.value }))}
        rows="3"
        placeholder="ObservaÃ§Ãµes do pedido ou resultado"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
      />
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        onChange={(e) =>
          setNovoExame((prev) => ({ ...prev, arquivo: e.target.files?.[0] || null }))
        }
        className="w-full text-sm text-gray-600"
      />
      <button
        type="button"
        onClick={onSalvar}
        disabled={salvandoExame || !novoExame.nome.trim()}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg transition-colors font-medium"
      >
        {salvandoExame ? "Salvando exame..." : "Salvar exame"}
      </button>
    </div>
  );
}
