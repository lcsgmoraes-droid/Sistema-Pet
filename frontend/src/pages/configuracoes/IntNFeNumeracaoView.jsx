import { FiHash, FiRefreshCw } from "react-icons/fi";
import {
  currentSequence,
  documentName,
  environmentName,
  formatSequence,
  prepareNumbering,
} from "./intnfeNumeracao.mjs";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";
const fieldClass =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-white";

export default function IntNFeNumeracaoView({
  rows,
  form,
  busy,
  error,
  message,
  review,
  onChange,
  onReload,
  onReview,
  onCancel,
  onSave,
}) {
  const current = rows && currentSequence(rows, form.serie, form.ambiente_codigo, form.modelo);
  const document = documentName(form.modelo);
  const prepared = prepareNumbering(rows, form);
  const visible =
    rows
      ?.filter(
        (row) =>
          row.modelo === Number(form.modelo) && row.ambienteCodigo === Number(form.ambiente_codigo),
      )
      .sort((a, b) => Number(a.serie) - Number(b.serie)) ?? [];
  return (
    <section
      aria-busy={busy}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FiHash className="mt-1 h-7 w-7 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">Numeração fiscal</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Informe manualmente de qual número sua empresa vai continuar em cada série e ambiente.
            </p>
          </div>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={onReload}
          className={`${buttonClass} border border-slate-300`}
        >
          <FiRefreshCw aria-hidden="true" />
          {busy ? "Aguarde…" : "Consultar numeração"}
        </button>
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
      <form onSubmit={onReview} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-sm font-semibold">
            Documento
            <select
              value={form.modelo}
              disabled={busy || Boolean(review)}
              onChange={(e) => onChange({ modelo: e.target.value, proximo_numero: "" })}
              className={fieldClass}
            >
              <option value="55">NF-e (modelo 55)</option>
              <option value="65">NFC-e (modelo 65)</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            Ambiente
            <select
              value={form.ambiente_codigo}
              disabled={busy || Boolean(review)}
              onChange={(e) => onChange({ ambiente_codigo: e.target.value, proximo_numero: "" })}
              className={fieldClass}
            >
              <option value="2">Homologação (testes)</option>
              <option value="1">Produção</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            Série
            <input
              value={form.serie}
              inputMode="numeric"
              maxLength={3}
              disabled={busy || Boolean(review)}
              onChange={(e) => onChange({ serie: e.target.value, proximo_numero: "" })}
              className={fieldClass}
              aria-describedby="intnfe-series-help"
            />
          </label>
          <label className="text-sm font-semibold">
            Próximo número da {document}
            <input
              value={form.proximo_numero}
              inputMode="numeric"
              maxLength={9}
              disabled={busy || !rows || Boolean(review)}
              onChange={(e) => onChange({ proximo_numero: e.target.value })}
              placeholder={current ? String(current.proximoNumero) : "Ex.: 4501"}
              className={fieldClass}
              aria-describedby="intnfe-number-help"
            />
          </label>
        </div>
        <p id="intnfe-series-help" className="text-sm text-slate-600 dark:text-slate-300">
          {document} (modelo {form.modelo}). Séries de 0 a 889. Cada modelo e ambiente mantém sua
          própria sequência.
        </p>
        {Number(form.ambiente_codigo) === 1 && (
          <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
            Você está configurando a numeração de produção. Confira a última {document} desta mesma
            série no sistema que sua empresa já utiliza.
          </p>
        )}
        {current && (
          <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800" aria-live="polite">
            <p className="font-semibold">
              {environmentName(form.ambiente_codigo)} · Série {current.serie.padStart(3, "0")}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-8 gap-y-2">
              <p>
                Último número no emissor: <strong>{formatSequence(current.ultimoNumero)}</strong>
              </p>
              <p>
                Próxima {document}: <strong>{formatSequence(current.proximoNumero)}</strong>
              </p>
            </div>
            {current.nova && (
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                Esta série ainda não aparece no emissor. Começar pelo número 1 não exige ajuste.
              </p>
            )}
          </div>
        )}
        <div
          id="intnfe-number-help"
          className="space-y-1 text-sm text-slate-600 dark:text-slate-300"
        >
          <p>Exemplo: se a última nota foi 4.500, informe 4501 como próximo número.</p>
          <p>
            Consulte a última nota no sistema que sua empresa usava antes. O CorePet não tenta
            adivinhar essa sequência.
          </p>
          <p>
            A numeração só avança. Depois de salvar, os números anteriores não poderão ser
            reutilizados neste emissor.
          </p>
          {prepared.error && <p aria-live="polite">{prepared.error}</p>}
        </div>
        {!review ? (
          <button
            type="submit"
            disabled={busy || Boolean(prepared.error)}
            className={`${buttonClass} bg-blue-600 text-white`}
          >
            Revisar ajuste
          </button>
        ) : (
          <div
            className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"
            role="group"
            aria-label="Revisão do ajuste de numeração"
          >
            <p className="font-bold">
              Confirme o ajuste em {environmentName(review.payload.ambiente_codigo)}
            </p>
            <p className="text-sm">
              {documentName(review.payload.modelo)} · Série {review.payload.serie.padStart(3, "0")}{" "}
              · Próximo número:{" "}
              <strong>
                {formatSequence(review.current.proximoNumero)} →{" "}
                {formatSequence(review.payload.proximo_numero)}
              </strong>
              .
            </p>
            <p className="text-sm">
              O emissor passará a considerar a sequência alcançada até{" "}
              {formatSequence(review.payload.proximo_numero - 1)}. Esse avanço não pode ser
              desfeito.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={onSave}
                className={`${buttonClass} bg-blue-600 text-white`}
              >
                Confirmar e salvar numeração
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={onCancel}
                className={`${buttonClass} border border-amber-400`}
              >
                Voltar e revisar
              </button>
            </div>
          </div>
        )}
      </form>
      {rows && (
        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <h3 className="font-semibold">
            Séries de {document} em {environmentName(form.ambiente_codigo)}
          </h3>
          {visible.length ? (
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {visible.map((row) => (
                <li key={row.serie}>
                  <button
                    type="button"
                    disabled={busy || Boolean(review)}
                    onClick={() =>
                      onChange({ serie: String(Number(row.serie)), proximo_numero: "" })
                    }
                    className="w-full rounded-lg border border-slate-200 p-3 text-left text-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    <strong>Série {row.serie.padStart(3, "0")}</strong>{" "}
                    <span className="ml-3">Próxima: {formatSequence(row.proximoNumero)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Nenhuma série de {document} registrada neste ambiente.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
