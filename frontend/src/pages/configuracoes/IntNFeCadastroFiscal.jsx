import { useCallback, useEffect, useRef, useState } from "react";
import { FiDatabase, FiRefreshCw } from "react-icons/fi";
import { Link } from "react-router-dom";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";

function errorMessage(failure, fallback) {
  const detail = failure?.response?.data?.detail;
  return (typeof detail === "string" ? detail : detail?.mensagem) || fallback;
}

export default function IntNFeCadastroFiscal({
  apiClient,
  disabled = false,
  onBusy,
  onData,
  refreshKey = 0,
}) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mounted = useRef(false);

  const execute = useCallback(
    async (sync = false) => {
      setBusy(true);
      onBusy?.(true);
      setError("");
      try {
        const response = sync
          ? await apiClient.post("/intnfe/cadastro-fiscal/sincronizar")
          : await apiClient.get("/intnfe/cadastro-fiscal");
        if (mounted.current) {
          setState(response.data);
          onData?.(response.data);
        }
      } catch (failure) {
        if (mounted.current) {
          if (!sync) {
            setState(null);
            onData?.(null);
          }
          setError(
            errorMessage(
              failure,
              sync
                ? "Não foi possível sincronizar os dados fiscais."
                : "Não foi possível consultar os dados fiscais.",
            ),
          );
        }
      } finally {
        if (mounted.current) {
          setBusy(false);
          onBusy?.(false);
        }
      }
    },
    [apiClient, onBusy, onData],
  );

  useEffect(() => {
    mounted.current = true;
    execute();
    return () => {
      mounted.current = false;
      onBusy?.(false);
    };
  }, [execute, onBusy, refreshKey]);

  const locked = busy || disabled;

  return (
    <section
      aria-busy={locked}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FiDatabase className="mt-1 h-7 w-7 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">
              Cadastro fiscal do emitente
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              O CorePet reaproveita os dados da empresa e envia somente o que precisa ser
              atualizado.
            </p>
          </div>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            state?.sincronizado ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"
          }`}
        >
          {state?.sincronizado ? "Sincronizado" : "Revisão necessária"}
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
      {state && (
        <div
          className={`rounded-xl border p-4 text-sm ${
            state.sincronizado
              ? "border-emerald-200 bg-emerald-50 text-emerald-950"
              : "border-amber-300 bg-amber-50 text-amber-950"
          }`}
        >
          <p className="font-semibold">{state.mensagem}</p>
          {state.pendencias?.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {state.pendencias.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {!state.sincronizado && state.diferencas?.length > 0 && (
            <p className="mt-2">Campos a atualizar: {state.diferencas.join(", ")}.</p>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={locked || !state?.pronto_para_sincronizar}
          onClick={() => execute(true)}
          className={`${buttonClass} bg-blue-600 text-white`}
        >
          <FiRefreshCw aria-hidden="true" />
          {busy ? "Sincronizando…" : "Sincronizar agora"}
        </button>
        <Link
          to="/configuracoes/fiscal"
          className={`${buttonClass} border border-slate-300 text-slate-700 dark:text-slate-200`}
        >
          Conferir dados da empresa
        </Link>
      </div>
    </section>
  );
}
