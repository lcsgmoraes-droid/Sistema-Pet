import { FiChevronDown, FiChevronRight, FiEdit2, FiTrash2 } from "react-icons/fi";
import CategoriasFinanceirasExpandedPanel from "./CategoriasFinanceirasExpandedPanel";
import { normalizeDisplayText } from "./categoriasFinanceirasUtils";

export default function CategoriasFinanceirasRow({
  cat,
  filhasFinanceiras,
  handleDelete,
  handleEdit,
  handleQuickCustoPeDRE,
  handleQuickTipoCusto,
  isExpanded,
  subsDRE,
  toggleExpansao,
}) {
  const temSubcategoria = subsDRE.length > 0 || filhasFinanceiras.length > 0;

  return (
    <div>
      <div className="px-6 py-4 hover:bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          <button
            onClick={() => toggleExpansao(cat.id)}
            className={`flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 transform hover:scale-105 ${
              !temSubcategoria
                ? "text-gray-300 cursor-not-allowed bg-gray-50"
                : isExpanded
                  ? "text-white bg-gradient-to-r from-purple-600 to-purple-700 shadow-lg hover:shadow-xl"
                  : "text-purple-600 bg-purple-100 hover:bg-purple-200 hover:text-purple-700 shadow-md hover:shadow-lg"
            }`}
            disabled={!temSubcategoria}
            title={
              !temSubcategoria
                ? "Sem subcategorias DRE"
                : isExpanded
                  ? "Recolher subcategorias"
                  : "Expandir subcategorias"
            }
          >
            {temSubcategoria ? (
              isExpanded ? (
                <FiChevronDown size={22} strokeWidth={2.5} />
              ) : (
                <FiChevronRight size={22} strokeWidth={2.5} />
              )
            ) : (
              <FiChevronRight size={22} />
            )}
          </button>

          <div className="flex items-center gap-3 flex-1">
            <div>
              <div className="font-semibold text-gray-800">{normalizeDisplayText(cat.nome)}</div>
              {cat.descricao && (
                <div className="text-sm text-gray-500">{normalizeDisplayText(cat.descricao)}</div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                cat.tipo === "receita" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
              }`}
            >
              {cat.tipo === "receita" ? "Receita" : "Despesa"}
            </span>

            {cat.tipo === "despesa" && cat.tipo_custo && (
              <span
                className={`px-2 py-1 rounded-full text-xs font-semibold ${
                  cat.tipo_custo === "fixo"
                    ? "bg-orange-100 text-orange-700"
                    : cat.tipo_custo === "variavel"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-purple-100 text-purple-700"
                }`}
              >
                {cat.tipo_custo === "fixo"
                  ? "ðŸ”’ Fixo"
                  : cat.tipo_custo === "variavel"
                    ? "ðŸ“ˆ VariÃ¡vel"
                    : "â†• Ambos"}
              </span>
            )}

            {temSubcategoria && (
              <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium flex items-center gap-1">
                <span>DRE</span>
                <span className="bg-purple-200 text-purple-900 px-1.5 rounded-full font-bold">
                  {subsDRE.length}
                </span>
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          <button
            onClick={() => handleEdit(cat)}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
            title="Editar"
          >
            <FiEdit2 size={18} />
          </button>
          <button
            onClick={() => handleDelete(cat.id)}
            className="p-2 text-red-600 hover:bg-red-50 rounded-md"
            title="Excluir"
          >
            <FiTrash2 size={18} />
          </button>
        </div>
      </div>

      {isExpanded && (
        <CategoriasFinanceirasExpandedPanel
          cat={cat}
          filhasFinanceiras={filhasFinanceiras}
          handleQuickCustoPeDRE={handleQuickCustoPeDRE}
          handleQuickTipoCusto={handleQuickTipoCusto}
          subsDRE={subsDRE}
        />
      )}
    </div>
  );
}
