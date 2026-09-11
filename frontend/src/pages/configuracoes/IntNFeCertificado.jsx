import { useCallback, useEffect, useRef, useState } from "react";
import { FiRefreshCw, FiShield, FiUploadCloud } from "react-icons/fi";

const MAX_CERTIFICATE_BYTES = 512 * 1024;
const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
const fieldClass =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-white";

function errorMessage(failure, fallback) {
  const detail = failure?.response?.data?.detail;
  return (typeof detail === "string" ? detail : detail?.mensagem) || fallback;
}

export default function IntNFeCertificado({
  apiClient,
  disabled = false,
  onBusy,
  onData,
  onChanged,
}) {
  const [state, setState] = useState(null);
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const mounted = useRef(false);
  const formRef = useRef(null);

  const load = useCallback(async () => {
    setBusy(true);
    onBusy?.(true);
    setError("");
    try {
      const response = await apiClient.get("/intnfe/certificado");
      if (mounted.current) {
        setState(response.data);
        onData?.(response.data);
      }
    } catch (failure) {
      if (mounted.current) {
        setState(null);
        onData?.(null);
        setError(errorMessage(failure, "Não foi possível consultar o certificado A1."));
      }
    } finally {
      if (mounted.current) {
        setBusy(false);
        onBusy?.(false);
      }
    }
  }, [apiClient, onBusy, onData]);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
      onBusy?.(false);
    };
  }, [load, onBusy]);

  async function upload(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!file || !password) {
      setError("Selecione o certificado A1 e informe a senha.");
      return;
    }
    if (file.size > MAX_CERTIFICATE_BYTES) {
      setError("O certificado deve ter no máximo 512 KB.");
      return;
    }

    const body = new FormData();
    body.append("arquivo", file);
    body.append("senha", password);
    setBusy(true);
    onBusy?.(true);
    try {
      const response = await apiClient.post("/intnfe/certificado", body);
      if (mounted.current) {
        setState(response.data);
        onData?.(response.data);
        setMessage("Certificado A1 recebido e validado.");
        setFile(null);
        setPassword("");
        formRef.current?.reset();
        onChanged?.();
      }
    } catch (failure) {
      if (mounted.current) {
        setError(
          errorMessage(
            failure,
            "Não foi possível confirmar o envio. Consulte a situação antes de tentar novamente.",
          ),
        );
      }
    } finally {
      if (mounted.current) {
        setBusy(false);
        onBusy?.(false);
      }
    }
  }

  const locked = busy || disabled;
  const valid = ["valido", "expirando"].includes(state?.situacao);

  return (
    <section
      aria-busy={locked}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FiShield className="mt-1 h-7 w-7 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">
              Certificado digital A1
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Envie o arquivo .pfx ou .p12 aqui. A senha é usada somente durante o envio.
            </p>
          </div>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            valid ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"
          }`}
        >
          {valid ? "A1 válido" : "A1 pendente"}
        </span>
      </header>

      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      {message && (
        <p
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
        >
          {message}
        </p>
      )}

      {state && (
        <div
          className={`rounded-xl border p-4 text-sm ${
            state.alerta_vencimento
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-emerald-200 bg-emerald-50 text-emerald-950"
          }`}
        >
          <p className="font-semibold">{state.mensagem}</p>
          {state.valido_ate && (
            <p className="mt-1">
              Validade: {new Date(state.valido_ate).toLocaleDateString("pt-BR")}
              {Number.isInteger(state.dias_para_expirar)
                ? ` · ${Math.max(state.dias_para_expirar, 0)} dia(s)`
                : ""}
            </p>
          )}
        </div>
      )}

      <form ref={formRef} onSubmit={upload} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-semibold">
            Arquivo do certificado
            <input
              type="file"
              accept=".pfx,.p12,application/x-pkcs12"
              required
              disabled={locked}
              className={fieldClass}
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <label className="text-sm font-semibold">
            Senha do certificado
            <input
              type="password"
              value={password}
              required
              maxLength={1024}
              autoComplete="new-password"
              disabled={locked}
              className={fieldClass}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={locked}
            className={`${buttonClass} bg-blue-600 text-white`}
          >
            <FiUploadCloud aria-hidden="true" />
            {busy ? "Enviando…" : state?.tem_certificado ? "Substituir A1" : "Enviar A1"}
          </button>
          <button
            type="button"
            disabled={locked}
            onClick={load}
            className={`${buttonClass} border border-slate-300`}
          >
            <FiRefreshCw aria-hidden="true" />
            Consultar situação
          </button>
        </div>
      </form>

      <p className="border-t border-slate-100 pt-4 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
        O A1 deve pertencer ao mesmo CNPJ da empresa. O CorePet não exibe nem guarda a senha no
        formulário depois do envio.
      </p>
    </section>
  );
}
