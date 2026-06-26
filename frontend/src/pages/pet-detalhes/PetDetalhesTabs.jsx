import { PawPrint } from "lucide-react";
import { FiActivity, FiCalendar, FiClipboard, FiHeart } from "react-icons/fi";

const TABS = [
  { id: "geral", label: "Dados Gerais", icon: FiClipboard },
  { id: "saude", label: "SaÃºde", icon: FiHeart },
  { id: "vacinas", label: "Vacinas", icon: FiActivity },
  { id: "consultas", label: "Consultas", icon: FiCalendar },
  { id: "internacoes", label: "InternaÃ§Ãµes", icon: FiActivity },
  { id: "servicos", label: "ServiÃ§os", icon: PawPrint },
];

export default function PetDetalhesTabs({ abaAtiva, onChange }) {
  return (
    <div className="mb-6 border-b border-gray-200">
      <div className="flex gap-4">
        {TABS.map((aba) => {
          const Icon = aba.icon;
          return (
            <button
              key={aba.id}
              onClick={() => onChange(aba.id)}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
                abaAtiva === aba.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              <Icon size={18} />
              {aba.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
