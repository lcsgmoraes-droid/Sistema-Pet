export default function NovoAgendamentoConflitosHorario({
  conflitoHorarioSelecionado,
  consultorioSelecionadoModal,
  diagnosticoConflitoSelecionado,
  formNovo,
  veterinarioSelecionadoModal,
}) {
  if (conflitoHorarioSelecionado) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
        {diagnosticoConflitoSelecionado.conflitosVeterinario.length > 0 && (
          <p>
            {veterinarioSelecionadoModal?.nome || "O veterinario selecionado"} ja possui paciente nesse horario.
          </p>
        )}
        {diagnosticoConflitoSelecionado.conflitosConsultorio.length > 0 && (
          <p>
            {consultorioSelecionadoModal?.nome || "O consultorio selecionado"} ja esta reservado nesse horario.
          </p>
        )}
        <p className="mt-1">Escolha outro horario, profissional ou consultorio para continuar.</p>
      </div>
    );
  }

  if (!formNovo.hora || diagnosticoConflitoSelecionado.outrosNoHorario.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
      Ja existe outro atendimento nesse horario, mas com profissional/sala diferentes.
    </div>
  );
}
