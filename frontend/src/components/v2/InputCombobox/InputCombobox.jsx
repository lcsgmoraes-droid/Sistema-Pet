import { ChevronDown, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import useRevealFloatingPanel from "../../../hooks/useRevealFloatingPanel";

function normalizar(texto) {
  return String(texto ?? "")
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export default function InputCombobox({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  onChange,
  opcoes = [],
  permitirLimpar = true,
  placeholder = "Selecione...",
  required = false,
  value,
}) {
  const containerRef = useRef(null);
  const panelRef = useRef(null);
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const [indiceAtivo, setIndiceAtivo] = useState(0);

  const selecionada = useMemo(
    () => opcoes.find((opcao) => String(opcao.value) === String(value)) || null,
    [opcoes, value],
  );

  useEffect(() => {
    setTermo(aberto ? "" : selecionada?.label || "");
  }, [aberto, selecionada]);

  const filtradas = useMemo(() => {
    if (!termo) return opcoes;
    const alvo = normalizar(termo);
    return opcoes.filter((opcao) => normalizar(opcao.label).includes(alvo));
  }, [opcoes, termo]);

  useRevealFloatingPanel({ enabled: aberto, panelRef, refreshKey: filtradas.length });

  useEffect(() => {
    if (!aberto) return undefined;
    const aoClicarFora = (evento) => {
      if (!containerRef.current?.contains(evento.target)) setAberto(false);
    };
    document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [aberto]);

  const escolher = (opcao) => {
    onChange?.(opcao.value, opcao);
    setAberto(false);
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
      if (aberto && filtradas[indiceAtivo]) escolher(filtradas[indiceAtivo]);
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
      <div className="relative mt-1">
        <input
          id={id}
          disabled={disabled}
          value={termo}
          placeholder={selecionada?.label || placeholder}
          onFocus={() => setAberto(true)}
          onChange={(evento) => {
            setTermo(evento.target.value);
            setAberto(true);
            setIndiceAtivo(0);
          }}
          onKeyDown={aoPressionarTecla}
          className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 pr-16 text-sm text-slate-900 outline-none transition-colors focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-cyan-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500"
        />
        <div className="absolute inset-y-0 right-1 flex items-center gap-0.5">
          {permitirLimpar && selecionada ? (
            <button
              type="button"
              aria-label="Limpar seleção"
              title="Limpar seleção"
              onClick={() => {
                onChange?.("", null);
                setTermo("");
              }}
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : null}
          <ChevronDown className="h-4 w-4 text-slate-400" aria-hidden="true" />
        </div>

        {aberto ? (
          <div
            ref={panelRef}
            role="listbox"
            className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            {filtradas.length === 0 ? (
              <div className="px-3 py-2 text-slate-400 dark:text-slate-500">
                Nenhuma opção encontrada
              </div>
            ) : (
              filtradas.map((opcao, indice) => (
                <button
                  key={opcao.value}
                  type="button"
                  role="option"
                  aria-selected={String(opcao.value) === String(value)}
                  onMouseDown={(evento) => evento.preventDefault()}
                  onClick={() => escolher(opcao)}
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
      </div>
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
