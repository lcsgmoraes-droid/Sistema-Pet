import { useId, useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import BotaoInteracao from "../BotaoInteracao/BotaoInteracao";
import { formatMoneyBRL } from "../../../utils/formatters";
import { urlConsultaVendaPdv } from "../../../utils/conferenciaFechamentoUtils";
import { formatarDataFaturamento } from "./faturamentoPresentation";
import { motivoDiferencaPagamento } from "./pagamentosPresentation";
import { abrirConsultaPagamentoVenda } from "./AvisoPagamentoVenda.jsx";

export default function TotaisFormasPagamento({ composicao }) {
  const [origensAbertas, setOrigensAbertas] = useState(false);
  const [limite, setLimite] = useState(20);
  const origensId = useId();
  const formas = composicao?.formas_pagamento;
  const disponivel =
    Array.isArray(formas) &&
    composicao.valor_pago != null &&
    Number.isFinite(Number(composicao.valor_pago)) &&
    composicao.ajustes_formas_pagamento != null &&
    Number.isFinite(Number(composicao.ajustes_formas_pagamento));
  const ajuste = disponivel ? Number(composicao.ajustes_formas_pagamento) : 0;
  const origens = composicao?.diferencas_pagamentos || [];
  const resumo = composicao?.resumo_diferencas_pagamentos || [];
  const temDiferencas = ajuste !== 0 || origens.length > 0;
  const totalRegistrado = composicao?.total_formas_pagamento;

  return (
    <section
      aria-label="Pagamentos das vendas do período"
      className="border-t border-slate-200 pt-3 dark:border-slate-700"
    >
      <h4 className="mb-2 text-sm font-bold text-slate-900 dark:text-white">
        Pagamentos das vendas do período
      </h4>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Pagamentos das mesmas vendas deste indicador, inclusive os realizados em outras datas ou
        caixas. Créditos, cashback e crediário a receber aparecem separados na situação das vendas.
      </p>
      {!disponivel ? (
        <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
          Os totais por forma de pagamento estão indisponíveis. Atualize o painel.
        </p>
      ) : (
        <>
          {formas.length === 0 && Number(composicao.valor_pago) === 0 && ajuste === 0 && (
            <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
              Nenhum pagamento registrado para as vendas do período.
            </p>
          )}
          <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            {formas.map((forma) => (
              <div key={forma.forma_pagamento} className="flex items-start justify-between gap-3">
                <dt className="text-slate-600 dark:text-slate-300">{forma.forma_pagamento}</dt>
                <dd className="shrink-0 font-semibold tabular-nums text-slate-950 dark:text-white">
                  {formatMoneyBRL(forma.total)}
                </dd>
              </div>
            ))}
            {temDiferencas &&
              totalRegistrado != null &&
              Number.isFinite(Number(totalRegistrado)) && (
                <div className="flex items-start justify-between gap-3 border-t border-slate-200 pt-2 sm:col-span-2 dark:border-slate-700">
                  <dt className="font-semibold text-slate-900 dark:text-white">
                    Pagamentos registrados
                  </dt>
                  <dd className="font-semibold tabular-nums text-slate-950 dark:text-white">
                    {formatMoneyBRL(totalRegistrado)}
                  </dd>
                </div>
              )}
            {(resumo.length > 0
              ? resumo
              : ajuste !== 0
                ? [{ motivo: null, diferenca: ajuste }]
                : []
            ).map((item) => (
              <div
                key={item.motivo || "diferenca"}
                className="flex items-start justify-between gap-3 sm:col-span-2"
              >
                <dt className="text-slate-600 dark:text-slate-300">
                  {motivoDiferencaPagamento(item.motivo)}
                </dt>
                <dd className="shrink-0 font-semibold tabular-nums text-slate-950 dark:text-white">
                  {formatMoneyBRL(item.diferenca)}
                </dd>
              </div>
            ))}
            <div className="flex items-start justify-between gap-3 border-t border-slate-200 pt-2 sm:col-span-2 dark:border-slate-700">
              <dt className="font-bold text-slate-900 dark:text-white">Total aplicado às vendas</dt>
              <dd className="shrink-0 font-bold tabular-nums text-slate-950 dark:text-white">
                {formatMoneyBRL(composicao.valor_pago)}
              </dd>
            </div>
          </dl>
          {temDiferencas && (
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              O histórico preserva os pagamentos registrados. O valor aplicado acompanha o total
              atual das vendas, após descontos e devoluções. As diferenças abaixo não criam
              lançamentos financeiros.
            </p>
          )}
          {origens.length > 0 && (
            <div className="mt-3 space-y-3">
              <BotaoInteracao
                tamanho="pequeno"
                icon={origensAbertas ? ChevronUp : ChevronDown}
                aria-expanded={origensAbertas}
                aria-controls={origensId}
                onClick={() => setOrigensAbertas((atual) => !atual)}
              >
                {origensAbertas
                  ? "Ocultar origem das diferenças"
                  : `Ver origem das diferenças (${origens.length})`}
              </BotaoInteracao>
              {origensAbertas && (
                <div id={origensId} className="space-y-3">
                  <div role="list" className="max-h-80 space-y-2 overflow-y-auto">
                    {origens.slice(0, limite).map((origem, indice) => (
                      <article
                        key={origem.venda_id ?? indice}
                        role="listitem"
                        className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <strong>
                            Venda #{origem.numero_venda || origem.venda_id} ·{" "}
                            {formatarDataFaturamento(origem.data_venda)}
                          </strong>
                          {urlConsultaVendaPdv(origem.venda_id) && (
                            <BotaoInteracao
                              tamanho="pequeno"
                              icon={ExternalLink}
                              onClick={() => abrirConsultaPagamentoVenda(origem.venda_id)}
                              aria-label={`${origem.motivo === "devolucao" ? "Consultar" : "Corrigir pagamento da"} venda ${origem.numero_venda || origem.venda_id} em outra aba`}
                            >
                              {origem.motivo === "devolucao" ? "Consultar venda" : "Corrigir"}
                            </BotaoInteracao>
                          )}
                        </div>
                        <p className="mt-2 font-semibold">
                          {motivoDiferencaPagamento(origem.motivo)}:{" "}
                          {formatMoneyBRL(origem.diferenca)}
                        </p>
                        <p className="mt-1">
                          Pagamentos registrados:{" "}
                          {formatMoneyBRL(origem.total_pagamentos_registrados)} · Aplicado à venda:{" "}
                          {formatMoneyBRL(origem.valor_pago)}
                        </p>
                        {origem.descontos != null && Number(origem.descontos) > 0 && (
                          <p className="mt-1">
                            Descontos da venda: {formatMoneyBRL(origem.descontos)}
                          </p>
                        )}
                        {origem.devolucoes != null && Number(origem.devolucoes) > 0 && (
                          <p className="mt-1">
                            Devoluções da venda: {formatMoneyBRL(origem.devolucoes)}
                          </p>
                        )}
                        {(origem.formas_pagamento || []).map((forma) => (
                          <p key={forma.forma_pagamento} className="mt-1">
                            {forma.forma_pagamento}: {formatMoneyBRL(forma.total)}
                          </p>
                        ))}
                        {origem.motivo === "devolucao" && (
                          <p className="mt-2">
                            As formas acima são dos pagamentos originais. Consulte a venda para
                            conferir a restituição.
                          </p>
                        )}
                      </article>
                    ))}
                  </div>
                  {limite < origens.length && (
                    <BotaoInteracao
                      tamanho="pequeno"
                      onClick={() => setLimite((atual) => atual + 20)}
                    >
                      Mostrar mais diferenças
                    </BotaoInteracao>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
