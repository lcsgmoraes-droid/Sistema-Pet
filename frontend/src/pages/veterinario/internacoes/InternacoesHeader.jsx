import { BedDouble, Plus } from "lucide-react";

export default function InternacoesHeader({ onNovaInternacao }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-purple-100 rounded-xl">
          <BedDouble size={22} className="text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-800">Internações</h1>
      </div>
      <button
        type="button"
        onClick={onNovaInternacao}
        className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
      >
        <Plus size={15} />
        Nova internação
      </button>
    </div>
  );
}
