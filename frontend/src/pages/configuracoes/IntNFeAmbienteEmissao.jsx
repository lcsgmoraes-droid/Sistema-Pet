import { useEffect, useMemo, useState } from "react";
import { FiAlertTriangle, FiCheckCircle, FiPower } from "react-icons/fi";
import { currentSequence, formatSequence } from "./intnfeNumeracao.mjs";

function messageFrom(error) {
  const detail = error?.response?.data?.detail;
  return detail?.mensagem || detail || "Não foi possível atualizar o ambiente de emissão.";
}

function uniqueSeries(rows, environment, model, extra = []) {
  const values = new Set(
    (rows || [])
      .filter((row) => row.ambienteCodigo === environment && row.modelo === model)
      .map((row) => String(Number(row.serie))),
  );
  extra.filter(Boolean).forEach((serie) => values.add(String(Number(serie))));
  return [...values].sort((a, b) => Number(a) - Number(b));
}

function SequenceProgress({ document, model, series, sequence, initialNumber }) {
  if (!series || !sequence) {
    return (
      <article className="rounded-xl border border-dashed border-slate-300 p-4 dark:border-slate-600">
        <p className="font-bold text-slate-900 dark:text-white">
          {document} <span className="font-normal text-slate-500">· modelo {model}</span>
        </p>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Nenhuma série foi escolhida para este documento.
        </p>
      </article>
    );
  }

  return (
    <article className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
      <p className="font-bold text-slate-900 dark:text-white">
        {document} <span className="font-normal text-slate-500">· modelo {model}</span>
      </p>
      <p className="mt-1 text-sm font-semibold text-blue-800">Série {series.padStart(3, "0")}</p>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Início no CorePet</dt>
          <dd className="font-bold text-slate-900 dark:text-white">
            {formatSequence(initialNumber)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Último no emissor</dt>
          <dd className="font-bold text-slate-900 dark:text-white">
            {formatSequence(sequence.ultimoNumero)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Próxima emissão</dt>
          <dd className="font-bold text-slate-900 dark:text-white">
            {formatSequence(sequence.proximoNumero)}
          </dd>
        </div>
      </dl>
    </article>
  );
}

function SequenceRadar({ rows, environment, savedConfigurations }) {
  const visible = rows
    .filter((row) => row.ambienteCodigo === environment)
    .sort((a, b) => a.modelo - b.modelo || Number(a.serie) - Number(b.serie));

  if (!visible.length) return null;

  return (
    <div className="space-y-3">
      <div>
        <h3 className="font-bold text-slate-950 dark:text-white">Radar das sequências fiscais</h3>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Consulte o último número registrado e o próximo número disponível em cada modelo e série.
        </p>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-700">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/50">
            <tr>
              <th className="px-4 py-3">Documento</th>
              <th className="px-4 py-3">Série</th>
              <th className="px-4 py-3">Início no CorePet</th>
              <th className="px-4 py-3">Último no emissor</th>
              <th className="px-4 py-3">Próximo número</th>
              <th className="px-4 py-3">Uso no CorePet</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-800 dark:bg-slate-900">
            {visible.map((row) => {
              const saved = savedConfigurations.find(
                (item) =>
                  item.ambiente_codigo === environment &&
                  item.modelo === row.modelo &&
                  Number(item.serie) === Number(row.serie),
              );
              return (
                <tr key={`${row.modelo}:${row.serie}`}>
                  <td className="whitespace-nowrap px-4 py-3 font-semibold">
                    {row.modelo === 65 ? "NFC-e" : "NF-e"} · modelo {row.modelo}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">{row.serie.padStart(3, "0")}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {saved ? formatSequence(saved.numero_inicial) : "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-semibold">
                    {formatSequence(row.ultimoNumero)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-semibold">
                    {formatSequence(row.proximoNumero)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {saved ? (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-900">
                        Escolhida no CorePet
                      </span>
                    ) : (
                      <span className="text-slate-500">Disponível</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        O número é controlado separadamente por ambiente, modelo e série. A sequência só pode
        avançar. Este é o número fiscal da NF-e ou NFC-e; não é o NSU da SEFAZ nem o NSU de uma
        transação de cartão.
      </p>
    </div>
  );
}

export default function IntNFeAmbienteEmissao({
  apiClient,
  disabled,
  environment = 2,
  choices = {},
  numberingData,
  configurationData,
  onBusy,
  onData,
}) {
  const [data, setData] = useState(null);
  const [selections, setSelections] = useState({ 1: { 55: "", 65: "" }, 2: { 55: "", 65: "" } });
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [productionReview, setProductionReview] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    onBusy?.(true);
    apiClient
      .get("/intnfe/ambiente-emissao")
      .then((response) => {
        if (!active) return;
        setData(response.data);
        setSelections((current) => {
          const next = {
            1: { ...current[1] },
            2: { ...current[2] },
          };
          for (const configuration of response.data.configuracoes || []) {
            next[configuration.ambiente_codigo][configuration.modelo] = configuration.serie;
          }
          const activeEnvironment = response.data.ambiente_codigo;
          if (!next[activeEnvironment][55]) next[activeEnvironment][55] = response.data.serie_nfe;
          if (!next[activeEnvironment][65]) next[activeEnvironment][65] = response.data.serie_nfce;
          return next;
        });
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

  useEffect(() => {
    if (!configurationData) return;
    setData(configurationData);
    setSelections((current) => {
      const next = { 1: { ...current[1] }, 2: { ...current[2] } };
      for (const configuration of configurationData.configuracoes || []) {
        next[configuration.ambiente_codigo][configuration.modelo] = configuration.serie;
      }
      return next;
    });
  }, [configurationData]);

  useEffect(() => {
    setSelections((current) => ({
      ...current,
      [environment]: {
        55: choices[55]?.origem === "sequencia" ? choices[55].serie : current[environment][55],
        65: choices[65]?.origem === "sequencia" ? choices[65].serie : current[environment][65],
      },
    }));
    setProductionReview(false);
    setMessage(null);
  }, [choices, environment]);

  const rows = numberingData?.series || [];
  const selected = selections[environment];
  const nfeOptions = useMemo(
    () => uniqueSeries(rows, environment, 55, [choices[55]?.serie, selected[55]]),
    [choices, environment, rows, selected],
  );
  const nfceOptions = useMemo(
    () => uniqueSeries(rows, environment, 65, [choices[65]?.serie, selected[65]]),
    [choices, environment, rows, selected],
  );
  const nfeSequence = selected[55] ? currentSequence(rows, selected[55], environment, 55) : null;
  const nfceSequence = selected[65] ? currentSequence(rows, selected[65], environment, 65) : null;
  const savedConfigurations = configurationData?.configuracoes || data?.configuracoes || [];
  const savedNfe = savedConfigurations.find(
    (item) => item.ambiente_codigo === environment && item.modelo === 55,
  );
  const savedNfce = savedConfigurations.find(
    (item) => item.ambiente_codigo === environment && item.modelo === 65,
  );
  const nfeInitial =
    savedNfe?.serie === selected[55]
      ? savedNfe.numero_inicial
      : ((choices[55]?.serie === selected[55] ? choices[55].proximoNumero : null) ??
        nfeSequence?.proximoNumero);
  const nfceInitial =
    savedNfce?.serie === selected[65]
      ? savedNfce.numero_inicial
      : ((choices[65]?.serie === selected[65] ? choices[65].proximoNumero : null) ??
        nfceSequence?.proximoNumero);

  const updateSelection = (model, serie) => {
    setSelections((current) => ({
      ...current,
      [environment]: { ...current[environment], [model]: serie },
    }));
    setProductionReview(false);
    setMessage(null);
  };

  async function save() {
    setLoading(true);
    onBusy?.(true);
    setMessage(null);
    try {
      const response = await apiClient.put("/intnfe/ambiente-emissao", {
        ambiente_codigo: environment,
        serie_nfe: selected[55],
        serie_nfce: selected[65] || "1",
        numero_inicial_nfe: nfeInitial,
        numero_inicial_nfce: nfceSequence ? nfceInitial : null,
      });
      setData(response.data);
      onData?.(response.data);
      setProductionReview(false);
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
      setProductionReview(false);
      setMessage({ type: "success", text: response.data.mensagem });
    } catch (error) {
      setMessage({ type: "error", text: messageFrom(error) });
    } finally {
      setLoading(false);
      onBusy?.(false);
    }
  }

  const locked = disabled || loading;
  const production = environment === 1;
  const pendingSequence = Boolean(choices[55]?.pendente || choices[65]?.pendente);
  const exhaustedSequence = Boolean(
    (nfeSequence && nfeSequence.proximoNumero > 999999999) ||
    (nfceSequence && nfceSequence.proximoNumero > 999999999),
  );
  const canActivate = Boolean(
    selected[55] && nfeSequence && !pendingSequence && !exhaustedSequence,
  );

  return (
    <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 dark:border-slate-700 dark:bg-slate-900">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-950 dark:text-white">
            2. Séries que o CorePet usará
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Escolha, entre as sequências acima, a série padrão de cada documento.
          </p>
        </div>
        {data?.habilitada && data.ambiente_codigo === environment ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">
            <FiCheckCircle /> Ativa em {data.ambiente}
          </span>
        ) : null}
      </header>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
        Se for continuar uma série existente, marque{" "}
        <strong>“Continuar com esta série no CorePet”</strong> no bloco acima. A escolha será
        preenchida aqui automaticamente.
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
          Série padrão da NF-e
          <select
            value={selected[55]}
            onChange={(event) => updateSelection(55, event.target.value)}
            disabled={locked || !nfeOptions.length}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          >
            <option value="">Selecione uma sequência cadastrada</option>
            {nfeOptions.map((serie) => (
              <option key={serie} value={serie}>
                Série {serie.padStart(3, "0")}
              </option>
            ))}
          </select>
          <span className="block font-normal text-slate-500">
            {nfeSequence
              ? `Próxima NF-e: ${formatSequence(nfeSequence.proximoNumero)}`
              : "Configure ou escolha uma sequência de NF-e acima."}
          </span>
        </label>

        <label className="space-y-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
          Série padrão da NFC-e
          <select
            value={selected[65]}
            onChange={(event) => updateSelection(65, event.target.value)}
            disabled={locked || !nfceOptions.length}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
          >
            <option value="">NFC-e ainda não configurada</option>
            {nfceOptions.map((serie) => (
              <option key={serie} value={serie}>
                Série {serie.padStart(3, "0")}
              </option>
            ))}
          </select>
          <span className="block font-normal text-slate-500">
            {nfceSequence
              ? `Próxima NFC-e: ${formatSequence(nfceSequence.proximoNumero)}`
              : "Adicione o modelo 65 acima somente se sua empresa emitir NFC-e."}
          </span>
        </label>
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="font-bold text-slate-950 dark:text-white">Resumo das séries escolhidas</h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Acompanhe o ponto de partida e o avanço de cada documento no emissor.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <SequenceProgress
            document="NF-e"
            model={55}
            series={selected[55]}
            sequence={nfeSequence}
            initialNumber={nfeInitial}
          />
          <SequenceProgress
            document="NFC-e"
            model={65}
            series={selected[65]}
            sequence={nfceSequence}
            initialNumber={nfceInitial}
          />
        </div>
      </div>

      <SequenceRadar
        rows={rows}
        environment={environment}
        savedConfigurations={savedConfigurations}
      />

      {pendingSequence ? (
        <p className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-950">
          Salve o avanço da sequência informado acima antes de ativar este ambiente.
        </p>
      ) : null}

      {exhaustedSequence ? (
        <p className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm font-semibold text-red-900">
          Uma das séries atingiu o limite de numeração. Cadastre e escolha outra série antes de
          ativar este ambiente.
        </p>
      ) : null}

      {production ? (
        <div className="flex gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
          <FiAlertTriangle className="mt-0.5 shrink-0" />
          <p>
            Produção gera documentos fiscais reais. Confira as séries e as próximas numerações antes
            da confirmação final.
          </p>
        </div>
      ) : null}

      {message ? (
        <p
          className={`rounded-lg px-4 py-3 text-sm ${message.type === "error" ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"}`}
        >
          {message.text}
        </p>
      ) : null}

      {productionReview ? (
        <div className="space-y-3 rounded-xl border border-amber-400 bg-amber-50 p-4 text-amber-950">
          <p className="font-bold">Confirmar ativação da emissão real</p>
          <p className="text-sm">
            O CorePet usará NF-e série <strong>{selected[55].padStart(3, "0")}</strong>, próxima{" "}
            <strong>{formatSequence(nfeSequence.proximoNumero)}</strong>
            {nfceSequence ? (
              <>
                , e NFC-e série <strong>{selected[65].padStart(3, "0")}</strong>, próxima{" "}
                <strong>{formatSequence(nfceSequence.proximoNumero)}</strong>
              </>
            ) : null}
            .
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={locked}
              onClick={save}
              className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-bold text-white hover:bg-amber-800 disabled:opacity-50"
            >
              Confirmar e ativar produção
            </button>
            <button
              type="button"
              disabled={locked}
              onClick={() => setProductionReview(false)}
              className="rounded-lg border border-amber-400 px-4 py-2 text-sm font-semibold"
            >
              Voltar e revisar
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => (production ? setProductionReview(true) : save())}
            disabled={locked || !canActivate}
            className={`rounded-lg px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 ${production ? "bg-amber-700 hover:bg-amber-800" : "bg-blue-700 hover:bg-blue-800"}`}
          >
            {loading
              ? "Salvando…"
              : production
                ? "Revisar e ativar produção"
                : "Ativar emissão de teste"}
          </button>
          {data?.habilitada ? (
            <button
              type="button"
              onClick={disableEmission}
              disabled={locked}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200"
            >
              <FiPower /> Desativar emissão direta
            </button>
          ) : null}
        </div>
      )}
    </section>
  );
}
