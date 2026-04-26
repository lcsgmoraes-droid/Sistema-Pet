import { Plus, Stethoscope } from "lucide-react";

export default function ConsultasHeader({ onNovaConsulta, total }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-xl">
          <Stethoscope size={22} className="text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Consultas / Prontuarios</h1>
          <p className="text-sm text-gray-500">{total} registro{total !== 1 ? "s" : ""}</p>
        </div>
      </div>
      <button
        onClick={onNovaConsulta}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
      >
        <Plus size={16} />
        Nova consulta
      </button>
    </div>
  );
}
