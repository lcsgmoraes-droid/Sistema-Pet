export default function NovoAgendamentoMotivoEmergenciaSection({
  formNovo,
  motivoPlaceholderPorTipo,
  onChangeCampo,
  tipoSelecionado,
}) {
  return (
    <>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Motivo</label>
        <input
          type="text"
          value={formNovo.motivo}
          onChange={(event) => onChangeCampo("motivo", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder={motivoPlaceholderPorTipo[tipoSelecionado]}
        />
      </div>

      <label className="flex cursor-pointer items-center gap-2">
        <input
          type="checkbox"
          checked={formNovo.emergencia}
          onChange={(event) => onChangeCampo("emergencia", event.target.checked)}
          className="rounded"
        />
        <span className="text-sm text-gray-700">Emergencia</span>
      </label>
    </>
  );
}
