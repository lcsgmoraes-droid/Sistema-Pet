import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { buildConsultaPayloadFromAgendamento } from "./fluxoConsultaAgendamentoUtils";
import { vetApi } from "./vetApi";
import ConsultasAgendaHojeCard from "./consultas/ConsultasAgendaHojeCard";
import ConsultasFiltros from "./consultas/ConsultasFiltros";
import ConsultasHeader from "./consultas/ConsultasHeader";
import ConsultasPaginacao from "./consultas/ConsultasPaginacao";
import ConsultasTableCard from "./consultas/ConsultasTableCard";
import { useVetConsultas } from "./consultas/useVetConsultas";

export default function VetConsultas() {
  const navigate = useNavigate();
  const consultas = useVetConsultas();
  const [abrindoAgendamentoId, setAbrindoAgendamentoId] = useState(null);
  const [erroAcaoAgenda, setErroAcaoAgenda] = useState(null);

  function abrirConsulta(consultaId) {
    navigate(`/veterinario/consultas/${consultaId}`);
  }

  async function iniciarAgendamentoClinico(agendamento) {
    if (!agendamento?.id) return;
    setErroAcaoAgenda(null);
    setAbrindoAgendamentoId(agendamento.id);
    try {
      if (agendamento.consulta_id) {
        navigate(`/veterinario/consultas/${agendamento.consulta_id}`);
        return;
      }

      const res = await vetApi.criarConsulta(buildConsultaPayloadFromAgendamento(agendamento));
      await consultas.recarregarAgendaHoje();
      await consultas.recarregarConsultas();
      navigate(`/veterinario/consultas/${res.data.id}`);
    } catch (error) {
      setErroAcaoAgenda(error?.response?.data?.detail ?? "Nao foi possivel iniciar a consulta.");
    } finally {
      setAbrindoAgendamentoId(null);
    }
  }

  return (
    <div className="p-6 space-y-5">
      <ConsultasHeader
        onNovaConsulta={() => navigate("/veterinario/consultas/nova")}
        total={consultas.total}
      />

      <ConsultasAgendaHojeCard
        abrindoAgendamentoId={abrindoAgendamentoId}
        agendamentos={consultas.agendamentosHoje}
        carregando={consultas.carregandoAgendaHoje}
        erro={consultas.erroAgendaHoje}
        erroAcao={erroAcaoAgenda}
        onAbrirAgenda={() => navigate("/veterinario/agenda")}
        onIniciarAgendamento={iniciarAgendamentoClinico}
        onRecarregar={consultas.recarregarAgendaHoje}
      />

      <ConsultasFiltros
        busca={consultas.busca}
        filtroStatus={consultas.filtroStatus}
        onBuscaChange={consultas.setBusca}
        onStatusChange={consultas.alterarStatus}
      />

      <ConsultasTableCard
        carregando={consultas.carregando}
        consultas={consultas.consultasFiltradas}
        erro={consultas.erro}
        onAbrirConsulta={abrirConsulta}
      />

      <ConsultasPaginacao
        pagina={consultas.pagina}
        setPagina={consultas.setPagina}
        totalPaginas={consultas.totalPaginas}
      />
    </div>
  );
}
