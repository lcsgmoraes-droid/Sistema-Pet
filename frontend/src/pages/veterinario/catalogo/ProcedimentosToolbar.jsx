import { Plus } from "lucide-react";

export default function ProcedimentosToolbar({ onNovo }) {
  return (
    <div className="flex justify-end">
      <button
        type="button"
        onClick={onNovo}
        className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
      >
        <Plus size={14} />
        Adicionar
      </button>
    </div>
  );
}
