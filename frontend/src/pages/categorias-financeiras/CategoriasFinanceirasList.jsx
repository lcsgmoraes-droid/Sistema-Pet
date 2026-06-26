import CategoriasFinanceirasRow from "./CategoriasFinanceirasRow";
import { getFilhasFinanceiras } from "./categoriasFinanceirasUtils";

export default function CategoriasFinanceirasList({
  categorias,
  categoriasFiltradas,
  categoriaExpandida,
  getSubcategoriasDREDaCategoria,
  handleDelete,
  handleEdit,
  handleQuickCustoPeDRE,
  handleQuickTipoCusto,
  loading,
  toggleExpansao,
}) {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {loading ? (
        <div className="px-6 py-8 text-center text-gray-500">Carregando...</div>
      ) : categoriasFiltradas.length === 0 ? (
        <div className="px-6 py-8 text-center text-gray-500">Nenhuma categoria encontrada</div>
      ) : (
        <div className="divide-y divide-gray-200">
          {categoriasFiltradas.map((cat) => (
            <CategoriasFinanceirasRow
              key={cat.id}
              cat={cat}
              filhasFinanceiras={getFilhasFinanceiras(categorias, cat.id)}
              handleDelete={handleDelete}
              handleEdit={handleEdit}
              handleQuickCustoPeDRE={handleQuickCustoPeDRE}
              handleQuickTipoCusto={handleQuickTipoCusto}
              isExpanded={categoriaExpandida.has(cat.id)}
              subsDRE={getSubcategoriasDREDaCategoria(cat)}
              toggleExpansao={toggleExpansao}
            />
          ))}
        </div>
      )}
    </div>
  );
}
