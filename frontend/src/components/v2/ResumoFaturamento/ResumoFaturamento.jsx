import { useId, useState } from "react";
import { ChevronDown, ChevronUp, TrendingUp } from "lucide-react";
import BotaoInteracao from "../BotaoInteracao/BotaoInteracao";
import BotaoLink from "../BotaoLink/BotaoLink";
import CartaoIndicador from "../CartaoIndicador/CartaoIndicador";
import { formatMoneyBRL } from "../../../utils/formatters";
import {
  formatarDataFaturamento,
  formulaFaturamento,
  linhasFaturamento,
  linhasQuitacao,
  periodoFaturamento,
} from "./faturamentoPresentation";

function LinhasValores({ linhas }) {
  return (
    <dl className="space-y-2 text-sm">
      {linhas.map(([rotulo, valor]) => (
        <div key={rotulo} className="flex items-start justify-between gap-3">
          <dt className="text-slate-600 dark:text-slate-300">{rotulo}</dt>
          <dd className="shrink-0 font-semibold tabular-nums text-slate-950 dark:text-white">
            {formatMoneyBRL(valor)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function DetalhesFaturamento({ composicao, id, aoAbrirRelatorio }) {
  const [limite, setLimite] = useState(20);
  if (!composicao) return null;
  const vendas = composicao.detalhes || [];

  return (
    <section
      id={id}
      aria-label="Detalhes do faturamento líquido"
      className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950"
    >
      {(composicao.avisos || []).map((aviso) => (
        <p
          key={aviso}
          role="status"
          className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200"
        >
          {aviso}
        </p>
      ))}
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
            Composição das vendas
          </h4>
          <LinhasValores linhas={linhasFaturamento(composicao)} />
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Antes de custos, taxas de cartão e comissões. A entrega aparece separadamente.
          </p>
        </div>
        <div>
          <h4 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
            Situação das vendas
          </h4>
          <LinhasValores linhas={linhasQuitacao(composicao)} />
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Pago + créditos utilizados + crediário a receber + aguardando pagamento = total das
            vendas
            {Number(composicao.taxa_entrega || 0) !== 0 ? " com entrega" : ""}. Os pagamentos podem
            ter ocorrido em outra data ou caixa.
          </p>
        </div>
      </div>
      <div className="border-t border-slate-200 pt-3 dark:border-slate-700">
        <h4 className="mb-2 text-sm font-bold text-slate-900 dark:text-white">
          Vendas que compõem o valor ({composicao.quantidade || 0})
        </h4>
        <div className="max-h-96 space-y-2 overflow-y-auto" role="list">
          {vendas.slice(0, limite).map((venda) => (
            <article
              key={venda.venda_id}
              role="listitem"
              className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-2 text-sm">
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">
                    Venda #{venda.numero_venda || venda.venda_id}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {formatarDataFaturamento(venda.data_venda)}
                  </p>
                </div>
                <strong className="tabular-nums text-slate-950 dark:text-white">
                  {formatMoneyBRL(venda.faturamento_liquido)}
                </strong>
              </div>
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
                Bruto {formatMoneyBRL(venda.faturamento_bruto)} · Descontos{" "}
                {formatMoneyBRL(venda.descontos)}
                {Number(venda.devolucoes || 0) !== 0
                  ? ` · Devoluções ${formatMoneyBRL(venda.devolucoes)}`
                  : ""}
                {Number(venda.taxa_entrega || 0) !== 0
                  ? ` · Entrega ${formatMoneyBRL(venda.taxa_entrega)}`
                  : ""}
              </p>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                Pago {formatMoneyBRL(venda.valor_pago)} · Créditos{" "}
                {formatMoneyBRL(venda.creditos_utilizados)}
                {" · "}Crediário {formatMoneyBRL(venda.crediario_receber)} · Em aberto{" "}
                {formatMoneyBRL(venda.em_aberto)}
              </p>
              {(venda.pagamentos || []).length > 0 && (
                <p className="mt-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
                  Histórico de pagamentos e formas de quitação
                </p>
              )}
              {(venda.pagamentos || []).map((pagamento, indice) => (
                <p
                  key={pagamento.id || indice}
                  className="mt-1 text-xs text-slate-500 dark:text-slate-400"
                >
                  {pagamento.forma_pagamento} · {formatMoneyBRL(pagamento.valor)}
                  {pagamento.tipo === "crediario"
                    ? " · A prazo, não recebido"
                    : pagamento.tipo === "beneficio"
                      ? " · Crédito ou benefício"
                      : ""}
                  {pagamento.data_pagamento
                    ? ` · ${formatarDataFaturamento(pagamento.data_pagamento)}`
                    : ""}
                </p>
              ))}
              {Number(venda.devolucoes || 0) > 0 && (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  O valor pago considera a devolução. O histórico preserva os lançamentos originais.
                </p>
              )}
            </article>
          ))}
          {vendas.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma venda no período.</p>
          )}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {limite < vendas.length && (
            <BotaoInteracao tamanho="pequeno" onClick={() => setLimite((atual) => atual + 20)}>
              Mostrar mais vendas
            </BotaoInteracao>
          )}
          {aoAbrirRelatorio && (
            <BotaoLink onClick={aoAbrirRelatorio}>
              Abrir relatório de vendas e rentabilidade
            </BotaoLink>
          )}
        </div>
      </div>
    </section>
  );
}

export default function ResumoFaturamento({
  composicao,
  titulo = "Faturamento líquido",
  periodo,
  expandido,
  aoAlternarDetalhes,
  detalhesFora = false,
  detalhesId,
  aoAbrirRelatorio,
}) {
  const idGerado = useId();
  const id = detalhesId || `faturamento-${idGerado}`;
  const [aberto, setAberto] = useState(false);
  const expandidoAtual = expandido ?? aberto;
  const alternar = aoAlternarDetalhes || (() => setAberto((atual) => !atual));

  return (
    <div className="h-full space-y-3">
      <CartaoIndicador
        icone={TrendingUp}
        tom="informativo"
        titulo={titulo}
        detalhe={periodoFaturamento(composicao, periodo)}
      >
        {composicao ? (
          <>
            {titulo !== "Faturamento líquido" && (
              <p className="mb-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
                Faturamento líquido
              </p>
            )}
            <p className="text-2xl font-bold leading-tight tabular-nums text-slate-950 dark:text-white">
              {formatMoneyBRL(composicao.faturamento_liquido)}
            </p>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
              {formulaFaturamento(composicao)}
            </p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Todas as vendas da empresa pela data da venda.
            </p>
            {composicao.avisos?.length > 0 && (
              <p className="mt-2 text-xs font-semibold text-amber-800 dark:text-amber-300">
                Há ressalvas neste cálculo. Consulte os detalhes.
              </p>
            )}
            <div className="mt-3">
              <BotaoInteracao
                tamanho="pequeno"
                icon={expandidoAtual ? ChevronUp : ChevronDown}
                onClick={alternar}
                aria-expanded={expandidoAtual}
                aria-controls={id}
                aria-label={`${expandidoAtual ? "Ocultar" : "Ver"} detalhes do faturamento líquido`}
              >
                {expandidoAtual ? "Ocultar detalhes" : "Detalhes"}
              </BotaoInteracao>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            O detalhamento do faturamento está indisponível. Atualize o painel.
          </p>
        )}
      </CartaoIndicador>
      {expandidoAtual && !detalhesFora && (
        <DetalhesFaturamento composicao={composicao} id={id} aoAbrirRelatorio={aoAbrirRelatorio} />
      )}
    </div>
  );
}
