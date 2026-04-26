import AgendaSelectField from "./AgendaSelectField";

export default function NovoAgendamentoEquipeSection({
  consultorios,
  formNovo,
  onChangeCampo,
  onConfiguracoesVet,
  veterinarios,
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <AgendaSelectField
        alerta={
          veterinarios.length === 0
            ? "Cadastre um veterinario em Pessoas para vincular o atendimento corretamente."
            : ""
        }
        disabled={veterinarios.length === 0}
        label="Veterinario*"
        onChange={(valor) => onChangeCampo("veterinario_id", valor)}
        options={veterinarios}
        placeholder={veterinarios.length > 0 ? "Selecione o veterinario..." : "Nenhum veterinario cadastrado"}
        value={formNovo.veterinario_id}
      />

      <div>
        <AgendaSelectField
          disabled={consultorios.length === 0}
          label="Consultorio*"
          onChange={(valor) => onChangeCampo("consultorio_id", valor)}
          options={consultorios}
          placeholder={consultorios.length > 0 ? "Selecione o consultorio..." : "Nenhum consultorio cadastrado"}
          value={formNovo.consultorio_id}
        />
        {consultorios.length === 0 && (
          <div className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <p className="text-xs text-amber-700">
              Cadastre os consultorios para a agenda alertar conflito de sala.
            </p>
            <button
              type="button"
              onClick={onConfiguracoesVet}
              className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100"
            >
              Configurar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
