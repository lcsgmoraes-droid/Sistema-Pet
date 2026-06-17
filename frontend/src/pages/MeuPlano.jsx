import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  CreditCard,
  Lock,
  MessageCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { MODULOS_INFO, useModulos } from "../contexts/ModulosContext";

const WHATSAPP_NUMERO = "5518997401641";

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

  if (status === "active") {
    return {
      label: "Plano ativo",
      tone: "emerald",
      icon: CheckCircle2,
      text: "A empresa esta ativa no Plano Basico.",
    };
  }

  if (status === "expired") {
    return {
      label: "Trial encerrado",
      tone: "amber",
      icon: AlertTriangle,
      text: "Fale com atendimento para ativar o Plano Basico e manter a operacao regular.",
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

  return {
    label: "Trial em andamento",
    tone: "blue",
    icon: Clock3,
    text: "Use o Plano Basico por 30 dias e contrate com atendimento assistido.",
  };
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
    modulosBetaPublicos,
    modulosForaOfertaPublica,
    planoAtual,
    trialPadrao,
  } = useModulos();

  const statusInfo = getStatusInfo(assinaturaAtual);
  const StatusIcon = statusInfo.icon;
  const diasRestantes = assinaturaAtual?.dias_restantes_trial;
  const betaModules = (modulosBetaPublicos || [])
    .filter((modulo) => !(modulosForaOfertaPublica || []).includes(modulo))
    .slice(0, 8);
  const msgContratar = encodeURIComponent(
    "Ola! Quero ativar meu Plano Basico do CorePet apos o periodo gratuito.",
  );
  const msgBeta = encodeURIComponent("Ola! Quero solicitar acesso Beta a um modulo do CorePet.");

  return (
    <main className="min-h-full bg-slate-50 p-4 md:p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-bold uppercase text-emerald-700">Assinatura</p>
            <h1 className="mt-1 text-2xl font-extrabold text-slate-950 md:text-3xl">Meu Plano</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              A contratacao inicial e assistida: voce usa o Plano Basico no trial, fala com
              atendimento e a ativacao e registrada manualmente.
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
                <h2 className="mt-4 text-xl font-extrabold text-slate-950">Plano Basico</h2>
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

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
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
          </article>

          <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-md bg-violet-50 p-3 text-violet-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-950">Sem pagamento integrado</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Por enquanto, a cobranca e feita fora do sistema. Depois da confirmacao, o acesso
                  e ativado manualmente pelo administrativo.
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Fluxo atual</p>
              <ol className="mt-3 space-y-2">
                <li>1. Criar empresa com 30 dias gratis.</li>
                <li>2. Usar o Plano Basico no trial.</li>
                <li>3. Confirmar pagamento com atendimento.</li>
                <li>4. Administrativo ativa o plano manualmente.</li>
              </ol>
            </div>
          </aside>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-bold uppercase text-violet-700">Beta acompanhado</p>
              <h2 className="mt-1 text-xl font-extrabold text-slate-950">
                Modulos que podem entrar depois
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Eles aparecem como pilotos controlados. O trial padrao continua focado no Plano
                Basico para reduzir risco na primeira venda.
              </p>
            </div>
            <a
              href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgBeta}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center justify-center gap-2 rounded-md border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-bold text-violet-800 transition hover:bg-violet-100"
            >
              <Sparkles className="h-4 w-4" />
              Solicitar Beta
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
                    <Lock className="h-3 w-3" />
                    Beta
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
