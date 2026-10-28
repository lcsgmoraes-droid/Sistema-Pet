import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { CheckCircle2, ExternalLink, Receipt, RefreshCw, RotateCw } from "lucide-react";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { formatMoneyBRL } from "../../../utils/formatters";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import { confirmarCorePet } from "../../../services/corepetDialog";

export default function BanhoTosaFechamentosView({ onChanged }) {
  const [pendencias, setPendencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState("");
  const [proximoCursor, setProximoCursor] = useState(null);
  const [buscaIncompleta, setBuscaIncompleta] = useState(false);
  const [cursorPagina, setCursorPagina] = useState(null);
  const [erroCarga, setErroCarga] = useState("");
  const carregando = useRef(false);
  const requisicaoAtual = useRef(0);

  useEffect(() => {
    let ativo = true;
    void carregar(null, false, () => ativo);
    return () => {
      ativo = false;
      requisicaoAtual.current += 1;
      carregando.current = false;
    };
  }, []);

  async function carregar(cursor = null, acumular = false, estaAtivo = () => true) {
    if (carregando.current) return;
    const requisicao = ++requisicaoAtual.current;
    const ativo = () => estaAtivo() && requisicao === requisicaoAtual.current;
    carregando.current = true;
    setLoading(true);
    setErroCarga("");
    try {
      const response = await banhoTosaApi.listarPendenciasFechamento({ limit: 300, cursor });
      if (!ativo()) return;
      const novos = Array.isArray(response.data?.itens) ? response.data.itens : [];
      setPendencias((anteriores) => mesclarPendencias(acumular ? anteriores : [], novos));
      setProximoCursor(response.data?.proximo_cursor ?? null);
      setBuscaIncompleta(Boolean(response.data?.busca_incompleta));
      setCursorPagina(cursor);
    } catch (error) {
      if (!ativo()) return;
      const mensagem = getApiErrorMessage(error, "Não foi possível carregar os fechamentos.");
      setErroCarga(mensagem);
      toast.error(mensagem);
    } finally {
      if (requisicao === requisicaoAtual.current) {
        if (estaAtivo()) setLoading(false);
        carregando.current = false;
      }
    }
  }

  async function executar(chave, operacao, mensagem) {
    setProcessing(chave);
    try {
      const response = await operacao();
      toast.success(mensagem);
      await carregar();
      await onChanged?.(true);
      return response;
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível concluir a operação."));
      return null;
    } finally {
      setProcessing("");
    }
  }

  async function gerarVenda(item) {
    const response = await executar(
      `venda-${item.atendimento_id}`,
      () => banhoTosaApi.gerarVendaAtendimento(item.atendimento_id),
      "Cobrança gerada no PDV.",
    );
    if (response?.data?.pdv_url) {
      window.open(response.data.pdv_url, "_blank", "noopener,noreferrer");
    }
  }

  async function entregar(item) {
    const confirmou = await confirmarCorePet(
      `Confirmar a entrega de ${item.pet_nome || "este pet"} e encerrar o atendimento?`,
    );
    if (!confirmou) return;
    await executar(
      `entrega-${item.atendimento_id}`,
      () =>
        banhoTosaApi.moverEtapaAtendimento(item.atendimento_id, {
          tipo: "entregue",
          iniciar_timer: false,
        }),
      "Entrega confirmada.",
    );
  }

  const semVenda = pendencias.filter((item) => !item.venda_id).length;
  const cobrancaAberta = pendencias.filter((item) =>
    ["pendente", "parcial"].includes(item.status_pagamento),
  ).length;

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <BotaoInteracao
              icon={RotateCw}
              loading={processing === "sincronizar-todos"}
              disabled={loading}
              onClick={() =>
                executar(
                  "sincronizar-todos",
                  () =>
                    banhoTosaApi.sincronizarPendenciasFechamento({
                      limit: 300,
                      cursor: cursorPagina,
                    }),
                  "Página atual sincronizada. A consulta voltou aos atendimentos recentes.",
                )
              }
            >
              Sincronizar página atual
            </BotaoInteracao>
            <BotaoInteracao
              icon={RefreshCw}
              loading={loading}
              disabled={Boolean(processing)}
              onClick={() => void carregar()}
            >
              Atualizar
            </BotaoInteracao>
          </>
        }
        subtitle="Centralize cobrança, conferência financeira e entrega sem perder atendimentos prontos."
        title="Fechamentos"
      >
        <MetricGrid>
          <MetricCard intent="amber" label="Pendências" value={pendencias.length} />
          <MetricCard intent="red" label="Sem venda" value={semVenda} />
          <MetricCard intent="blue" label="Cobrança aberta" value={cobrancaAberta} />
        </MetricGrid>
      </Panel>

      {buscaIncompleta && (
        <Panel>
          <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
            Ainda há histórico anterior para conferir.
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            A lista mostra as pendências encontradas até agora. A sincronização atua somente na
            página atual.
          </p>
          <div className="mt-3">
            <BotaoInteracao
              loading={loading}
              disabled={Boolean(processing) || proximoCursor == null}
              onClick={() => void carregar(proximoCursor, true)}
            >
              Buscar pendências anteriores
            </BotaoInteracao>
          </div>
        </Panel>
      )}
      {erroCarga && (
        <Panel>
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">
            {erroCarga}
          </p>
        </Panel>
      )}

      <ConteudoFechamentos
        loading={loading}
        pendencias={pendencias}
        buscaIncompleta={buscaIncompleta}
        erroCarga={erroCarga}
        processing={processing}
        executar={executar}
        gerarVenda={gerarVenda}
        entregar={entregar}
      />
    </div>
  );
}

function mesclarPendencias(anteriores, novos) {
  const porId = new Map(anteriores.map((item) => [item.atendimento_id, item]));
  for (const item of novos) porId.set(item.atendimento_id, item);
  return [...porId.values()];
}

function ConteudoFechamentos({
  loading,
  pendencias,
  buscaIncompleta,
  erroCarga,
  processing,
  executar,
  gerarVenda,
  entregar,
}) {
  if (loading && !pendencias.length) {
    return <Panel className="p-8 text-center text-sm text-slate-500">Carregando...</Panel>;
  }
  if (!pendencias.length) {
    if (buscaIncompleta || erroCarga) return null;
    return (
      <EmptyState
        description="Os atendimentos conferidos estão com cobrança e financeiro em dia."
        title="Nenhum fechamento pendente"
      />
    );
  }
  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {pendencias.map((item) => (
        <PendenciaFechamento
          key={item.atendimento_id}
          item={item}
          processing={processing}
          executar={executar}
          gerarVenda={gerarVenda}
          entregar={entregar}
        />
      ))}
    </div>
  );
}

function PendenciaFechamento({ item, processing, executar, gerarVenda, entregar }) {
  return (
    <Panel padding="sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Atendimento #{item.atendimento_id}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            {item.pet_nome || `Pet #${item.pet_id}`}
          </h3>
          <p className="text-sm text-slate-500">
            Tutor: {item.cliente_nome || "Tutor não informado"}
          </p>
        </div>
        <span className="w-fit rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
          {item.status_atendimento === "pronto" ? "Pronto" : "Entregue"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-3 text-sm">
        <div>
          <p className="text-xs text-slate-500">Total</p>
          <p className="font-semibold text-slate-900">{formatMoneyBRL(item.total)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Restante</p>
          <p className="font-semibold text-slate-900">{formatMoneyBRL(item.valor_restante)}</p>
        </div>
      </div>

      {item.alertas?.length ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-800">
          {item.alertas.map((alerta) => (
            <p key={alerta}>{alerta}</p>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {!item.venda_id ? (
          <BotaoInteracao
            icon={Receipt}
            loading={processing === `venda-${item.atendimento_id}`}
            onClick={() => gerarVenda(item)}
          >
            Gerar cobrança
          </BotaoInteracao>
        ) : (
          <>
            <BotaoInteracao
              icon={ExternalLink}
              onClick={() => window.open(item.pdv_url, "_blank", "noopener,noreferrer")}
            >
              Abrir PDV
            </BotaoInteracao>
            <BotaoInteracao
              icon={RotateCw}
              loading={processing === `sync-${item.atendimento_id}`}
              onClick={() =>
                executar(
                  `sync-${item.atendimento_id}`,
                  () => banhoTosaApi.sincronizarFechamentoAtendimento(item.atendimento_id),
                  "Fechamento sincronizado.",
                )
              }
            >
              Sincronizar
            </BotaoInteracao>
          </>
        )}
        {item.status_atendimento === "pronto" && (
          <BotaoInteracao
            disabled={!item.venda_id}
            icon={CheckCircle2}
            loading={processing === `entrega-${item.atendimento_id}`}
            onClick={() => entregar(item)}
          >
            Confirmar entrega
          </BotaoInteracao>
        )}
      </div>
    </Panel>
  );
}
