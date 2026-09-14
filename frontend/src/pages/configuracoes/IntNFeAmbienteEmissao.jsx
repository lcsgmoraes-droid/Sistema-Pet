import { useEffect, useState } from "react";
import { FiAlertTriangle, FiCheckCircle, FiPower } from "react-icons/fi";

function messageFrom(error) {
  const detail = error?.response?.data?.detail;
  return detail?.mensagem || detail || "Não foi possível atualizar o ambiente de emissão.";
}

export default function IntNFeAmbienteEmissao({ apiClient, disabled, onBusy, onData }) {
  const [data, setData] = useState(null);
  const [environment, setEnvironment] = useState("2");
  const [nfeSeries, setNfeSeries] = useState("1");
  const [nfceSeries, setNfceSeries] = useState("1");
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    onBusy?.(true);
    apiClient
      .get("/intnfe/ambiente-emissao")
      .then((response) => {
        if (!active) return;
        setData(response.data);
        setEnvironment(String(response.data.ambiente_codigo));
        setNfeSeries(response.data.serie_nfe);
        setNfceSeries(response.data.serie_nfce);
        onData?.(response.data);
      })
      .catch((error) => active && setMessage({ type: "error", text: messageFrom(error) }))
      .finally(() => {
        if (active) {
          setLoading(false);
          onBusy?.(false);
        }
      });
    return () => {
      active = false;
    };
  }, [apiClient, onBusy, onData]);

  async function save() {
    setLoading(true);
    onBusy?.(true);
    setMessage(null);
    try {
      const response = await apiClient.put("/intnfe/ambiente-emissao", {
        ambiente_codigo: Number(environment),
        serie_nfe: nfeSeries,
        serie_nfce: nfceSeries,
      });
      setData(response.data);
      onData?.(response.data);
      setMessage({ type: "success", text: response.data.mensagem });
    } catch (error) {
      setMessage({ type: "error", text: messageFrom(error) });
    } finally {
      setLoading(false);
      onBusy?.(false);
    }
  }

  async function disableEmission() {
    setLoading(true);
    onBusy?.(true);
    setMessage(null);
    try {
      const response = await apiClient.delete("/intnfe/ambiente-emissao");
      setData(response.data);
      onData?.(response.data);
      setMessage({ type: "success", text: response.data.mensagem });
    } catch (error) {
      setMessage({ type: "error", text: messageFrom(error) });
    } finally {
      setLoading(false);
      onBusy?.(false);
    }
  }

  const production = environment === "1";

  return (
    <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 dark:border-slate-700 dark:bg-slate-900">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-950 dark:text-white">Ambiente de emissão</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Esta escolha controla para onde o CorePet transmite as próximas notas desta empresa.
          </p>
        </div>
        {data?.habilitada && (
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">
            <FiCheckCircle /> Ativa em {data.ambiente}
          </span>
        )}
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="space-y-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
          Ambiente
          <select
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            disabled={disabled || loading}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          >
            <option value="2">Homologação (teste)</option>
            <option value="1">Produção (nota real)</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
          Série da NF-e
          <input
            value={nfeSeries}
            onChange={(event) => setNfeSeries(event.target.value.replace(/\D/g, "").slice(0, 3))}
            disabled={disabled || loading}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          />
        </label>
        <label className="space-y-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
          Série da NFC-e
          <input
            value={nfceSeries}
            onChange={(event) => setNfceSeries(event.target.value.replace(/\D/g, "").slice(0, 3))}
            disabled={disabled || loading}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          />
        </label>
      </div>

      {production && (
        <div className="flex gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
          <FiAlertTriangle className="mt-0.5 shrink-0" />
          <p>
            Produção gera documento fiscal real. Confira primeiro a última numeração usada em cada
            série e faça a primeira emissão com uma venda revisada.
          </p>
        </div>
      )}

      {message && (
        <p
          className={`rounded-lg px-4 py-3 text-sm ${message.type === "error" ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"}`}
        >
          {message.text}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={save}
          disabled={disabled || loading || !nfeSeries || !nfceSeries}
          className={`rounded-lg px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 ${production ? "bg-amber-700 hover:bg-amber-800" : "bg-blue-700 hover:bg-blue-800"}`}
        >
          {loading
            ? "Salvando…"
            : production
              ? "Ativar emissão real em produção"
              : "Ativar emissão de teste"}
        </button>
        {data?.habilitada && (
          <button
            type="button"
            onClick={disableEmission}
            disabled={disabled || loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200"
          >
            <FiPower /> Desativar emissão direta
          </button>
        )}
      </div>
    </section>
  );
}
