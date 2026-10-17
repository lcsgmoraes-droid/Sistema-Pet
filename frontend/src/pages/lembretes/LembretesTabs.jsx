import { BarChart3, CalendarClock, Gift, PackageCheck, Repeat, Users } from "lucide-react";
import AbasNavegacao from "../../components/v2/AbasNavegacao/AbasNavegacao";

// Ordem: primeiro as abas só de consulta, à direita as que alteram dados do sistema.
export function montarAbas(controller) {
  return [
    { id: "relatorios", label: "Relatórios", icon: BarChart3 },
    controller.blingAtivo && {
      id: "bling",
      label: "Auto cadastro Bling",
      icon: PackageCheck,
      contador: controller.autocadastrosBling.total,
    },
    { id: "relacionamento", label: "Relacionamento", icon: Users },
    {
      id: "aniversarios",
      label: "Aniversários",
      icon: Gift,
      contador: controller.aniversariantes.length,
    },
    { id: "recompras", label: "Recompras", icon: Repeat, contador: controller.lembretes.length },
    {
      id: "validade",
      label: "Validade",
      icon: CalendarClock,
      contador: controller.validadePendencias.length,
    },
  ].filter(Boolean);
}

export default function LembretesTabs({ controller }) {
  return (
    <AbasNavegacao
      abas={montarAbas(controller)}
      ariaLabel="Áreas da central de lembretes"
      ativa={controller.abaAtiva}
      onChange={controller.setAbaAtiva}
    />
  );
}
