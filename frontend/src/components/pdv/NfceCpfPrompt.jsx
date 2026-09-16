import { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { atualizarCliente } from "../../api/clientes";
import { formatCpf, normalizeCpf, validarCpf } from "../../utils/cpf";

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
  onResolvedChange,
  onSaved,
  visible = true,
}) {
  const existingDocument = cliente?.cpf || cliente?.cnpj || cliente?.cpf_cnpj || "";
  const [choice, setChoice] = useState(existingDocument ? "registered" : "");
  const [cpf, setCpf] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const resolved = Boolean(existingDocument || choice === "skip" || choice === "saved");

  useEffect(() => {
    setChoice(existingDocument ? "registered" : "");
    setCpf("");
    setError("");
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
      setChoice("saved");
      onSaved?.(updatedCustomer || { ...cliente, cpf: normalized });
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">
      {choice === "saved" ? (
        <p className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-4 w-4" /> CPF salvo no cadastro e incluído na NFC-e.
        </p>
      ) : choice === "skip" ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-medium">A NFC-e será emitida sem CPF.</p>
          {cliente?.id && (
            <button
              type="button"
              onClick={() => setChoice("form")}
              disabled={disabled}
              className="font-semibold text-sky-800 underline disabled:opacity-50"
            >
              Adicionar CPF
            </button>
          )}
        </div>
      ) : choice === "form" ? (
        <form onSubmit={saveCpf} className="space-y-3">
          <div>
            <label htmlFor="nfce-cpf" className="font-semibold">
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
              disabled={disabled || saving}
              className="mt-2 w-full rounded-lg border border-sky-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-600/20"
            />
          </div>
          {error && <p className="text-xs font-medium text-red-700">{error}</p>}
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={disabled || saving}
              className="rounded-lg bg-sky-700 px-3 py-2 font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
            >
              {saving ? "Salvando…" : "Salvar CPF"}
            </button>
            <button
              type="button"
              onClick={() => {
                setChoice("skip");
                setError("");
              }}
              disabled={disabled || saving}
              className="rounded-lg border border-sky-300 px-3 py-2 font-semibold disabled:opacity-50"
            >
              Continuar sem CPF
            </button>
          </div>
        </form>
      ) : (
        <div>
          <p className="font-semibold">Quer colocar CPF na nota?</p>
          <p className="mt-1 text-xs text-sky-800">
            {cliente?.id
              ? "O CPF ficará salvo no cadastro deste cliente para as próximas compras."
              : "Para salvar um CPF, selecione o cliente no PDV antes de finalizar a venda."}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {cliente?.id && (
              <button
                type="button"
                onClick={() => setChoice("form")}
                disabled={disabled}
                className="rounded-lg bg-sky-700 px-3 py-2 font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
              >
                Sim, adicionar CPF
              </button>
            )}
            <button
              type="button"
              onClick={() => setChoice("skip")}
              disabled={disabled}
              className="rounded-lg border border-sky-300 px-3 py-2 font-semibold disabled:opacity-50"
            >
              Não, continuar sem CPF
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
