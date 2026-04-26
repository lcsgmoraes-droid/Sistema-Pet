import { Calendar, Plus } from "lucide-react";

const MODOS = [
  { id: "dia", label: "Dia" },
  { id: "semana", label: "Semana" },
  { id: "mes", label: "Mês" },
];

export default function AgendaHeader({ modo, onChangeModo, onAbrirNovo }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-blue-100 p-2">
          <Calendar size={22} className="text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-800">Agenda</h1>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex overflow-hidden rounded-lg border border-gray-200 text-sm">
          {MODOS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onChangeModo(item.id)}
              className={`px-3 py-1.5 ${modo === item.id ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onAbrirNovo}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <Plus size={15} />
          Agendar
        </button>
      </div>
    </div>
  );
}
