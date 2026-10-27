import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FiActivity,
  FiAlertTriangle,
  FiCheckCircle,
  FiDatabase,
  FiLink,
  FiRefreshCw,
  FiSend,
  FiXCircle,
} from "react-icons/fi";
import { api } from "../../services/api";
import { confirmarCorePet } from "../../services/corepetDialog";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCheck from "../../components/v2/InputCheck/InputCheck";
import AmazonFiscalPanel from "./amazonFiscal/AmazonFiscalPanel";
import { fiscalError, SCOPE_LABELS } from "./amazonFiscal/amazonFiscalUtils";

const money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : dateTime.format(parsed);
}

export default function EcommerceAIIntegracaoCard() {
  const requestId = useMemo(
    () => new URLSearchParams(globalThis.location.search).get("ecommerceai_request"),
    [],
  );
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState(null);
  const [message, setMessage] = useState(null);
  const [fiscalConsent, setFiscalConsent] = useState(false);
  const actionRef = useRef(false);

  const load = useCallback(
    async ({ active = () => true, preserveMessage = false } = {}) => {
      try {
        const response = await api.get("/integracoes/ecommerceai/status", {
          params: requestId ? { request_id: requestId } : undefined,
        });
        if (!active()) return;
        setData(response.data);
        if (!preserveMessage) setMessage(null);
      } catch (error) {
        const text = await fiscalError(error);
        if (active())
          setMessage({
            type: "error",
            text,
          });
      } finally {
        if (active()) setLoading(false);
      }
    },
    [requestId],
  );

  useEffect(() => {
    let active = true;
    void load({ active: () => active });
    return () => {
      active = false;
    };
  }, [load]);

  async function approve() {
    if (!requestId || actionRef.current) return;
    const requestsFiscal = data?.request?.requested_scopes?.some((scope) =>
      scope.startsWith("fiscal:"),
    );
    if (requestsFiscal && !fiscalConsent) return;
    actionRef.current = true;
    try {
      setAction("approve");
      await api.post(
        `/integracoes/ecommerceai/requests/${requestId}/approve`,
        requestsFiscal ? { confirm_fiscal_scopes: true } : undefined,
      );
      setMessage({ type: "success", text: "EcommerceAI conectado com sucesso." });
      await load({ preserveMessage: true });
    } catch (error) {
      setMessage({
        type: "error",
        text: await fiscalError(error),
      });
      await load({ preserveMessage: true });
    } finally {
      actionRef.current = false;
      setAction(null);
    }
  }

  async function reject() {
    if (!requestId || actionRef.current) return;
    actionRef.current = true;
    try {
      setAction("reject");
      await api.post(`/integracoes/ecommerceai/requests/${requestId}/reject`);
      setMessage({ type: "success", text: "Solicitação recusada." });
      await load({ preserveMessage: true });
    } catch (error) {
      setMessage({
        type: "error",
        text: await fiscalError(error),
      });
    } finally {
      actionRef.current = false;
      setAction(null);
    }
  }

  async function disconnect() {
    if (actionRef.current) return;
    if (!(await confirmarCorePet("Desconectar o EcommerceAI do CorePet?"))) return;
    if (actionRef.current) return;
    actionRef.current = true;
    try {
      setAction("disconnect");
      await api.post("/integracoes/ecommerceai/disconnect");
      setMessage({ type: "success", text: "Integração desconectada." });
      await load({ preserveMessage: true });
    } catch (error) {
      setMessage({
        type: "error",
        text: await fiscalError(error),
      });
    } finally {
      actionRef.current = false;
      setAction(null);
    }
  }

  const connection = data?.connection;
  const pendingRequest = data?.request;
  const overview = data?.latest_overview;
  const isPending = ["pending", "callback_failed"].includes(pendingRequest?.status);
  const fiscalRequested = pendingRequest?.requested_scopes?.some((scope) =>
    scope.startsWith("fiscal:"),
  );

  return (
    <section className="rounded-2xl border border-cyan-100 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-cyan-100 p-2 text-cyan-700">
            <FiLink size={18} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">EcommerceAI</h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Recebe indicadores, vendas e eventos processados pelo EcommerceAI e permite que ele
              consulte o cadastro completo de produtos, custos, preços e estoque do CorePet.
            </p>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${
            data?.connected
              ? "bg-emerald-100 text-emerald-700"
              : isPending
                ? "bg-amber-100 text-amber-700"
                : "bg-slate-100 text-slate-600"
          }`}
        >
          {data?.connected ? <FiCheckCircle /> : isPending ? <FiAlertTriangle /> : <FiLink />}
          {data?.connected ? "Conectado" : isPending ? "Aceite pendente" : "Não conectado"}
        </span>
      </div>

      {message && (
        <div
          className={`mt-4 rounded-xl border px-4 py-3 text-sm ${
            message.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="mt-5 flex items-center gap-2 text-sm text-slate-500">
          <FiRefreshCw className="animate-spin" /> Consultando integração...
        </div>
      ) : null}

      {!loading && isPending ? (
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <FiAlertTriangle className="mt-0.5 shrink-0 text-amber-600" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-amber-900">O EcommerceAI quer acessar esta empresa</p>
              <p className="mt-1 text-sm text-amber-800">
                Conta:{" "}
                {pendingRequest.account_name || pendingRequest.account_email || "EcommerceAI"}
              </p>
              <p className="mt-1 text-xs text-amber-700">
                Permissões solicitadas abaixo. Expira em {formatDate(pendingRequest.expires_at)}.
              </p>
              <ul className="mt-2 list-inside list-disc text-sm text-amber-900 dark:text-amber-200">
                {(pendingRequest.requested_scopes || []).map((scope) => (
                  <li key={scope}>{SCOPE_LABELS[scope] || scope}</li>
                ))}
              </ul>
              {fiscalRequested && (
                <div className="mt-3">
                  <InputCheck
                    id="ecommerceai-fiscal-scope-consent"
                    label="Autorizo as permissões fiscais solicitadas para esta empresa"
                    checked={fiscalConsent}
                    onChange={setFiscalConsent}
                    disabled={Boolean(action)}
                    help="Preparação, emissão e consulta somente nos escopos acima. A emissão automática também exige ativação da conta fiscal."
                  />
                </div>
              )}
              {pendingRequest.callback_error ? (
                <p className="mt-2 text-xs text-red-700">
                  A confirmação anterior falhou. Você pode tentar aprovar novamente.
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <BotaoInteracao
                  type="button"
                  onClick={approve}
                  disabled={Boolean(action) || (fiscalRequested && !fiscalConsent)}
                >
                  <FiCheckCircle /> {action === "approve" ? "Conectando..." : "Aceitar e conectar"}
                </BotaoInteracao>
                {pendingRequest.status === "pending" ? (
                  <BotaoCancelar type="button" onClick={reject} disabled={Boolean(action)}>
                    <FiXCircle /> Recusar
                  </BotaoCancelar>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {!loading && !data?.connected && !isPending ? (
        <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
          Inicie a conexão na tela de Integrações do EcommerceAI. Ele abrirá esta página para o
          aceite seguro.
        </div>
      ) : null}

      {data?.connected ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Conta</p>
              <p className="mt-1 truncate text-sm font-medium text-slate-900">
                {connection?.account_name || connection?.account_email || "EcommerceAI"}
              </p>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Último evento</p>
              <p className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(connection?.last_event_at)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Última leitura do catálogo
              </p>
              <p className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(connection?.last_catalog_read_at)}
              </p>
            </div>
          </div>

          {overview ? (
            <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50 p-4">
              <div className="flex items-center gap-2 text-indigo-900">
                <FiActivity />
                <p className="font-medium">Resultado recebido do EcommerceAI</p>
              </div>
              <p className="mt-1 text-xs text-indigo-700">
                {overview.period?.label || "Período enviado"} · atualizado em{" "}
                {formatDate(overview.last_updated)}
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-indigo-600">Base de vendas</p>
                  <p className="font-semibold text-indigo-950">
                    {money.format(overview.sales_base || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-indigo-600">Margem de contribuição</p>
                  <p className="font-semibold text-indigo-950">
                    {money.format(overview.contribution_margin || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-indigo-600">Margem</p>
                  <p className="font-semibold text-indigo-950">
                    {Number(overview.contribution_margin_pct || 0).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-indigo-600">Pedidos</p>
                  <p className="font-semibold text-indigo-950">{overview.orders || 0}</p>
                </div>
              </div>
            </div>
          ) : null}

          <div className="mt-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                <FiSend /> Últimos recebimentos
              </div>
              <BotaoInteracao
                type="button"
                onClick={() => void load()}
                aria-label="Atualizar integração"
              >
                <FiRefreshCw />
              </BotaoInteracao>
            </div>
            <div className="mt-2 overflow-hidden rounded-xl border border-slate-100">
              {(data.events || []).length ? (
                (data.events || []).slice(0, 8).map((event) => (
                  <div
                    key={event.event_id}
                    className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-sm last:border-b-0"
                  >
                    <div>
                      <p className="font-medium text-slate-800">{event.event_type}</p>
                      <p className="text-xs text-slate-500">{formatDate(event.received_at)}</p>
                    </div>
                    <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs text-emerald-700">
                      {event.status}
                    </span>
                  </div>
                ))
              ) : (
                <div className="flex items-center gap-2 px-3 py-4 text-sm text-slate-500">
                  <FiDatabase /> Nenhum evento recebido ainda.
                </div>
              )}
            </div>
          </div>

          <div className="mt-5 flex justify-end">
            <BotaoCancelar type="button" onClick={disconnect} disabled={Boolean(action)}>
              {action === "disconnect" ? "Desconectando..." : "Desconectar"}
            </BotaoCancelar>
          </div>
        </>
      ) : null}
      {!loading && <AmazonFiscalPanel scopes={connection?.scopes || []} />}
    </section>
  );
}
