import { Trash2, Wallet, X } from 'lucide-react';
import { formatBRL, formatMoneyBRL } from '../utils/formatters';

export default function ModalPagamentoResumoLateral({
  valorTotal,
  valorPago,
  valorRestante,
  moduloCampanhasAtivo,
  clienteId,
  loadingBeneficiosCampanha,
  carimbosPrevistos,
  cashbackPrevisto,
  recompraPrevista,
  pagamentosExistentes,
  pagamentos,
  loading,
  excluirPagamentoExistente,
  removerPagamento,
}) {
  return (
    <>
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-semibold text-gray-900 mb-4">Resumo da Venda</h3>

        <div className="space-y-3">
          <div className="flex justify-between text-gray-600">
            <span>Total da Venda:</span>
            <span className="font-medium">R$ {valorTotal.toFixed(2)}</span>
          </div>

          <div className="flex justify-between text-green-600">
            <span>Valor Pago:</span>
            <span className="font-medium">R$ {valorPago.toFixed(2)}</span>
          </div>

          <div className="flex justify-between text-blue-600 text-lg font-semibold border-t pt-3">
            <span>Restante:</span>
            <span>R$ {valorRestante.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {moduloCampanhasAtivo && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <h3 className="font-semibold text-indigo-900 mb-2">Benefícios que esta venda pode gerar</h3>
          <p className="text-xs text-indigo-700 mb-3">
            Prévia para o cliente com base nas campanhas ativas no momento.
          </p>

          {!clienteId ? (
            <p className="text-sm text-indigo-800">Associe um cliente para visualizar os benefícios de campanhas.</p>
          ) : loadingBeneficiosCampanha ? (
            <p className="text-sm text-indigo-800">Carregando campanhas ativas...</p>
          ) : (
            <div className="space-y-1.5 text-sm text-indigo-900">
              {carimbosPrevistos.length > 0 && carimbosPrevistos.map((item) => (
                <div key={`carimbo-modal-${item.campanha}`}>
                  {item.campanha}: esta venda está gerando <strong>{item.quantidade}</strong> carimbo(s).
                </div>
              ))}

              {cashbackPrevisto.length > 0 && cashbackPrevisto.map((item) => (
                <div key={`cashback-modal-${item.campanha}`}>
                  {item.campanha}: cashback previsto de <strong>{formatMoneyBRL(item.valor)}</strong> ({formatBRL(item.percentual)}%).
                </div>
              ))}

              {recompraPrevista.length > 0 && recompraPrevista.map((item) => (
                <div key={`recompra-modal-${item.campanha}`}>
                  {item.campanha}: pode gerar 1 cupom de recompra de
                  <strong> {item.tipo === 'fixed' ? formatMoneyBRL(item.valor) : `${formatBRL(item.valor)}%`}</strong>.
                </div>
              ))}

              {carimbosPrevistos.length === 0 && cashbackPrevisto.length === 0 && recompraPrevista.length === 0 && (
                <div>Nenhum benefício de campanha previsto para esta venda.</div>
              )}
            </div>
          )}
        </div>
      )}

      <div>
        <h3 className="font-semibold text-gray-900 mb-4">
          Formas de Pagamento
        </h3>

        {pagamentosExistentes.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-600 mb-2">
              💰 Pagamentos Registrados ({pagamentosExistentes.length})
            </h4>
            <div className="space-y-2">
              {pagamentosExistentes.map((pag, idx) => (
                <div
                  key={pag.id}
                  className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <div className="font-medium text-gray-900">
                        {pag.forma_pagamento === 'dinheiro' ? '💵 Dinheiro' :
                          pag.forma_pagamento === 'pix' ? '📱 PIX' :
                            pag.forma_pagamento === 'credito' ? '💳 Cartão de Crédito' :
                              pag.forma_pagamento === 'debito' ? '💳 Cartão de Débito' :
                                pag.forma_pagamento === 'boleto' ? '📄 Boleto' :
                                  pag.forma_pagamento}
                      </div>
                      <span className="px-2 py-0.5 bg-green-200 text-green-800 text-xs rounded-full font-medium">
                        Pagamento {idx + 1}
                      </span>
                    </div>
                    {pag.bandeira && (
                      <div className="text-sm text-gray-500 mt-1">Bandeira: {pag.bandeira}</div>
                    )}
                    {pag.nsu_cartao && (
                      <div className="text-sm text-gray-600 mt-1 font-mono">🔢 NSU: {pag.nsu_cartao}</div>
                    )}
                    {pag.numero_parcelas && pag.numero_parcelas > 1 && (
                      <div className="text-sm text-blue-600 mt-1 font-medium">
                        🔢 Parcelado em {pag.numero_parcelas}x de R$ {(parseFloat(pag.valor) / pag.numero_parcelas).toFixed(2)}
                      </div>
                    )}
                    <div className="text-xs text-gray-400 mt-1">
                      📅 {new Date(pag.data_pagamento).toLocaleString('pt-BR')}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <div className="font-semibold text-green-700 text-lg">
                        R$ {parseFloat(pag.valor).toFixed(2)}
                      </div>
                      {pag.troco && parseFloat(pag.troco) > 0 && (
                        <div className="text-xs text-yellow-600">
                          Troco: R$ {parseFloat(pag.troco).toFixed(2)}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => excluirPagamentoExistente(pag.id)}
                      disabled={loading}
                      className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors disabled:opacity-50"
                      title="Excluir pagamento"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {pagamentos.length === 0 && pagamentosExistentes.length === 0 ? (
          <div className="text-center py-8 text-gray-400 bg-gray-50 rounded-lg border-2 border-dashed">
            <Wallet className="w-12 h-12 mx-auto mb-2 opacity-40" />
            <p className="text-sm font-medium">Nenhuma forma de pagamento adicionada</p>
            <p className="text-xs mt-1">Selecione uma forma acima para começar</p>
          </div>
        ) : pagamentos.length > 0 ? (
          <div>
            <h4 className="text-sm font-medium text-gray-600 mb-2">
              ⏳ Novos Pagamentos (a confirmar)
            </h4>
            <div className="space-y-3">
              {pagamentos.map((pag, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    pag.is_cashback
                      ? 'bg-green-50 border-green-200'
                      : 'bg-blue-50 border-blue-200'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <div className="font-medium text-gray-900">{pag.is_cashback ? '💰 ' : ''}{pag.nome}</div>
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        pag.is_cashback
                          ? 'bg-green-200 text-green-800'
                          : 'bg-blue-200 text-blue-800'
                      }`}>
                        {pag.is_cashback ? 'Cashback' : 'Novo'}
                      </span>
                    </div>
                    {pag.bandeira && (
                      <div className="text-sm text-gray-500 mt-1">Bandeira: {pag.bandeira}</div>
                    )}
                    {pag.nsu_cartao && (
                      <div className="text-sm text-gray-600 mt-1 font-mono">🔢 NSU: {pag.nsu_cartao}</div>
                    )}
                    {pag.numero_parcelas > 1 && (
                      <div className="text-sm text-blue-600 mt-1 font-medium">
                        🔢 {pag.numero_parcelas}x de R$ {(pag.valor / pag.numero_parcelas).toFixed(2)}
                      </div>
                    )}
                    {pag.troco && pag.troco > 0 && (
                      <div className="text-sm text-yellow-600 mt-1">
                        💵 Troco: R$ {pag.troco.toFixed(2)}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`font-semibold text-lg ${pag.is_cashback ? 'text-green-700' : 'text-blue-700'}`}>
                      R$ {pag.valor.toFixed(2)}
                    </span>
                    <button
                      onClick={() => removerPagamento(index)}
                      className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                      title="Remover"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
