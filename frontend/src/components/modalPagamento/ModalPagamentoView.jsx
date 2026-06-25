import { X, CreditCard, CheckCircle, AlertCircle } from "lucide-react";

import StatusMargemIndicador from "../StatusMargemIndicador";
import ModalAdicionarCredito from "../ModalAdicionarCredito";
import ModalPagamentoResumoLateral from "../ModalPagamentoResumoLateral";
import ModalPagamentoFormaPanel from "./ModalPagamentoFormaPanel";

export default function ModalPagamentoView({
  venda,
  onClose,
  modalPagamentoContentRef,
  formaPagamentoSelecionada,
  setFormaPagamentoSelecionada,
  numeroParcelas,
  setNumeroParcelas,
  setBandeira,
  setNsuCartao,
  setValorRecebido,
  valorRestante,
  saldoCashback,
  formasPagamento,
  valorRecebido,
  bandeira,
  nsuCartao,
  operadoras,
  operadoraSelecionada,
  setOperadoraSelecionada,
  troco,
  opcaoExcedente,
  setOpcaoExcedente,
  opcoesParcelamentoRef,
  estiloVisualParcelamento,
  valorTotal,
  valorPago,
  moduloCampanhasAtivo,
  loadingBeneficiosCampanha,
  carimbosPrevistos,
  cashbackPrevisto,
  recompraPrevista,
  pagamentosExistentes,
  pagamentos,
  loading,
  excluirPagamentoExistente,
  removerPagamento,
  statusMargem,
  statusMargemRef,
  loadingStatusMargem,
  sugestaoPix,
  faixasParcelamento,
  simulacoesParcelamento,
  loadingSimulacao,
  mostrarCampoJustificativa,
  justificativaRef,
  descricaoCupomMargem,
  justificativaTextareaRef,
  justificativaTexto,
  setJustificativaTexto,
  erroJustificativa,
  setErroJustificativa,
  setErro,
  erro,
  adicionarPagamento,
  mostrarBotaoAdicionarRodape,
  handleFinalizar,
  podeConfirmarFinalizacao,
  mostrarModalCreditoExcedente,
  setMostrarModalCreditoExcedente,
  valorExcedente,
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <CreditCard className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Registrar Recebimento</h2>
                <p className="text-sm text-gray-500">Selecione as formas de pagamento</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div ref={modalPagamentoContentRef} className="flex-1 overflow-y-auto p-6">
            <div className="grid grid-cols-2 gap-6">
              <ModalPagamentoFormaPanel
                venda={venda}
                formaPagamentoSelecionada={formaPagamentoSelecionada}
                setFormaPagamentoSelecionada={setFormaPagamentoSelecionada}
                setNumeroParcelas={setNumeroParcelas}
                setBandeira={setBandeira}
                setNsuCartao={setNsuCartao}
                setValorRecebido={setValorRecebido}
                valorRestante={valorRestante}
                saldoCashback={saldoCashback}
                formasPagamento={formasPagamento}
                valorRecebido={valorRecebido}
                troco={troco}
                opcaoExcedente={opcaoExcedente}
                setOpcaoExcedente={setOpcaoExcedente}
                operadoras={operadoras}
                operadoraSelecionada={operadoraSelecionada}
                setOperadoraSelecionada={setOperadoraSelecionada}
                numeroParcelas={numeroParcelas}
                bandeira={bandeira}
                nsuCartao={nsuCartao}
                opcoesParcelamentoRef={opcoesParcelamentoRef}
                estiloVisualParcelamento={estiloVisualParcelamento}
                simulacoesParcelamento={simulacoesParcelamento}
                adicionarPagamento={adicionarPagamento}
              />

              {/* Coluna Direita - Resumo */}
              <div className="space-y-6">
                <ModalPagamentoResumoLateral
                  valorTotal={valorTotal}
                  valorPago={valorPago}
                  valorRestante={valorRestante}
                  moduloCampanhasAtivo={moduloCampanhasAtivo}
                  clienteId={venda.cliente?.id}
                  loadingBeneficiosCampanha={loadingBeneficiosCampanha}
                  carimbosPrevistos={carimbosPrevistos}
                  cashbackPrevisto={cashbackPrevisto}
                  recompraPrevista={recompraPrevista}
                  pagamentosExistentes={pagamentosExistentes}
                  pagamentos={pagamentos}
                  loading={loading}
                  excluirPagamentoExistente={excluirPagamentoExistente}
                  removerPagamento={removerPagamento}
                />

                {/* ✅ Indicador de Status de Margem Operacional (movido para cá) */}
                {statusMargem && (
                  <div ref={statusMargemRef}>
                    <StatusMargemIndicador status={statusMargem} loading={loadingStatusMargem} />
                  </div>
                )}

                {/* 💡 Sugestão PIX — aparece quando forma atual NÃO é PIX e há margem para oferecer desconto */}
                {sugestaoPix && (
                  <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border-2 border-emerald-300 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">💡</span>
                      <div className="flex-1">
                        <div className="font-bold text-emerald-900 text-sm mb-1">
                          Ofereça desconto no PIX
                        </div>
                        <div className="text-sm text-emerald-800">
                          Você pode oferecer{" "}
                          <span className="font-bold text-emerald-700 text-base">
                            {sugestaoPix.percentual_sugerido}% de desconto
                          </span>{" "}
                          se o cliente pagar no PIX.
                        </div>
                        {sugestaoPix.modo === "comparativo_cartao" ? (
                          <div className="text-xs text-emerald-700 mt-1">
                            Cliente pagaria{" "}
                            <strong>
                              R${" "}
                              {sugestaoPix.total_com_desconto?.toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </strong>
                            {sugestaoPix.economia_cliente > 0 && (
                              <>
                                {" "}
                                · cliente economiza{" "}
                                <strong>
                                  R${" "}
                                  {sugestaoPix.economia_cliente?.toLocaleString("pt-BR", {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })}
                                </strong>
                              </>
                            )}{" "}
                            · você recebe mais do que pelo cartão (
                            <strong>
                              R${" "}
                              {sugestaoPix.liquido_cartao?.toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </strong>
                            )
                          </div>
                        ) : (
                          <div className="text-xs text-emerald-700 mt-1">
                            Cliente pagaria{" "}
                            <strong>
                              R${" "}
                              {sugestaoPix.total_com_desconto?.toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </strong>{" "}
                            · sua margem ficaria em{" "}
                            <strong>~{sugestaoPix.margem_final_estimada}%</strong> (mínimo:{" "}
                            {sugestaoPix.margem_minima}%)
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* 🆕 PASSO 3️⃣ - Exibir faixas de parcelamento recomendadas */}
                {/* Mostrar SEMPRE que houver faixas calculadas (não depende de seleção) */}
                {faixasParcelamento && Object.keys(simulacoesParcelamento).length > 0 && (
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-4">
                    <h4 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
                      <span className="text-xl">📊</span>
                      <span>Parcelamento Recomendado</span>
                    </h4>

                    {loadingSimulacao ? (
                      <div className="text-center py-4">
                        <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                        <p className="text-sm text-blue-700 mt-2">Analisando opções...</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {faixasParcelamento.saudavel.max > 0 && (
                          <div className="flex items-start space-x-3 p-3 bg-green-100 border border-green-300 rounded-lg">
                            <div className="text-2xl">🟢</div>
                            <div className="flex-1">
                              <div className="font-medium text-green-900">
                                {faixasParcelamento.saudavel.min === faixasParcelamento.saudavel.max
                                  ? `${faixasParcelamento.saudavel.max}x`
                                  : `${faixasParcelamento.saudavel.min}x a ${faixasParcelamento.saudavel.max}x`}
                                <span className="ml-2 text-sm font-normal">- Saudável</span>
                              </div>
                              <div className="text-xs text-green-700 mt-1">
                                Margem adequada, sem restrições
                              </div>
                            </div>
                          </div>
                        )}

                        {faixasParcelamento.alerta.max >= faixasParcelamento.alerta.min &&
                          faixasParcelamento.alerta.min > 0 && (
                            <div className="flex items-start space-x-3 p-3 bg-yellow-100 border border-yellow-300 rounded-lg">
                              <div className="text-2xl">🟡</div>
                              <div className="flex-1">
                                <div className="font-medium text-yellow-900">
                                  {faixasParcelamento.alerta.min === faixasParcelamento.alerta.max
                                    ? `${faixasParcelamento.alerta.max}x`
                                    : `${faixasParcelamento.alerta.min}x a ${faixasParcelamento.alerta.max}x`}
                                  <span className="ml-2 text-sm font-normal">- Atenção</span>
                                </div>
                                <div className="text-xs text-yellow-700 mt-1">
                                  Margem próxima ao mínimo, evite se possível
                                </div>
                              </div>
                            </div>
                          )}

                        {faixasParcelamento.proibido.min <=
                          (formaPagamentoSelecionada?.parcelas_maximas ?? 12) && (
                          <div className="flex items-start space-x-3 p-3 bg-red-100 border border-red-300 rounded-lg">
                            <div className="text-2xl">🔴</div>
                            <div className="flex-1">
                              <div className="font-medium text-red-900">
                                {faixasParcelamento.proibido.min}x ou mais
                                <span className="ml-2 text-sm font-normal">
                                  - Exige justificativa
                                </span>
                              </div>
                              <div className="text-xs text-red-700 mt-1">
                                Margem crítica, justificativa obrigatória
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 🆕 PASSO 5: Campo de Justificativa Inline (aparece AUTOMATICAMENTE quando margem vermelha) */}
                {mostrarCampoJustificativa && (
                  <div
                    ref={justificativaRef}
                    data-testid="justificativa-margem-obrigatoria"
                    className="bg-red-50 border-2 border-red-300 rounded-lg p-4 scroll-mt-6"
                  >
                    <div className="flex items-start space-x-3 mb-3">
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="font-semibold text-red-900">⚠️ Justificativa Obrigatória</h4>
                        <p className="text-sm text-red-700 mt-1">
                          {descricaoCupomMargem ||
                            "Esta venda tem margem crítica. Informe o motivo para prosseguir."}
                        </p>
                      </div>
                    </div>

                    <textarea
                      ref={justificativaTextareaRef}
                      value={justificativaTexto}
                      onChange={(e) => {
                        setJustificativaTexto(e.target.value);
                        if (e.target.value.trim().length >= 10) {
                          setErroJustificativa("");
                          setErro("");
                        }
                      }}
                      placeholder={
                        descricaoCupomMargem
                          ? "Ex: cupom autorizado pela campanha de fidelidade."
                          : "Ex: Cliente especial, promoção de lançamento, acordo comercial..."
                      }
                      className={`w-full px-3 py-2 border-2 rounded-lg focus:ring-2 focus:ring-red-500 resize-none ${
                        erroJustificativa ? "border-red-500" : "border-red-300"
                      }`}
                      rows={3}
                    />

                    {erroJustificativa && (
                      <p className="text-xs text-red-700 font-medium mt-2">{erroJustificativa}</p>
                    )}

                    <p className="text-xs text-red-600 mt-2">
                      💡 Mínimo 10 caracteres. Depois use o botão "Adicionar Pagamento" no rodapé.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t p-6 bg-gray-50">
            {erro && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-red-700">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm">{erro}</span>
              </div>
            )}

            <div className="flex items-center justify-between gap-3">
              <button
                onClick={onClose}
                disabled={loading}
                className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                Cancelar
              </button>

              <div className="flex items-center gap-3">
                {mostrarBotaoAdicionarRodape && (
                  <button
                    type="button"
                    data-testid="modal-pagamento-footer-adicionar"
                    onClick={adicionarPagamento}
                    disabled={loading}
                    className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <CheckCircle className="w-5 h-5" />
                    <span>Adicionar Pagamento</span>
                  </button>
                )}

                <button
                  onClick={handleFinalizar}
                  disabled={loading || !podeConfirmarFinalizacao}
                  className="flex items-center space-x-2 px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Processando...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      <span>
                        {pagamentos.length === 0 ? "Confirmar Ajustes" : "Registrar Recebimento"}
                      </span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal de Crédito para excedente */}
      {mostrarModalCreditoExcedente && venda.cliente && (
        <ModalAdicionarCredito
          cliente={venda.cliente}
          valorInicial={valorExcedente}
          motivoPadrao="Crédito de excedente no pagamento"
          onConfirmar={() => setMostrarModalCreditoExcedente(false)}
          onClose={() => setMostrarModalCreditoExcedente(false)}
        />
      )}
    </>
  );
}
