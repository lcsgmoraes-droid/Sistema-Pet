import AgendaInputField from "./AgendaInputField";
import { TIPO_OPTIONS } from "./agendaUtils";

export default function NovoAgendamentoTipoDataSection({
  dicaTipoSelecionado,
  formNovo,
  onChangeCampo,
}) {
  return (
    <>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Tipo de servico*</label>
        <select
          value={formNovo.tipo}
          onChange={(event) => onChangeCampo("tipo", event.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
        >
          {TIPO_OPTIONS.map((tipo) => (
            <option key={tipo.value} value={tipo.value}>
              {tipo.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">{dicaTipoSelecionado}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <AgendaInputField
          label="Data*"
          type="date"
          value={formNovo.data}
          onChange={(valor) => onChangeCampo("data", valor)}
        />
        <AgendaInputField
          label="Horario*"
          type="time"
          value={formNovo.hora}
          onChange={(valor) => onChangeCampo("hora", valor)}
        />
      </div>

    </>
  );
}
