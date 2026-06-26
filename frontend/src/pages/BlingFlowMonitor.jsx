import { useCallback, useEffect, useState } from "react";
import { toast } from "react-hot-toast";

import api from "../api";

import {
  Badge,
  EventCard,
  IncidentCard,
  InfoHint,
  SummaryCard,
} from "./blingFlowMonitor/BlingFlowMonitorCards";
import {
  RECENT_EVENTS_LIMIT,
  friendlyErrorMessage,
  monitorRequest,
  splitEventBuckets,
} from "./blingFlowMonitor/blingFlowMonitorUtils";

export default function BlingFlowMonitor() {
  const [resumo, setResumo] = useState(null);
  const [incidentes, setIncidentes] = useState([]);
  const [eventos, setEventos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [rodandoAuditoria, setRodandoAuditoria] = useState(false);
  const [acaoId, setAcaoId] = useState("");
  const [mostrarTodosEventos, setMostrarTodosEventos] = useState(false);
  const [mostrarHistorico, setMostrarHistorico] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [resumoRes, incidentesRes, eventosRes] = await Promise.all([
        monitorRequest("get", "/resumo"),
        monitorRequest("get", "/incidentes", { params: { status: "open", limite: 50 } }),
        monitorRequest("get", "/eventos", { params: { limite: 30 } }),
      ]);
      setResumo(resumoRes.data);
      setIncidentes(incidentesRes.data || []);
      setEventos(eventosRes.data || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao carregar monitor do Bling");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function executarAuditoria() {
    setRodandoAuditoria(true);
    try {
      const response = await monitorRequest("post", "/auditar?dias=7&limite=300&auto_fix=true");
      const data = response.data || {};
      toast.success(
        `Auditoria concluida: ${data.incidentes_detectados || 0} incidente(s), ${data.auto_fix_sucessos || 0} correcao(oes).`,
      );
      await carregar();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao executar auditoria");
    } finally {
      setRodandoAuditoria(false);
    }
  }

  async function corrigirIncidente(incidente) {
    const acaoForcada = incidente.acao_forcada;
    const pedidoId = incidente.pedido_integrado_id;
    const actionKey =
      acaoForcada === "consolidar_duplicidade"
        ? `consolidar-${incidente.id}`
        : acaoForcada === "reconciliar_fluxo"
          ? `reconciliar-${incidente.id}`
          : `corrigir-${incidente.id}`;
    setAcaoId(actionKey);
    try {
      if (acaoForcada === "consolidar_duplicidade" && pedidoId) {
        const response = await api.post(
          `/integracoes/bling/pedidos/${pedidoId}/consolidar-duplicidade`,
        );
        const totalMesclados = response.data?.pedidos_mesclados?.length || 0;
        toast.success(`Duplicidade consolidada. ${totalMesclados} pedido(s) incorporado(s).`);
      } else if (acaoForcada === "reconciliar_fluxo" && pedidoId) {
        const response = await api.post(`/integracoes/bling/pedidos/${pedidoId}/reconciliar-fluxo`);
        toast.success(
          response.data?.nf_numero
            ? `Fluxo reconciliado com a NF ${response.data.nf_numero}.`
            : "Fluxo reconciliado com sucesso.",
        );
      } else {
        const response = await monitorRequest("post", `/incidentes/${incidente.id}/corrigir`);
        const detalhe =
          response.data?.details?.error ||
          response.data?.details?.motivo ||
          (Array.isArray(response.data?.details?.erros)
            ? response.data.details.erros.join(" | ")
            : "");

        if (response.data?.success) {
          toast.success("Correcao automatica aplicada.");
        } else {
          toast.error(
            friendlyErrorMessage(detalhe) ||
              "A correcao automatica nao conseguiu resolver o incidente.",
          );
        }
      }
      await carregar();
    } catch (error) {
      const detail =
        typeof error.response?.data?.detail === "string"
          ? error.response?.data?.detail
          : error.response?.data?.detail?.motivo || error.response?.data?.detail?.error;
      toast.error(friendlyErrorMessage(detail) || "Erro ao corrigir incidente");
    } finally {
      setAcaoId("");
    }
  }

  async function resolverIncidente(incidente) {
    setAcaoId(`resolver-${incidente.id}`);
    try {
      await monitorRequest("post", `/incidentes/${incidente.id}/resolver`);
      toast.success("Incidente marcado como resolvido manualmente.");
      await carregar();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao resolver incidente");
    } finally {
      setAcaoId("");
    }
  }

  const { timeline: eventosTimeline, history: eventosHistorico } = splitEventBuckets(eventos);
  const eventosRecentesVisiveis = mostrarTodosEventos
    ? eventosTimeline
    : eventosTimeline.slice(0, RECENT_EVENTS_LIMIT);
  const eventosRecentesOcultos = Math.max(eventosTimeline.length - RECENT_EVENTS_LIMIT, 0);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Monitor Bling</h1>
          <p className="mt-1 text-sm text-slate-500">
            Auditoria do fluxo pedido, NF, reserva e baixa de estoque.
          </p>
          <div className="mt-3 inline-flex items-start gap-2 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
            <InfoHint text="Os horarios abaixo sao renderizados sempre em America/Sao_Paulo, mesmo quando o evento chegou em UTC." />
            <p>
              Horarios exibidos em Brasilia. Cada evento mostra o recebimento, o vinculo pedido/NF e
              o resultado da etapa.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={carregar}
            disabled={carregando}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Atualizar
          </button>
          <button
            type="button"
            onClick={executarAuditoria}
            disabled={rodandoAuditoria}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50"
          >
            Rodar auditoria
          </button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard title="Status" value={resumo?.status || "-"} hint="Saude atual do fluxo" />
        <SummaryCard
          title="Incidentes abertos"
          value={resumo?.incidentes_abertos ?? "-"}
          hint="Pendencias em aberto"
        />
        <SummaryCard
          title="Criticos"
          value={resumo?.por_severidade?.critical || 0}
          hint="Exigem atencao imediata"
        />
        <SummaryCard title="High" value={resumo?.por_severidade?.high || 0} hint="Fluxo em risco" />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Incidentes</h2>
            <span className="text-sm text-slate-500">{incidentes.length} item(ns)</span>
          </div>

          {carregando ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
              Carregando...
            </div>
          ) : incidentes.length === 0 ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center text-emerald-700">
              Nenhum incidente aberto no momento.
            </div>
          ) : (
            <div className="space-y-3">
              {incidentes.map((incidente) => (
                <IncidentCard
                  key={incidente.id}
                  incidente={incidente}
                  onCorrigir={corrigirIncidente}
                  onResolver={resolverIncidente}
                  acaoId={acaoId}
                />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Eventos recentes</h2>
            <span className="text-sm text-slate-500">{eventos.length} item(ns)</span>
          </div>

          <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="blue">{eventosTimeline.length} em foco</Badge>
                <Badge tone="green">mostrando {eventosRecentesVisiveis.length}</Badge>
                {eventosHistorico.length > 0 && (
                  <Badge tone="slate">{eventosHistorico.length} no historico</Badge>
                )}
              </div>
              {eventosTimeline.length > RECENT_EVENTS_LIMIT && (
                <button
                  type="button"
                  onClick={() => setMostrarTodosEventos((current) => !current)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  {mostrarTodosEventos
                    ? `Mostrar so os ${RECENT_EVENTS_LIMIT} ultimos`
                    : `Mostrar mais ${eventosRecentesOcultos}`}
                </button>
              )}
            </div>
            <p className="mt-2 text-sm text-slate-600">
              A coluna mostra so os {RECENT_EVENTS_LIMIT} eventos mais recentes por padrao. O
              restante pode ser aberto sob demanda, e a rotina antiga continua no historico.
            </p>
          </div>

          <div className="space-y-3">
            {eventosRecentesVisiveis.map((evento) => (
              <EventCard
                key={evento.id}
                evento={evento}
                defaultExpanded={["warning", "error"].includes(evento.status)}
              />
            ))}
          </div>

          {eventosHistorico.length > 0 && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">Historico de rotina</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Eventos informativos antigos continuam disponiveis aqui, sem poluir a leitura
                    principal.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setMostrarHistorico((current) => !current)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  {mostrarHistorico
                    ? "Ocultar historico"
                    : `Mostrar historico (${eventosHistorico.length})`}
                </button>
              </div>

              {mostrarHistorico && (
                <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                  {eventosHistorico.map((evento) => (
                    <EventCard key={evento.id} evento={evento} />
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
