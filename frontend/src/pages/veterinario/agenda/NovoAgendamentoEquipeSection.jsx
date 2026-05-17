import { Plus } from "lucide-react";

import ActionButton from "../../../components/ui/ActionButton";
import AgendaSelectField from "./AgendaSelectField";

export default function NovoAgendamentoEquipeSection({
  consultorios,
  formNovo,
  onChangeCampo,
  onNovoConsultorio,
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
          labelAccessory={
            <ActionButton
              icon={Plus}
              intent="create"
              onClick={onNovoConsultorio}
              size="xs"
              tone="soft"
            >
              Novo
            </ActionButton>
          }
          label="Consultorio*"
          onChange={(valor) => onChangeCampo("consultorio_id", valor)}
          options={consultorios}
          placeholder={consultorios.length > 0 ? "Selecione o consultorio..." : "Nenhum consultorio cadastrado"}
          value={formNovo.consultorio_id}
        />
        {consultorios.length === 0 && (
          <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <p className="text-xs text-amber-700">
              Cadastre um consultorio aqui mesmo para a agenda alertar conflito de sala.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
