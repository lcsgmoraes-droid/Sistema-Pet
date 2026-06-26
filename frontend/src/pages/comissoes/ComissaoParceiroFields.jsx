export default function ComissaoParceiroFields({
  dataFechamento,
  funcionarioId,
  funcionarioSel,
  funcionarios,
  onSaveDataFechamento,
  setDataFechamento,
  setFuncionarioSel,
}) {
  return (
    <>
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Parceiro</label>
        <select
          value={funcionarioSel}
          onChange={(event) => setFuncionarioSel(event.target.value)}
          className="w-full border rounded-lg px-3 py-2"
          disabled={Boolean(funcionarioId)}
        >
          <option value="">Selecione um parceiro</option>
          {funcionarios.map((funcionario) => (
            <option key={funcionario.id} value={funcionario.id}>
              {funcionario.nome} - {funcionario.cargo}
            </option>
          ))}
        </select>

        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-xs">
          <div className="flex items-start gap-2">
            <span className="text-blue-600">ℹ️</span>
            <div className="text-blue-700">
              <strong>Apenas parceiros podem receber comissões.</strong>
              <br />
              Se a pessoa não aparecer na lista, marque-a como "Parceiro" no cadastro de pessoas
              primeiro.
            </div>
          </div>
        </div>
      </div>

      {funcionarioSel && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            📅 Dia do mês para fechamento de comissão
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              min="1"
              max="31"
              value={dataFechamento}
              onChange={(event) => setDataFechamento(event.target.value)}
              placeholder="Ex: 5 (paga dia 5 de cada mês)"
              className="flex-1 border rounded-lg px-3 py-2"
            />
            <button
              onClick={onSaveDataFechamento}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 whitespace-nowrap"
            >
              💾 Salvar Data
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Deixe em branco para pagamento 30 dias após a venda (padrão)
          </p>
        </div>
      )}
    </>
  );
}
