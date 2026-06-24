import { Plus, Trash2, X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import { safeArray } from "../../utils/safeArray";

export default function ContasPagarModals({
  mostrarModalPagamento,
  contaSelecionada,
  setMostrarModalPagamento,
  formatarMoeda,
  dadosPagamento,
  setDadosPagamento,
  handleFormaChange,
  formasPagamento,
  contasBancarias,
  registrarPagamento,
  mostrarModalNovaForma,
  setMostrarModalNovaForma,
  novaFormaData,
  setNovaFormaData,
  salvarNovaForma,
  mostrarModalClassificacao,
  setMostrarModalClassificacao,
  dadosClassificacao,
  setDadosClassificacao,
  categoriasFinanceiras,
  subcategoriasDre,
  tiposDespesaOrdenados,
  salvarClassificacao,
  modalExclusaoRecorrencia,
  setModalExclusaoRecorrencia,
  recorrenciasSelecionadasExclusao,
  setRecorrenciasSelecionadasExclusao,
  formatarData,
  alternarRecorrenciaExclusao,
  confirmarExclusaoRecorrencia,
}) {
  return (
    <>
      {/* Modal de Pagamento */}
      {mostrarModalPagamento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">💰 Registrar Pagamento</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar modal de pagamento"
                onClick={() => setMostrarModalPagamento(false)}
              />
            </div>

            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}
                <br />
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}
                <br />
                <strong>Já Pago:</strong> {formatarMoeda(contaSelecionada.valor_pago)}
                <br />
                <strong>Saldo Restante:</strong>{" "}
                {formatarMoeda(contaSelecionada.valor_final - contaSelecionada.valor_pago)}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Valor a Pagar *</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_pago}
                    onChange={(e) =>
                      setDadosPagamento({
                        ...dadosPagamento,
                        valor_pago: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Data do Pagamento *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.data_pagamento}
                    onChange={(e) =>
                      setDadosPagamento({ ...dadosPagamento, data_pagamento: e.target.value })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Forma de Pagamento</label>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 border border-gray-300 rounded px-3 py-2"
                      value={dadosPagamento.forma_pagamento_id || ""}
                      onChange={(e) => handleFormaChange(e.target.value)}
                    >
                      <option value="">Selecione...</option>
                      {safeArray(formasPagamento).map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.nome}
                        </option>
                      ))}
                    </select>
                    <ActionButton
                      type="button"
                      onClick={() => setMostrarModalNovaForma(true)}
                      title="Adicionar nova forma de pagamento"
                      intent="create"
                      size="sm"
                      icon={Plus}
                    >
                      Nova
                    </ActionButton>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Conta Bancária *
                    {dadosPagamento.forma_pagamento_id &&
                      formasPagamento.find((f) => f.id === dadosPagamento.forma_pagamento_id)
                        ?.conta_bancaria_destino_id && (
                        <span className="text-xs text-gray-500 ml-2">
                          (Padrão da forma selecionada)
                        </span>
                      )}
                  </label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.conta_bancaria_id || ""}
                    onChange={(e) =>
                      setDadosPagamento({
                        ...dadosPagamento,
                        conta_bancaria_id: parseInt(e.target.value) || null,
                      })
                    }
                  >
                    <option value="">Selecione a conta...</option>
                    {safeArray(contasBancarias).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome} - {formatarMoeda(c.saldo_atual || 0)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Juros</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_juros}
                    onChange={(e) =>
                      setDadosPagamento({
                        ...dadosPagamento,
                        valor_juros: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Multa</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_multa}
                    onChange={(e) =>
                      setDadosPagamento({
                        ...dadosPagamento,
                        valor_multa: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Desconto</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_desconto}
                    onChange={(e) =>
                      setDadosPagamento({
                        ...dadosPagamento,
                        valor_desconto: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Observações</label>
                  <textarea
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    rows="3"
                    value={dadosPagamento.observacoes}
                    onChange={(e) =>
                      setDadosPagamento({ ...dadosPagamento, observacoes: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded p-3 mt-4">
                <strong>Valor Final do Pagamento:</strong>{" "}
                {formatarMoeda(
                  (dadosPagamento.valor_pago || 0) +
                    (dadosPagamento.valor_juros || 0) +
                    (dadosPagamento.valor_multa || 0) -
                    (dadosPagamento.valor_desconto || 0),
                )}
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalPagamento(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton intent="create" size="md" onClick={registrarPagamento}>
                Confirmar Pagamento
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nova Forma Rápida */}
      {mostrarModalNovaForma && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="bg-green-600 text-white px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-semibold">Nova Forma de Pagamento</h3>
              <ActionButton
                onClick={() => setMostrarModalNovaForma(false)}
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                className="text-white hover:bg-green-700"
                aria-label="Fechar nova forma de pagamento"
              />
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nome *</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.nome}
                  onChange={(e) => setNovaFormaData({ ...novaFormaData, nome: e.target.value })}
                  placeholder="Ex: PIX Santander, Dinheiro..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Tipo</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.tipo}
                  onChange={(e) => setNovaFormaData({ ...novaFormaData, tipo: e.target.value })}
                >
                  <option value="dinheiro">💵 Dinheiro</option>
                  <option value="pix">📱 PIX</option>
                  <option value="cartao_debito">💳 Cartão Débito</option>
                  <option value="cartao_credito">💳 Cartão Crédito</option>
                  <option value="transferencia">🏦 Transferência</option>
                  <option value="boleto">📄 Boleto</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Conta Bancária Padrão</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.conta_bancaria_destino_id || ""}
                  onChange={(e) =>
                    setNovaFormaData({
                      ...novaFormaData,
                      conta_bancaria_destino_id: parseInt(e.target.value) || null,
                    })
                  }
                >
                  <option value="">Nenhuma (selecionar manualmente)</option>
                  {safeArray(contasBancarias).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Esta conta será pré-selecionada automaticamente ao usar esta forma
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalNovaForma(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton intent="create" size="md" onClick={salvarNovaForma}>
                Criar
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* Modal Classificacao */}
      {mostrarModalClassificacao && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">🏷 Classificar Conta #{contaSelecionada.id}</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar classificação"
                onClick={() => setMostrarModalClassificacao(false)}
              />
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Categoria Financeira</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.categoria_id || ""}
                  onChange={(e) =>
                    setDadosClassificacao({
                      ...dadosClassificacao,
                      categoria_id: e.target.value ? parseInt(e.target.value, 10) : null,
                      dre_subcategoria_id: null,
                    })
                  }
                >
                  <option value="">Selecione...</option>
                  {safeArray(categoriasFinanceiras).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Subcategoria DRE</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.dre_subcategoria_id || ""}
                  onChange={(e) =>
                    setDadosClassificacao({
                      ...dadosClassificacao,
                      dre_subcategoria_id: e.target.value ? parseInt(e.target.value, 10) : null,
                    })
                  }
                >
                  <option value="">Selecione...</option>
                  {safeArray(subcategoriasDre)
                    .filter((s) => s.categoria_financeira_id === dadosClassificacao.categoria_id)
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.nome}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Tipo de despesa</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.tipo_despesa_id || ""}
                  onChange={(e) =>
                    setDadosClassificacao({
                      ...dadosClassificacao,
                      tipo_despesa_id: e.target.value ? parseInt(e.target.value, 10) : null,
                    })
                  }
                >
                  <option value="">Selecione...</option>
                  {tiposDespesaOrdenados.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Canal</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.canal || "loja_fisica"}
                  onChange={(e) =>
                    setDadosClassificacao({ ...dadosClassificacao, canal: e.target.value })
                  }
                >
                  <option value="loja_fisica">Loja Física</option>
                  <option value="mercado_livre">Mercado Livre</option>
                  <option value="shopee">Shopee</option>
                  <option value="amazon">Amazon</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalClassificacao(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton intent="warning" size="md" onClick={salvarClassificacao}>
                Salvar Classificação
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {modalExclusaoRecorrencia.aberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <div>
                <h5 className="text-xl font-bold">Lançamentos da recorrência</h5>
                <p className="text-sm text-gray-500">
                  Selecione quais lançamentos sem pagamento devem ser excluídos.
                </p>
              </div>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar exclusao de recorrencia"
                onClick={() => {
                  setModalExclusaoRecorrencia({
                    aberto: false,
                    conta: null,
                    itens: [],
                    loading: false,
                  });
                  setRecorrenciasSelecionadasExclusao([]);
                }}
              />
            </div>

            <div className="max-h-[60vh] overflow-y-auto p-4">
              {modalExclusaoRecorrencia.loading ? (
                <p className="py-8 text-center text-gray-500">Carregando lançamentos...</p>
              ) : (
                <div className="space-y-2">
                  {safeArray(modalExclusaoRecorrencia.itens).map((item) => {
                    const selecionado = recorrenciasSelecionadasExclusao.includes(item.id);
                    return (
                      <label
                        key={item.id}
                        className={`flex items-center gap-3 rounded-lg border p-3 ${
                          item.pode_excluir
                            ? "border-gray-200 bg-white"
                            : "border-gray-100 bg-gray-50 opacity-70"
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={!item.pode_excluir}
                          checked={selecionado}
                          onChange={() => alternarRecorrenciaExclusao(item.id)}
                          className="h-4 w-4"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-gray-900">#{item.id}</span>
                            {item.eh_origem && (
                              <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">
                                Origem
                              </span>
                            )}
                            <span className="text-sm text-gray-500">
                              {formatarData(item.data_vencimento)}
                            </span>
                            <span className="text-sm font-semibold text-gray-900">
                              {formatarMoeda(item.valor_final)}
                            </span>
                          </div>
                          <p className="mt-1 truncate text-sm text-gray-700" title={item.descricao}>
                            {item.descricao}
                          </p>
                          {item.motivo_bloqueio && (
                            <p className="mt-1 text-xs text-red-600">{item.motivo_bloqueio}</p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t p-4 md:flex-row md:items-center md:justify-between">
              <p className="text-sm text-gray-500">
                {recorrenciasSelecionadasExclusao.length} lançamento(s) selecionado(s)
              </p>
              <div className="flex justify-end gap-3">
                <ActionButton
                  intent="neutral"
                  tone="soft"
                  size="md"
                  onClick={() => {
                    setModalExclusaoRecorrencia({
                      aberto: false,
                      conta: null,
                      itens: [],
                      loading: false,
                    });
                    setRecorrenciasSelecionadasExclusao([]);
                  }}
                >
                  Cancelar
                </ActionButton>
                <ActionButton
                  intent="delete"
                  size="md"
                  icon={Trash2}
                  disabled={recorrenciasSelecionadasExclusao.length === 0}
                  onClick={confirmarExclusaoRecorrencia}
                >
                  Excluir selecionados
                </ActionButton>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
