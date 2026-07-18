import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  CreditCard,
  FileText,
  Lock,
  MessageCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MODULOS_INFO, useModulos } from "../contexts/ModulosContext";
import { buildSalesContactUrl, publicPlans, serviceInvoiceAddon } from "../data/publicPlans";
import { api } from "../services/api";

const WHATSAPP_NUMERO = "5518997401641";
const PLAN_OPTIONS = Object.entries(publicPlans).flatMap(([segment, plans]) =>
  plans.map((plan) => ({ ...plan, segment })),
);

function normalizedPlanCode(value) {
  return PLAN_OPTIONS.some((plan) => plan.id === value) ? value : "pet-start";
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function getStatusInfo(assinatura) {
  const status = assinatura?.status_efetivo || assinatura?.status || "trial";

  if (assinatura?.acesso_completo_durante_trial) {
    return {
      label: "Experiencia completa em andamento",
      tone: "blue",
      icon: Clock3,
      text: "Todos os modulos do CorePet permanecem liberados durante os primeiros 30 dias.",
    };
  }

  if (status === "active") {
    return {
      label: "Plano ativo",
      tone: "emerald",
      icon: CheckCircle2,
      text: "A empresa está ativa no plano contratado.",
    };
  }

  if (status === "expired") {
    return {
      label: "Trial encerrado",
      tone: "amber",
      icon: AlertTriangle,
      text: "O período de acesso completo terminou. Escolha um plano com nosso atendimento.",
    };
  }

  if (status === "blocked") {
    return {
      label: "Acesso em analise",
      tone: "rose",
      icon: Lock,
      text: "Entre em contato para regularizar o acesso da empresa.",
    };
  }

  if (status === "pending") {
    return {
      label: "Pagamento pendente",
      tone: "amber",
      icon: Clock3,
      text: "A assinatura foi criada e aguarda a confirmacao do pagamento.",
    };
  }

  if (["past_due", "refunded", "canceled"].includes(status)) {
    return {
      label: "Pagamento precisa de atencao",
      tone: "rose",
      icon: AlertTriangle,
      text: "Regularize a assinatura para manter os recursos do plano liberados.",
    };
  }

  return {
    label: "Trial em andamento",
    tone: "blue",
    icon: Clock3,
    text: "Todos os módulos do CorePet ficam liberados durante os primeiros 30 dias.",
  };
}

function trustedAsaasUrl(value) {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      (url.hostname === "asaas.com" || url.hostname.endsWith(".asaas.com"))
    );
  } catch {
    return false;
  }
}

function toneClasses(tone) {
  const map = {
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
    rose: "border-rose-200 bg-rose-50 text-rose-800",
  };
  return map[tone] || map.blue;
}

export default function MeuPlano() {
  const {
    assinaturaAtual,
    carregarModulos,
    modulosAtivos,
    modulosBetaPublicos,
    modulosForaOfertaPublica,
    planoAtual,
    trialPadrao,
  } = useModulos();
  const [billing, setBilling] = useState(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingError, setBillingError] = useState("");
  const [selectedPlan, setSelectedPlan] = useState(() => normalizedPlanCode(planoAtual));

  useEffect(() => {
    let active = true;
    api
      .get("/billing/asaas/status")
      .then((response) => {
        if (active) setBilling(response.data);
      })
      .catch(() => {
        if (active) setBilling(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setSelectedPlan(normalizedPlanCode(planoAtual));
  }, [planoAtual]);

  const statusInfo = getStatusInfo(assinaturaAtual);
  const StatusIcon = statusInfo.icon;
  const diasRestantes = assinaturaAtual?.dias_restantes_trial;
  const betaModules = (modulosBetaPublicos || [])
    .filter((modulo) => !(modulosForaOfertaPublica || []).includes(modulo))
    .slice(0, 8);
  const msgContratar = encodeURIComponent(
    "Olá! Quero escolher meu plano do CorePet após o período de acesso completo.",
  );
  const msgBeta = encodeURIComponent("Olá! Quero ajuda para escolher meu plano do CorePet.");
  const emTrial = Boolean(assinaturaAtual?.acesso_completo_durante_trial);
  const podeContratarNfse = ["veterinario", "banho_tosa"].some((modulo) =>
    (modulosAtivos || []).includes(modulo),
  );
  const nfseContactUrl = buildSalesContactUrl(
    "Olá! Quero ativar a emissão de NFS-e integrada ao CorePet por R$ 59,90 mensais.",
  );

  async function handleSubscribe() {
    if (billing?.checkout_url && trustedAsaasUrl(billing.checkout_url)) {
      window.location.assign(billing.checkout_url);
      return;
    }

    setBillingLoading(true);
    setBillingError("");
    try {
      const response = await api.post("/billing/asaas/subscriptions", {
        plan_code: selectedPlan,
        billing_type: "UNDEFINED",
      });
      setBilling(response.data);
      if (trustedAsaasUrl(response.data?.checkout_url)) {
        window.location.assign(response.data.checkout_url);
      } else {
        setBillingError(
          "A assinatura foi criada, mas o link de pagamento ainda esta sendo preparado.",
        );
      }
      await carregarModulos();
    } catch (error) {
      setBillingError(
        error.response?.data?.detail || "Nao foi possivel iniciar a assinatura agora.",
      );
    } finally {
      setBillingLoading(false);
    }
  }

  return (
    <main className="min-h-full bg-slate-50 p-4 md:p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-bold uppercase text-emerald-700">Assinatura</p>
            <h1 className="mt-1 text-2xl font-extrabold text-slate-950 md:text-3xl">Meu Plano</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              A contratação inicial é assistida: você conhece todo o CorePet por 30 dias e nossa
              equipe ajuda a escolher o melhor plano para continuar.
            </p>
          </div>
          <button
            type="button"
            onClick={carregarModulos}
            className="inline-flex w-fit items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Atualizar status
          </button>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
          <article className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <span
                  className={`inline-flex items-center gap-2 rounded-md border px-3 py-1 text-sm font-bold ${toneClasses(
                    statusInfo.tone,
                  )}`}
                >
                  <StatusIcon className="h-4 w-4" />
                  {statusInfo.label}
                </span>
                <h2 className="mt-4 text-xl font-extrabold text-slate-950">
                  {emTrial ? "Experiência CorePet Completa" : planoAtual || "Plano contratado"}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{statusInfo.text}</p>
              </div>
              <div className="rounded-md bg-slate-950 p-3 text-white">
                <CreditCard className="h-6 w-6" />
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-bold uppercase text-slate-500">Plano</p>
                <p className="mt-1 text-lg font-bold text-slate-950">{planoAtual || "basico"}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-bold uppercase text-slate-500">Trial</p>
                <p className="mt-1 text-lg font-bold text-slate-950">
                  {diasRestantes == null
                    ? `${trialPadrao?.dias || 30} dias`
                    : `${diasRestantes} dia(s)`}
                </p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-bold uppercase text-slate-500">Fim do trial</p>
                <p className="mt-1 text-lg font-bold text-slate-950">
                  {formatDate(assinaturaAtual?.trial_fim)}
                </p>
              </div>
            </div>

            <div className="mt-6 max-w-md">
              <label htmlFor="billing-plan" className="text-sm font-bold text-slate-800">
                Plano que deseja contratar
              </label>
              <select
                id="billing-plan"
                value={selectedPlan}
                onChange={(event) => {
                  setSelectedPlan(event.target.value);
                  setBilling(null);
                  setBillingError("");
                }}
                className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <optgroup label="Loja Pet">
                  {PLAN_OPTIONS.filter((plan) => plan.segment === "pet").map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - R$ {plan.price}/mes
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Veterinario">
                  {PLAN_OPTIONS.filter((plan) => plan.segment === "vet").map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - R$ {plan.price}/mes
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Banho e Tosa">
                  {PLAN_OPTIONS.filter((plan) => plan.segment === "grooming").map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - R$ {plan.price}/mes
                    </option>
                  ))}
                </optgroup>
              </select>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                O primeiro vencimento respeita o fim dos seus 30 dias de experiencia completa.
              </p>
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleSubscribe}
                disabled={billingLoading || !selectedPlan}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-500 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <CreditCard className="h-4 w-4" />
                {billingLoading
                  ? "Preparando pagamento..."
                  : billing?.checkout_url
                    ? "Abrir pagamento"
                    : "Assinar pelo Asaas"}
              </button>
              <a
                href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgContratar}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-500 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-emerald-400"
              >
                <MessageCircle className="h-4 w-4" />
                Falar sobre ativacao
              </a>
              <Link
                to="/planos"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Ver plano publico
              </Link>
            </div>
            {billingError && (
              <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-rose-800">
                {billingError}
              </p>
            )}
          </article>

          <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-md bg-violet-50 p-3 text-violet-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-950">Pagamento seguro pelo Asaas</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  O pagamento acontece na pagina protegida do Asaas. Boleto, Pix e as opcoes
                  disponiveis ficam fora do CorePet, e a liberacao ocorre automaticamente apos a
                  confirmacao.
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Como funciona</p>
              <ol className="mt-3 space-y-2">
                <li>1. Criar a empresa e receber 30 dias completos.</li>
                <li>2. Conhecer os módulos com acompanhamento humano.</li>
                <li>3. Escolher o plano ideal com nossa equipe.</li>
                <li>4. Pagar com seguranca e ter a liberacao automatica.</li>
              </ol>
            </div>
          </aside>
        </section>

        {podeContratarNfse && (
          <section className="overflow-hidden rounded-lg border border-amber-200 bg-white shadow-sm">
            <div className="grid gap-6 p-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-amber-100 p-3 text-amber-800">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold uppercase text-amber-700">Adicional opcional</p>
                  <h2 className="mt-1 text-xl font-extrabold text-slate-950">
                    {serviceInvoiceAddon.name}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Emissor fiscal parceiro conectado ao fluxo do CorePet.
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-4 rounded-lg bg-slate-50 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-2xl font-extrabold text-slate-950">
                    R$ {serviceInvoiceAddon.price}
                    <span className="text-sm font-semibold text-slate-500">/mês</span>
                  </p>
                  <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">
                    A liberação passa pela validação dos dados fiscais e da compatibilidade do seu
                    município.
                  </p>
                </div>
                <a
                  href={nfseContactUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex flex-none items-center justify-center gap-2 rounded-md bg-amber-300 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-amber-200"
                >
                  <MessageCircle className="h-4 w-4" />
                  Ativar NFS-e
                </a>
              </div>
            </div>
          </section>
        )}

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-bold uppercase text-violet-700">Experiência completa</p>
              <h2 className="mt-1 text-xl font-extrabold text-slate-950">
                Conheça os módulos antes de escolher
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Durante os primeiros 30 dias, os módulos do CorePet ficam liberados para você
                descobrir quais realmente geram valor para sua operação.
              </p>
            </div>
            <a
              href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgBeta}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center justify-center gap-2 rounded-md border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-bold text-violet-800 transition hover:bg-violet-100"
            >
              <Sparkles className="h-4 w-4" />
              Escolher meu plano
            </a>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {betaModules.map((modulo) => {
              const info = MODULOS_INFO[modulo] || { nome: modulo, descricao: "" };
              return (
                <article
                  key={modulo}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="text-sm font-bold text-slate-950">{info.nome}</p>
                  <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-600">
                    {info.descricao}
                  </p>
                  <p className="mt-3 inline-flex items-center gap-1 rounded-md bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800">
                    <Sparkles className="h-3 w-3" />
                    Incluído nos 30 dias
                  </p>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
