import { useState } from "react";

const BRASILIA_TIMEZONE = "America/Sao_Paulo";
const EVENT_LABELS = {
  "order.created": "Pedido criado/importado",
  "order.updated": "Atualizacao do pedido recebida",
  "invoice.updated": "NF recebida do Bling",
  "invoice.linked_to_order": "NF vinculada ao pedido",
  "invoice.authorized": "NF autorizada e processada",
  "invoice.cancelled": "NF cancelada processada",
  "pedido.confirmado": "Pedido confirmado no sistema",
  "pedido.cancelado": "Pedido cancelado no sistema",
  "pedido.confirmacao.baixa": "Baixa de estoque do pedido",
  "nf.processada": "NF processada com reconciliacao",
  "nf.baixa_estoque": "Baixa de estoque via NF",
};
const LINK_SOURCE_LABELS = {
  "nf.webhook": "webhook da NF",
  "pedido.webhook": "webhook do pedido",
  auditoria: "auditoria automatica",
};
export const RECENT_EVENTS_LIMIT = 3;

function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    yellow: "bg-amber-100 text-amber-700",
    red: "bg-rose-100 text-rose-700",
    blue: "bg-blue-100 text-blue-700",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone] || tones.slate}`}
    >
      {children}
    </span>
  );
}

function toneFromSeverity(severity) {
  if (severity === "critical") return "red";
  if (severity === "high") return "yellow";
  if (severity === "medium") return "blue";
  if (severity === "info") return "green";
  return "slate";
}

function toneFromStatus(status) {
  if (status === "ok") return "green";
  if (status === "received") return "blue";
  if (status === "warning") return "yellow";
  if (status === "error") return "red";
  return "slate";
}

function statusLabel(status) {
  if (status === "ok") return "ok";
  if (status === "received") return "recebido";
  if (status === "warning") return "pendencia";
  if (status === "error") return "erro";
  return status || "-";
}

function normalizeUtcDateInput(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  if (/z$/i.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw)) return raw;

  const base = raw.includes("T") ? raw : raw.replace(" ", "T");
  return `${base}Z`;
}

function formatDate(value) {
  const normalized = normalizeUtcDateInput(value);
  if (!normalized) return "-";
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "-";
  return `${date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: BRASILIA_TIMEZONE,
  })} BRT`;
}

function displayValue(value) {
  if (value === null || value === undefined) return "-";
  if (value === "") return "-";
  return String(value);
}

function InfoHint({ text }) {
  if (!text) return null;
  return (
    <span
      title={text}
      className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-300 text-[10px] font-bold text-slate-400"
    >
      ?
    </span>
  );
}

function DetailField({ label, value, hint, mono = false }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        <span>{label}</span>
        <InfoHint text={hint} />
      </div>
      <p className={`mt-1 break-all text-sm text-slate-700 ${mono ? "font-mono" : ""}`}>
        {displayValue(value)}
      </p>
    </div>
  );
}

function SummaryCard({ title, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

function friendlyErrorMessage(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  const lower = raw.toLowerCase();

  if (lower.includes("estoque_movimentacoes_user_id_fkey")) {
    return "Nao foi possivel registrar a baixa automatica porque faltava um usuario valido para a operacao.";
  }
  if (lower.includes("session's transaction has been rolled back")) {
    return "A tentativa automatica falhou por um erro interno de processamento. O incidente continua aberto para nova tentativa.";
  }
  if (lower.includes("foreign key constraint")) {
    return "A correcao automatica nao conseguiu salvar todos os vinculos necessarios no banco.";
  }
  if (lower.includes("produto nao encontrado") || lower.includes("produto não encontrado")) {
    return "O produto do item ainda nao foi encontrado no cadastro local.";
  }
  if (lower.includes("sku") && lower.includes("nao encontrado")) {
    return "O SKU do item ainda nao foi encontrado no cadastro local.";
  }
  if (lower.includes("autocorrecao falhou") || lower.includes("autocorreção falhou")) {
    return "A correcao automatica nao conseguiu concluir a acao sugerida.";
  }
  if (raw.length > 220) {
    return `${raw.slice(0, 217)}...`;
  }

  return raw;
}

function formatAutofixDetails(details) {
  if (!details || typeof details !== "object") return "";

  if (details.auto_fix_error) return friendlyErrorMessage(details.auto_fix_error);

  const result = details.auto_fix_result;
  if (result?.error) return friendlyErrorMessage(result.error);
  if (Array.isArray(result?.erros) && result.erros.length > 0)
    return friendlyErrorMessage(result.erros.join(" | "));
  if (result?.motivo) return friendlyErrorMessage(result.motivo);

  return "";
}

function eventLabel(eventType) {
  return EVENT_LABELS[eventType] || eventType || "Evento do monitor";
}

function buildEventResult(evento) {
  const erros = Array.isArray(evento?.payload?.erros_estoque)
    ? evento.payload.erros_estoque.filter(Boolean)
    : [];
  const errorDetail = friendlyErrorMessage(evento?.error_message || erros.join(" | "));

  if (
    evento?.event_type === "invoice.authorized" &&
    evento?.payload?.acao === "venda_ja_confirmada"
  ) {
    return "A NF foi processada e o pedido ja estava conciliado anteriormente.";
  }
  if (
    evento?.event_type === "pedido.confirmado" &&
    evento?.payload?.baixa_estoque_status === "ok"
  ) {
    return "Pedido confirmado e estoque baixado sem pendencias.";
  }
  if (
    evento?.event_type === "pedido.confirmado" &&
    evento?.payload?.baixa_estoque_status === "nf_pendente"
  ) {
    return "Pedido confirmado no Bling; a venda segue aguardando a NF para consolidar o estoque.";
  }
  if (
    evento?.event_type === "pedido.confirmado" &&
    evento?.payload?.baixa_estoque_status === "warning"
  ) {
    return errorDetail || "Pedido confirmado, mas a baixa de estoque ficou com pendencias.";
  }
  if (evento?.status === "ok") return "Tudo certo nesta etapa.";
  if (evento?.status === "received")
    return "Evento recebido; os proximos cards mostram o processamento e o resultado.";
  if (evento?.status === "warning") return errorDetail || "A etapa foi concluida com pendencias.";
  if (evento?.status === "error") return errorDetail || "A etapa falhou e precisa de revisao.";
  return errorDetail || evento?.message || "-";
}

function buildEventNarrative(evento) {
  const pedidoLabel = evento.pedido_bling_numero || evento.pedido_bling_id;
  const nfLabel = evento.nf_numero;
  const linkSource = LINK_SOURCE_LABELS[evento?.payload?.link_source] || "";

  switch (evento.event_type) {
    case "order.created":
      return {
        title: eventLabel(evento.event_type),
        what: "O pedido entrou no sistema a partir do webhook do Bling e ficou pronto para acompanhar NF, reserva e baixa.",
        result: buildEventResult(evento),
      };
    case "order.updated":
      return {
        title: eventLabel(evento.event_type),
        what: "O Bling enviou uma atualizacao do pedido e o sistema reavaliou o status do fluxo.",
        result: buildEventResult(evento),
      };
    case "invoice.updated":
      return {
        title: eventLabel(evento.event_type),
        what: "A NF chegou do Bling e o sistema iniciou a localizacao do pedido para atualizar o vinculo da nota.",
        result: buildEventResult(evento),
      };
    case "invoice.linked_to_order":
      return {
        title: eventLabel(evento.event_type),
        what: `${nfLabel ? `A NF ${nfLabel}` : "A NF recebida"} foi vinculada ao ${pedidoLabel ? `pedido ${pedidoLabel}` : "pedido correspondente"}${linkSource ? ` via ${linkSource}` : ""}.`,
        result: "O vinculo pedido/NF ficou salvo para as proximas etapas do fluxo.",
      };
    case "invoice.authorized":
      return {
        title: eventLabel(evento.event_type),
        what: "Com a NF autorizada, o sistema consolidou o pedido e executou a reconciliacao do estoque.",
        result: buildEventResult(evento),
      };
    case "invoice.cancelled":
      return {
        title: eventLabel(evento.event_type),
        what: "A NF cancelada foi processada e o pedido foi ajustado de acordo com o evento recebido.",
        result: buildEventResult(evento),
      };
    case "pedido.confirmado":
      return {
        title: eventLabel(evento.event_type),
        what: "O pedido foi consolidado no sistema depois da atualizacao recebida do Bling.",
        result: buildEventResult(evento),
      };
    case "pedido.cancelado":
      return {
        title: eventLabel(evento.event_type),
        what: "O pedido foi cancelado no sistema e as reservas logicas foram liberadas.",
        result: buildEventResult(evento),
      };
    default:
      return {
        title: eventLabel(evento.event_type),
        what: evento.message || "Evento registrado no monitor do fluxo Bling.",
        result: buildEventResult(evento),
      };
  }
}

function buildEventReferenceSummary(evento) {
  const partes = [];

  const pedido = evento.pedido_bling_numero || evento.pedido_bling_id;
  if (pedido) partes.push(`Pedido ${pedido}`);
  if (evento.numero_pedido_loja) partes.push(`Loja ${evento.numero_pedido_loja}`);
  if (evento.nf_numero) partes.push(`NF ${evento.nf_numero}`);
  if (evento.sku) partes.push(`SKU ${evento.sku}`);

  return partes.join(" | ");
}

function isRoutineEvent(evento) {
  return evento?.severity === "info" && ["ok", "received"].includes(evento?.status);
}

function splitEventBuckets(eventos) {
  const timeline = [];
  const history = [];

  eventos.forEach((evento, index) => {
    const destaque =
      index < 6 || !isRoutineEvent(evento) || ["warning", "error"].includes(evento?.status);
    if (destaque) {
      timeline.push(evento);
      return;
    }
    history.push(evento);
  });

  return { timeline, history };
}

function IncidentCard({ incidente, onCorrigir, onResolver, acaoId }) {
  const pedidoLabel = incidente.pedido_bling_numero || incidente.pedido_bling_id || "-";
  const autoFixDetalhe = formatAutofixDetails(incidente.details);
  const duplicidade = incidente.duplicidade || {};
  const acoesDisponiveis = incidente.acoes_disponiveis || {};
  const pedidoCanonico = duplicidade.pedido_canonico || {};

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={toneFromSeverity(incidente.severity)}>{incidente.severity}</Badge>
            <Badge tone={incidente.status === "resolved" ? "green" : "slate"}>
              {incidente.status}
            </Badge>
            <span className="text-xs font-mono text-slate-500">{incidente.code}</span>
          </div>
          <h3 className="mt-2 text-sm font-semibold text-slate-900">{incidente.title}</h3>
          <p className="mt-1 text-sm text-slate-600">{incidente.message}</p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <p>{formatDate(incidente.last_seen_em)}</p>
          <p>{incidente.occurrences}x</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
        <DetailField
          label="Pedido Bling"
          value={pedidoLabel}
          hint="Numero visivel do pedido no Bling."
        />
        <DetailField
          label="ID interno"
          value={incidente.pedido_integrado_id}
          hint="Identificador do pedido dentro do sistema local."
          mono
        />
        <DetailField
          label="Pedido loja"
          value={incidente.numero_pedido_loja}
          hint="Numero do pedido no canal ou marketplace."
        />
        <DetailField
          label="NF numero"
          value={incidente.nf_numero}
          hint="Numero humano da NF vinculada a este fluxo."
        />
        <DetailField
          label="NF Bling"
          value={incidente.nf_bling_id}
          hint="Identificador tecnico da nota no Bling."
          mono
        />
        <DetailField
          label="SKU"
          value={incidente.sku}
          hint="SKU do item impactado pelo incidente."
          mono
        />
      </div>

      {duplicidade.tem_duplicados && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3">
          <div className="flex items-center gap-2">
            <Badge tone="yellow">pedido duplicado</Badge>
            <span className="text-sm font-semibold text-amber-900">
              Pedido loja {duplicidade.numero_pedido_loja || incidente.numero_pedido_loja || "-"}
            </span>
          </div>
          <p className="mt-2 text-sm text-amber-800">
            O sistema identificou mais de um pedido local para o mesmo numero de pedido da loja. O
            pedido canonico fica como fonte principal do fluxo.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            <DetailField
              label="Pedido canonico"
              value={pedidoCanonico.pedido_bling_numero || pedidoCanonico.pedido_bling_id || "-"}
              hint="Pedido principal escolhido pelo sistema para centralizar NF, estoque e historico."
            />
            <DetailField
              label="NF do canonico"
              value={pedidoCanonico.nf_numero}
              hint="NF atualmente vinculada ao pedido canonico."
            />
          </div>
          {(duplicidade.pedidos_duplicados || []).length > 0 && (
            <div className="mt-3 rounded-lg border border-amber-100 bg-white px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                Pedidos duplicados detectados
              </p>
              <div className="mt-2 space-y-2">
                {duplicidade.pedidos_duplicados.map((pedido) => (
                  <div
                    key={pedido.id}
                    className="flex flex-wrap items-center gap-2 text-sm text-slate-700"
                  >
                    <span className="font-medium">
                      #{pedido.pedido_bling_numero || pedido.pedido_bling_id || pedido.id}
                    </span>
                    <Badge tone={pedido.pode_mesclar_automaticamente ? "green" : "yellow"}>
                      {pedido.pode_mesclar_automaticamente
                        ? "seguro para mesclar"
                        : "revisao manual"}
                    </Badge>
                    {pedido.motivos_bloqueio?.length > 0 && (
                      <span className="text-xs text-amber-700">
                        {pedido.motivos_bloqueio.join(", ")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {incidente.suggested_action && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {incidente.suggested_action}
        </div>
      )}

      {incidente.auto_fix_status === "failed" && autoFixDetalhe && (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          Ultima tentativa de correcao: {autoFixDetalhe}
        </div>
      )}

      <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
        <strong>Corrigir</strong> tenta executar a acao automatica sugerida.
        <br />
        <strong>Resolver</strong> apenas marca o incidente como tratado manualmente, sem corrigir o
        pedido.
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {acoesDisponiveis.pode_consolidar_duplicidade && incidente.status !== "resolved" && (
          <button
            type="button"
            onClick={() => onCorrigir({ ...incidente, acao_forcada: "consolidar_duplicidade" })}
            disabled={acaoId === `consolidar-${incidente.id}`}
            className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-amber-600 disabled:opacity-50"
          >
            Consolidar duplicados
          </button>
        )}
        {acoesDisponiveis.pode_reconciliar_fluxo && incidente.status !== "resolved" && (
          <button
            type="button"
            onClick={() => onCorrigir({ ...incidente, acao_forcada: "reconciliar_fluxo" })}
            disabled={acaoId === `reconciliar-${incidente.id}`}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
          >
            Reconciliar fluxo
          </button>
        )}
        {incidente.auto_fixable && incidente.status !== "resolved" && (
          <button
            type="button"
            onClick={() => onCorrigir(incidente)}
            disabled={acaoId === `corrigir-${incidente.id}`}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
          >
            Tentar corrigir
          </button>
        )}
        {incidente.status !== "resolved" && (
          <button
            type="button"
            onClick={() => onResolver(incidente)}
            disabled={acaoId === `resolver-${incidente.id}`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Marcar como resolvido
          </button>
        )}
      </div>
    </div>
  );
}

function EventCard({ evento, defaultExpanded = false }) {
  const copy = buildEventNarrative(evento);
  const [expanded, setExpanded] = useState(defaultExpanded);
  const hasReferences = Boolean(
    evento.pedido_bling_numero ||
    evento.pedido_bling_id ||
    evento.pedido_integrado_id ||
    evento.numero_pedido_loja ||
    evento.nf_numero ||
    evento.nf_bling_id ||
    evento.sku,
  );
  const referenceSummary = buildEventReferenceSummary(evento);
  const statusTone =
    evento.status === "error"
      ? "red"
      : evento.status === "warning"
        ? "yellow"
        : evento.status === "received"
          ? "blue"
          : "green";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={toneFromSeverity(evento.severity)}>{evento.severity}</Badge>
            <Badge tone={toneFromStatus(evento.status)}>{statusLabel(evento.status)}</Badge>
            <span className="text-[11px] uppercase tracking-wide text-slate-400">
              {evento.source || "runtime"}
            </span>
            {expanded && (
              <span className="text-[11px] font-mono text-slate-400">{evento.event_type}</span>
            )}
          </div>
          <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">{copy.title}</p>
              <p className="mt-1 text-sm text-slate-600 line-clamp-2">{copy.result}</p>
              {referenceSummary && (
                <p className="mt-1 text-xs text-slate-500">{referenceSummary}</p>
              )}
            </div>
            <div className="flex items-center gap-2 md:ml-4 md:flex-col md:items-end">
              <Badge tone={statusTone}>
                {evento.status === "ok" ? "sem pendencia" : statusLabel(evento.status)}
              </Badge>
              <span
                title="Horario exibido em Brasilia."
                className="shrink-0 text-right text-xs text-slate-500"
              >
                {formatDate(evento.processed_at)}
              </span>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="shrink-0 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
        >
          {expanded ? "Ocultar detalhes" : "Ver detalhes"}
        </button>
      </div>

      {expanded && (
        <>
          <div className="mt-3 space-y-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
            <div>
              <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <span>O que aconteceu</span>
                <InfoHint text="Resumo do passo do fluxo que acabou de acontecer." />
              </div>
              <p className="mt-1 text-sm text-slate-700">{copy.what}</p>
            </div>
            <div>
              <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <span>Resultado</span>
                <InfoHint text="Mostra se a etapa terminou bem, com pendencia ou com erro." />
              </div>
              <p
                className={`mt-1 text-sm ${evento.status === "error" ? "text-rose-700" : evento.status === "warning" ? "text-amber-700" : "text-slate-700"}`}
              >
                {copy.result}
              </p>
            </div>
          </div>

          {hasReferences && (
            <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-3">
              <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                <span>Referencias do evento</span>
                <InfoHint text="Aqui ficam os identificadores usados para ligar pedido, NF e item dentro do fluxo." />
              </div>
              <p className="mt-1 text-sm text-emerald-800">
                {displayValue(evento.pedido_bling_numero || evento.pedido_bling_id || "-")}
                {evento.numero_pedido_loja ? ` | Pedido loja ${evento.numero_pedido_loja}` : ""}
                {evento.nf_numero ? ` | NF ${evento.nf_numero}` : ""}
              </p>
            </div>
          )}

          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            <DetailField
              label="Pedido Bling"
              value={evento.pedido_bling_numero}
              hint="Numero visivel do pedido no Bling."
            />
            <DetailField
              label="ID Bling"
              value={evento.pedido_bling_id}
              hint="Identificador tecnico do pedido recebido do Bling."
              mono
            />
            <DetailField
              label="ID interno"
              value={evento.pedido_integrado_id}
              hint="Identificador do pedido dentro do sistema local."
              mono
            />
            <DetailField
              label="Pedido loja"
              value={evento.numero_pedido_loja}
              hint="Numero do pedido no canal ou marketplace."
            />
            <DetailField
              label="NF numero"
              value={evento.nf_numero}
              hint="Numero humano da nota fiscal associada ao evento."
            />
            <DetailField
              label="NF Bling"
              value={evento.nf_bling_id}
              hint="Identificador tecnico da nota no Bling."
              mono
            />
            <DetailField
              label="Status atual"
              value={evento.pedido_status_atual}
              hint="Status mais recente conhecido do pedido local."
            />
            <DetailField
              label="SKU"
              value={evento.sku}
              hint="SKU do item impactado por esta etapa."
              mono
            />
          </div>
        </>
      )}
    </div>
  );
}

export {
  Badge,
  EventCard,
  IncidentCard,
  InfoHint,
  SummaryCard,
  friendlyErrorMessage,
  splitEventBuckets,
};
