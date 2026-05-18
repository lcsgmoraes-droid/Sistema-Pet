import { Plus, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  filtrarCatalogoClinico,
  montarOpcoesCatalogoClinico,
} from "./catalogoClinicoAutocompleteUtils";

export default function CatalogoClinicoAutocomplete({
  disabled = false,
  label = "Medicamento ou procedimento",
  medicamentos = [],
  onCreate,
  onSelect,
  onTextChange,
  placeholder = "Digite para buscar no catalogo...",
  procedimentos = [],
  value = "",
}) {
  const containerRef = useRef(null);
  const [aberto, setAberto] = useState(false);

  const opcoes = useMemo(
    () => montarOpcoesCatalogoClinico({ medicamentos, procedimentos }),
    [medicamentos, procedimentos]
  );

  const sugestoes = useMemo(
    () => filtrarCatalogoClinico(opcoes, value),
    [opcoes, value]
  );

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const termoSuficiente = String(value || "").trim().length >= 2;

  function selecionar(opcao) {
    setAberto(false);
    onSelect?.(opcao);
  }

  function limpar() {
    onTextChange?.("");
    setAberto(false);
  }

  return (
    <div className="relative" ref={containerRef}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <label className="text-xs font-medium text-gray-600">{label}</label>
        {onCreate ? (
          <button
            type="button"
            onClick={onCreate}
            className="inline-flex items-center gap-1 rounded-md border border-blue-100 bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700 hover:bg-blue-100"
          >
            <Plus size={12} />
            Novo
          </button>
        ) : null}
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={value}
          onChange={(event) => {
            onTextChange?.(event.target.value);
            setAberto(true);
          }}
          onFocus={() => setAberto(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setAberto(false);
            }
            if (event.key === "Enter" && aberto && sugestoes[0]) {
              event.preventDefault();
              selecionar(sugestoes[0]);
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 pl-9 pr-9 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          autoComplete="off"
        />
        {value ? (
          <button
            type="button"
            onClick={limpar}
            disabled={disabled}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
            title="Limpar"
          >
            <X size={14} />
          </button>
        ) : null}
      </div>

      {aberto && !disabled ? (
        <div className="absolute z-40 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {!termoSuficiente ? (
            <div className="px-4 py-3 text-sm text-slate-500">Digite pelo menos 2 letras para buscar.</div>
          ) : sugestoes.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-500">Nenhum item encontrado. Voce pode manter o texto digitado.</div>
          ) : (
            sugestoes.map((opcao) => (
              <button
                key={opcao.valor}
                type="button"
                onClick={() => selecionar(opcao)}
                className="w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
              >
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-slate-800">{opcao.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    opcao.tipo === "medicamento"
                      ? "bg-blue-50 text-blue-700"
                      : "bg-purple-50 text-purple-700"
                  }`}>
                    {opcao.tipo}
                  </span>
                </div>
                {opcao.meta ? <div className="mt-0.5 truncate text-xs text-slate-500">{opcao.meta}</div> : null}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
