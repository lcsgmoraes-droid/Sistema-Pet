import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { formatMoneyBRL } from "../../utils/formatters";
import { useEscapeToClose } from "../../utils/modalEscape";
import {
  apresentacaoMovimentacao,
  orcamentoExpirou,
  podeConfirmarOrcamento,
} from "./creditosModel";

const numero = (value) =>
  Number.isSafeInteger(value) ? value.toLocaleString("pt-BR") : "Indisponível";

export default function CreditUsageModal({
  quote,
  title,
  mode,
  wallet,
  entries,
  warning,
  onClose,
  onConfirm,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const descriptionId = useId();
  const [now, setNow] = useState(Date.now);
  useEscapeToClose({ onClose });

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  useEffect(() => {
    if (!quote) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [quote]);

  const expired = quote && orcamentoExpirou(quote, now);
  const canConfirm = quote && podeConfirmarOrcamento(quote, wallet, now);
  return createPortal(
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      className="m-auto w-[min(94vw,560px)] rounded-2xl border-0 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/50"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="max-h-[85vh] overflow-y-auto p-6">
        <h2 id={titleId} className="text-xl font-bold">
          {quote ? "Confirmar geração com IA" : "Créditos CorePet"}
        </h2>
        <p id={descriptionId} className="mt-2 text-sm text-slate-600">
          {mode === "shadow"
            ? "SIMULAÇÃO DE CRÉDITOS: não haverá débito. Ao confirmar, a IA fará uma geração real e a conta do provedor poderá ter custo."
            : "Confira o valor antes de iniciar. O consumo será registrado nesta empresa."}
        </p>
        {quote && (
          <div className="mt-4 rounded-xl bg-violet-50 p-4">
            <p className="font-semibold">{title}</p>
            <p className="mt-1 text-lg font-bold text-violet-800">
              {numero(quote.credits)} créditos · {formatMoneyBRL(quote.price_cents / 100)}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {mode === "shadow" ? "Valor simulado. " : ""}Reabrir ou baixar um resultado existente
              não gera novo consumo.
            </p>
          </div>
        )}
        <dl className="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-slate-200 p-3 text-sm">
          <div>
            <dt className="text-slate-600">Disponível</dt>
            <dd className="font-bold">{numero(wallet?.available_credits)} créditos</dd>
          </div>
          <div>
            <dt className="text-slate-600">Reservado</dt>
            <dd className="font-bold">{numero(wallet?.reserved_credits)} créditos</dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-slate-500">
          A compra de créditos ainda não está disponível. Nenhum pagamento será solicitado nesta
          tela.
        </p>
        {warning && (
          <p role="status" className="mt-3 text-sm text-amber-800">
            {warning}
          </p>
        )}
        {expired && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            O orçamento expirou. Cancele e solicite um novo.
          </p>
        )}
        {quote?.mode === "enforced" && !expired && !canConfirm && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            Saldo insuficiente ou indisponível para esta geração.
          </p>
        )}
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-semibold">Últimas movimentações</summary>
          {entries?.length ? (
            <ul className="mt-2 space-y-2">
              {entries.slice(0, 8).map((entry, index) => {
                const presentation = apresentacaoMovimentacao(entry);
                return (
                  <li key={entry.id || index} className="border-t border-slate-100 pt-2">
                    <span className="font-medium">{presentation.label}</span>
                    <span className="float-right">{numero(entry.credits)} créditos</span>
                    <p>{entry.title || entry.service_code || "Movimentação"}</p>
                    <p className="mt-1 text-xs text-slate-600">{presentation.note}</p>
                    {entry.mode !== "shadow" && Number.isSafeInteger(entry.available_after) && (
                      <p className="text-xs text-slate-500">
                        Disponível após: {numero(entry.available_after)} créditos
                      </p>
                    )}
                    {entry.created_at && (
                      <p className="text-xs text-slate-500">
                        {new Date(entry.created_at).toLocaleString("pt-BR")}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mt-2 text-slate-500">Nenhuma movimentação disponível.</p>
          )}
        </details>
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            autoFocus
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 font-medium"
          >
            {quote ? "Cancelar" : "Fechar"}
          </button>
          {quote && (
            <button
              type="button"
              disabled={!canConfirm}
              onClick={onConfirm}
              className="rounded-lg bg-violet-700 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {mode === "shadow" ? "Confirmar geração real (sem débito)" : "Confirmar e gerar"}
            </button>
          )}
        </div>
      </div>
    </dialog>,
    document.body,
  );
}
