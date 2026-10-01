import { useState } from "react";
import { FiCheck, FiCopy, FiExternalLink, FiLink } from "react-icons/fi";

import { MODULOS_INFO, MODULOS_PREMIUM } from "../../contexts/ModulosContext";
import { formatMoneyBRL } from "../../utils/formatters";

import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheckGroup from "../../components/v2/InputCheckGroup/InputCheckGroup";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";

import { BILLING_OFFER_PLAN_OPTIONS, BILLING_TYPE_OPTIONS } from "./opsTenantsConstants";

const MODULO_OPCOES = MODULOS_PREMIUM.map((modulo) => ({
  value: modulo,
  label: MODULOS_INFO[modulo]?.nome || modulo,
}));

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

function validar(form) {
  const erros = {};
  if (!form.title.trim()) erros.title = "Informe o nome da proposta.";
  if (!(form.price > 0)) erros.price = "Informe uma mensalidade maior que zero.";
  if (!form.first_due_date) erros.first_due_date = "Informe o primeiro vencimento.";
  if (!form.scope_summary.trim()) erros.scope_summary = "Descreva o escopo contratado.";
  if (!form.implementation_summary.trim()) {
    erros.implementation_summary = "Descreva a implantação e migração.";
  }
  if (!form.exclusions_summary.trim()) {
    erros.exclusions_summary = "Descreva o que fica fora do escopo.";
  }
  if (!form.support_channel.trim()) erros.support_channel = "Informe o canal oficial de suporte.";
  return erros;
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
  const [tentouEnviar, setTentouEnviar] = useState(false);

  async function copyPublicUrl() {
    if (!publicUrl) return;
    await navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  if (!tenant) return null;

  const erros = tentouEnviar ? validar(form) : {};

  function handleSubmit(event) {
    event.preventDefault();
    const errosAtuais = validar(form);
    if (Object.keys(errosAtuais).length > 0) {
      setTentouEnviar(true);
      return;
    }
    onSubmit(event);
  }

  return (
    <div>
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

      <form onSubmit={handleSubmit} noValidate className="mt-4 space-y-3">
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
          <InputTexto
            id="oferta-titulo"
            label="Nome da proposta"
            value={form.title}
            onChange={(value) => onChange("title", value)}
            maxLength={160}
            error={erros.title}
            required
          />
          <InputCombobox
            id="oferta-plano"
            label="Plano-base"
            opcoes={BILLING_OFFER_PLAN_OPTIONS}
            value={form.plan_code}
            onChange={(value) => onChange("plan_code", value)}
            permitirLimpar={false}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <InputMoeda
            id="oferta-valor"
            label="Mensalidade"
            value={form.price}
            onChange={(value) => onChange("price", value)}
            error={erros.price}
            required
          />
          <InputData
            id="oferta-vencimento"
            label="Primeiro vencimento"
            value={form.first_due_date}
            onChange={(value) => onChange("first_due_date", value)}
            error={erros.first_due_date}
            required
          />
          <InputCombobox
            id="oferta-pagamento"
            label="Pagamento"
            opcoes={BILLING_TYPE_OPTIONS}
            value={form.billing_type}
            onChange={(value) => onChange("billing_type", value)}
            permitirLimpar={false}
          />
        </div>

        <InputCheckGroup
          name="oferta-modulos-extras"
          label="Módulos extras ao plano-base"
          opcoes={MODULO_OPCOES}
          value={form.extra_modules}
          onChange={(modulos) => {
            const adicionado = modulos.find((modulo) => !form.extra_modules.includes(modulo));
            const removido = form.extra_modules.find((modulo) => !modulos.includes(modulo));
            onToggleModule(adicionado || removido);
          }}
        />

        <fieldset className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
          <legend className="px-1 text-xs font-bold uppercase tracking-wide text-slate-500">
            Condições específicas da proposta
          </legend>
          <p className="text-xs leading-5 text-slate-500">
            Registre aqui o que foi prometido. Conversas fora da proposta não alteram o contrato.
          </p>

          <InputTextoLongo
            id="oferta-escopo"
            label="Escopo contratado"
            value={form.scope_summary}
            onChange={(value) => onChange("scope_summary", value)}
            maxLength={2000}
            linhas={3}
            error={erros.scope_summary}
            required
          />

          <InputTextoLongo
            id="oferta-implantacao"
            label="Implantação e migração"
            value={form.implementation_summary}
            onChange={(value) => onChange("implementation_summary", value)}
            maxLength={2000}
            linhas={3}
            error={erros.implementation_summary}
            required
          />

          <InputTextoLongo
            id="oferta-exclusoes"
            label="Fora do escopo e dependências"
            value={form.exclusions_summary}
            onChange={(value) => onChange("exclusions_summary", value)}
            maxLength={2000}
            linhas={3}
            error={erros.exclusions_summary}
            required
          />

          <div className="sm:max-w-xs">
            <InputTexto
              id="oferta-suporte"
              label="Canal oficial de suporte"
              value={form.support_channel}
              onChange={(value) => onChange("support_channel", value)}
              maxLength={200}
              error={erros.support_channel}
              required
            />
          </div>

          <InputTextoLongo
            id="oferta-sob-medida"
            label="Desenvolvimento sob medida (opcional)"
            value={form.custom_work_summary}
            onChange={(value) => onChange("custom_work_summary", value)}
            maxLength={2000}
            linhas={2}
          />

          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
            Padrão seguro: sem SLA contratual, sem fidelidade, suporte em dias úteis das 9h às 18h,
            exportação assistida solicitável por 30 dias e código reutilizável do CorePet. Exceções
            exigem anexo específico.
          </div>
        </fieldset>

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
            {success}
          </div>
        ) : null}

        <BotaoSalva loading={creating} larguraTotal>
          Gerar link de contratação
        </BotaoSalva>
      </form>

      {publicUrl ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900 dark:bg-emerald-950">
          <p className="text-xs font-bold uppercase text-emerald-800 dark:text-emerald-300">
            Link pronto para enviar
          </p>
          <p className="mt-2 break-all text-xs text-emerald-950 dark:text-emerald-100">
            {publicUrl}
          </p>
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

      <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
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
            <article
              key={offer.id}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-xs font-bold text-slate-900 dark:text-slate-100">
                    {offer.title}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {formatMoneyBRL(offer.price_cents / 100)} / mês · vence{" "}
                    {formatDateOnly(offer.first_due_date)}
                  </p>
                </div>
                <span
                  className={`flex-none rounded-full border px-2 py-1 text-xs font-bold ${statusClasses(offer.status)}`}
                >
                  {statusLabels[offer.status] || offer.status}
                </span>
              </div>
              {offer.extra_modules?.length ? (
                <p className="mt-2 text-[11px] leading-4 text-slate-500 dark:text-slate-400">
                  Extras:{" "}
                  {offer.extra_modules.map((item) => MODULOS_INFO[item]?.nome || item).join(", ")}
                </p>
              ) : null}
              {offer.commercial_terms ? (
                <p className="mt-2 text-[11px] leading-4 text-slate-500 dark:text-slate-400">
                  Suporte: {offer.commercial_terms.support.channel} · sem SLA contratual
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
