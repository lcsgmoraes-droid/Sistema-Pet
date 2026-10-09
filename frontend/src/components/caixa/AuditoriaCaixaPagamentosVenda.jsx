import { descricaoFormaPagamento } from "../../utils/pdvPaymentDisplay";
import { formatMoneyBRL } from "../../utils/formatters";
import { chaveFormaAuditoria, pagamentosVendaAuditoria } from "../../utils/auditoriaCaixaUtils";

const formatarData = (data) =>
  data ? new Date(data).toLocaleString("pt-BR") : "Data não informada";

export default function AuditoriaCaixaPagamentosVenda({ venda, caixaId }) {
  const pagamentos = pagamentosVendaAuditoria(venda);
  const recebimentos = venda.recebimentos || [];
  return (
    <div className="mt-3 grid gap-3 md:grid-cols-2">
      <section className="rounded border bg-gray-50 p-3">
        <h3 className="text-sm font-semibold">Pagamentos registrados da venda</h3>
        {pagamentos.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">Sem pagamentos registrados.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {pagamentos.map((pagamento, indice) => (
              <li
                key={`${pagamento.tipo || "pagamento"}:${pagamento.id ?? indice}`}
                className="text-sm"
              >
                <div className="flex flex-wrap justify-between gap-2 font-medium">
                  <span>
                    {descricaoFormaPagamento(pagamento)}
                    {pagamento.intervalo_crediario || chaveFormaAuditoria(pagamento) === "crediario"
                      ? " (plano a prazo)"
                      : ""}
                  </span>
                  <span>{formatMoneyBRL(pagamento.valor)}</span>
                </div>
                <p className="text-xs text-gray-600">
                  {formatarData(pagamento.data_pagamento || pagamento.data_recebimento)}
                  {pagamento.status ? ` · Status do registro: ${pagamento.status}` : ""}
                </p>
                {pagamento.caixa_id == null ? (
                  <p className="text-xs text-amber-700">Caixa não informado neste registro.</p>
                ) : Number(pagamento.caixa_id) === Number(caixaId) ? (
                  <p className="text-xs text-blue-700">Vinculado a este caixa.</p>
                ) : (
                  <p className="text-xs text-gray-600">Vinculado a outro caixa.</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="rounded border bg-blue-50 p-3">
        <h3 className="text-sm font-semibold">Lançamentos vinculados a este caixa</h3>
        <p className="mt-1 text-xs text-gray-600">
          Recebimentos vinculados e movimentos em dinheiro desta venda.
        </p>
        {recebimentos.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">Sem lançamentos vinculados a este caixa.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {recebimentos.map((item) => (
              <li key={`${item.tipo}:${item.id}`} className="text-sm">
                <div className="flex flex-wrap justify-between gap-2 font-medium">
                  <span>{descricaoFormaPagamento(item)}</span>
                  <span>{formatMoneyBRL(item.valor)}</span>
                </div>
                <p className="text-xs text-gray-600">{formatarData(item.data_recebimento)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
