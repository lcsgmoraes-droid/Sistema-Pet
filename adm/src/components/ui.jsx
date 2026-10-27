import { forwardRef, useEffect, useId, useRef } from "react";
import { Loader2 } from "lucide-react";

// Componentes base do painel. Pequenos e acessiveis: alvo de toque de 44 px, foco visivel,
// estado dito em texto (nunca so em cor).

const VARIANTES = {
  primario:
    "bg-teal-700 text-white hover:bg-teal-800 disabled:bg-slate-300 disabled:text-slate-500 dark:bg-teal-600 dark:hover:bg-teal-500 dark:disabled:bg-slate-700 dark:disabled:text-slate-400",
  secundario:
    "border border-slate-300 bg-white text-slate-800 hover:bg-slate-100 disabled:text-slate-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800",
  perigo:
    "bg-red-700 text-white hover:bg-red-800 disabled:bg-slate-300 disabled:text-slate-500 dark:bg-red-600 dark:hover:bg-red-500",
};

export const Botao = forwardRef(function Botao(
  { variante = "primario", carregando = false, children, className = "", ...resto },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      {...resto}
      disabled={resto.disabled || carregando}
      className={[
        "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed",
        VARIANTES[variante],
        className,
      ].join(" ")}
    >
      {carregando ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
});

export function Campo({ rotulo, erro = "", ajuda = "", direita = null, id, ...resto }) {
  const gerado = useId();
  const idDoCampo = id || gerado;
  const idDaMensagem = `${idDoCampo}-msg`;
  return (
    <div>
      <label htmlFor={idDoCampo} className="block text-sm font-medium text-slate-800 dark:text-slate-200">
        {rotulo}
      </label>
      <div className="relative mt-1">
        <input
          id={idDoCampo}
          aria-invalid={Boolean(erro)}
          aria-describedby={erro || ajuda ? idDaMensagem : undefined}
          {...resto}
          className={[
            "min-h-[44px] w-full rounded-lg border bg-white px-3 text-base text-slate-900 dark:bg-slate-900 dark:text-slate-100",
            direita ? "pr-12" : "",
            erro ? "border-red-600" : "border-slate-300 dark:border-slate-600",
          ].join(" ")}
        />
        {direita ? <div className="absolute inset-y-0 right-1 flex items-center">{direita}</div> : null}
      </div>
      {erro || ajuda ? (
        <p
          id={idDaMensagem}
          role={erro ? "alert" : undefined}
          className={[
            "mt-1 text-sm",
            erro ? "font-medium text-red-700 dark:text-red-300" : "text-slate-600 dark:text-slate-400",
          ].join(" ")}
        >
          {erro || ajuda}
        </p>
      ) : null}
    </div>
  );
}

/** Interruptor (liga/desliga). O estado tambem aparece em texto ao lado, no chamador. */
export function Interruptor({ ligado, aoAlternar, desabilitado = false, rotulo }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={ligado}
      aria-label={rotulo}
      disabled={desabilitado}
      onClick={aoAlternar}
      className="flex min-h-[44px] min-w-[44px] items-center justify-center disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span
        className={[
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
          ligado ? "bg-teal-700 dark:bg-teal-500" : "bg-slate-400 dark:bg-slate-600",
        ].join(" ")}
      >
        <span
          className={[
            "inline-block h-5 w-5 rounded-full bg-white shadow transition-transform",
            ligado ? "translate-x-5" : "translate-x-0.5",
          ].join(" ")}
        />
      </span>
    </button>
  );
}

const TONS_DO_AVISO = {
  erro: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100",
  atencao: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100",
  info: "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-100",
  ok: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100",
};

export function Aviso({ tom = "info", children, ...resto }) {
  return (
    <div
      role={tom === "erro" ? "alert" : "status"}
      {...resto}
      className={`rounded-lg border px-4 py-3 text-sm ${TONS_DO_AVISO[tom]}`}
    >
      {children}
    </div>
  );
}

export function Etiqueta({ children, tom = "neutro" }) {
  const tons = {
    neutro: "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100",
    ok: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-100",
    atencao: "bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100",
    erro: "bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-100",
  };
  return <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ${tons[tom]}`}>{children}</span>;
}

export function Carregando({ rotulo = "Carregando" }) {
  return (
    <div role="status" aria-label={rotulo} className="space-y-3">
      {[0, 1, 2].map((item) => (
        <div key={item} className="h-16 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
      ))}
    </div>
  );
}

export function VazioComTexto({ titulo, descricao, icone: Icone }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center dark:border-slate-700">
      {Icone ? <Icone className="mx-auto h-8 w-8 text-slate-400" aria-hidden="true" /> : null}
      <p className="mt-2 font-semibold text-slate-800 dark:text-slate-100">{titulo}</p>
      {descricao ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{descricao}</p> : null}
    </div>
  );
}

/** Caixa de confirmacao. Esc cancela; o foco inicial fica em "Cancelar" (acao segura). */
export function Confirmacao({ titulo, children, rotuloConfirmar, perigo = false, carregando = false, aoConfirmar, aoCancelar }) {
  const cancelar = useRef(null);
  const idTitulo = useId();

  useEffect(() => {
    cancelar.current?.focus();
    const aoTeclar = (evento) => {
      if (evento.key === "Escape") aoCancelar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoCancelar]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900"
      >
        <h2 id={idTitulo} className="text-lg font-bold">
          {titulo}
        </h2>
        <div className="mt-2 text-sm text-slate-700 dark:text-slate-300">{children}</div>
        <div className="mt-6 flex justify-end gap-3">
          <Botao ref={cancelar} variante="secundario" onClick={aoCancelar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao variante={perigo ? "perigo" : "primario"} onClick={aoConfirmar} carregando={carregando}>
            {rotuloConfirmar}
          </Botao>
        </div>
      </div>
    </div>
  );
}
