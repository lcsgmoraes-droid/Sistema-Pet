import DiagnosticoTratamentoSection from "./DiagnosticoTratamentoSection";
import ExameClinicoSection from "./ExameClinicoSection";
import TriagemInicialSection from "./TriagemInicialSection";

export default function ConsultaEtapaAtual({ consulta, css, renderCampo }) {
  if (consulta.etapa === 0) {
    return <TriagemStep consulta={consulta} css={css} renderCampo={renderCampo} />;
  }

  if (consulta.etapa === 1) {
    return <ExameClinicoStep consulta={consulta} css={css} renderCampo={renderCampo} />;
  }

  if (consulta.etapa === 2) {
    return <DiagnosticoStep consulta={consulta} />;
  }

  return null;
}

function TriagemStep({ consulta, css, renderCampo }) {
  return (
    <TriagemInicialSection
      modoSomenteLeitura={consulta.modoSomenteLeitura}
      isEdicao={consulta.isEdicao}
      form={consulta.form}
      setCampo={consulta.setCampo}
      css={css}
      renderCampo={renderCampo}
      buscaTutor={consulta.buscaTutor}
      setBuscaTutor={consulta.setBuscaTutor}
      tutorSelecionado={consulta.tutorSelecionado}
      setTutorSelecionado={consulta.setTutorSelecionado}
      tutoresSugeridos={consulta.tutoresSugeridos}
      selecionarTutor={consulta.selecionarTutor}
      limparTutor={consulta.limparTutor}
      veterinarios={consulta.veterinarios}
      listaPetsExpandida={consulta.listaPetsExpandida}
      setListaPetsExpandida={consulta.setListaPetsExpandida}
      petSelecionadoLabel={consulta.petSelecionadoLabel}
      petsDoTutor={consulta.petsDoTutor}
      abrirModalNovoPet={consulta.abrirModalNovoPet}
    />
  );
}

function ExameClinicoStep({ consulta, css, renderCampo }) {
  return (
    <ExameClinicoSection
      modoSomenteLeitura={consulta.modoSomenteLeitura}
      form={consulta.form}
      setCampo={consulta.setCampo}
      css={css}
      renderCampo={renderCampo}
      consultaIdAtual={consulta.consultaIdAtual}
      refreshExamesToken={consulta.refreshExamesToken}
      onNovoExame={consulta.abrirModalNovoExame}
      abrirFluxoConsulta={consulta.abrirFluxoConsulta}
    />
  );
}

function DiagnosticoStep({ consulta }) {
  return (
    <DiagnosticoTratamentoSection
      modoSomenteLeitura={consulta.modoSomenteLeitura}
      form={consulta.form}
      setCampo={consulta.setCampo}
      medicamentosCatalogo={consulta.medicamentosCatalogo}
      procedimentosCatalogo={consulta.procedimentosCatalogo}
      consultaIdAtual={consulta.consultaIdAtual}
      timelineConsulta={consulta.timelineConsulta}
      carregandoTimeline={consulta.carregandoTimeline}
      adicionarItem={consulta.adicionarItem}
      removerItem={consulta.removerItem}
      setItem={consulta.setItem}
      selecionarMedicamentoNoItem={consulta.selecionarMedicamentoNoItem}
      recalcularDoseItem={consulta.recalcularDoseItem}
      adicionarProcedimento={consulta.adicionarProcedimento}
      removerProcedimento={consulta.removerProcedimento}
      setProcedimentoItem={consulta.setProcedimentoItem}
      selecionarProcedimentoCatalogo={consulta.selecionarProcedimentoCatalogo}
      abrirModalInsumoRapido={consulta.abrirModalInsumoRapido}
      abrirFluxoConsulta={consulta.abrirFluxoConsulta}
      carregarTimelineConsulta={consulta.carregarTimelineConsulta}
      onOpenTimelineLink={consulta.abrirTimelineLink}
    />
  );
}
