import MoneyCell from "../../../components/ui/MoneyCell";

export default function ComissoesListagemFechamentoModal({ controller }) {
  const {
    calcularTotalSelecionado,
    confirmarFechamento,
    contaBancariaId,
    contasBancarias,
    dataPagamento,
    fecharModalFechamento,
    formaPagamento,
    formasPagamentoDisponiveis,
    formatarMoeda,
    loadingFechamento,
    mostrarModalFechamento,
    observacaoFechamento,
    setContaBancariaId,
    setDataPagamento,
    setFormaPagamento,
    setObservacaoFechamento,
    setTipoPagamento,
    setValorTotalEditavel,
    tipoPagamento,
    valorTotalEditavel,
    comissoesSelecionadas,
  } = controller;

  if (!mostrarModalFechamento) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-800">Fechar Comissões Selecionadas</h3>
          <button onClick={fecharModalFechamento} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Resumo de Comissões */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-sm text-gray-700 font-medium">
                {comissoesSelecionadas.length} comissão(ões) selecionada(s)
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-600">Valor Total</p>
              <p className="text-2xl font-bold text-blue-600">
                <MoneyCell value={calcularTotalSelecionado()} />
              </p>
            </div>
          </div>
        </div>

        {/* SELEÇÃO DE TIPO DE FECHAMENTO */}
        <div className="mb-6">
          <label className="block text-sm font-bold text-gray-700 mb-3">
            ⚙️ Tipo de Fechamento
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setTipoPagamento("sem_pagar")}
              className={`p-4 border-2 rounded-lg transition-all ${
                tipoPagamento === "sem_pagar"
                  ? "border-blue-500 bg-blue-50 shadow-md"
                  : "border-gray-300 hover:border-blue-300"
              }`}
            >
              <div className="text-center">
                <div className="text-3xl mb-2">📋</div>
                <div className="font-bold text-gray-800">Fechar sem Pagar</div>
                <div className="text-xs text-gray-600 mt-1">Apenas registrar fechamento</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setTipoPagamento("com_pagamento")}
              className={`p-4 border-2 rounded-lg transition-all ${
                tipoPagamento === "com_pagamento"
                  ? "border-green-500 bg-green-50 shadow-md"
                  : "border-gray-300 hover:border-green-300"
              }`}
            >
              <div className="text-center">
                <div className="text-3xl mb-2">💰</div>
                <div className="font-bold text-gray-800">Fechar e Pagar</div>
                <div className="text-xs text-gray-600 mt-1">Com lançamento financeiro</div>
              </div>
            </button>
          </div>
        </div>

        {/* CAMPOS COMUNS */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            📅 Data do Fechamento/Pagamento <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={dataPagamento}
            onChange={(e) => setDataPagamento(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* CAMPOS CONDICIONAIS - PAGAMENTO */}
        {tipoPagamento === "com_pagamento" && (
          <div className="space-y-4 mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="text-sm font-bold text-green-800 mb-3">💳 Dados do Pagamento</h4>

            {/* Valor Total (editável) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💵 Valor a Pagar (editável)
              </label>
              <input
                type="number"
                step="0.01"
                value={valorTotalEditavel}
                onChange={(e) => setValorTotalEditavel(parseFloat(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <p className="text-xs text-gray-600 mt-1">
                Valor original: <MoneyCell value={calcularTotalSelecionado()} />
              </p>
            </div>

            {/* Forma de Pagamento */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💳 Forma de Pagamento <span className="text-red-500">*</span>
              </label>
              <select
                value={formaPagamento}
                onChange={(e) => setFormaPagamento(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Selecione...</option>
                {formasPagamentoDisponiveis.map((fp) => (
                  <option key={fp.id} value={fp.id}>
                    {fp.nome}
                  </option>
                ))}
              </select>
            </div>

            {/* Conta Bancária */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🏦 Conta Bancária <span className="text-red-500">*</span>
              </label>
              <select
                value={contaBancariaId}
                onChange={(e) => setContaBancariaId(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Selecione...</option>
                {contasBancarias.map((cb) => (
                  <option key={cb.id} value={cb.id}>
                    {cb.nome} ({cb.banco}) - Saldo: {formatarMoeda(cb.saldo || 0)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Observações */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">📝 Observações</label>
          <textarea
            value={observacaoFechamento}
            onChange={(e) => setObservacaoFechamento(e.target.value)}
            rows={3}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Observações sobre o fechamento..."
          />
        </div>

        {/* Botões de Ação */}
        <div className="flex gap-3">
          <button
            onClick={fecharModalFechamento}
            disabled={loadingFechamento}
            className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={confirmarFechamento}
            disabled={
              loadingFechamento ||
              !dataPagamento ||
              (tipoPagamento === "com_pagamento" && (!formaPagamento || !contaBancariaId))
            }
            className={`flex-1 px-4 py-2 rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2 ${
              tipoPagamento === "com_pagamento"
                ? "bg-green-600 hover:bg-green-700"
                : "bg-blue-600 hover:bg-blue-700"
            } text-white`}
          >
            {loadingFechamento ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Processando...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                {tipoPagamento === "com_pagamento" ? "💰 Fechar e Pagar" : "📋 Fechar sem Pagar"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
