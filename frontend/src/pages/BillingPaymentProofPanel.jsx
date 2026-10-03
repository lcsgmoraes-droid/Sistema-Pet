import { useEffect, useState } from "react";

import { api } from "../services/api";

const labels = {
  pending: "Aguardando conferência",
  approved: "Aprovado pela equipe",
  rejected: "Recusado",
};

export default function BillingPaymentProofPanel({ billing, onRefresh }) {
  const [items, setItems] = useState([]);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const overdue = billing?.payment_status === "OVERDUE" || billing?.billing_status === "past_due";

  useEffect(() => {
    let active = true;
    api
      .get("/billing/asaas/payment-proofs")
      .then((response) => {
        if (active) setItems(response.data?.items || []);
      })
      .catch(() => {
        if (active) setError("Não foi possível consultar os comprovantes.");
      });
    return () => {
      active = false;
    };
  }, []);

  if (!overdue && items.length === 0) return null;
  const current = items.find((item) => item.due_date === billing?.next_due_date);
  const pending = current?.status === "pending";

  async function submit(event) {
    event.preventDefault();
    if (!file) return;
    const formElement = event.currentTarget;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await api.post("/billing/asaas/payment-proofs", form);
      setItems((previous) => [response.data, ...previous]);
      setFile(null);
      formElement.reset();
      setMessage("Comprovante recebido. A equipe vai conferir antes de liberar a cobrança.");
      onRefresh?.();
    } catch (err) {
      setError(err.response?.data?.detail || "Não foi possível enviar o comprovante.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-lg border border-amber-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold text-slate-950">Comprovante de pagamento</h2>
      <p className="mt-2 text-sm text-slate-600">
        Pagou e a cobrança ainda aparece em atraso? Envie o comprovante. A liberação é feita após
        conferência da equipe.
      </p>
      {overdue && !pending && current?.status !== "approved" && (
        <form onSubmit={submit} className="mt-4 flex flex-wrap items-end gap-3">
          <label className="text-sm font-semibold text-slate-800">
            Arquivo PDF, JPG ou PNG, até 5 MB
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              required
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="mt-2 block w-full max-w-sm text-sm text-slate-700"
            />
          </label>
          <button
            type="submit"
            disabled={busy || !file}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            {busy ? "Enviando..." : "Enviar comprovante"}
          </button>
        </form>
      )}
      {message && <p className="mt-3 text-sm font-semibold text-emerald-700">{message}</p>}
      {error && <p className="mt-3 text-sm font-semibold text-rose-700">{error}</p>}
      {items.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm text-slate-700">
          {items.map((item) => (
            <li key={item.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <strong>{labels[item.status] || item.status}</strong> · {item.filename}
              {item.review_note && <p className="mt-1">Observação: {item.review_note}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
