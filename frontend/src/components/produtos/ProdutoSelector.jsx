import { Search } from "lucide-react";
import { useRef } from "react";

import useRevealFloatingPanel from "../../hooks/useRevealFloatingPanel";

export default function ProdutoSelector({
  autoFocus = false,
  className = "",
  containerRef,
  disabled = false,
  id,
  inputClassName = "",
  inputRef,
  minChars = 2,
  onChange,
  onFocus,
  onKeyDown,
  onSelect,
  placeholder = "Digite o nome, codigo de barras ou SKU...",
  renderSuggestion,
  showSuggestions = false,
  suggestions = [],
  value = "",
}) {
  const panelRef = useRef(null);
  const searchValue = String(value || "");
  const shouldShowSuggestions =
    showSuggestions &&
    searchValue.trim().length >= minChars &&
    suggestions.length > 0;

  useRevealFloatingPanel({
    enabled: shouldShowSuggestions && !disabled,
    panelRef,
    refreshKey: `${searchValue}:${suggestions.length}`,
  });

  return (
    <div id={id} ref={containerRef} className={`relative ${className}`.trim()}>
      <div className="flex items-center">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(event) => onChange?.(event.target.value)}
          onFocus={onFocus}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className={[
            "h-9 flex-1 rounded-lg border border-gray-300 px-3 pr-9 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50",
            inputClassName,
          ]
            .filter(Boolean)
            .join(" ")}
          autoFocus={autoFocus}
        />
        <Search className="absolute right-3 h-5 w-5 text-gray-400" />
      </div>

      {shouldShowSuggestions && (
        <div
          ref={panelRef}
          className="absolute z-10 mt-2 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg"
        >
          {suggestions.map((produto, index) =>
            renderSuggestion ? (
              renderSuggestion(produto, index)
            ) : (
              <button
                key={produto?.id ?? index}
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => onSelect?.(produto)}
                className="w-full border-b px-4 py-3 text-left last:border-b-0 hover:bg-gray-50"
              >
                <div className="font-medium text-gray-900">{produto?.nome}</div>
                {(produto?.codigo || produto?.sku || produto?.codigo_barras) && (
                  <div className="text-sm text-gray-500">
                    Cod: {produto.codigo || produto.sku || produto.codigo_barras}
                  </div>
                )}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
