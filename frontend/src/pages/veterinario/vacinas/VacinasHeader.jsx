import { Plus, Syringe } from "lucide-react";

export default function VacinasHeader({ onRegistrarVacina }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-orange-100 rounded-xl">
          <Syringe size={22} className="text-orange-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-800">Vacinas</h1>
      </div>
      <button
        type="button"
        onClick={onRegistrarVacina}
        className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
      >
        <Plus size={15} />
        Registrar vacina
      </button>
    </div>
  );
}
