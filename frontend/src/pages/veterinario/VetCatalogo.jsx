import { useState } from "react";
import { BookOpen, ClipboardList, Pill, Syringe } from "lucide-react";
import CatMedicamentos from "./catalogo/CatMedicamentos";
import CatProcedimentos from "./catalogo/CatProcedimentos";
import CatProtocolosVacinas from "./catalogo/CatProtocolosVacinas";

const ABAS = [
  { id: "medicamentos", label: "Medicamentos", icon: Pill },
  { id: "procedimentos", label: "Procedimentos", icon: ClipboardList },
  { id: "vacinas", label: "Protocolos de vacinas", icon: Syringe },
];

export default function VetCatalogo() {
  const [aba, setAba] = useState("medicamentos");

  return (
    <div className="space-y-5 p-6">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-teal-100 p-2">
          <BookOpen size={22} className="text-teal-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Catalogos</h1>
          <p className="text-sm text-gray-500">Medicamentos, procedimentos e protocolos de vacinas.</p>
        </div>
      </div>

      <div className="flex border-b border-gray-200">
        {ABAS.map((abaAtual) => {
          const Icon = abaAtual.icon;
          return (
            <button
              key={abaAtual.id}
              type="button"
              onClick={() => setAba(abaAtual.id)}
              className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                aba === abaAtual.id
                  ? "border-teal-500 text-teal-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <Icon size={14} />
              {abaAtual.label}
            </button>
          );
        })}
      </div>

      {aba === "medicamentos" && <CatMedicamentos />}
      {aba === "procedimentos" && <CatProcedimentos />}
      {aba === "vacinas" && <CatProtocolosVacinas />}
    </div>
  );
}
