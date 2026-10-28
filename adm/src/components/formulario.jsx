import { useEffect, useId } from "react";
import { Botao } from "./ui";

export function Selecao({ rotulo, opcoes, erro = "", id, ...resto }) {
  const gerado = useId();
  const idDoCampo = id || gerado;
  return (
    <div>
      <label htmlFor={idDoCampo} className="block text-sm font-medium text-slate-800 dark:text-slate-200">
        {rotulo}
      </label>
      <select
        id={idDoCampo}
        aria-invalid={Boolean(erro)}
        {...resto}
        className="mt-1 min-h-[44px] w-full rounded-lg border border-slate-300 bg-white px-3 text-base text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
      >
        {opcoes.map((opcao) => (
          <option key={opcao.value} value={opcao.value}>
            {opcao.label}
          </option>
        ))}
      </select>
      {erro ? (
        <p role="alert" className="mt-1 text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}
    </div>
  );
}

export function CaixaDeMarcar({ children, ...resto }) {
  return (
    <label className="flex min-h-[44px] items-center gap-3 text-sm">
      <input type="checkbox" {...resto} className="h-5 w-5 accent-teal-700" />
      {children}
    </label>
  );
}

/**
 * Janela com formulario. Esc e o botao Cancelar fecham; clicar fora nao fecha,
 * para ninguem perder o que digitou sem querer.
 */
export function Janela({
  titulo,
  formId,
  rotuloSalvar = "Salvar",
  enviando = false,
  aoSalvar,
  aoFechar,
  soFechar = false,
  children,
}) {
  const idTitulo = useId();
  useEffect(() => {
    const aoTeclar = (evento) => {
      if (evento.key === "Escape") aoFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        className="my-8 w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900"
      >
        <h2 id={idTitulo} className="text-lg font-bold">
          {titulo}
        </h2>
        <form
          id={formId}
          noValidate
          onSubmit={(evento) => {
            evento.preventDefault();
            if (aoSalvar) aoSalvar();
          }}
          className="mt-4 space-y-4"
        >
          {children}
        </form>
        <div className="mt-6 flex justify-end gap-3">
          <Botao variante="secundario" onClick={aoFechar} disabled={enviando}>
            {soFechar ? "Fechar" : "Cancelar"}
          </Botao>
          {soFechar ? null : (
            <Botao type="submit" form={formId} carregando={enviando}>
              {rotuloSalvar}
            </Botao>
          )}
        </div>
      </div>
    </div>
  );
}
