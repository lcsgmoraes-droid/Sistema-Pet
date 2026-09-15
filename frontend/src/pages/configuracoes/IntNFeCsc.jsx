import { useCallback, useEffect, useRef, useState } from "react";
import { FiExternalLink, FiHelpCircle, FiKey, FiRefreshCw } from "react-icons/fi";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
const fieldClass =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-white";

export default function IntNFeCsc({
  apiClient,
  disabled = false,
  environment = 2,
  onBusy,
  onData,
}) {
  const [state, setState] = useState(null);
  const [form, setForm] = useState({ ambiente_codigo: "2", csc_id: "", csc: "" });
  const [review, setReview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const mounted = useRef(false);
  const inFlight = useRef(false);
  const requestController = useRef(null);

  const execute = useCallback(
    async (payload = null) => {
      if (inFlight.current) return;
      inFlight.current = true;
      const controller = new AbortController();
      requestController.current = controller;
      const isCurrent = () => mounted.current && requestController.current === controller;
      setBusy(true);
      onBusy?.(true);
      setError("");
      setMessage("");
      try {
        const response = payload
          ? await apiClient.put("/intnfe/csc", payload, { signal: controller.signal })
          : await apiClient.get("/intnfe/csc", { signal: controller.signal });
        if (isCurrent()) {
          setState(response.data);
          onData?.(response.data);
          setReview(false);
          if (payload) {
            setForm((previous) => ({ ...previous, csc_id: "", csc: "" }));
            setMessage(response.data.mensagem || "CSC salvo.");
          }
        }
      } catch (failure) {
        if (isCurrent()) {
          const detail = failure?.response?.data?.detail;
          const text = typeof detail === "string" ? detail : detail?.mensagem;
          setState(null);
          onData?.(null);
          setReview(false);
          setForm((previous) => ({ ...previous, csc_id: "", csc: "" }));
          setError(
            text ||
              (payload
                ? "Não foi possível confirmar o cadastro. Consulte a situação antes de tentar novamente."
                : "Não foi possível consultar os CSCs."),
          );
        }
      } finally {
        if (isCurrent()) {
          requestController.current = null;
          inFlight.current = false;
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
      requestController.current?.abort();
      requestController.current = null;
      inFlight.current = false;
      onBusy?.(false);
    };
  }, [execute, onBusy]);

  useEffect(() => {
    setForm({ ambiente_codigo: String(environment), csc_id: "", csc: "" });
    setReview(false);
    setMessage("");
  }, [environment]);

  const locked = busy || disabled;
  const selected = state?.ambientes?.find(
    (item) => item.ambiente_codigo === Number(form.ambiente_codigo),
  );
  const environmentName = environment === 1 ? "produção" : "homologação";

  return (
    <section
      aria-busy={locked}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FiKey className="mt-1 h-7 w-7 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">CSC da NFC-e</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Código da NFC-e para o ambiente de {environmentName}. Necessário somente para o modelo
              65.
            </p>
          </div>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
          NFC-e · modelo 65
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

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800">
        <p>
          CSC de {environmentName}:{" "}
          <strong>
            {selected?.tem_csc
              ? `cadastrado · ID ${selected.csc_id}`
              : state
                ? "não cadastrado"
                : "não consultado"}
          </strong>
        </p>
        <button
          type="button"
          disabled={locked}
          onClick={() => execute()}
          className={`${buttonClass} border border-slate-300 bg-white dark:bg-slate-900`}
        >
          <FiRefreshCw aria-hidden="true" />
          {busy ? "Aguarde…" : "Verificar cadastro na IntNFe"}
        </button>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Esta verificação apenas atualiza a situação e o ID cadastrados. Ela não altera o CSC e, por
        segurança, nunca recupera o código secreto.
      </p>

      <details className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
        <summary className="flex cursor-pointer list-none items-center gap-2 font-bold">
          <FiHelpCircle aria-hidden="true" /> Como obter o CSC?
        </summary>
        <div className="mt-3 space-y-3">
          <p>
            O CSC é gerado pela Secretaria da Fazenda do estado da empresa. Ele é necessário apenas
            para emitir NFC-e (modelo 65).
          </p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>Confirme que o estabelecimento está credenciado para emitir NFC-e.</li>
            <li>Acesse o portal da NFC-e da SEFAZ usando o certificado digital da empresa.</li>
            <li>Selecione o estabelecimento e o ambiente correto.</li>
            <li>
              Abra <strong>Gerenciar Cód Segurança</strong> e gere ou consulte o CSC.
            </li>
            <li>Copie o ID do CSC e o código secreto para os campos abaixo.</li>
          </ol>
          <p>
            Homologação e produção usam CSCs diferentes. Gere e informe o código correspondente à
            aba em que você está.
          </p>
          <a
            href="https://portal.fazenda.sp.gov.br/servicos/nfce/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-semibold text-blue-700 underline decoration-blue-300 underline-offset-2"
          >
            <FiExternalLink aria-hidden="true" /> Abrir orientações oficiais da SEFAZ-SP
          </a>
          <p className="text-xs text-blue-800">
            Empresa de outro estado: use o portal de NFC-e da Secretaria da Fazenda da sua UF, pois
            cada estado administra o próprio CSC.
          </p>
        </div>
      </details>

      {state && selected && !review && (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!locked && form.csc_id.trim() && form.csc.trim()) setReview(true);
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold">
              ID do CSC
              <input
                className={fieldClass}
                value={form.csc_id}
                maxLength={32}
                autoComplete="off"
                disabled={locked}
                required
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, csc_id: event.target.value }))
                }
              />
            </label>
            <label className="text-sm font-semibold">
              Código CSC
              <input
                className={fieldClass}
                type="password"
                value={form.csc}
                maxLength={4096}
                autoComplete="new-password"
                disabled={locked}
                required
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, csc: event.target.value }))
                }
              />
            </label>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            O código é enviado à IntNFe e não volta nas consultas. O CorePet não o salva neste
            formulário.
          </p>
          <button
            type="submit"
            disabled={locked}
            className={`${buttonClass} bg-blue-600 text-white`}
          >
            Revisar cadastro
          </button>
        </form>
      )}

      {state && selected && review && (
        <div
          role="group"
          aria-label="Revisão do CSC"
          className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"
        >
          <p className="font-bold">Confirmar CSC de {environmentName}</p>
          <p className="text-sm">
            Será salvo o ID <strong>{form.csc_id.trim()}</strong>.{" "}
            {selected.tem_csc
              ? `O cadastro atual de ID ${selected.csc_id} será substituído.`
              : "Este será o primeiro CSC deste emitente."}
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={locked}
              onClick={() => {
                const payload = {
                  ambiente_codigo: Number(form.ambiente_codigo),
                  csc_id: form.csc_id.trim(),
                  csc: form.csc.trim(),
                  csc_id_consultado: selected.csc_id,
                  confirmar_substituicao: selected.tem_csc,
                };
                setForm((previous) => ({ ...previous, csc_id: "", csc: "" }));
                execute(payload);
              }}
              className={`${buttonClass} bg-blue-600 text-white`}
            >
              Confirmar e salvar CSC
            </button>
            <button
              type="button"
              disabled={locked}
              onClick={() => setReview(false)}
              className={`${buttonClass} border border-amber-400`}
            >
              Voltar e revisar
            </button>
          </div>
        </div>
      )}

      <p className="border-t border-slate-100 pt-4 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
        Homologação e produção usam CSCs diferentes. O código digitado aqui será associado somente
        ao ambiente de {environmentName}.
      </p>
    </section>
  );
}
