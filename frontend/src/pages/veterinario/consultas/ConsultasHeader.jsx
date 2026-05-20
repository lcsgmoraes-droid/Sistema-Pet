import { Plus, Stethoscope } from "lucide-react";

export default function ConsultasHeader({ onNovaConsulta, total }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <div className="shrink-0 rounded-xl bg-blue-100 p-2">
          <Stethoscope size={22} className="text-blue-600" />
        </div>
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-gray-800 sm:text-2xl">
            Consultas / Prontuarios
          </h1>
          <p className="text-sm text-gray-500">{total} registro{total !== 1 ? "s" : ""}</p>
        </div>
      </div>
      <button
        onClick={onNovaConsulta}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 sm:w-auto"
      >
        <Plus size={16} />
        Nova consulta
      </button>
    </div>
  );
}
