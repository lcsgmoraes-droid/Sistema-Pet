import AgendaCalendarioCard from "./agenda/AgendaCalendarioCard";
import AgendaConteudo from "./agenda/AgendaConteudo";
import AgendaErro from "./agenda/AgendaErro";
import AgendaHeader from "./agenda/AgendaHeader";
import AgendaPeriodoNav from "./agenda/AgendaPeriodoNav";
import GerenciarAgendamentoModal from "./agenda/GerenciarAgendamentoModal";
import NovoAgendamentoModal from "./agenda/NovoAgendamentoModal";
import { useVetAgenda } from "./agenda/useVetAgenda";

export default function VetAgenda() {
  const agenda = useVetAgenda();

  return (
    <div className="p-6 space-y-5">
      <AgendaHeader
        modo={agenda.modo}
        onChangeModo={agenda.setModo}
        onAbrirNovo={() => agenda.abrirModalNovo(agenda.dataRef)}
      />

      <AgendaPeriodoNav
        titulo={agenda.tituloAgenda}
        onAnterior={() => agenda.nav(-1)}
        onHoje={() => agenda.setDataRef(new Date())}
        onProximo={() => agenda.nav(1)}
      />

      <AgendaErro erro={agenda.erro} />

      <AgendaCalendarioCard
        calendarioMeta={agenda.calendarioMeta}
        carregandoCalendario={agenda.carregandoCalendario}
        mensagemCalendario={agenda.mensagemCalendario}
        onBaixarCalendario={agenda.baixarCalendarioAgenda}
        onCopiarLink={agenda.copiarLinkCalendario}
      />

      <AgendaConteudo
        carregando={agenda.carregando}
        modo={agenda.modo}
        diasMes={agenda.diasMes}
        diasVisiveis={agenda.diasVisiveis}
        dataRef={agenda.dataRef}
        agsDia={agenda.agsDia}
        abrindoAgendamentoId={agenda.abrindoAgendamentoId}
        onAbrirNovo={agenda.abrirModalNovo}
        onGerenciarAgendamento={agenda.abrirGerenciarAgendamento}
      />

      <GerenciarAgendamentoModal
        agendamento={agenda.agendamentoSelecionado}
        tipoAgendamento={agenda.tipoAgendamentoSelecionado}
        mensagem={agenda.mensagemAgendamentoSelecionado}
        podeVoltarStatus={agenda.podeVoltarStatus}
        labelVoltarStatus={agenda.labelVoltarStatus}
        podeExcluir={agenda.podeExcluirAgendamento}
        labelAbrir={agenda.labelAbrirAgendamentoSelecionado}
        abrindoAgendamentoId={agenda.abrindoAgendamentoId}
        processandoAgendamentoId={agenda.processandoAgendamentoId}
        onClose={agenda.fecharGerenciarAgendamento}
        onEdit={agenda.editarAgendamentoSelecionado}
        onVoltarStatus={agenda.voltarStatusAgendamento}
        onExcluir={agenda.excluirAgendamentoSelecionado}
        onIniciar={agenda.iniciarAgendamentoSelecionado}
      />

      <NovoAgendamentoModal
        isOpen={agenda.novoAberto}
        agendamentoEditandoId={agenda.agendamentoEditandoId}
        erroNovo={agenda.erroNovo}
        tutorSelecionado={agenda.tutorSelecionado}
        formNovo={agenda.formNovo}
        setFormNovo={agenda.setFormNovo}
        petsDoTutor={agenda.petsDoTutor}
        carregandoPetsTutor={agenda.carregandoPetsTutor}
        retornoNovoPet={agenda.retornoNovoPet}
        veterinarios={agenda.veterinarios}
        consultorios={agenda.consultorios}
        dicaTipoSelecionado={agenda.dicaTipoSelecionado}
        tipoSelecionado={agenda.tipoSelecionado}
        motivoPlaceholderPorTipo={agenda.motivoPlaceholderPorTipo}
        conflitoHorarioSelecionado={agenda.conflitoHorarioSelecionado}
        diagnosticoConflitoSelecionado={agenda.diagnosticoConflitoSelecionado}
        veterinarioSelecionadoModal={agenda.veterinarioSelecionadoModal}
        consultorioSelecionadoModal={agenda.consultorioSelecionadoModal}
        agendaDiaModal={agenda.agendaDiaModal}
        horariosAgendaModal={agenda.horariosAgendaModal}
        carregandoAgendaDiaModal={agenda.carregandoAgendaDiaModal}
        abrindoAgendamentoId={agenda.abrindoAgendamentoId}
        salvandoNovo={agenda.salvandoNovo}
        bloqueioCamposAgendamento={agenda.bloqueioCamposAgendamento}
        onClose={agenda.fecharModalNovo}
        onTutorSelect={agenda.selecionarTutorNovoAgendamento}
        onHideForNovoPet={agenda.ocultarNovoParaNovoPet}
        onConfiguracoesVet={agenda.abrirConfiguracoesVet}
        onOpenAgendamento={agenda.abrirGerenciarAgendamento}
        onConfirm={agenda.criarAgendamento}
      />
    </div>
  );
}
