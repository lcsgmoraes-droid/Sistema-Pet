import { ChevronDown, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import useRevealFloatingPanel from "../../../hooks/useRevealFloatingPanel";
import { normalizar } from "../utils/texto";

export default function InputComboboxMultiplo({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  onChange,
  opcoes = [],
  placeholder = "Selecione...",
  required = false,
  value = [],
}) {
  const containerRef = useRef(null);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const [indiceAtivo, setIndiceAtivo] = useState(0);

  const selecionadas = useMemo(
    () =>
      value
        .map((valorItem) => opcoes.find((opcao) => String(opcao.value) === String(valorItem)))
        .filter(Boolean),
    [value, opcoes],
  );

  const disponiveis = useMemo(
    () =>
      opcoes.filter(
        (opcao) => !value.some((valorItem) => String(valorItem) === String(opcao.value)),
      ),
    [opcoes, value],
  );

  const filtradas = useMemo(() => {
    if (!termo) return disponiveis;
    const alvo = normalizar(termo);
    return disponiveis.filter((opcao) => normalizar(opcao.label).includes(alvo));
  }, [disponiveis, termo]);

  useEffect(() => setIndiceAtivo(0), [termo, aberto]);

  useRevealFloatingPanel({ enabled: aberto, panelRef, refreshKey: filtradas.length });

  useEffect(() => {
    if (!aberto) return undefined;
    const aoClicarFora = (evento) => {
      if (!containerRef.current?.contains(evento.target)) setAberto(false);
    };
    document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [aberto]);

  const adicionar = (opcao) => {
    onChange?.([...value, opcao.value]);
    setTermo("");
    inputRef.current?.focus();
  };

  const remover = (valorRemovido) => {
    onChange?.(value.filter((valorItem) => String(valorItem) !== String(valorRemovido)));
  };

  const aoPressionarTecla = (evento) => {
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setAberto(true);
      setIndiceAtivo((atual) => Math.min(atual + 1, filtradas.length - 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setIndiceAtivo((atual) => Math.max(atual - 1, 0));
    } else if (evento.key === "Enter") {
      evento.preventDefault();
      if (aberto && filtradas[indiceAtivo]) adicionar(filtradas[indiceAtivo]);
    } else if (evento.key === "Backspace" && termo === "" && selecionadas.length > 0) {
      remover(selecionadas[selecionadas.length - 1].value);
    } else if (evento.key === "Escape") {
      setAberto(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </span>
      ) : null}
      <div
        onClick={() => inputRef.current?.focus()}
        className={[
          "mt-1 flex min-h-9 w-full flex-wrap items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 transition-colors",
          "focus-within:border-transparent focus-within:ring-2 focus-within:ring-blue-500",
          "dark:border-slate-700 dark:focus-within:ring-cyan-400",
          disabled
            ? "cursor-not-allowed bg-slate-50 dark:bg-slate-800"
            : "cursor-text bg-white dark:bg-slate-900",
        ].join(" ")}
      >
        {selecionadas.map((opcao) => (
          <span
            key={opcao.value}
            className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-200"
          >
            {opcao.label}
            {disabled ? null : (
              <button
                type="button"
                aria-label={`Remover ${opcao.label}`}
                onClick={(evento) => {
                  evento.stopPropagation();
                  remover(opcao.value);
                }}
                className="rounded hover:text-blue-900 dark:hover:text-white"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        ))}
        <input
          ref={inputRef}
          id={id}
          disabled={disabled}
          value={termo}
          placeholder={selecionadas.length === 0 ? placeholder : ""}
          onFocus={() => setAberto(true)}
          onChange={(evento) => {
            setTermo(evento.target.value);
            setAberto(true);
          }}
          onKeyDown={aoPressionarTecla}
          className="h-6 min-w-[60px] flex-1 border-0 bg-transparent text-sm text-slate-900 outline-none dark:text-slate-100"
        />
        <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
      </div>

      {aberto ? (
        <div
          ref={panelRef}
          role="listbox"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          {filtradas.length === 0 ? (
            <div className="px-3 py-2 text-slate-400 dark:text-slate-500">
              {disponiveis.length === 0
                ? "Todas as opções já foram selecionadas"
                : "Nenhuma opção encontrada"}
            </div>
          ) : (
            filtradas.map((opcao, indice) => (
              <button
                key={opcao.value}
                type="button"
                role="option"
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => adicionar(opcao)}
                className={[
                  "block w-full px-3 py-2 text-left",
                  indice === indiceAtivo
                    ? "bg-blue-50 text-blue-700 dark:bg-slate-800 dark:text-cyan-300"
                    : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800",
                ].join(" ")}
              >
                {opcao.label}
              </button>
            ))
          )}
        </div>
      ) : null}

      {error || help ? (
        <span
          className={[
            "mt-1 block text-xs",
            error ? "text-red-600 dark:text-red-400" : "text-slate-500 dark:text-slate-400",
          ].join(" ")}
        >
          {error || help}
        </span>
      ) : null}
    </div>
  );
}
