import { FiPlus } from "react-icons/fi";

export default function CategoriasFinanceirasHeader({
  countDespesas,
  countReceitas,
  onNewCategory,
}) {
  return (
    <div className="flex justify-between items-center mb-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Categorias Financeiras</h2>
        <p className="text-gray-600 mt-1">
          Organize suas receitas e despesas |
          <span className="text-red-600 ml-2">{countDespesas} despesas</span>
          <span className="text-green-600 ml-2">{countReceitas} receitas</span>
        </p>
      </div>
      <button
        onClick={onNewCategory}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
      >
        <FiPlus /> Nova Categoria
      </button>
    </div>
  );
}
