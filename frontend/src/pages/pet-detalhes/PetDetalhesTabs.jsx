import { BedDouble, Calendar, HeartPulse, PawPrint, ShoppingBag, Syringe } from "lucide-react";
import AbasNavegacao from "../../components/v2/AbasNavegacao/AbasNavegacao";

const ABAS = [
  { id: "geral", label: "Dados Gerais", icon: PawPrint },
  { id: "saude", label: "Saúde", icon: HeartPulse },
  { id: "vacinas", label: "Vacinas", icon: Syringe },
  { id: "consultas", label: "Consultas", icon: Calendar },
  { id: "internacoes", label: "Internações", icon: BedDouble },
  { id: "servicos", label: "Serviços", icon: ShoppingBag },
];

export default function PetDetalhesTabs({ abaAtiva, onChange }) {
  return <AbasNavegacao abas={ABAS} ativa={abaAtiva} onChange={onChange} className="mb-6" />;
}
