import { Check, CheckCircle2, Clock3, ExternalLink, FileText, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "../api";
import { MODULOS_INFO } from "../contexts/ModulosContext";
import {
  BILLING_ACCEPTANCE_TEXT,
  BILLING_CONTRACT_DOCUMENT_SHA256,
  BILLING_CONTRACT_VERSION,
} from "../data/billingContract";
import { formatMoneyBRL } from "../utils/formatters";

const billingTypeLabels = {
  UNDEFINED: "Forma escolhida na página segura do Asaas",
  CREDIT_CARD: "Cartão de crédito recorrente",
  PIX: "PIX mensal",
  BOLETO: "Boleto mensal",
};

function formatDateOnly(value) {
  if (!value) return "-";
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("pt-BR");
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

function statusContent(status) {
  if (status === "active") {
    return {
      title: "Pagamento confirmado",
      text: "A assinatura está ativa e o CorePet já recebeu a confirmação do Asaas.",
      classes: "border-emerald-200 bg-emerald-50 text-emerald-800",
      Icon: CheckCircle2,
    };
  }
  if (["past_due", "blocked"].includes(status)) {
    return {
      title: "Pagamento precisa de atenção",
      text: "Abra a cobrança do Asaas para consultar ou regularizar a mensalidade.",
      classes: "border-rose-200 bg-rose-50 text-rose-800",
      Icon: Clock3,
    };
  }
  return {
    title: "Proposta aceita",
    text: "A assinatura foi preparada. O pagamento pode ser concluído no ambiente seguro do Asaas.",
    classes: "border-amber-200 bg-amber-50 text-amber-900",
    Icon: Clock3,
  };
}

export default function BillingOfferPublicPage() {
  const { token } = useParams();
  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [form, setForm] = useState({
    representative_name: "",
    representative_email: "",
    representative_role: "Proprietário(a)",
  });

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get(`/billing/asaas/offers/public/${encodeURIComponent(token)}`)
      .then((response) => {
        if (active) setOffer(response.data);
      })
      .catch((requestError) => {
        if (active) {
          setError(
            requestError.response?.data?.detail ||
              "Não foi possível abrir esta proposta de contratação.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function handleAccept(event) {
    event.preventDefault();
    if (!accepted) {
      setError("Confirme o aceite dos documentos para continuar.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const response = await api.post(
        `/billing/asaas/offers/public/${encodeURIComponent(token)}/accept`,
        {
          ...form,
          accepted: true,
          contract_version: BILLING_CONTRACT_VERSION,
          contract_document_sha256: BILLING_CONTRACT_DOCUMENT_SHA256,
          client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        },
      );
      setOffer(response.data);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Não foi possível preparar a assinatura. Tente novamente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <p className="text-sm font-semibold text-slate-500">Abrindo proposta segura...</p>
      </main>
    );
  }

  if (!offer) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <section className="max-w-lg rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-black text-slate-950">Proposta indisponível</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">{error}</p>
          <Link to="/landing" className="mt-6 inline-flex font-bold text-emerald-700 underline">
            Conhecer o CorePet
          </Link>
        </section>
      </main>
    );
  }

  const alreadyAccepted = offer.status !== "ready";
  const paymentUrl = trustedAsaasUrl(offer.checkout_url) ? offer.checkout_url : "";
  const status = statusContent(offer.status);
  const StatusIcon = status.Icon;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/landing" className="flex items-center gap-3 font-black">
            <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-9 w-9 rounded-lg" />
            CorePet
          </Link>
          <span className="inline-flex items-center gap-2 text-xs font-bold text-emerald-700">
            <ShieldCheck className="h-4 w-4" />
            Contratação segura
          </span>
        </div>
      </header>

      <div className="mx-auto grid max-w-5xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:py-12">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-black uppercase tracking-[0.14em] text-emerald-700">
            Proposta de assinatura
          </p>
          <h1 className="mt-3 text-3xl font-black tracking-tight">{offer.title}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Preparada para <strong>{offer.tenant.name}</strong>.
          </p>

          <div className="mt-7 rounded-2xl bg-slate-950 p-6 text-white">
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
              Mensalidade
            </p>
            <p className="mt-2 text-4xl font-black">
              {formatMoneyBRL(offer.price_cents / 100)}
              <span className="ml-2 text-sm font-semibold text-slate-400">/ mês</span>
            </p>
            <div className="mt-5 grid gap-3 border-t border-white/10 pt-5 text-sm sm:grid-cols-2">
              <div>
                <p className="text-xs text-slate-400">Plano-base</p>
                <p className="mt-1 font-bold">{offer.plan.name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Primeiro vencimento</p>
                <p className="mt-1 font-bold">{formatDateOnly(offer.first_due_date)}</p>
              </div>
            </div>
          </div>

          <div className="mt-7">
            <h2 className="text-sm font-black uppercase tracking-wide text-slate-700">
              Módulos incluídos
            </h2>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {offer.included_modules.map((module) => (
                <div
                  key={module}
                  className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700"
                >
                  <Check className="h-4 w-4 flex-none text-emerald-600" />
                  {MODULOS_INFO[module]?.nome || module}
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              {billingTypeLabels[offer.billing_type] || offer.billing_type}. O ciclo é mensal e
              continua enquanto a assinatura permanecer ativa.
            </p>
          </div>
        </section>

        <aside className="self-start rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          {alreadyAccepted ? (
            <div>
              <div className={`rounded-xl border p-4 ${status.classes}`}>
                <div className="flex items-start gap-3">
                  <StatusIcon className="mt-0.5 h-5 w-5 flex-none" />
                  <div>
                    <h2 className="font-black">{status.title}</h2>
                    <p className="mt-1 text-sm leading-6">{status.text}</p>
                  </div>
                </div>
              </div>
              {offer.representative ? (
                <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                  <p className="font-bold text-slate-900">Aceite registrado</p>
                  <p className="mt-2">{offer.representative.name}</p>
                  <p>{offer.representative.email}</p>
                </div>
              ) : null}
              {paymentUrl ? (
                <a
                  href={paymentUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 text-sm font-black text-white hover:bg-emerald-700"
                >
                  Abrir pagamento no Asaas
                  <ExternalLink className="h-4 w-4" />
                </a>
              ) : (
                <p className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
                  A cobrança está sendo preparada. Atualize esta página em alguns instantes.
                </p>
              )}
            </div>
          ) : (
            <form onSubmit={handleAccept}>
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-emerald-700" />
                <h2 className="text-lg font-black">Aceite da contratação</h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Preencha os dados de quem representa a empresa e revise os documentos.
              </p>

              <div className="mt-5 space-y-4">
                <label className="block text-sm font-bold text-slate-700">
                  Nome completo
                  <input
                    required
                    minLength={3}
                    value={form.representative_name}
                    onChange={(event) => updateForm("representative_name", event.target.value)}
                    className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="block text-sm font-bold text-slate-700">
                  E-mail
                  <input
                    required
                    type="email"
                    value={form.representative_email}
                    onChange={(event) => updateForm("representative_email", event.target.value)}
                    className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="block text-sm font-bold text-slate-700">
                  Cargo ou função
                  <input
                    value={form.representative_role}
                    onChange={(event) => updateForm("representative_role", event.target.value)}
                    className="mt-1 h-11 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
              </div>

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                <p>{BILLING_ACCEPTANCE_TEXT}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 font-bold text-emerald-700">
                  <Link to="/contrato-assinatura" target="_blank">
                    Contrato
                  </Link>
                  <Link to="/termos" target="_blank">
                    Termos de Uso
                  </Link>
                  <Link to="/privacidade" target="_blank">
                    Política de Privacidade
                  </Link>
                </div>
              </div>

              <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm leading-6 text-slate-700">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(event) => {
                    setAccepted(event.target.checked);
                    setError("");
                  }}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-600"
                />
                <span>Confirmo que li, aceito a proposta e posso representar a empresa.</span>
              </label>

              {error ? (
                <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting || !accepted}
                className="mt-5 inline-flex h-12 w-full items-center justify-center rounded-xl bg-emerald-600 px-4 text-sm font-black text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Preparando assinatura..." : "Aceitar e continuar para pagamento"}
              </button>
            </form>
          )}
        </aside>
      </div>
    </main>
  );
}
