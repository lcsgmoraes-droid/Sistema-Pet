import { X } from "lucide-react";

import { safeArray } from "../../utils/safeArray";
import ActionButton from "../ui/ActionButton";

export default function ContasPagarPagamentoLoteModal({
  aberto,
  contasSelecionadasObjetos,
  contasBancarias,
  dadosPagamentoLote,
  formasPagamento,
  formatarMoeda,
  handleFormaPagamentoLoteChange,
  onClose,
  onConfirmar,
  saldoTotalPagamentoLote,
  setDadosPagamentoLote,
}) {
  if (!aberto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="mx-4 w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b p-4">
          <div>
            <h5 className="text-xl font-bold">Pagamento em lote</h5>
            <p className="text-sm text-gray-500">
              {contasSelecionadasObjetos.length} lancamento(s) selecionado(s)
            </p>
          </div>
          <ActionButton
            intent="neutral"
            tone="ghost"
            size="sm"
            icon={X}
            aria-label="Fechar pagamento em lote"
            onClick={onClose}
          />
        </div>

        <div className="space-y-4 p-6">
          <div className="rounded border border-green-200 bg-green-50 p-3">
            <strong>Saldo total selecionado:</strong> {formatarMoeda(saldoTotalPagamentoLote)}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Data do pagamento *</label>
              <input
                type="date"
                className="w-full rounded border border-gray-300 px-3 py-2"
                value={dadosPagamentoLote.data_pagamento}
                onChange={(e) =>
                  setDadosPagamentoLote({
                    ...dadosPagamentoLote,
                    data_pagamento: e.target.value,
                  })
                }
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Forma de pagamento</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2"
                value={dadosPagamentoLote.forma_pagamento_id || ""}
                onChange={(e) => handleFormaPagamentoLoteChange(e.target.value)}
              >
                <option value="">Selecione...</option>
                {safeArray(formasPagamento).map((forma) => (
                  <option key={forma.id} value={forma.id}>
                    {forma.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="mb-1 block text-sm font-medium">Conta bancaria</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2"
                value={dadosPagamentoLote.conta_bancaria_id || ""}
                onChange={(e) =>
                  setDadosPagamentoLote({
                    ...dadosPagamentoLote,
                    conta_bancaria_id: parseInt(e.target.value, 10) || "",
                  })
                }
              >
                <option value="">Sem movimentar conta bancaria</option>
                {safeArray(contasBancarias).map((conta) => (
                  <option key={conta.id} value={conta.id}>
                    {conta.nome} - {formatarMoeda(conta.saldo_atual || 0)}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="mb-1 block text-sm font-medium">Observacoes</label>
              <textarea
                className="w-full rounded border border-gray-300 px-3 py-2"
                rows="3"
                value={dadosPagamentoLote.observacoes}
                onChange={(e) =>
                  setDadosPagamentoLote({
                    ...dadosPagamentoLote,
                    observacoes: e.target.value,
                  })
                }
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 border-t p-4">
          <ActionButton intent="neutral" tone="soft" size="md" onClick={onClose}>
            Cancelar
          </ActionButton>
          <ActionButton intent="create" size="md" onClick={onConfirmar}>
            Confirmar pagamentos
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
