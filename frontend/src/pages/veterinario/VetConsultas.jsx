import { useNavigate } from "react-router-dom";

import ConsultasFiltros from "./consultas/ConsultasFiltros";
import ConsultasHeader from "./consultas/ConsultasHeader";
import ConsultasPaginacao from "./consultas/ConsultasPaginacao";
import ConsultasTableCard from "./consultas/ConsultasTableCard";
import { useVetConsultas } from "./consultas/useVetConsultas";

export default function VetConsultas() {
  const navigate = useNavigate();
  const consultas = useVetConsultas();

  function abrirConsulta(consultaId) {
    navigate(`/veterinario/consultas/${consultaId}`);
  }

  return (
    <div className="p-6 space-y-5">
      <ConsultasHeader
        onNovaConsulta={() => navigate("/veterinario/consultas/nova")}
        total={consultas.total}
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
