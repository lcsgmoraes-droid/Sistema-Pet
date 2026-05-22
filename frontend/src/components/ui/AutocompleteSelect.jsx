import { ChevronDown, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import useRevealFloatingPanel from "../../hooks/useRevealFloatingPanel";
import { filtrarOpcoesAutocomplete } from "./autocompleteSelectUtils";

export default function AutocompleteSelect({
  allowClear = true,
  className = "",
  disabled = false,
  emptyLabel = "Nenhuma opcao encontrada",
  getOptionLabel = (option) => option?.label || option?.nome || "",
  getOptionMeta,
  getOptionSearchText,
  getOptionValue = (option) => option?.value ?? option?.id ?? "",
  inputClassName = "",
  label,
  maxOptions = 30,
  onChange,
  options = [],
  placeholder = "Selecione...",
  searchPlaceholder,
  showLabel = true,
  value,
}) {
  const containerRef = useRef(null);
  const panelRef = useRef(null);
  const [termo, setTermo] = useState("");
  const [aberto, setAberto] = useState(false);

  const selecionado = useMemo(
    () => options.find((option) => String(getOptionValue(option)) === String(value)) || null,
    [getOptionValue, options, value],
  );

  useEffect(() => {
    if (selecionado) {
      setTermo(getOptionLabel(selecionado));
      return;
    }

    if (!value) {
      setTermo("");
    }
  }, [getOptionLabel, selecionado, value]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const opcoesFiltradas = useMemo(
    () =>
      filtrarOpcoesAutocomplete({
        termo,
        options,
        getOptionLabel,
        getOptionMeta,
        getOptionSearchText,
        maxOptions,
      }),
    [getOptionLabel, getOptionMeta, getOptionSearchText, maxOptions, options, termo],
  );

  useRevealFloatingPanel({
    enabled: aberto && !disabled,
    panelRef,
    refreshKey: `${termo}:${opcoesFiltradas.length}`,
  });

  const selecionar = (option) => {
    setTermo(getOptionLabel(option));
    setAberto(false);
    onChange?.(String(getOptionValue(option)), option);
  };

  const limpar = () => {
    setTermo("");
    setAberto(false);
    onChange?.("", null);
  };

  const handleInputChange = (event) => {
    const novoTermo = event.target.value;
    setTermo(novoTermo);
    setAberto(true);

    if (value) {
      onChange?.("", null);
    }
  };

  const handleInputKeyDown = (event) => {
    if (event.key === "Escape") {
      setAberto(false);
      return;
    }

    if (event.key === "Enter" && aberto && opcoesFiltradas.length > 0) {
      event.preventDefault();
      selecionar(opcoesFiltradas[0]);
    }
  };

  return (
    <div className={`relative ${className}`.trim()} ref={containerRef}>
      {showLabel && label ? (
        <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      ) : null}

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={termo}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={() => setAberto(true)}
          placeholder={searchPlaceholder || placeholder}
          disabled={disabled}
          className={[
            "h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-16 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500",
            inputClassName,
          ]
            .filter(Boolean)
            .join(" ")}
          autoComplete="off"
        />
        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
          {allowClear && (termo || value) ? (
            <button
              type="button"
              onClick={limpar}
              disabled={disabled}
              className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
              title="Limpar"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setAberto((prev) => !prev)}
            disabled={disabled}
            className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
            title="Abrir lista"
          >
            <ChevronDown className={`h-4 w-4 transition ${aberto ? "rotate-180" : ""}`} />
          </button>
        </div>
      </div>

      {aberto && !disabled ? (
        <div
          ref={panelRef}
          className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg"
        >
          {opcoesFiltradas.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-500">{emptyLabel}</div>
          ) : (
            opcoesFiltradas.map((option) => {
              const optionValue = String(getOptionValue(option));
              const ativo = String(value || "") === optionValue;
              const meta = getOptionMeta?.(option);

              return (
                <button
                  key={optionValue}
                  type="button"
                  onClick={() => selecionar(option)}
                  className={`w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50 ${
                    ativo ? "bg-blue-50 text-blue-800" : "text-slate-800"
                  }`}
                >
                  <div className="truncate text-sm font-medium">{getOptionLabel(option)}</div>
                  {meta ? <div className="mt-0.5 truncate text-xs text-slate-500">{meta}</div> : null}
                </button>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );
}
