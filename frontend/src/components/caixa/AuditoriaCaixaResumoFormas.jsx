import { formatMoneyBRL } from "../../utils/formatters";
import { rotuloFormaPagamento } from "../../utils/pdvPaymentDisplay";

export default function AuditoriaCaixaResumoFormas({ titulo, descricao, formas = {} }) {
  return (
    <section className="rounded-lg border p-3">
      <h3 className="text-sm font-semibold">{titulo}</h3>
      <p className="mt-1 text-xs text-gray-600">{descricao}</p>
      <div className="mt-2 space-y-1">
        {Object.entries(formas).map(([forma, dados]) => (
          <p key={forma} className="flex flex-wrap justify-between gap-2 text-sm">
            <span>{rotuloFormaPagamento({ forma_pagamento: forma })}</span>
            <span className="font-medium">{formatMoneyBRL(dados.total)}</span>
          </p>
        ))}
        {Object.keys(formas).length === 0 && (
          <p className="text-sm text-gray-500">Sem registros.</p>
        )}
      </div>
    </section>
  );
}
