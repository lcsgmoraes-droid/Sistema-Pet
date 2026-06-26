import {
  AlertCircle,
  AlertTriangle,
  Calculator,
  CheckCircle,
  DollarSign,
  Receipt,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import CurrencyInput from "../CurrencyInput";
import {
  CashCountPanel,
  DifferenceTipsModal,
  PaymentBreakdownPanel,
} from "./ModalFecharCaixaPanels";

export default function ModalFecharCaixaContent({
  calcularTotalNotas,
  atualizarQuantidadeNota,
  atualizarValorMoedas,
  aplicarContagem,
  limparContagem,
  carregarVendasForma,
  confirmandoDiferenca,
  diferenca,
  erro,
  executarFechamento,
  formaExpandida,
  handleFechar,
  loadingVendas,
  mostrarContagem,
  mostrarDicasDiferenca,
  notas,
  observacoes,
  onClose,
  resumo,
  salvando,
  setConfirmandoDiferenca,
  setFormaExpandida,
  setMostrarContagem,
  setMostrarDicasDiferenca,
  setObservacoes,
  setValorContado,
  sucesso,
  valorContado,
  vendasDetalhe,
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-red-600 to-orange-600 text-white p-6 rounded-t-lg">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold flex items-center">
                  <Receipt className="w-7 h-7 mr-3" />
                  Fechar Caixa
                </h2>
                <p className="text-red-100 mt-1">
                  Caixa #{resumo.caixa.numero_caixa} - {resumo.caixa.usuario_nome}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Conteúdo */}
          <div className="p-6 space-y-6">
            {/* Resumo do Caixa */}
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-6 border-2 border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <Calculator className="w-5 h-5 mr-2 text-gray-700" />
                  Resumo do Movimento
                </h3>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Abertura */}
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-600 mb-1">Valor de Abertura</div>
                  <div className="text-2xl font-bold text-gray-900">
                    R$ {resumo.caixa.valor_abertura.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(resumo.caixa.data_abertura).toLocaleString("pt-BR")}
                  </div>
                </div>

                {/* Entradas (renomeado de Vendas) */}
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <div className="flex items-center text-sm text-green-700 mb-1">
                    <Receipt className="w-4 h-4 mr-1" />
                    Entradas
                  </div>
                  <div className="text-2xl font-bold text-green-600">
                    + R$ {resumo.totais.vendas.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Movimento de entrada</div>
                </div>

                {/* Suprimentos */}
                <div className="bg-white rounded-lg p-4 border border-blue-200">
                  <div className="flex items-center text-sm text-blue-700 mb-1">
                    <TrendingUp className="w-4 h-4 mr-1" />
                    Suprimentos
                  </div>
                  <div className="text-2xl font-bold text-blue-600">
                    + R$ {resumo.totais.suprimentos.toFixed(2)}
                  </div>
                </div>

                {/* Sangrias */}
                <div className="bg-white rounded-lg p-4 border border-orange-200">
                  <div className="flex items-center text-sm text-orange-700 mb-1">
                    <TrendingDown className="w-4 h-4 mr-1" />
                    Sangrias
                  </div>
                  <div className="text-2xl font-bold text-orange-600">
                    - R$ {resumo.totais.sangrias.toFixed(2)}
                  </div>
                </div>

                {/* Despesas */}
                <div className="bg-white rounded-lg p-4 border border-red-200">
                  <div className="flex items-center text-sm text-red-700 mb-1">
                    <DollarSign className="w-4 h-4 mr-1" />
                    Despesas
                  </div>
                  <div className="text-2xl font-bold text-red-600">
                    - R$ {resumo.totais.despesas.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {/* Valor Contado */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-gray-900">
                  Valor Contado no Caixa *
                </label>
                <button
                  type="button"
                  onClick={() => setMostrarContagem(!mostrarContagem)}
                  className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors border border-blue-200"
                  title="Auxiliar na contagem de notas"
                >
                  <Calculator className="w-4 h-4" />
                  <span>Auxiliar Contagem</span>
                </button>
              </div>

              <CashCountPanel
                aplicarContagem={aplicarContagem}
                atualizarQuantidadeNota={atualizarQuantidadeNota}
                atualizarValorMoedas={atualizarValorMoedas}
                calcularTotalNotas={calcularTotalNotas}
                limparContagem={limparContagem}
                mostrarContagem={mostrarContagem}
                notas={notas}
                setMostrarContagem={setMostrarContagem}
              />

              <div className="relative">
                <DollarSign className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <CurrencyInput
                  value={valorContado}
                  onChange={setValorContado}
                  className="w-full pl-10 pr-4 py-3 text-lg font-semibold border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0,00"
                  autoFocus
                />
              </div>

              {/* Diferença */}
              {valorContado !== null &&
                valorContado !== undefined &&
                Math.abs(diferenca) > 0.01 && (
                  <button
                    type="button"
                    onClick={() => setMostrarDicasDiferenca(true)}
                    className={`mt-3 w-full p-4 rounded-lg border-2 text-left hover:opacity-90 transition-opacity ${
                      diferenca > 0
                        ? "bg-blue-50 border-blue-300"
                        : "bg-yellow-50 border-yellow-300"
                    }`}
                    title="Clique para ver possíveis causas"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-900">
                        {diferenca > 0 ? "⚠️ Sobra" : "⚠️ Falta"}:
                      </span>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xl font-bold ${
                            diferenca > 0 ? "text-blue-600" : "text-yellow-700"
                          }`}
                        >
                          R$ {Math.abs(diferenca).toFixed(2)}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            diferenca > 0
                              ? "bg-blue-200 text-blue-800"
                              : "bg-yellow-200 text-yellow-800"
                          }`}
                        >
                          Ver possíveis causas →
                        </span>
                      </div>
                    </div>
                  </button>
                )}

              {valorContado !== null &&
                valorContado !== undefined &&
                Math.abs(diferenca) <= 0.01 && (
                  <div className="mt-3 p-4 rounded-lg border-2 bg-green-50 border-green-300">
                    <div className="flex items-center justify-center space-x-2 text-green-700 font-semibold">
                      <span className="text-2xl">✓</span>
                      <span>Caixa conferido - Valores corretos!</span>
                    </div>
                  </div>
                )}
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Observações (opcional)
              </label>
              <textarea
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Adicione observações sobre o fechamento..."
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />
            </div>

            {/* 📊 Vendas por Forma de Pagamento - INFORMATIVO */}
            <PaymentBreakdownPanel
              carregarVendasForma={carregarVendasForma}
              formaExpandida={formaExpandida}
              loadingVendas={loadingVendas}
              resumo={resumo}
              setFormaExpandida={setFormaExpandida}
              vendasDetalhe={vendasDetalhe}
            />

            {/* Mensagem de erro da API */}
            {erro && (
              <div className="bg-red-50 border-2 border-red-400 rounded-xl p-4 flex items-start space-x-3">
                <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-red-800 text-sm mb-1">
                    Não foi possível fechar o caixa
                  </div>
                  <div className="text-red-700 text-sm">{erro}</div>
                </div>
              </div>
            )}

            {/* Mensagem de sucesso */}
            {sucesso && (
              <div className="bg-green-50 border-2 border-green-400 rounded-xl p-4 flex items-center space-x-3">
                <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
                <div className="font-bold text-green-800">Caixa fechado com sucesso!</div>
              </div>
            )}

            {/* Botões / Confirmação de diferença */}
            {confirmandoDiferenca ? (
              <div className="pt-4 border-t">
                <div className="bg-amber-50 border-2 border-amber-400 rounded-xl p-4 mb-3">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold text-amber-800">Diferença de caixa detectada</div>
                      <div className="text-amber-700 text-sm mt-1">
                        Existe uma diferença de <strong>R$ {Math.abs(diferenca).toFixed(2)}</strong>{" "}
                        <strong>{diferenca > 0 ? "a mais" : "a menos"}</strong> no caixa. A
                        diferença ficará registrada no histórico.
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => setConfirmandoDiferenca(false)}
                    disabled={salvando}
                    className="flex-1 px-4 py-3 border-2 border-amber-300 text-amber-700 rounded-lg hover:bg-amber-100 font-semibold transition-colors disabled:opacity-50"
                  >
                    Voltar e corrigir
                  </button>
                  <button
                    type="button"
                    onClick={executarFechamento}
                    disabled={salvando}
                    className="flex-1 px-4 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    {salvando ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        <span>Fechando...</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4" />
                        <span>Sim, fechar com diferença</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={salvando}
                  className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleFechar}
                  disabled={
                    salvando ||
                    valorContado === null ||
                    valorContado === undefined ||
                    valorContado === ""
                  }
                  className="px-8 py-3 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {salvando ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      <span>Fechando...</span>
                    </>
                  ) : (
                    <>
                      <Receipt className="w-5 h-5" />
                      <span>Fechar Caixa</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <DifferenceTipsModal
        diferenca={diferenca}
        mostrarDicasDiferenca={mostrarDicasDiferenca}
        resumo={resumo}
        setMostrarDicasDiferenca={setMostrarDicasDiferenca}
        valorContado={valorContado}
      />
    </>
  );
}
