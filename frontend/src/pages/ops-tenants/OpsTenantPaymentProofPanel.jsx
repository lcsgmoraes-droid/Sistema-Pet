import { useCallback, useEffect, useRef, useState } from "react";

import api from "../../platformApi";

const labels = { pending: "Aguardando conferência", approved: "Aprovado", rejected: "Recusado" };

export default function OpsTenantPaymentProofPanel({ tenant, onUpdated }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [notes, setNotes] = useState({});
  const tenantId = tenant?.id;
  const selectedTenantRef = useRef(tenantId);
  selectedTenantRef.current = tenantId;

  const load = useCallback(async () => {
    if (!tenantId) {
      setItems([]);
      return;
    }
    try {
      const response = await api.get(`/admin/tenants/${tenantId}/payment-proofs`);
      if (selectedTenantRef.current === tenantId) {
        setItems(response.data?.items || []);
        setError("");
      }
    } catch (err) {
      if (selectedTenantRef.current === tenantId) {
        setError(err.response?.data?.detail || "Não foi possível consultar os comprovantes.");
      }
    }
  }, [tenantId]);

  useEffect(() => {
    setItems([]);
    setError("");
    load();
    if (!tenantId) return undefined;
    const interval = window.setInterval(load, 60 * 1000);
    return () => window.clearInterval(interval);
  }, [load, tenantId]);

  async function download(item) {
    try {
      const response = await api.get(`/admin/tenants/${tenantId}/payment-proofs/${item.id}/file`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.filename;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError("Não foi possível baixar o comprovante.");
    }
  }

  async function review(item, decision) {
    setBusyId(item.id);
    setError("");
    try {
      const note = notes[item.id]?.trim() || null;
      await api.post(`/admin/tenants/${tenantId}/payment-proofs/${item.id}/review`, {
        decision,
        note,
      });
      setNotes((previous) => ({ ...previous, [item.id]: "" }));
      await load();
      onUpdated?.();
    } catch (err) {
      setError(err.response?.data?.detail || "Não foi possível registrar a decisão.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-bold text-slate-900">Comprovantes para conferência</h3>
        <button
          type="button"
          onClick={load}
          className="text-xs font-semibold text-blue-700 underline"
        >
          Atualizar
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-600">
        Aprovar libera a cobrança atual e retira o aviso. Recusar mantém o status.
      </p>
      {error && <p className="mt-3 text-sm text-rose-700">{error}</p>}
      {!items.length && <p className="mt-3 text-sm text-slate-500">Nenhum comprovante enviado.</p>}
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-md border border-slate-200 p-3 text-sm">
            <p className="font-semibold text-slate-800">{labels[item.status] || item.status}</p>
            <p className="mt-1 text-slate-600">
              {item.filename} · vencimento {item.due_date || "não informado"}
            </p>
            <button
              type="button"
              onClick={() => download(item)}
              className="mt-2 text-blue-700 underline"
            >
              Baixar para conferir
            </button>
            {item.review_note && (
              <p className="mt-2 text-slate-600">Observação: {item.review_note}</p>
            )}
            {item.status === "pending" && (
              <div className="mt-3 space-y-2">
                <input
                  value={notes[item.id] || ""}
                  onChange={(event) =>
                    setNotes((previous) => ({ ...previous, [item.id]: event.target.value }))
                  }
                  maxLength={1000}
                  placeholder="Observação (obrigatória se recusar)"
                  className="w-full rounded border border-slate-300 p-2"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busyId != null}
                    onClick={() => review(item, "approve")}
                    className="rounded bg-emerald-600 px-3 py-2 font-semibold text-white disabled:opacity-50"
                  >
                    Aprovar e liberar
                  </button>
                  <button
                    type="button"
                    disabled={busyId != null || !notes[item.id]?.trim()}
                    onClick={() => review(item, "reject")}
                    className="rounded border border-rose-300 px-3 py-2 font-semibold text-rose-700 disabled:opacity-50"
                  >
                    Recusar
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
