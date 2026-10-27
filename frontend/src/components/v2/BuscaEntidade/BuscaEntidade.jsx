import { Search } from "lucide-react";
import { useId, useMemo, useRef, useState } from "react";
import useRevealFloatingPanel from "../../../hooks/useRevealFloatingPanel";
import { ordenarSugestoesEntidade } from "../../../utils/buscaEntidades";
import InputTexto from "../InputTexto/InputTexto";

// Base interna das buscas. Consumidores mantêm filtros de permissão/estoque e scanner.
export default function BuscaEntidade({
  tipo,
  className = "",
  containerRef,
  containerId,
  inputRef,
  inputId,
  id,
  name,
  value = "",
  onChange,
  onFocus,
  onBlur,
  onKeyDown,
  onSelect,
  label,
  error,
  help,
  placeholder,
  disabled = false,
  required = false,
  autoFocus = false,
  autoComplete = "off",
  minChars = 1,
  showSuggestions = false,
  suggestions = [],
  renderSuggestion,
  renderSuggestionContent,
  renderDefault,
  loading = false,
}) {
  const identificador = useId();
  const rootRef = useRef(null);
  const panelRef = useRef(null);
  const [fechado, setFechado] = useState(false);
  const [indiceAtivo, setIndiceAtivo] = useState(-1);
  const listaId = `${inputId || id || identificador}-resultados`;
  const itens = useMemo(
    () => ordenarSugestoesEntidade(suggestions, value, tipo),
    [suggestions, value, tipo],
  );
  const aberto =
    !disabled &&
    !fechado &&
    showSuggestions &&
    String(value).trim().length >= minChars &&
    itens.length > 0;
  const indiceSeguro = Math.min(indiceAtivo, itens.length - 1);
  useRevealFloatingPanel({ enabled: aberto, panelRef, refreshKey: `${value}:${itens.length}` });
  const selecionar = (item) => {
    if (!item) return;
    setFechado(true);
    setIndiceAtivo(-1);
    onSelect?.(item);
  };
  const aoPressionar = (evento) => {
    if (evento.key === "Escape") {
      setFechado(true);
      setIndiceAtivo(-1);
    }
    if (aberto && ["ArrowDown", "ArrowUp"].includes(evento.key)) {
      evento.preventDefault();
      setIndiceAtivo((atual) =>
        evento.key === "ArrowDown" ? Math.min(atual + 1, itens.length - 1) : Math.max(atual - 1, 0),
      );
      return;
    }
    if (aberto && evento.key === "Enter" && onSelect && (indiceSeguro >= 0 || !onKeyDown)) {
      evento.preventDefault();
      selecionar(itens[indiceSeguro >= 0 ? indiceSeguro : 0]);
      return;
    }
    onKeyDown?.(evento);
  };
  return (
    <div
      id={containerId}
      ref={(elemento) => {
        rootRef.current = elemento;
        if (typeof containerRef === "function") containerRef(elemento);
        else if (containerRef) containerRef.current = elemento;
      }}
      className={`relative ${className}`.trim()}
    >
      <InputTexto
        ref={inputRef}
        id={inputId || id}
        name={name}
        value={value}
        label={label}
        error={error}
        help={help}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        autoFocus={autoFocus}
        autoComplete={autoComplete}
        inputProps={{
          role: "combobox",
          "aria-expanded": aberto,
          "aria-controls": aberto ? listaId : undefined,
          "aria-autocomplete": "list",
          "aria-activedescendant":
            aberto && indiceSeguro >= 0 ? `${listaId}-${indiceSeguro}` : undefined,
        }}
        onChange={(texto) => {
          setFechado(false);
          setIndiceAtivo(-1);
          onChange?.(texto);
        }}
        onFocus={(evento) => {
          setFechado(false);
          onFocus?.(evento);
        }}
        onBlur={(evento) => {
          if (!rootRef.current?.contains(evento.relatedTarget)) setFechado(true);
          onBlur?.(evento);
        }}
        onKeyDown={aoPressionar}
        right={<Search aria-hidden="true" className="h-4 w-4 text-slate-400" />}
      />
      {loading && (
        <span role="status" className="text-xs text-slate-500">
          Buscando…
        </span>
      )}
      {aberto && (
        <div
          ref={panelRef}
          id={listaId}
          role="listbox"
          aria-label={label || placeholder}
          className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          {itens.map((item, indice) =>
            renderSuggestion ? (
              <div
                key={item?.id ?? indice}
                id={`${listaId}-${indice}`}
                role="option"
                aria-selected={indice === indiceAtivo}
                className={indice === indiceAtivo ? "bg-blue-50 dark:bg-slate-800" : ""}
              >
                {renderSuggestion(item, indice)}
              </div>
            ) : (
              <button
                key={item?.id ?? indice}
                id={`${listaId}-${indice}`}
                type="button"
                role="option"
                aria-selected={indice === indiceAtivo}
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => selecionar(item)}
                className={`w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800 ${indice === indiceAtivo ? "bg-blue-50 dark:bg-slate-800" : ""}`}
              >
                {renderSuggestionContent
                  ? renderSuggestionContent(item, value)
                  : renderDefault(item, value)}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
