import AssistenteIAComposer from "./assistenteIA/AssistenteIAComposer";
import AssistenteIAContextoPanel from "./assistenteIA/AssistenteIAContextoPanel";
import AssistenteIAConversaSelector from "./assistenteIA/AssistenteIAConversaSelector";
import AssistenteIAHeader from "./assistenteIA/AssistenteIAHeader";
import AssistenteIAHistorico from "./assistenteIA/AssistenteIAHistorico";
import useAssistenteIAController from "./assistenteIA/useAssistenteIAController";

export default function VetAssistenteIA() {
  const assistente = useAssistenteIAController();

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <AssistenteIAHeader memoriaAtiva={assistente.memoriaAtiva} />

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <AssistenteIAConversaSelector
          conversaId={assistente.conversaId}
          conversas={assistente.conversas}
          filtrarConversasContexto={assistente.filtrarConversasContexto}
          onAtualizarConversas={assistente.carregarConversas}
          onNovaConversa={assistente.novaConversa}
          setConversaId={assistente.setConversaId}
          setFiltrarConversasContexto={assistente.setFiltrarConversasContexto}
        />

        <AssistenteIAContextoPanel
          consultaId={assistente.consultaId}
          consultaSelecionada={assistente.consultaSelecionada}
          consultas={assistente.consultas}
          exameId={assistente.exameId}
          exameSelecionado={assistente.exameSelecionado}
          exames={assistente.exames}
          med1={assistente.med1}
          med2={assistente.med2}
          modo={assistente.modo}
          onAbrirConsulta={assistente.abrirConsulta}
          onSelecionarPet={assistente.selecionarPet}
          onSelecionarTutor={assistente.selecionarTutor}
          pesoKg={assistente.pesoKg}
          petId={assistente.petId}
          petsDoTutor={assistente.petsDoTutor}
          retornoNovoPet={assistente.retornoNovoPet}
          setConsultaId={assistente.setConsultaId}
          setExameId={assistente.setExameId}
          setMed1={assistente.setMed1}
          setMed2={assistente.setMed2}
          setModo={assistente.setModo}
          setPesoKg={assistente.setPesoKg}
          tutorSelecionado={assistente.tutorSelecionado}
        />

        <AssistenteIAComposer
          carregando={assistente.carregando}
          erro={assistente.erro}
          mensagem={assistente.mensagem}
          onEnviar={assistente.enviar}
          onPerguntaRapida={assistente.perguntaRapida}
          setMensagem={assistente.setMensagem}
        />
      </div>

      <AssistenteIAHistorico
        carregandoHistorico={assistente.carregandoHistorico}
        historico={assistente.historico}
        onEnviarFeedback={assistente.enviarFeedback}
        salvandoFeedbackId={assistente.salvandoFeedbackId}
      />
    </div>
  );
}
