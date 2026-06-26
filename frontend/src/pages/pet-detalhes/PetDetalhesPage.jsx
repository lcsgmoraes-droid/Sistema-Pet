import PetDetalhesConsultasTab from "./PetDetalhesConsultasTab";
import PetDetalhesErrorState from "./PetDetalhesErrorState";
import PetDetalhesGeralTab from "./PetDetalhesGeralTab";
import PetDetalhesHeader from "./PetDetalhesHeader";
import PetDetalhesInternacoesTab from "./PetDetalhesInternacoesTab";
import PetDetalhesLoadingState from "./PetDetalhesLoadingState";
import PetDetalhesSaudeTab from "./PetDetalhesSaudeTab";
import PetDetalhesServicosTab from "./PetDetalhesServicosTab";
import PetDetalhesTabs from "./PetDetalhesTabs";
import PetDetalhesVacinasTab from "./PetDetalhesVacinasTab";
import { usePetDetalhesController } from "./usePetDetalhesController";

export default function PetDetalhesPage() {
  const controller = usePetDetalhesController();

  if (controller.loading) {
    return <PetDetalhesLoadingState />;
  }

  if (controller.error || !controller.pet) {
    return <PetDetalhesErrorState error={controller.error} onBack={controller.voltarParaPets} />;
  }

  return (
    <div className="p-6">
      <PetDetalhesHeader
        onBack={controller.voltarParaPets}
        onEdit={controller.editarPet}
        onToggleStatus={controller.toggleAtivacao}
        pet={controller.pet}
      />

      <PetDetalhesTabs abaAtiva={controller.abaAtiva} onChange={controller.setAbaAtiva} />

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {controller.abaAtiva === "geral" && (
          <PetDetalhesGeralTab
            pet={controller.pet}
            ultimaAlta={controller.ultimaAlta}
            ultimaVacina={controller.ultimaVacina}
          />
        )}

        {controller.abaAtiva === "saude" && (
          <PetDetalhesSaudeTab
            carregarExames={controller.carregarExames}
            carteirinha={controller.carteirinha}
            exames={controller.exames}
            loadingExames={controller.loadingExames}
            novoExame={controller.novoExame}
            onInterpretarExameIA={controller.interpretarExameIA}
            onSalvarNovoExame={controller.salvarNovoExame}
            pet={controller.pet}
            salvandoExame={controller.salvandoExame}
            setNovoExame={controller.setNovoExame}
          />
        )}

        {controller.abaAtiva === "vacinas" && (
          <PetDetalhesVacinasTab
            carteirinha={controller.carteirinha}
            filtroVacinas={controller.filtroVacinas}
            limiteVacinas={controller.limiteVacinas}
            loadingVacinas={controller.loadingVacinas}
            onLoadMore={() => controller.setLimiteVacinas((prev) => prev + 6)}
            onRegistrarVacina={controller.registrarVacina}
            setFiltroVacinas={controller.setFiltroVacinas}
            vacinasFiltradas={controller.vacinasFiltradas}
          />
        )}

        {controller.abaAtiva === "consultas" && (
          <PetDetalhesConsultasTab
            consultasFiltradas={controller.consultasFiltradas}
            filtroConsultas={controller.filtroConsultas}
            limiteConsultas={controller.limiteConsultas}
            loadingConsultas={controller.loadingConsultas}
            onAbrirConsulta={controller.abrirConsulta}
            onLoadMore={() => controller.setLimiteConsultas((prev) => prev + 6)}
            onNovaConsulta={controller.novaConsulta}
            setFiltroConsultas={controller.setFiltroConsultas}
          />
        )}

        {controller.abaAtiva === "internacoes" && (
          <PetDetalhesInternacoesTab
            historicoInternacoes={controller.historicoInternacoes}
            loadingInternacoes={controller.loadingInternacoes}
            onOpenInternacoes={controller.abrirModuloInternacoes}
          />
        )}

        {controller.abaAtiva === "servicos" && (
          <PetDetalhesServicosTab carteirinha={controller.carteirinha} />
        )}
      </div>
    </div>
  );
}
