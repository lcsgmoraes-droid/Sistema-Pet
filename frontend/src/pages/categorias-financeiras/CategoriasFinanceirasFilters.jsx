const FILTERS = [
  { value: "todos", label: "Todas", activeClass: "bg-blue-600 text-white" },
  { value: "despesa", label: "Despesas", activeClass: "bg-red-600 text-white" },
  { value: "receita", label: "Receitas", activeClass: "bg-green-600 text-white" },
];

export default function CategoriasFinanceirasFilters({
  countDespesas,
  countReceitas,
  filtroTipo,
  onFiltroTipoChange,
  totalCategorias,
}) {
  const counts = {
    todos: totalCategorias,
    despesa: countDespesas,
    receita: countReceitas,
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-6">
      <div className="flex gap-4">
        {FILTERS.map((filter) => (
          <button
            key={filter.value}
            onClick={() => onFiltroTipoChange(filter.value)}
            className={`px-4 py-2 rounded-lg ${
              filtroTipo === filter.value ? filter.activeClass : "bg-gray-200 text-gray-700"
            }`}
          >
            {filter.label} ({counts[filter.value]})
          </button>
        ))}
      </div>
    </div>
  );
}
