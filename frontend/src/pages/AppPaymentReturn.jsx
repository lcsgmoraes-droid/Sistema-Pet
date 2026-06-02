import { useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FiCheckCircle, FiClock, FiXCircle } from "react-icons/fi";

const STATUS_COPY = {
  success: {
    icon: FiCheckCircle,
    title: "Pagamento confirmado",
    message: "Estamos voltando para seus pedidos no app CorePet.",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  pending: {
    icon: FiClock,
    title: "Pagamento em analise",
    message: "Estamos voltando para seus pedidos no app CorePet.",
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  failure: {
    icon: FiXCircle,
    title: "Pagamento nao concluido",
    message: "Volte ao app para tentar novamente ou acompanhar o pedido.",
    color: "text-red-600",
    bg: "bg-red-50",
  },
};

export default function AppPaymentReturn() {
  const [searchParams] = useSearchParams();
  const paymentStatus = searchParams.get("payment_status") || "pending";
  const pedidoId = searchParams.get("pedido_id") || "";
  const loja =
    searchParams.get("loja") ||
    searchParams.get("tenant") ||
    searchParams.get("store") ||
    "";
  const statusCopy = STATUS_COPY[paymentStatus] || STATUS_COPY.pending;
  const Icon = statusCopy.icon;

  const deepLink = useMemo(() => {
    const params = new URLSearchParams();
    if (paymentStatus) params.set("payment_status", paymentStatus);
    if (pedidoId) params.set("pedido_id", pedidoId);
    if (loja) params.set("loja", loja);
    return `corepet://app/pedidos${params.toString() ? `?${params.toString()}` : ""}`;
  }, [paymentStatus, pedidoId, loja]);

  const androidIntentLink = useMemo(() => {
    const params = new URLSearchParams();
    if (paymentStatus) params.set("payment_status", paymentStatus);
    if (pedidoId) params.set("pedido_id", pedidoId);
    if (loja) params.set("loja", loja);
    const query = params.toString();
    return `intent://app/pedidos${query ? `?${query}` : ""}#Intent;scheme=corepet;package=br.com.corepet.app;end`;
  }, [paymentStatus, pedidoId, loja]);

  const appOpenLink = useMemo(() => {
    if (typeof navigator !== "undefined" && /Android/i.test(navigator.userAgent || "")) {
      return androidIntentLink;
    }
    return deepLink;
  }, [androidIntentLink, deepLink]);

  const fallbackAppUrl = useMemo(() => {
    if (!loja) return "/app";
    return `/app?loja=${encodeURIComponent(loja)}`;
  }, [loja]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      window.location.href = appOpenLink;
    }, 350);
    return () => window.clearTimeout(timer);
  }, [appOpenLink]);

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xl">
        <div className={`mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full ${statusCopy.bg}`}>
          <Icon className={`h-8 w-8 ${statusCopy.color}`} />
        </div>
        <h1 className="text-2xl font-bold text-slate-900">{statusCopy.title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{statusCopy.message}</p>
        {pedidoId && (
          <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
            Pedido {pedidoId}
          </p>
        )}
        <a
          className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-teal-700 px-4 py-3 text-sm font-bold text-white hover:bg-teal-800"
          href={appOpenLink}
        >
          Abrir app CorePet
        </a>
        <Link
          className="mt-3 inline-flex w-full items-center justify-center rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          to={fallbackAppUrl}
        >
          Abrir dados da loja
        </Link>
      </section>
    </main>
  );
}
