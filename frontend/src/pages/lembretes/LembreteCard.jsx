import {
  FiBell,
  FiCheckCircle,
  FiChevronDown,
  FiMessageCircle,
  FiRefreshCw,
  FiTrash2,
} from "react-icons/fi";
import { formatarDataHora, formatarMoeda } from "./lembretesFormatters";
import { TIPOS_LEMBRETE } from "./lembretesUtils";

export default function LembreteCard({ controller, lembrete }) {
  const days = lembrete.dias_restantes;
  const dueDate = new Date(lembrete.data_proxima_dose).toLocaleDateString("pt-BR");
  const lastContact = lembrete.ultimo_contato;
  const pushLoading = controller.acaoContato === `push-${lembrete.id}`;

  return (
    <article className="grid gap-4 p-4 transition hover:bg-slate-50/70 dark:hover:bg-slate-800/30 sm:p-5 xl:grid-cols-[160px_minmax(0,1fr)_auto] xl:items-center">
      <div>
        <span className={deadlineClass(days)}>{deadlineLabel(days)}</span>
        <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-200">{dueDate}</p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Previsão de retorno</p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 truncate text-base font-semibold text-slate-900 dark:text-slate-100">
            {lembrete.cliente_nome || "Cliente não informado"}
          </h3>
          {lembrete.pet_nome && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              • {lembrete.pet_nome}
            </span>
          )}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <p className="m-0 text-sm font-medium text-slate-700 dark:text-slate-300">
            {lembrete.produto_nome}
          </p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {TIPOS_LEMBRETE[lembrete.tipo_lembrete] || "Recorrência"}
          </span>
          {lembrete.dose_total > 1 && (
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
              Dose {lembrete.dose_atual}/{lembrete.dose_total}
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          {lembrete.intervalo_estimado_dias && (
            <span>Ciclo de {lembrete.intervalo_estimado_dias} dias</span>
          )}
          {lembrete.preco_estimado > 0 && (
            <span>Valor previsto {formatarMoeda(lembrete.preco_estimado)}</span>
          )}
          <span
            className={
              lembrete.contatado_hoje ? "font-semibold text-amber-700 dark:text-amber-300" : ""
            }
          >
            <FiMessageCircle aria-hidden="true" className="mr-1 inline" />
            {lembrete.contatos_total || 0} contato(s) neste ciclo
            {lastContact?.criado_em
              ? ` · último em ${formatarDataHora(lastContact.criado_em)}`
              : ""}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 xl:justify-end">
        <button
          className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
          onClick={() => controller.abrirContato(lembrete)}
          type="button"
        >
          <FiMessageCircle aria-hidden="true" /> Criar mensagem
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          disabled={!lembrete.cliente_tem_app || pushLoading}
          onClick={() => controller.enviarPush(lembrete)}
          title={
            lembrete.cliente_tem_app
              ? "Enviar notificação no app"
              : "Cliente sem conta vinculada no app"
          }
          type="button"
        >
          <FiBell className={pushLoading ? "animate-pulse" : ""} aria-hidden="true" />
          {pushLoading ? "Enviando..." : "Push"}
        </button>
        <details className="relative">
          <summary className="flex cursor-pointer list-none items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800">
            Mais <FiChevronDown aria-hidden="true" />
          </summary>
          <div className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl dark:border-slate-700 dark:bg-slate-900">
            <Action
              icon={FiCheckCircle}
              label="Registrar recompra"
              onClick={() => controller.completarLembrete(lembrete.id)}
            />
            <Action
              icon={FiRefreshCw}
              label="Criar próximo ciclo"
              onClick={() => controller.renovarLembrete(lembrete.id)}
            />
            <Action
              danger
              icon={FiTrash2}
              label="Cancelar lembrete"
              onClick={() => controller.cancelarLembrete(lembrete.id)}
            />
          </div>
        </details>
      </div>
    </article>
  );
}

function Action({ danger = false, icon: Icon, label, onClick }) {
  return (
    <button
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition ${
        danger
          ? "text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10"
          : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
      }`}
      onClick={onClick}
      type="button"
    >
      <Icon aria-hidden="true" /> {label}
    </button>
  );
}

function deadlineLabel(days) {
  if (days < 0) return `${Math.abs(days)} dia(s) atrasado`;
  if (days === 0) return "Retorno hoje";
  return `Faltam ${days} dia(s)`;
}

function deadlineClass(days) {
  const base = "inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset";
  if (days < 0) {
    return `${base} bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30`;
  }
  if (days <= 7) {
    return `${base} bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30`;
  }
  return `${base} bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700`;
}
