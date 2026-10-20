import { useId, useState } from "react";
import { ChevronDown, ChevronUp, WalletCards } from "lucide-react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  formatarDataFaturamento,
  periodoFaturamento,
} from "../v2/ResumoFaturamento/faturamentoPresentation";

export default function RecebimentosCaixaPanel({ composicao }) {
  const [expandido, setExpandido] = useState(false);
  const [formaSelecionada, setFormaSelecionada] = useState(null);
  const [limite, setLimite] = useState(20);
  const [creditosExpandidos, setCreditosExpandidos] = useState(false);
  const detalhesId = useId();
  const creditosId = useId();
  if (!composicao) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        O detalhamento dos recebimentos está indisponível. Atualize o caixa.
      </p>
    );
  }
  const formas = Object.entries(composicao.por_forma_pagamento || {});
  const pagamentos = (composicao.detalhes || []).filter(
    (pagamento) => !formaSelecionada || pagamento.forma_pagamento === formaSelecionada,
  );

  const abrirForma = (forma) => {
    setFormaSelecionada((atual) => (atual === forma ? null : forma));
    setLimite(20);
    setExpandido(true);
  };

  return (
    <section className="space-y-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-950/30">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
            <WalletCards className="h-4 w-4" />
            Recebimentos neste caixa
          </h4>
          <p className="mt-1 text-2xl font-bold tabular-nums text-slate-950 dark:text-white">
            {formatMoneyBRL(composicao.total_recebido)}
          </p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            {periodoFaturamento(composicao)} · Somente este caixa
          </p>
        </div>
        <BotaoInteracao
          tamanho="pequeno"
          icon={expandido ? ChevronUp : ChevronDown}
          onClick={() => setExpandido((atual) => !atual)}
          aria-expanded={expandido}
          aria-controls={detalhesId}
          aria-label={`${expandido ? "Ocultar" : "Ver"} detalhes dos recebimentos neste caixa`}
        >
          {expandido ? "Ocultar detalhes" : "Detalhes"}
        </BotaoInteracao>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-300">
        Pagamentos das vendas do período e de vendas anteriores, incluindo parcelas de crediário
        pagas. Crédito do cliente e cashback ficam separados.
      </p>
      <div>
        <h5 className="mb-2 text-sm font-bold text-slate-900 dark:text-white">
          Formas de recebimento
        </h5>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {formas.map(([forma, dados]) => (
            <div
              key={forma}
              className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="min-w-0 text-sm text-slate-800 dark:text-slate-200">
                <p className="font-semibold">{forma}</p>
                <p className="tabular-nums">{formatMoneyBRL(dados.total)}</p>
              </div>
              <BotaoInteracao
                tamanho="pequeno"
                onClick={() => abrirForma(forma)}
                aria-pressed={formaSelecionada === forma}
                aria-label={`Ver recebimentos em ${forma}`}
              >
                Detalhes
              </BotaoInteracao>
            </div>
          ))}
          {formas.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Nenhum recebimento neste caixa.
            </p>
          )}
        </div>
      </div>
      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-slate-900 dark:text-white">
              Créditos e cashback utilizados no caixa
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Quitam vendas, mas não entram no total recebido acima.
            </p>
          </div>
          <strong className="shrink-0 tabular-nums text-slate-900 dark:text-white">
            {formatMoneyBRL(composicao.creditos_utilizados)}
          </strong>
        </div>
        {(composicao.detalhes_creditos || []).length > 0 && (
          <>
            <BotaoInteracao
              tamanho="pequeno"
              onClick={() => setCreditosExpandidos((atual) => !atual)}
              aria-expanded={creditosExpandidos}
              aria-controls={creditosId}
            >
              {creditosExpandidos
                ? "Ocultar créditos utilizados"
                : "Detalhes dos créditos utilizados"}
            </BotaoInteracao>
            {creditosExpandidos && (
              <div id={creditosId} className="max-h-60 space-y-2 overflow-y-auto">
                {composicao.detalhes_creditos.map((credito) => (
                  <div
                    key={credito.id}
                    className="border-t border-slate-200 pt-2 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300"
                  >
                    <p>
                      Venda #{credito.numero_venda || credito.venda_id} · {credito.forma_pagamento}
                    </p>
                    <p>
                      {formatMoneyBRL(credito.valor)} ·{" "}
                      {formatarDataFaturamento(credito.data_recebimento)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
      {expandido && (
        <div
          id={detalhesId}
          className="space-y-3 border-t border-emerald-200 pt-3 dark:border-emerald-800"
        >
          <dl className="space-y-2 text-sm text-slate-700 dark:text-slate-200">
            <div className="flex justify-between gap-3">
              <dt>Vendas do período</dt>
              <dd className="font-semibold tabular-nums">
                {formatMoneyBRL(composicao.vendas_periodo)}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>Vendas anteriores</dt>
              <dd className="font-semibold tabular-nums">
                {formatMoneyBRL(composicao.vendas_anteriores)}
              </dd>
            </div>
            {Number(composicao.devolucoes || 0) !== 0 && (
              <div className="flex justify-between gap-3">
                <dt>Devoluções e estornos</dt>
                <dd className="font-semibold tabular-nums">
                  − {formatMoneyBRL(composicao.devolucoes)}
                </dd>
              </div>
            )}
          </dl>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h5 className="text-sm font-bold text-slate-900 dark:text-white">
              {formaSelecionada
                ? `Recebimentos em ${formaSelecionada}`
                : "Pagamentos que compõem o total"}
            </h5>
            {formaSelecionada && (
              <BotaoInteracao
                tamanho="pequeno"
                onClick={() => {
                  setFormaSelecionada(null);
                  setLimite(20);
                }}
              >
                Ver todas as formas
              </BotaoInteracao>
            )}
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto" role="list">
            {pagamentos.slice(0, limite).map((pagamento, indice) => (
              <div
                key={`${pagamento.tipo}-${pagamento.id}-${indice}`}
                role="listitem"
                className="rounded-lg border border-slate-200 bg-white p-3 text-xs dark:border-slate-700 dark:bg-slate-900"
              >
                <div className="flex justify-between gap-2 text-slate-900 dark:text-white">
                  <strong>
                    Venda #{pagamento.numero_venda || pagamento.venda_id || "sem vínculo"}
                  </strong>
                  <strong className="shrink-0 tabular-nums">
                    {formatMoneyBRL(pagamento.valor)}
                  </strong>
                </div>
                <p className="mt-1 text-slate-600 dark:text-slate-300">
                  {pagamento.forma_pagamento} ·{" "}
                  {Number(pagamento.valor) < 0 ? "Devolvido ou estornado em" : "Recebido em"}{" "}
                  {formatarDataFaturamento(pagamento.data_recebimento)}
                </p>
                <p className="mt-1 text-slate-500 dark:text-slate-400">
                  Venda de {formatarDataFaturamento(pagamento.data_venda)}
                </p>
              </div>
            ))}
          </div>
          {limite < pagamentos.length && (
            <BotaoInteracao tamanho="pequeno" onClick={() => setLimite((atual) => atual + 20)}>
              Mostrar mais pagamentos
            </BotaoInteracao>
          )}
        </div>
      )}
      <p className="text-xs text-slate-600 dark:text-slate-300">
        Somente dinheiro altera o saldo físico. Abertura e suprimentos não são vendas nem
        recebimentos de clientes.
      </p>
    </section>
  );
}
