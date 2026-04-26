export default function NovoAgendamentoModalFooter({
  agendamentoEditandoId,
  bloqueioCamposAgendamento,
  conflitoHorarioSelecionado,
  formNovo,
  onClose,
  onConfirm,
  salvandoNovo,
}) {
  const confirmacaoBloqueada =
    salvandoNovo ||
    !formNovo.pet_id ||
    !formNovo.data ||
    !formNovo.hora ||
    bloqueioCamposAgendamento.veterinario ||
    bloqueioCamposAgendamento.consultorio ||
    conflitoHorarioSelecionado;

  return (
    <div className="flex gap-3 pt-5">
      <button
        type="button"
        onClick={onClose}
        className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
      >
        Cancelar
      </button>
      <button
        type="button"
        onClick={onConfirm}
        disabled={confirmacaoBloqueada}
        className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {salvandoNovo ? "Salvando..." : agendamentoEditandoId ? "Salvar alteracoes" : "Confirmar"}
      </button>
    </div>
  );
}
