import { normalizeDisplayText } from "./categoriasFinanceirasUtils";

export default function CategoriasFinanceirasExpandedPanel({
  cat,
  filhasFinanceiras,
  handleQuickCustoPeDRE,
  handleQuickTipoCusto,
  subsDRE,
}) {
  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-t border-purple-100">
      {filhasFinanceiras.length > 0 && (
        <>
          <div className="px-6 py-2 bg-orange-50 border-b border-orange-200">
            <span className="text-xs font-semibold text-orange-700 uppercase tracking-wide">
              Subcategorias Financeiras ({filhasFinanceiras.length}) â€” classifique cada uma
            </span>
          </div>
          {filhasFinanceiras.map((filha) => (
            <div
              key={filha.id}
              className="px-6 py-3 flex items-center gap-3 ml-9 border-b border-orange-100 last:border-b-0"
            >
              <span className="text-orange-400 text-lg">â””â”€</span>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-700">
                  {normalizeDisplayText(filha.nome)}
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() =>
                    handleQuickTipoCusto(filha.id, filha.tipo_custo === "fixo" ? null : "fixo")
                  }
                  className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                    filha.tipo_custo === "fixo"
                      ? "bg-orange-500 text-white border-orange-500"
                      : "bg-white text-gray-600 border-gray-300 hover:border-orange-400 hover:text-orange-600"
                  }`}
                >
                  ðŸ”’ Fixo
                </button>
                <button
                  onClick={() =>
                    handleQuickTipoCusto(
                      filha.id,
                      filha.tipo_custo === "variavel" ? null : "variavel",
                    )
                  }
                  className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                    filha.tipo_custo === "variavel"
                      ? "bg-blue-500 text-white border-blue-500"
                      : "bg-white text-gray-600 border-gray-300 hover:border-blue-400 hover:text-blue-600"
                  }`}
                >
                  ðŸ“ˆ VariÃ¡vel
                </button>
              </div>
            </div>
          ))}
        </>
      )}

      {subsDRE.length > 0 && (
        <>
          <div className="px-6 py-2 bg-purple-100/50 border-b border-purple-200">
            <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
              Subcategorias DRE ({subsDRE.length})
              {cat.tipo_custo === "ambos" && " â€” classifique cada uma"}
            </span>
          </div>
          {subsDRE.map((sub) => (
            <div
              key={sub.id}
              className="px-6 py-3 flex items-center gap-4 ml-9 border-b border-purple-100 last:border-b-0"
            >
              <span className="text-purple-400 text-lg">â””â”€</span>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-700">
                  {normalizeDisplayText(sub.nome)}
                </div>
              </div>
              <div className="flex gap-1 items-center">
                {sub.custo_pe && (
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      sub.custo_pe === "fixo"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-blue-100 text-blue-700"
                    }`}
                  >
                    {sub.custo_pe === "fixo" ? "ðŸ”’ Fixo" : "ðŸ“ˆ VariÃ¡vel"}
                  </span>
                )}
                {cat.tipo_custo === "ambos" && (
                  <div className="flex gap-1">
                    <button
                      onClick={() =>
                        handleQuickCustoPeDRE(sub.id, sub.custo_pe === "fixo" ? "" : "fixo")
                      }
                      className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                        sub.custo_pe === "fixo"
                          ? "bg-orange-500 text-white border-orange-500"
                          : "bg-white text-gray-500 border-gray-300 hover:border-orange-400 hover:text-orange-600"
                      }`}
                    >
                      ðŸ”’ Fixo
                    </button>
                    <button
                      onClick={() =>
                        handleQuickCustoPeDRE(sub.id, sub.custo_pe === "variavel" ? "" : "variavel")
                      }
                      className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                        sub.custo_pe === "variavel"
                          ? "bg-blue-500 text-white border-blue-500"
                          : "bg-white text-gray-500 border-gray-300 hover:border-blue-400 hover:text-blue-600"
                      }`}
                    >
                      ðŸ“ˆ VariÃ¡vel
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}

      {filhasFinanceiras.length === 0 && subsDRE.length === 0 && (
        <div className="px-6 py-4 ml-9 text-center">
          <div className="text-gray-400 text-sm">Nenhuma subcategoria cadastrada</div>
        </div>
      )}
    </div>
  );
}
