import { Search } from "lucide-react";

function defaultPessoaLabel(pessoa) {
  return pessoa?.nome || pessoa?.razao_social || pessoa?.fantasia || "Pessoa";
}

function defaultPessoaMeta(pessoa) {
  return [pessoa?.cpf || pessoa?.cnpj, pessoa?.telefone || pessoa?.celular]
    .filter(Boolean)
    .join(" - ");
}

export default function PessoaSelector({
  autoComplete = "off",
  className = "",
  disabled = false,
  id,
  inputClassName = "",
  inputRef,
  minChars = 2,
  name,
  onChange,
  onFocus,
  onKeyDown,
  onSelect,
  placeholder = "Digite nome, CPF/CNPJ ou telefone...",
  renderSuggestion,
  showSuggestions = false,
  suggestions = [],
  value = "",
}) {
  const searchValue = String(value || "");
  const shouldShowSuggestions =
    showSuggestions &&
    searchValue.trim().length >= minChars &&
    suggestions.length > 0;

  return (
    <div className={`relative ${className}`.trim()}>
      <input
        id={id}
        name={name || id}
        ref={inputRef}
        type="text"
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className={[
          "h-9 w-full rounded-lg border border-gray-300 px-3 pr-9 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50",
          inputClassName,
        ]
          .filter(Boolean)
          .join(" ")}
        disabled={disabled}
        autoComplete={autoComplete}
      />
      <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />

      {shouldShowSuggestions && (
        <div className="absolute z-10 mt-2 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
          {suggestions.map((pessoa, index) =>
            renderSuggestion ? (
              renderSuggestion(pessoa, index)
            ) : (
              <button
                key={pessoa?.id ?? index}
                type="button"
                onClick={() => onSelect?.(pessoa)}
                className="w-full border-b px-4 py-3 text-left last:border-b-0 hover:bg-gray-50"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1 truncate font-medium text-gray-900">
                    {defaultPessoaLabel(pessoa)}
                  </div>
                  {pessoa?.codigo && (
                    <div className="flex-shrink-0 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-600">
                      #{pessoa.codigo}
                    </div>
                  )}
                </div>
                {defaultPessoaMeta(pessoa) && (
                  <div className="text-sm text-gray-500">
                    {defaultPessoaMeta(pessoa)}
                  </div>
                )}
                {pessoa?.pets?.length > 0 && (
                  <div className="mt-1 text-xs text-blue-600">
                    {pessoa.pets.length} pet(s)
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
