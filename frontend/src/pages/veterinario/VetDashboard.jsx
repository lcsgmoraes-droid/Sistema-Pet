import { useNavigate } from "react-router-dom";

import AgendaCelularCard from "./dashboard/AgendaCelularCard";
import AgendaHojeCard from "./dashboard/AgendaHojeCard";
import AtalhosRapidos from "./dashboard/AtalhosRapidos";
import { DashboardErro, DashboardLoading } from "./dashboard/DashboardEstados";
import DashboardHeader from "./dashboard/DashboardHeader";
import DashboardKpiGrid from "./dashboard/DashboardKpiGrid";
import FinanceiroProcedimentosCard from "./dashboard/FinanceiroProcedimentosCard";
import TopListCard from "./dashboard/TopListCard";
import { useVetDashboard } from "./dashboard/useVetDashboard";

export default function VetDashboard() {
  const navigate = useNavigate();
  const {
    agendamentos,
    baixarCalendarioAgenda,
    calendarioMeta,
    cards,
    carregando,
    copiarLinkCalendario,
    dados,
    erro,
    exportando,
    exportarCsvRelatorio,
    mensagemCalendario,
    relatorio,
  } = useVetDashboard();

  if (carregando) {
    return <DashboardLoading />;
  }

  if (erro) {
    return <DashboardErro erro={erro} />;
  }

  return (
    <div className="p-6 space-y-6">
      <DashboardHeader
        exportando={exportando}
        onExportar={exportarCsvRelatorio}
        onNovaConsulta={() => navigate("/veterinario/consultas/nova")}
      />

      <DashboardKpiGrid cards={cards} />

      <AgendaHojeCard
        agendamentos={agendamentos}
        onAbrirAgenda={() => navigate("/veterinario/agenda")}
        onAbrirAgendamento={(agendamento) => {
          if (agendamento.consulta_id) {
            navigate(`/veterinario/consultas/${agendamento.consulta_id}`);
            return;
          }
          navigate("/veterinario/agenda");
        }}
      />

      <AgendaCelularCard
        calendarioMeta={calendarioMeta}
        mensagemCalendario={mensagemCalendario}
        onBaixarCalendario={baixarCalendarioAgenda}
        onCopiarLink={copiarLinkCalendario}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <FinanceiroProcedimentosCard dados={dados} />
        <TopListCard
          title="Top diagnósticos (30d)"
          itens={relatorio?.top_diagnosticos ?? []}
          vazio="Sem diagnósticos registrados no período."
        />
        <TopListCard
          title="Top procedimentos (30d)"
          itens={relatorio?.top_procedimentos ?? []}
          vazio="Sem procedimentos registrados no período."
        />
        <TopListCard
          title="Top medicamentos (30d)"
          itens={relatorio?.top_medicamentos ?? []}
          vazio="Sem medicamentos prescritos no período."
        />
      </div>

      <AtalhosRapidos onNavigate={navigate} />
    </div>
  );
}
