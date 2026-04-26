import { ChevronLeft, ChevronRight } from "lucide-react";

export default function AgendaPeriodoNav({ titulo, onAnterior, onHoje, onProximo }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3">
      <button type="button" onClick={onAnterior} className="rounded-full p-1 hover:bg-gray-100">
        <ChevronLeft size={18} className="text-gray-600" />
      </button>
      <button
        type="button"
        onClick={onHoje}
        className="flex-1 text-center text-sm font-medium capitalize text-gray-700"
      >
        {titulo}
      </button>
      <button type="button" onClick={onProximo} className="rounded-full p-1 hover:bg-gray-100">
        <ChevronRight size={18} className="text-gray-600" />
      </button>
    </div>
  );
}
