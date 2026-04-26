import ConsultaActionsFooter from "./consultaForm/ConsultaActionsFooter";
import ConsultaEtapaAtual from "./consultaForm/ConsultaEtapaAtual";
import ConsultaFeedbackAlerts from "./consultaForm/ConsultaFeedbackAlerts";
import ConsultaFinalizadaScreen from "./consultaForm/ConsultaFinalizadaScreen";
import ConsultaFormModals from "./consultaForm/ConsultaFormModals";
import ConsultaHeader from "./consultaForm/ConsultaHeader";
import ConsultaReadonlyNotice from "./consultaForm/ConsultaReadonlyNotice";
import ConsultaSteps from "./consultaForm/ConsultaSteps";
import { campo } from "./consultaForm/consultaCampo";
import { ETAPAS, css } from "./consultaForm/consultaFormUtils";
import useVetConsultaFormController from "./consultaForm/useVetConsultaFormController";

export default function VetConsultaForm() {
  const consulta = useVetConsultaFormController();

  if (consulta.carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (consulta.finalizado && !consulta.isEdicao) {
    return (
      <ConsultaFinalizadaScreen
        onVerConsultas={() => consulta.navigate("/veterinario/consultas")}
        onNovaConsulta={() => consulta.navigate("/veterinario/consultas/nova")}
      />
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <ConsultaHeader
        tituloConsulta={consulta.tituloConsulta}
        consultaIdAtual={consulta.consultaIdAtual}
        onAbrirAssistente={() => consulta.abrirFluxoConsulta("/veterinario/ia")}
        onAbrirCalculadora={consulta.abrirModalCalculadora}
      />

      {consulta.modoSomenteLeitura && (
        <ConsultaReadonlyNotice
          assinatura={consulta.assinatura}
          baixandoPdf={consulta.baixandoPdf}
          onBaixarProntuario={consulta.baixarProntuarioPdf}
          onBaixarReceita={consulta.baixarUltimaReceitaPdf}
        />
      )}

      <ConsultaSteps
        etapas={ETAPAS}
        etapaAtual={consulta.etapa}
        modoSomenteLeitura={consulta.modoSomenteLeitura}
        onChangeEtapa={consulta.setEtapa}
      />

      <ConsultaFeedbackAlerts
        erro={consulta.erro}
        sucesso={consulta.sucesso}
        onClearErro={consulta.handleClearErro}
        onClearSucesso={consulta.handleClearSucesso}
      />

      <ConsultaEtapaAtual consulta={consulta} css={css} renderCampo={campo} />

      <ConsultaActionsFooter
        modoSomenteLeitura={consulta.modoSomenteLeitura}
        etapa={consulta.etapa}
        totalEtapas={ETAPAS.length}
        salvando={consulta.salvando}
        diagnosticoPreenchido={Boolean(consulta.form.diagnostico)}
        onCancel={() => consulta.navigate(-1)}
        onVoltarConsultas={() => consulta.navigate("/veterinario/consultas")}
        onVoltarEtapa={() => consulta.setEtapa((e) => e - 1)}
        onSalvarRascunho={consulta.salvarRascunho}
        onFinalizar={consulta.finalizar}
      />

      <ConsultaFormModals
        css={css}
        modalInsumoAberto={consulta.modalInsumoAberto}
        setModalInsumoAberto={consulta.setModalInsumoAberto}
        consultaIdAtual={consulta.consultaIdAtual}
        petSelecionadoLabel={consulta.petSelecionadoLabel}
        insumoRapidoSelecionado={consulta.insumoRapidoSelecionado}
        setInsumoRapidoSelecionado={consulta.setInsumoRapidoSelecionado}
        insumoRapidoForm={consulta.insumoRapidoForm}
        setInsumoRapidoForm={consulta.setInsumoRapidoForm}
        salvarInsumoRapidoConsulta={consulta.salvarInsumoRapidoConsulta}
        salvandoInsumoRapido={consulta.salvandoInsumoRapido}
        modalNovoPetAberto={consulta.modalNovoPetAberto}
        setModalNovoPetAberto={consulta.setModalNovoPetAberto}
        tutorSelecionado={consulta.tutorSelecionado}
        sugestoesEspecies={consulta.sugestoesEspecies}
        handleNovoPetCriado={consulta.handleNovoPetCriado}
        modalCalculadoraAberto={consulta.modalCalculadoraAberto}
        setModalCalculadoraAberto={consulta.setModalCalculadoraAberto}
        calculadoraForm={consulta.calculadoraForm}
        setCalculadoraForm={consulta.setCalculadoraForm}
        medicamentosCatalogo={consulta.medicamentosCatalogo}
        medicamentoCalculadoraSelecionado={consulta.medicamentoCalculadoraSelecionado}
        calculadoraResultado={consulta.calculadoraResultado}
        modalNovoExameAberto={consulta.modalNovoExameAberto}
        setModalNovoExameAberto={consulta.setModalNovoExameAberto}
        petId={consulta.form.pet_id}
        novoExameForm={consulta.novoExameForm}
        setNovoExameForm={consulta.setNovoExameForm}
        setNovoExameArquivo={consulta.setNovoExameArquivo}
        salvarNovoExameRapido={consulta.salvarNovoExameRapido}
        salvandoNovoExame={consulta.salvandoNovoExame}
      />
    </div>
  );
}
