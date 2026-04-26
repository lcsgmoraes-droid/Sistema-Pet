import { BellRing, LayoutGrid, List, Map as MapIcon } from "lucide-react";

const ABAS_CENTRO = [
  { id: "widget", label: "Widget (resumo)", icon: LayoutGrid },
  { id: "mapa", label: "Mapa da internação", icon: MapIcon },
  { id: "lista", label: "Lista de internados", icon: List },
  { id: "agenda", label: "Agenda de procedimentos", icon: BellRing },
];

export default function CentroInternacaoTabs({ centroAba, onChangeCentroAba }) {
  return (
    <div className="flex flex-wrap gap-2 bg-white border border-gray-200 rounded-xl p-2">
      {ABAS_CENTRO.map((item) => {
        const Icon = item.icon;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChangeCentroAba(item.id)}
            className={`flex items-center gap-2 px-3 py-2 text-xs rounded-lg border transition-colors ${
              centroAba === item.id
                ? "bg-purple-600 text-white border-purple-600"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            <Icon size={13} />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
