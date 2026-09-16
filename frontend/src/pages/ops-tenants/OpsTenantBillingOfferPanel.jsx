import { useState } from "react";
import { FiCheck, FiCopy, FiExternalLink, FiLink, FiPlusCircle } from "react-icons/fi";

import CurrencyInput from "../../components/CurrencyInput";
import { MODULOS_INFO, MODULOS_PREMIUM } from "../../contexts/ModulosContext";
import { formatMoneyBRL } from "../../utils/formatters";

import { BILLING_OFFER_PLAN_OPTIONS, BILLING_TYPE_OPTIONS } from "./opsTenantsConstants";

function formatDateOnly(value) {
  if (!value) return "-";
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString("pt-BR");
}

const statusLabels = {
  ready: "Link pronto",
  accepted: "Aceito / aguardando pagamento",
  active: "Pago e ativo",
  past_due: "Vencido",
  blocked: "Bloqueado",
  expired: "Expirado",
  replaced: "Substituído",
};

function statusClasses(status) {
  if (status === "active") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (["past_due", "blocked", "expired"].includes(status)) {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (status === "accepted") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export default function OpsTenantBillingOfferPanel({
  tenant,
  form,
  offers,
  loadingOffers,
  creating,
  error,
  success,
  publicUrl,
  onChange,
  onToggleModule,
  onSubmit,
}) {
  const [copied, setCopied] = useState(false);

  async function copyPublicUrl() {
    if (!publicUrl) return;
    await navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  if (!tenant) return null;

  return (
    <section className="rounded-lg border border-emerald-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
          <FiLink className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-slate-950">Link de contratação personalizado</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            O cliente aceita a proposta e o Asaas acompanha a mensalidade automaticamente.
          </p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Nome da proposta
          </span>
          <input
            value={form.title}
            onChange={(event) => onChange("title", event.target.value)}
            maxLength={160}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Plano-base
          </span>
          <select
            value={form.plan_code}
            onChange={(event) => onChange("plan_code", event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold"
          >
            {BILLING_OFFER_PLAN_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Mensalidade personalizada
          </span>
          <div className="mt-1 flex h-10 items-center rounded-lg border border-slate-300 bg-white px-3">
            <span className="mr-2 text-sm font-bold text-slate-500">R$</span>
            <CurrencyInput
              value={form.price}
              onChange={(value) => onChange("price", value)}
              maxValue={100000}
              className="min-w-0 flex-1 bg-transparent text-sm font-bold text-slate-900 outline-none"
            />
          </div>
        </label>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              Primeiro vencimento
            </span>
            <input
              type="date"
              value={form.first_due_date}
              onChange={(event) => onChange("first_due_date", event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              Pagamento
            </span>
            <select
              value={form.billing_type}
              onChange={(event) => onChange("billing_type", event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
            >
              {BILLING_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <fieldset>
          <legend className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Módulos extras ao plano-base
          </legend>
          <div className="mt-2 grid max-h-48 gap-2 overflow-y-auto rounded-lg border border-slate-200 p-2">
            {MODULOS_PREMIUM.map((module) => (
              <label
                key={module}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={form.extra_modules.includes(module)}
                  onChange={() => onToggleModule(module)}
                  className="h-4 w-4 rounded border-slate-300 text-emerald-600"
                />
                <span>{MODULOS_INFO[module]?.nome || module}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <legend className="px-1 text-xs font-bold uppercase tracking-wide text-slate-500">
            Condições específicas da proposta
          </legend>
          <p className="text-xs leading-5 text-slate-500">
            Registre aqui o que foi prometido. Conversas fora da proposta não alteram o contrato.
          </p>

          <label className="block">
            <span className="text-xs font-bold text-slate-700">Escopo contratado</span>
            <textarea
              required
              value={form.scope_summary}
              onChange={(event) => onChange("scope_summary", event.target.value)}
              minLength={10}
              maxLength={2000}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-xs font-bold text-slate-700">Implantação e migração</span>
            <textarea
              required
              value={form.implementation_summary}
              onChange={(event) => onChange("implementation_summary", event.target.value)}
              minLength={10}
              maxLength={2000}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-xs font-bold text-slate-700">Fora do escopo e dependências</span>
            <textarea
              required
              value={form.exclusions_summary}
              onChange={(event) => onChange("exclusions_summary", event.target.value)}
              minLength={10}
              maxLength={2000}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-xs font-bold text-slate-700">Canal oficial de suporte</span>
            <input
              required
              value={form.support_channel}
              onChange={(event) => onChange("support_channel", event.target.value)}
              minLength={3}
              maxLength={200}
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-xs font-bold text-slate-700">Desenvolvimento sob medida</span>
            <textarea
              value={form.custom_work_summary}
              onChange={(event) => onChange("custom_work_summary", event.target.value)}
              maxLength={2000}
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>

          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
            Padrão seguro: sem SLA contratual, sem fidelidade, suporte em dias úteis das 9h às 18h,
            exportação assistida solicitável por 30 dias e código reutilizável do CorePet. Exceções
            exigem anexo específico.
          </div>
        </fieldset>

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
          disabled={
            creating ||
            !form.title.trim() ||
            form.price <= 0 ||
            !form.first_due_date ||
            !form.scope_summary.trim() ||
            !form.implementation_summary.trim() ||
            !form.exclusions_summary.trim() ||
            !form.support_channel.trim()
          }
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-bold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiPlusCircle className="h-4 w-4" />
          {creating ? "Gerando..." : "Gerar link de contratação"}
        </button>
      </form>

      {publicUrl ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <p className="text-xs font-bold uppercase text-emerald-800">Link pronto para enviar</p>
          <p className="mt-2 break-all text-xs text-emerald-950">{publicUrl}</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={copyPublicUrl}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-emerald-700 px-3 text-xs font-bold text-white"
            >
              {copied ? <FiCheck /> : <FiCopy />}
              {copied ? "Copiado" : "Copiar"}
            </button>
            <a
              href={publicUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-emerald-300 bg-white px-3 text-xs font-bold text-emerald-800"
            >
              <FiExternalLink />
              Conferir
            </a>
          </div>
        </div>
      ) : null}

      <div className="mt-5 border-t border-slate-200 pt-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Propostas recentes
          </h3>
          {loadingOffers ? <span className="text-xs text-slate-400">carregando</span> : null}
        </div>
        <div className="mt-2 space-y-2">
          {!loadingOffers && offers.length === 0 ? (
            <p className="text-xs text-slate-500">Nenhuma proposta gerada para esta empresa.</p>
          ) : null}
          {offers.map((offer) => (
            <article key={offer.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-xs font-bold text-slate-900">{offer.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatMoneyBRL(offer.price_cents / 100)} / mês · vence{" "}
                    {formatDateOnly(offer.first_due_date)}
                  </p>
                </div>
                <span
                  className={`flex-none rounded-full border px-2 py-1 text-[10px] font-bold ${statusClasses(offer.status)}`}
                >
                  {statusLabels[offer.status] || offer.status}
                </span>
              </div>
              {offer.extra_modules?.length ? (
                <p className="mt-2 text-[11px] leading-4 text-slate-500">
                  Extras:{" "}
                  {offer.extra_modules.map((item) => MODULOS_INFO[item]?.nome || item).join(", ")}
                </p>
              ) : null}
              {offer.commercial_terms ? (
                <p className="mt-2 text-[11px] leading-4 text-slate-500">
                  Suporte: {offer.commercial_terms.support.channel} · sem SLA contratual
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
