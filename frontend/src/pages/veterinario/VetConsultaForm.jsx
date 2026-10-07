import { useEffect, useState } from "react";

import ConsultaActionsFooter from "./consultaForm/ConsultaActionsFooter";
import ConsultaDocumentosPanel from "./consultaForm/ConsultaDocumentosPanel";
import ConsultaEtapaAtual from "./consultaForm/ConsultaEtapaAtual";
import ConsultaFeedbackAlerts from "./consultaForm/ConsultaFeedbackAlerts";
import ConsultaFinalizadaScreen from "./consultaForm/ConsultaFinalizadaScreen";
import ConsultaFinanceiroTab from "./consultaForm/ConsultaFinanceiroTab";
import ConsultaFormModals from "./consultaForm/ConsultaFormModals";
import ConsultaHeader from "./consultaForm/ConsultaHeader";
import ConsultaReadonlyNotice from "./consultaForm/ConsultaReadonlyNotice";
import ConsultaSteps from "./consultaForm/ConsultaSteps";
import { campo } from "./consultaForm/consultaCampo";
import { ETAPAS, css } from "./consultaForm/consultaFormUtils";
import useVetConsultaFormController from "./consultaForm/useVetConsultaFormController";

export default function VetConsultaForm() {
  const consulta = useVetConsultaFormController();
  const [abaAtual, setAbaAtual] = useState("clinico");

  useEffect(() => {
    if (
      consulta.carregando ||
      abaAtual !== "clinico" ||
      window.location.hash !== "#documentos-clinicos"
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("documentos-clinicos")?.scrollIntoView();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [abaAtual, consulta.carregando]);

  function abrirDocumentos() {
    setAbaAtual("clinico");
    window.location.hash = "documentos-clinicos";
    window.requestAnimationFrame(() => {
      document.getElementById("documentos-clinicos")?.scrollIntoView();
    });
  }

  function mudarAba(aba) {
    if (window.location.hash === "#documentos-clinicos") {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    setAbaAtual(aba);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

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
        onAbrirDocumentos={() =>
          consulta.navigate(
            `/veterinario/consultas/${consulta.consultaIdAtual}#documentos-clinicos`,
          )
        }
      />
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <ConsultaHeader
        tituloConsulta={consulta.tituloConsulta}
        consultaIdAtual={consulta.consultaIdAtual}
        onAbrirDocumentos={abrirDocumentos}
        onAbrirAssistente={() => consulta.abrirFluxoConsulta("/veterinario/ia")}
        onAbrirCalculadora={consulta.abrirModalCalculadora}
      />

      {consulta.modoSomenteLeitura && <ConsultaReadonlyNotice assinatura={consulta.assinatura} />}

      <div
        role="tablist"
        aria-label="Áreas da consulta"
        className="flex flex-wrap gap-2 border-b border-gray-200 pb-3"
      >
        <button
          type="button"
          id="aba-atendimento-clinico"
          role="tab"
          aria-controls="painel-atendimento-clinico"
          aria-selected={abaAtual === "clinico"}
          onClick={() => mudarAba("clinico")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${abaAtual === "clinico" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
        >
          Atendimento clínico
        </button>
        <button
          type="button"
          id="aba-valores-consulta"
          role="tab"
          aria-controls="painel-valores-consulta"
          aria-selected={abaAtual === "financeiro"}
          onClick={() => mudarAba("financeiro")}
          disabled={!consulta.consultaIdAtual}
          title={!consulta.consultaIdAtual ? "Salve a consulta para acessar os valores" : ""}
          className={`rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${abaAtual === "financeiro" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
        >
          Orçamento e extrato (opcional)
        </button>
      </div>

      {!consulta.consultaIdAtual && (
        <p className="text-xs text-gray-500">
          Salve a consulta em rascunho para acessar orçamento e extrato.
        </p>
      )}

      <ConsultaFeedbackAlerts
        erro={consulta.erro}
        sucesso={consulta.sucesso}
        onClearErro={consulta.handleClearErro}
        onClearSucesso={consulta.handleClearSucesso}
      />

      <div
        id="painel-atendimento-clinico"
        role="tabpanel"
        aria-labelledby="aba-atendimento-clinico"
        className={abaAtual === "clinico" ? "space-y-6" : "hidden"}
      >
        <ConsultaSteps
          etapas={ETAPAS}
          etapaAtual={consulta.etapa}
          modoSomenteLeitura={consulta.modoSomenteLeitura}
          podeNavegarLivremente={Boolean(consulta.consultaIdAtual)}
          onChangeEtapa={consulta.setEtapa}
        />

        <ConsultaEtapaAtual consulta={consulta} css={css} renderCampo={campo} />

        <ConsultaDocumentosPanel
          consultaIdAtual={consulta.consultaIdAtual}
          modoSomenteLeitura={consulta.modoSomenteLeitura}
          temPrescricao={consulta.form.prescricao_itens.length > 0}
          baixandoPdf={consulta.baixandoPdf}
          onBaixarProntuario={consulta.baixarProntuarioPdf}
          onBaixarReceita={consulta.baixarUltimaReceitaPdf}
        />

        <ConsultaActionsFooter
          modoSomenteLeitura={consulta.modoSomenteLeitura}
          etapa={consulta.etapa}
          totalEtapas={ETAPAS.length}
          salvando={consulta.salvando}
          diagnosticoPreenchido={Boolean(consulta.form.diagnostico)}
          consultaIdAtual={consulta.consultaIdAtual}
          onCancel={() => consulta.navigate(-1)}
          onVoltarConsultas={() => consulta.navigate("/veterinario/consultas")}
          onVoltarEtapa={() => consulta.setEtapa((e) => e - 1)}
          onAgendarRetorno={consulta.agendarRetornoConsulta}
          onAbrirInternacao={consulta.abrirInternacaoConsulta}
          onSalvarRascunho={consulta.salvarRascunho}
          onSalvarAssinar={consulta.finalizar}
          onFinalizar={consulta.finalizar}
        />
      </div>

      {consulta.consultaIdAtual && (
        <div
          id="painel-valores-consulta"
          role="tabpanel"
          aria-labelledby="aba-valores-consulta"
          className={abaAtual === "financeiro" ? "" : "hidden"}
        >
          <ConsultaFinanceiroTab consulta={consulta} />
        </div>
      )}

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
        modalRascunhoSalvoAberto={consulta.modalRascunhoSalvoAberto}
        rascunhoSalvoMensagem={consulta.rascunhoSalvoMensagem}
        fecharModalRascunhoSalvo={consulta.fecharModalRascunhoSalvo}
        irParaTopoAposRascunho={consulta.irParaTopoAposRascunho}
        sairParaListaAposRascunho={consulta.sairParaListaAposRascunho}
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
