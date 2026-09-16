import { FiHash, FiHelpCircle, FiPlus, FiRefreshCw, FiTrash2 } from "react-icons/fi";
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

function SequenceCard({
  model,
  form,
  rows,
  environment,
  busy,
  review,
  onChange,
  onToggleUse,
  onReview,
  onCancel,
  onSave,
  onRemove,
  savedConfiguration,
}) {
  const document = documentName(model);
  const current = rows && currentSequence(rows, form.serie, environment, model);
  const prepared = prepareNumbering(rows, {
    ...form,
    modelo: String(model),
    ambiente_codigo: String(environment),
  });
  const visible =
    rows
      ?.filter((row) => row.modelo === model && row.ambienteCodigo === environment)
      .sort((a, b) => Number(a.serie) - Number(b.serie)) ?? [];
  const reviewing = review?.model === model;
  const choicePersisted = Boolean(
    savedConfiguration && Number(savedConfiguration.serie) === Number(form.serie),
  );
  const sameNext =
    current &&
    (form.proximo_numero === "" || Number(form.proximo_numero) === current.proximoNumero);
  const canSaveChoice = Boolean(form.usar_no_corepet && current && sameNext);
  const canReview = canSaveChoice || !prepared.error;

  return (
    <article className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5 dark:border-slate-700 dark:bg-slate-950/40">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-950 dark:text-white">
            {document} <span className="font-normal text-slate-500">· modelo {model}</span>
          </h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Informe a série e a próxima numeração usadas antes da migração para o CorePet.
          </p>
        </div>
        {model === 65 && onRemove ? (
          <button
            type="button"
            disabled={busy || reviewing}
            onClick={onRemove}
            className={`${buttonClass} border border-slate-300 bg-white text-slate-700 dark:bg-slate-900 dark:text-slate-200`}
          >
            <FiTrash2 aria-hidden="true" /> Remover NFC-e
          </button>
        ) : null}
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          Série utilizada
          <input
            value={form.serie}
            inputMode="numeric"
            maxLength={3}
            disabled={busy || reviewing}
            onChange={(event) =>
              onChange(model, {
                serie: event.target.value.replace(/\D/g, "").slice(0, 3),
                proximo_numero: "",
              })
            }
            className={fieldClass}
          />
        </label>
        <label className="text-sm font-semibold">
          Próximo número da {document}
          <input
            value={form.proximo_numero}
            inputMode="numeric"
            min={current?.proximoNumero || 1}
            maxLength={9}
            disabled={busy || !rows || reviewing}
            onChange={(event) =>
              onChange(model, {
                proximo_numero: event.target.value.replace(/\D/g, "").slice(0, 9),
              })
            }
            placeholder={current ? String(current.proximoNumero) : "Ex.: 4501"}
            className={fieldClass}
          />
        </label>
      </div>

      {current ? (
        <div className="rounded-xl bg-white p-3 text-sm dark:bg-slate-900">
          {current.nova ? (
            <p>
              Esta série ainda não possui numeração. O menor próximo número permitido é{" "}
              <strong>1</strong>.
            </p>
          ) : (
            <p>
              No emissor: último número <strong>{formatSequence(current.ultimoNumero)}</strong> ·
              próximo <strong>{formatSequence(current.proximoNumero)}</strong>.
            </p>
          )}
          <p className="mt-1 text-xs text-slate-500">
            Esta sequência só pode continuar do próximo número mostrado ou avançar.
          </p>
        </div>
      ) : null}

      <label
        className={`flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 ${choicePersisted ? "cursor-default" : "cursor-pointer"}`}
      >
        <input
          type="checkbox"
          checked={form.usar_no_corepet}
          disabled={busy || reviewing || !current || choicePersisted}
          onChange={(event) => onToggleUse(model, event.target.checked)}
          className="mt-0.5 h-4 w-4"
        />
        <span>
          <strong>
            {choicePersisted
              ? "Esta é a série em uso no CorePet"
              : "Continuar com esta série no CorePet"}
          </strong>
          <span className="mt-1 block">
            {choicePersisted
              ? "A escolha está salva. Para trocar, selecione outra série e salve a nova escolha."
              : "Ao marcar e salvar, esta série será usada nas próximas emissões."}
          </span>
        </span>
      </label>

      {visible.length ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Séries já registradas neste ambiente
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {visible.map((row) => (
              <button
                key={row.serie}
                type="button"
                disabled={busy || reviewing}
                onClick={() =>
                  onChange(model, { serie: String(Number(row.serie)), proximo_numero: "" })
                }
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:border-blue-300 dark:border-slate-700 dark:bg-slate-900"
              >
                Série {row.serie.padStart(3, "0")} · próxima {formatSequence(row.proximoNumero)}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {!reviewing ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={busy || !canReview || (choicePersisted && sameNext)}
            onClick={() => onReview(model)}
            className={`${buttonClass} bg-blue-600 text-white`}
          >
            {choicePersisted && sameNext
              ? "Série em uso"
              : canSaveChoice
                ? "Salvar escolha"
                : "Salvar sequência"}
          </button>
          {prepared.error && !canSaveChoice && !(choicePersisted && sameNext) ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">{prepared.error}</p>
          ) : null}
        </div>
      ) : (
        <div className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950">
          <p className="font-bold">
            {review.selectionOnly
              ? `Confirmar escolha da ${document}`
              : `Confirmar sequência de ${document}`}
          </p>
          {review.selectionOnly ? (
            <p className="text-sm">
              A série <strong>{form.serie.padStart(3, "0")}</strong>, próxima numeração{" "}
              <strong>{formatSequence(review.current.proximoNumero)}</strong>, será salva como
              padrão da {document} no CorePet.
            </p>
          ) : (
            <p className="text-sm">
              Série {review.payload.serie.padStart(3, "0")} · próxima numeração:{" "}
              <strong>
                {formatSequence(review.current.proximoNumero)} →{" "}
                {formatSequence(review.payload.proximo_numero)}
              </strong>
              . Esse avanço não poderá ser desfeito.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={onSave}
              className={`${buttonClass} bg-blue-600 text-white`}
            >
              {review.selectionOnly ? "Confirmar escolha" : "Confirmar e salvar"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={onCancel}
              className={`${buttonClass} border border-amber-400`}
            >
              Voltar
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

export default function IntNFeNumeracaoView({
  rows,
  forms,
  models,
  environment,
  busy,
  error,
  message,
  review,
  savedConfigurations = [],
  onChange,
  onToggleUse,
  onReload,
  onAddNfce,
  onRemoveNfce,
  onReview,
  onCancel,
  onSave,
}) {
  return (
    <section
      aria-busy={busy}
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FiHash className="mt-1 h-7 w-7 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">
              1. Sequências usadas anteriormente
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Registre onde cada documento parou em {environmentName(environment).toLowerCase()}.
              Isso evita repetir números ao trocar de sistema.
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
          {busy ? "Aguarde…" : "Atualizar sequências"}
        </button>
      </header>

      {error ? (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      ) : null}
      {message ? (
        <p
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
        >
          {message}
        </p>
      ) : null}

      <details className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
        <summary className="flex cursor-pointer list-none items-center gap-2 font-bold">
          <FiHelpCircle aria-hidden="true" /> Qual modelo escolher?
        </summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-white/70 p-3">
            <p className="font-bold">NF-e · modelo 55</p>
            <p className="mt-1">
              Usada nas vendas de mercadorias que exigem NF-e, como operações com entrega,
              e-commerce e muitas vendas entre empresas. A regra fiscal da operação define o
              documento correto.
            </p>
          </div>
          <div className="rounded-lg bg-white/70 p-3">
            <p className="font-bold">NFC-e · modelo 65</p>
            <p className="mt-1">
              Usada no varejo para consumidor final, normalmente no atendimento presencial. Para
              emiti-la, a empresa também precisa cadastrar o CSC obtido na SEFAZ.
            </p>
          </div>
        </div>
        <p className="mt-3 font-semibold">
          Cada modelo possui numeração própria. NF-e 55 série 1 e NFC-e 65 série 1 não compartilham
          a mesma sequência.
        </p>
      </details>

      <div className="space-y-4">
        {models.map((model) => (
          <SequenceCard
            key={model}
            model={model}
            form={forms[model]}
            rows={rows}
            environment={environment}
            busy={busy}
            review={review}
            onChange={onChange}
            onToggleUse={onToggleUse}
            onReview={onReview}
            onCancel={onCancel}
            onSave={onSave}
            onRemove={model === 65 ? onRemoveNfce : null}
            savedConfiguration={savedConfigurations.find(
              (item) => item.ambiente_codigo === environment && item.modelo === model,
            )}
          />
        ))}
      </div>

      {!models.includes(65) ? (
        <button
          type="button"
          disabled={busy}
          onClick={onAddNfce}
          className={`${buttonClass} border border-blue-300 bg-blue-50 text-blue-800`}
        >
          <FiPlus aria-hidden="true" /> Adicionar NFC-e (modelo 65)
        </button>
      ) : null}
    </section>
  );
}
