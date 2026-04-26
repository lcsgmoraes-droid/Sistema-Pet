import ConfiguracoesAlertas from "./configuracoes/ConfiguracoesAlertas";
import ConfiguracoesHeader from "./configuracoes/ConfiguracoesHeader";
import ConsultoriosSection from "./configuracoes/ConsultoriosSection";
import ParceiroInfoBox from "./configuracoes/ParceiroInfoBox";
import ParceirosSection from "./configuracoes/ParceirosSection";
import { useVetConfiguracoes } from "./configuracoes/useVetConfiguracoes";

export default function VetConfiguracoes() {
  const {
    atualizarConsultorioForm,
    atualizarParceiroForm,
    cancelarConsultorio,
    cancelarParceiro,
    carregar,
    carregando,
    consultorioForm,
    consultorios,
    erro,
    mostrarForm,
    mostrarFormConsultorio,
    parceiroForm,
    parceiros,
    removerConsultorio,
    removerParceiro,
    salvando,
    salvarNovoConsultorio,
    salvarNovoParceiro,
    setErro,
    setMostrarForm,
    setMostrarFormConsultorio,
    sucesso,
    tenantsVet,
    toggleAtivoConsultorio,
    toggleAtivoParceiro,
  } = useVetConfiguracoes();

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <ConfiguracoesHeader onReload={carregar} />

      <ConfiguracoesAlertas erro={erro} sucesso={sucesso} onLimparErro={() => setErro(null)} />

      <ParceirosSection
        form={parceiroForm}
        mostrarForm={mostrarForm}
        onCancel={cancelarParceiro}
        onChangeForm={atualizarParceiroForm}
        onRemover={removerParceiro}
        onSave={salvarNovoParceiro}
        onToggleAtivo={toggleAtivoParceiro}
        onToggleForm={() => setMostrarForm((visivel) => !visivel)}
        parceiros={parceiros}
        salvando={salvando}
        tenantsVet={tenantsVet}
      />

      <ConsultoriosSection
        consultorios={consultorios}
        form={consultorioForm}
        mostrarForm={mostrarFormConsultorio}
        onCancel={cancelarConsultorio}
        onChangeForm={atualizarConsultorioForm}
        onRemover={removerConsultorio}
        onSave={salvarNovoConsultorio}
        onToggleAtivo={toggleAtivoConsultorio}
        onToggleForm={() => setMostrarFormConsultorio((visivel) => !visivel)}
        salvando={salvando}
      />

      <ParceiroInfoBox />
    </div>
  );
}
