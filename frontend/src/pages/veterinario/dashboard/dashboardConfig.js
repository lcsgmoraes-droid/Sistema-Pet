import { AlertCircle, BedDouble, Calendar, Stethoscope, Syringe, TrendingUp } from "lucide-react";

export const STATUS_AGENDAMENTO_COLOR = {
  aguardando: "bg-yellow-100 text-yellow-800",
  em_atendimento: "bg-blue-100 text-blue-800",
  finalizado: "bg-green-100 text-green-800",
  cancelado: "bg-gray-100 text-gray-600",
};

export const STATUS_AGENDAMENTO_LABEL = {
  aguardando: "Aguardando",
  em_atendimento: "Em atendimento",
  finalizado: "Finalizado",
  cancelado: "Cancelado",
};

export const ATALHOS_DASHBOARD_VET = [
  { label: "Agenda", path: "/veterinario/agenda", icon: Calendar },
  { label: "Vacinas a vencer", path: "/veterinario/vacinas", icon: Syringe },
  { label: "Internações", path: "/veterinario/internacoes", icon: BedDouble },
  { label: "Catálogos", path: "/veterinario/catalogo", icon: TrendingUp },
];

export function montarCardsDashboard(dados) {
  return [
    {
      label: "Consultas hoje",
      valor: dados?.consultas_hoje ?? 0,
      icon: Calendar,
      cor: "from-blue-500 to-blue-600",
    },
    {
      label: "Em atendimento",
      valor: dados?.em_atendimento ?? 0,
      icon: Stethoscope,
      cor: "from-green-500 to-green-600",
    },
    {
      label: "Internados",
      valor: dados?.internados ?? 0,
      icon: BedDouble,
      cor: "from-purple-500 to-purple-600",
    },
    {
      label: "Vacinas vencendo (30d)",
      valor: dados?.vacinas_vencendo_30d ?? 0,
      icon: Syringe,
      cor: "from-orange-500 to-orange-600",
    },
    {
      label: "Consultas este mês",
      valor: dados?.consultas_mes ?? 0,
      icon: TrendingUp,
      cor: "from-teal-500 to-teal-600",
    },
    {
      label: "Retornos pendentes",
      valor: dados?.retornos_pendentes ?? 0,
      icon: AlertCircle,
      cor: "from-rose-500 to-rose-600",
    },
    {
      label: "Taxa de retorno (30d)",
      valor: `${dados?.taxa_retorno_30d ?? 0}%`,
      icon: TrendingUp,
      cor: "from-indigo-500 to-indigo-600",
    },
    {
      label: "Tempo médio de atendimento",
      valor: `${dados?.tempo_medio_atendimento_min ?? 0} min`,
      icon: Stethoscope,
      cor: "from-cyan-500 to-cyan-600",
    },
  ];
}
