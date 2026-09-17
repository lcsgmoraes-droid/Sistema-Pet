import { useEffect, useState } from "react";
import { CheckCircle2, HelpCircle } from "lucide-react";

import { atualizarCliente } from "../../api/clientes";
import { documentoCpfCnpjCliente, formatCpf, normalizeCpf, validarCpf } from "../../utils/cpf";

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join("; ");
  return detail?.mensagem || "Não foi possível salvar o CPF no cadastro do cliente.";
}

export default function NfceCpfPrompt({
  cliente,
  disabled = false,
  onContinueWithoutCpf,
  onResolvedChange,
  onSaved,
  visible = true,
}) {
  const existingDocument = documentoCpfCnpjCliente(cliente);
  const [saved, setSaved] = useState(false);
  const [cpf, setCpf] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const resolved = Boolean(existingDocument || saved);

  useEffect(() => {
    setSaved(false);
    setCpf("");
    setError("");
    setHelpOpen(false);
  }, [cliente?.id, existingDocument]);

  useEffect(() => {
    onResolvedChange?.(resolved);
  }, [onResolvedChange, resolved]);

  if (!visible || existingDocument) return null;

  async function saveCpf(event) {
    event.preventDefault();
    const normalized = normalizeCpf(cpf);
    if (!validarCpf(normalized)) {
      setError("Informe um CPF válido com 11 dígitos.");
      return;
    }
    if (!cliente?.id) {
      setError("Selecione um cliente no PDV para salvar o CPF no cadastro.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const updatedCustomer = await atualizarCliente(cliente.id, { cpf: normalized });
      setSaved(true);
      onSaved?.(updatedCustomer || { ...cliente, cpf: normalized });
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(false);
    }
  }

  async function continueWithoutCpf() {
    setContinuing(true);
    setError("");
    try {
      await onContinueWithoutCpf?.();
    } finally {
      setContinuing(false);
    }
  }

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-100">
      {saved ? (
        <p className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-4 w-4" /> CPF salvo no cadastro e incluído na NFC-e.
        </p>
      ) : (
        <form onSubmit={saveCpf} className="space-y-2.5">
          <div className="flex items-center gap-1.5">
            <p className="font-semibold">Quer colocar CPF na nota?</p>
            <button
              type="button"
              onClick={() => setHelpOpen((open) => !open)}
              aria-label="Explicação sobre CPF na nota"
              aria-expanded={helpOpen}
              aria-controls="ajuda-cpf-na-nota"
              className="rounded-full p-1 text-sky-700 hover:bg-sky-100 dark:text-sky-200 dark:hover:bg-sky-900"
            >
              <HelpCircle className="h-4 w-4" />
            </button>
          </div>
          {helpOpen && (
            <p id="ajuda-cpf-na-nota" className="text-xs text-sky-800 dark:text-sky-200">
              {cliente?.id
                ? "O CPF ficará salvo no cadastro deste cliente para as próximas compras."
                : "Para salvar um CPF, selecione o cliente no PDV antes de finalizar a venda."}
            </p>
          )}
          {cliente?.id && (
            <div>
              <label htmlFor="nfce-cpf" className="sr-only">
                CPF para incluir na NFC-e
              </label>
              <input
                id="nfce-cpf"
                value={cpf}
                onChange={(event) => {
                  setCpf(formatCpf(event.target.value));
                  setError("");
                }}
                inputMode="numeric"
                autoComplete="off"
                placeholder="000.000.000-00"
                disabled={disabled || saving || continuing}
                className="w-full rounded-lg border border-sky-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-600/20 dark:border-sky-700 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
          )}
          {error && <p className="text-xs font-medium text-red-700">{error}</p>}
          <div className="flex flex-wrap gap-2">
            {cliente?.id && (
              <button
                type="submit"
                disabled={disabled || saving || continuing}
                className="rounded-lg bg-sky-700 px-3 py-2 font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
              >
                {saving ? "Salvando…" : "Salvar CPF"}
              </button>
            )}
            <button
              type="button"
              onClick={continueWithoutCpf}
              disabled={disabled || saving || continuing}
              className="rounded-lg border border-sky-300 px-3 py-2 font-semibold hover:bg-sky-100 disabled:opacity-50 dark:border-sky-700 dark:hover:bg-sky-900"
            >
              {continuing ? "Emitindo NFC-e…" : "Não, continuar sem CPF"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
