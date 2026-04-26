import CompromissosDiaSection from "./CompromissosDiaSection";
import HorariosSugeridosAgendaDia from "./HorariosSugeridosAgendaDia";

export default function NovoAgendamentoAgendaDiaSection({
  abrindoAgendamentoId,
  agendaDiaModal,
  carregandoAgendaDiaModal,
  formNovo,
  horariosAgendaModal,
  onChangeCampo,
  onOpenAgendamento,
}) {
  return (
    <div className="space-y-4">
      <HorariosSugeridosAgendaDia
        agendaDiaModal={agendaDiaModal}
        formNovo={formNovo}
        horariosAgendaModal={horariosAgendaModal}
        onChangeCampo={onChangeCampo}
      />

      <CompromissosDiaSection
        abrindoAgendamentoId={abrindoAgendamentoId}
        agendaDiaModal={agendaDiaModal}
        carregandoAgendaDiaModal={carregandoAgendaDiaModal}
        onOpenAgendamento={onOpenAgendamento}
      />
    </div>
  );
}
