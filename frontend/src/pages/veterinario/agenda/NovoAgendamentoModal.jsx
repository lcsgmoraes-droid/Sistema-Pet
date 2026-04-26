import { AlertCircle } from "lucide-react";

import NovoAgendamentoAgendaDiaSection from "./NovoAgendamentoAgendaDiaSection";
import NovoAgendamentoFormSection from "./NovoAgendamentoFormSection";
import NovoAgendamentoModalFooter from "./NovoAgendamentoModalFooter";
import NovoAgendamentoModalHeader from "./NovoAgendamentoModalHeader";

export default function NovoAgendamentoModal({
  isOpen,
  agendamentoEditandoId,
  erroNovo,
  tutorSelecionado,
  formNovo,
  setFormNovo,
  petsDoTutor,
  carregandoPetsTutor,
  retornoNovoPet,
  veterinarios,
  consultorios,
  dicaTipoSelecionado,
  tipoSelecionado,
  motivoPlaceholderPorTipo,
  conflitoHorarioSelecionado,
  diagnosticoConflitoSelecionado,
  veterinarioSelecionadoModal,
  consultorioSelecionadoModal,
  agendaDiaModal,
  horariosAgendaModal,
  carregandoAgendaDiaModal,
  abrindoAgendamentoId,
  salvandoNovo,
  bloqueioCamposAgendamento,
  onClose,
  onTutorSelect,
  onHideForNovoPet,
  onConfiguracoesVet,
  onOpenAgendamento,
  onConfirm,
}) {
  if (!isOpen) return null;

  function atualizarCampo(campo, valor) {
    setFormNovo((prev) => ({ ...prev, [campo]: valor }));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl rounded-2xl bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <NovoAgendamentoModalHeader
          agendamentoEditandoId={agendamentoEditandoId}
          onClose={onClose}
        />

        {erroNovo && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            <AlertCircle size={16} />
            <span>{erroNovo}</span>
          </div>
        )}

        <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
          <NovoAgendamentoFormSection
            carregandoPetsTutor={carregandoPetsTutor}
            conflitoHorarioSelecionado={conflitoHorarioSelecionado}
            consultorioSelecionadoModal={consultorioSelecionadoModal}
            consultorios={consultorios}
            diagnosticoConflitoSelecionado={diagnosticoConflitoSelecionado}
            dicaTipoSelecionado={dicaTipoSelecionado}
            formNovo={formNovo}
            motivoPlaceholderPorTipo={motivoPlaceholderPorTipo}
            onChangeCampo={atualizarCampo}
            onConfiguracoesVet={onConfiguracoesVet}
            onHideForNovoPet={onHideForNovoPet}
            onTutorSelect={onTutorSelect}
            petsDoTutor={petsDoTutor}
            retornoNovoPet={retornoNovoPet}
            tipoSelecionado={tipoSelecionado}
            tutorSelecionado={tutorSelecionado}
            veterinarioSelecionadoModal={veterinarioSelecionadoModal}
            veterinarios={veterinarios}
          />

          <NovoAgendamentoAgendaDiaSection
            abrindoAgendamentoId={abrindoAgendamentoId}
            agendaDiaModal={agendaDiaModal}
            carregandoAgendaDiaModal={carregandoAgendaDiaModal}
            formNovo={formNovo}
            horariosAgendaModal={horariosAgendaModal}
            onChangeCampo={atualizarCampo}
            onOpenAgendamento={onOpenAgendamento}
          />
        </div>

        <NovoAgendamentoModalFooter
          agendamentoEditandoId={agendamentoEditandoId}
          bloqueioCamposAgendamento={bloqueioCamposAgendamento}
          conflitoHorarioSelecionado={conflitoHorarioSelecionado}
          formNovo={formNovo}
          onClose={onClose}
          onConfirm={onConfirm}
          salvandoNovo={salvandoNovo}
        />
      </div>
    </div>
  );
}
