import { formatMoneyBRL } from "../../utils/formatters";

function informado(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

export default function IfoodVendaTaxasResumo({ financeiro, resumo = false }) {
  if (!financeiro) return null;
  const cobrancas = Array.isArray(financeiro.charges) ? financeiro.charges : [];
  const pendencias = Array.isArray(financeiro.pending_components)
    ? financeiro.pending_components
    : [];
  const checkout = financeiro.checkout || {};
  const simulacao = Boolean(financeiro.simulated);
  const classificadas = cobrancas.some((cobranca) => informado(cobranca.amount));

  return (
    <section
      className="mb-3 w-full rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-700 dark:bg-slate-900"
      style={{ maxWidth: "min(56rem, calc(100vw - 4rem))" }}
      aria-label={resumo ? "Cobranças iFood do período" : "Cobranças iFood desta venda"}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-semibold text-slate-900 dark:text-slate-100">
          {resumo ? "Cobranças iFood do período" : "Cobranças iFood desta venda"}
        </h4>
        <span
          className={`rounded-full px-2 py-1 text-xs font-semibold ${
            simulacao
              ? "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200"
              : financeiro.complete
                ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
                : "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
          }`}
        >
          {simulacao
            ? `Simulação em DEV${financeiro.simulation_complete ? " · apuração completa" : ""}`
            : financeiro.complete
              ? "Cobranças recebidas"
              : "Apuração parcial"}
        </span>
      </div>
      {simulacao && (
        <p className="mt-2 text-xs font-medium text-violet-800 dark:text-violet-200">
          Valores fictícios para testar o preenchimento. Não representam cobranças reais nem margem
          final da loja.
        </p>
      )}
      <dl className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
        {cobrancas.map((cobranca, indice) => (
          <div
            key={`${cobranca.code}-${cobranca.snapshot_id || "resumo"}-${cobranca.position ?? indice}`}
            className="flex flex-wrap items-start justify-between gap-2 py-2"
          >
            <dt className="text-slate-700 dark:text-slate-200">
              {cobranca.label || cobranca.code}
              {(cobranca.status === "unclassified" || !informado(cobranca.amount)) && (
                <span className="ml-2 text-xs text-amber-800 dark:text-amber-300">
                  Não classificado
                </span>
              )}
            </dt>
            <dd className="font-semibold tabular-nums text-slate-900 dark:text-slate-100">
              {informado(cobranca.amount)
                ? formatMoneyBRL(Number(cobranca.amount))
                : informado(cobranca.signed_amount)
                  ? `${formatMoneyBRL(Number(cobranca.signed_amount))} (valor observado)`
                  : "Valor não informado"}
            </dd>
          </div>
        ))}
        {pendencias.map((pendencia, indice) => (
          <div
            key={`pending-${pendencia.code}-${indice}`}
            className="flex flex-wrap justify-between gap-2 py-2"
          >
            <dt className="text-slate-700 dark:text-slate-200">
              {pendencia.label || pendencia.code}
              {pendencia.reason && (
                <p className="mt-0.5 max-w-2xl text-xs text-slate-500 dark:text-slate-400">
                  {pendencia.reason}
                </p>
              )}
            </dt>
            <dd className="text-xs font-semibold text-amber-800 dark:text-amber-300">
              {["ORDER_COMMISSION", "PAYMENT_TRANSACTION_FEE"].includes(pendencia.code)
                ? "Aguardando Financial"
                : "Conferência pendente"}
            </dd>
          </div>
        ))}
      </dl>
      {cobrancas.length === 0 && (
        <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
          Nenhuma cobrança recebida nesta apuração.
        </p>
      )}
      {classificadas && informado(financeiro.fee_known_total) && (
        <p className="mt-3 border-t border-slate-200 pt-3 font-semibold text-slate-900 dark:border-slate-700 dark:text-slate-100">
          {financeiro.complete ? "Total das cobranças" : "Total classificado até agora"}:{" "}
          {formatMoneyBRL(Number(financeiro.fee_known_total))}
        </p>
      )}
      {!resumo && (informado(checkout.delivery_fee) || informado(checkout.ifood_service_fee)) && (
        <div className="mt-3 rounded-md bg-slate-50 p-3 text-xs dark:bg-slate-950">
          {informado(checkout.delivery_fee) && (
            <p className="text-slate-700 dark:text-slate-200">
              Frete cobrado do cliente:{" "}
              <strong>{formatMoneyBRL(Number(checkout.delivery_fee))}</strong>
            </p>
          )}
          {informado(checkout.ifood_service_fee) && (
            <p className="mt-1 text-slate-700 dark:text-slate-200">
              Serviço iFood pago pelo consumidor:{" "}
              <strong>{formatMoneyBRL(Number(checkout.ifood_service_fee))}</strong>
            </p>
          )}
          <p className="mt-2 text-slate-600 dark:text-slate-300">
            O frete cobrado do cliente não comprova o custo da entrega. O serviço pago pelo
            consumidor pertence ao iFood e não é descontado novamente da loja.
          </p>
        </div>
      )}
      <p className="mt-3 text-xs text-slate-600 dark:text-slate-300">
        {pendencias.length > 0
          ? "As cobranças conhecidas continuam visíveis. Novos lançamentos do Financial são cruzados automaticamente com esta venda; pendências de conferência continuam identificadas."
          : "As cobranças recebidas não comprovam, por si só, que o repasse entrou no banco."}
      </p>
    </section>
  );
}
