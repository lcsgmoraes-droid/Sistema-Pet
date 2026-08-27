import {
  FiCalendar,
  FiCheckCircle,
  FiClipboard,
  FiMessageSquare,
  FiUserCheck,
} from "react-icons/fi";

import { buildOpsTenantOnboardingForm, buildOpsTenantOnboardingPayload } from "../opsTenantsUtils";

import { ONBOARDING_SATISFACTION_OPTIONS } from "./opsTenantsConstants";
import { formatDate, formatDateOnly } from "./opsTenantsFormatters";

export default function OpsTenantsOnboardingPanel({
  tenant,
  form,
  error,
  success,
  saving,
  onChange,
  onSubmit,
  notes,
  notesLoading,
  noteText,
  noteError,
  noteSuccess,
  noteSaving,
  onNoteChange,
  onNoteSubmit,
}) {
  if (!tenant) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-500">
          Selecione uma empresa para registrar o acompanhamento.
        </div>
      </section>
    );
  }

  const original = buildOpsTenantOnboardingForm(tenant);
  const payload = buildOpsTenantOnboardingPayload(original, form);
  const hasChanges = Object.keys(payload).length > 0;
  const followUp = tenant.onboarding_follow_up || {};

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
          <FiClipboard className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-slate-900">Registro do acompanhamento</h2>
          <p className="mt-1 text-sm text-slate-500">
            Dados internos para conduzir o onboarding desta empresa.
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
        <div className="truncate text-sm font-bold text-slate-900">{tenant.name}</div>
        <div className="mt-1 text-xs font-semibold text-blue-700">
          {tenant.pilot?.next_action || "Revisar o onboarding desta empresa."}
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Responsavel pelo acompanhamento
          </span>
          <div className="relative mt-1">
            <FiUserCheck className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={form.owner_name}
              maxLength={160}
              placeholder="Ex.: Lucas"
              onChange={(event) => onChange("owner_name", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Proximo contato
          </span>
          <div className="relative mt-1">
            <FiCalendar className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input
              type="date"
              value={form.next_contact_on}
              onChange={(event) => onChange("next_contact_on", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <span className="mt-1 block text-xs text-slate-500">
            A fila destacara automaticamente contatos vencidos ou marcados para hoje.
          </span>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Data de desbloqueio
          </span>
          <input
            type="date"
            value={form.unblocked_on}
            onChange={(event) => onChange("unblocked_on", event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
          <span className="mt-1 block text-xs text-slate-500">
            Preencha quando um impedimento do onboarding for resolvido.
          </span>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Satisfacao inicial
          </span>
          <select
            value={form.satisfaction}
            onChange={(event) => onChange("satisfaction", event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          >
            {ONBOARDING_SATISFACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {followUp.updated_at ? (
          <div className="text-xs text-slate-500">
            Ultima atualizacao: {formatDate(followUp.updated_at)}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {success}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={!hasChanges || saving}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiCheckCircle className={`h-4 w-4 ${saving ? "animate-pulse" : ""}`} />
          Salvar acompanhamento
        </button>
      </form>

      <div className="my-5 border-t border-slate-200" />

      <div className="flex items-start gap-2">
        <FiMessageSquare className="mt-0.5 h-4 w-4 text-blue-700" />
        <div>
          <h3 className="text-sm font-bold text-slate-900">Historico de contatos</h3>
          <p className="mt-1 text-xs text-slate-500">
            Registros cronologicos nao podem ser editados ou apagados nesta tela.
          </p>
        </div>
      </div>

      <form onSubmit={onNoteSubmit} className="mt-3 space-y-2">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Nova nota interna
          </span>
          <textarea
            value={noteText}
            maxLength={1000}
            rows={4}
            placeholder="Ex.: Primeiro acesso validado e proximo retorno combinado."
            onChange={(event) => onNoteChange(event.target.value)}
            className="mt-1 w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
          <span className="mt-1 flex justify-between gap-3 text-xs text-slate-500">
            <span>Nao inclua senhas, documentos ou dados pessoais sensiveis.</span>
            <span>{noteText.length}/1000</span>
          </span>
        </label>

        {noteError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {noteError}
          </div>
        ) : null}
        {noteSuccess ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {noteSuccess}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={noteText.trim().length < 3 || noteSaving}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiMessageSquare className={`h-4 w-4 ${noteSaving ? "animate-pulse" : ""}`} />
          Registrar nota
        </button>
      </form>

      <div className="mt-4 space-y-2">
        {notesLoading ? (
          <div className="text-xs text-slate-500">Carregando historico...</div>
        ) : notes.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 px-3 py-4 text-center text-xs text-slate-500">
            Nenhum contato registrado ainda.
          </div>
        ) : (
          notes.map((item) => (
            <article key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="whitespace-pre-wrap break-words text-sm text-slate-700">{item.note}</p>
              <div className="mt-2 text-xs text-slate-500">
                {item.created_by?.label || "Administrador da plataforma"} ·{" "}
                {formatDate(item.created_at)}
              </div>
              {item.next_contact_on ? (
                <div className="mt-1 text-xs font-semibold text-blue-700">
                  Proximo contato naquele momento: {formatDateOnly(item.next_contact_on)}
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
