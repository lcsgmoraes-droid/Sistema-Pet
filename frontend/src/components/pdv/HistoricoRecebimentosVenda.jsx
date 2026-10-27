import { useEffect, useState } from "react";
import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  formatarDataHistorico,
  formatarFormaPagamentoHistorico,
} from "../../utils/historicoFinanceiro";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";

export default function HistoricoRecebimentosVenda({ vendaId }) {
  const [pagina, setPagina] = useState(1);
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(false);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErro(false);
    api
      .get(`/vendas/${vendaId}/recebimentos-historico`, {
        params: { page: pagina, per_page: 20 },
      })
      .then(({ data }) => {
        if (ativo) setDados(data);
      })
      .catch(() => {
        if (ativo) setErro(true);
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [vendaId, pagina, tentativa]);

  const recebimentos = dados?.recebimentos || [];
  const totalPaginas = Math.max(dados?.paginacao?.total_pages || 0, 1);

  return (
    <section aria-label="Recebimentos da venda" className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Recebimentos</h4>
      {loading ? (
        <p role="status" className="text-sm text-gray-500 dark:text-slate-400">
          Carregando recebimentos...
        </p>
      ) : erro ? (
        <div role="alert" className="space-y-2 text-sm text-red-700 dark:text-red-400">
          <p>Não foi possível carregar os recebimentos desta venda.</p>
          <BotaoInteracao tamanho="pequeno" onClick={() => setTentativa((valor) => valor + 1)}>
            Tentar carregar recebimentos novamente
          </BotaoInteracao>
        </div>
      ) : recebimentos.length ? (
        <>
          {recebimentos.map((recebimento) => (
            <article
              key={recebimento.recebimento_id ?? recebimento.id}
              className="rounded-lg border border-gray-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div>
                  <dt className="text-gray-500">Data da baixa</dt>
                  <dd className="font-medium text-gray-900">
                    {formatarDataHistorico(recebimento.data_baixa)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Valor</dt>
                  <dd className="font-medium text-gray-900">{formatMoneyBRL(recebimento.valor)}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Forma de pagamento</dt>
                  <dd className="font-medium text-gray-900">
                    {formatarFormaPagamentoHistorico(recebimento.forma_pagamento)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Situação</dt>
                  <dd className="font-medium text-gray-900">
                    {recebimento.status === "estornado" ? "Estornado" : "Recebido"}
                  </dd>
                </div>
                {recebimento.baixa_lote_id ? (
                  <div className="col-span-2 md:col-span-4">
                    <dt className="text-gray-500">Origem</dt>
                    <dd className="text-gray-900">{`Baixa em lote #${recebimento.baixa_lote_id}`}</dd>
                  </div>
                ) : null}
                <div className="col-span-2 md:col-span-4">
                  <dt className="text-gray-500">Observação da baixa</dt>
                  <dd className="whitespace-pre-wrap break-words text-gray-900">
                    {recebimento.observacoes || "Nenhuma observação registrada."}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
          {totalPaginas > 1 ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <BotaoInteracao
                tamanho="pequeno"
                disabled={pagina <= 1}
                onClick={() => setPagina((valor) => valor - 1)}
              >
                Recebimentos anteriores
              </BotaoInteracao>
              <span>{`Página ${pagina} de ${totalPaginas} dos recebimentos`}</span>
              <BotaoInteracao
                tamanho="pequeno"
                disabled={pagina >= totalPaginas}
                onClick={() => setPagina((valor) => valor + 1)}
              >
                Próximos recebimentos
              </BotaoInteracao>
            </div>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-gray-500">Não há registros de baixa para esta venda.</p>
      )}
    </section>
  );
}
