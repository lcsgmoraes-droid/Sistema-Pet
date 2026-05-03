import { Plus, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { SelectField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";

export default function BanhoTosaTaxiDogForm({
  agendamentos,
  form,
  funcionarios,
  saving,
  onCancel,
  onChangeField,
  onSubmit,
}) {
  return (
    <Panel title="Novo transporte" subtitle="Vincule o taxi dog a um agendamento do dia e informe janela, motorista e valores.">
      <form onSubmit={onSubmit}>
        <div className="grid gap-3 lg:grid-cols-3">
          <SelectField label="Tipo" value={form.tipo} onChange={(value) => onChangeField("tipo", value)}>
            <option value="ida">Somente ida</option>
            <option value="volta">Somente volta</option>
            <option value="ida_volta">Ida e volta</option>
          </SelectField>
          <SelectField label="Agendamento" value={form.agendamento_id} onChange={(value) => onChangeField("agendamento_id", value)}>
            <option value="">Selecione</option>
            {agendamentos.map((item) => (
              <option key={item.id} value={item.id}>
                {hora(item.data_hora_inicio)} - {item.pet_nome} / {item.cliente_nome}
              </option>
            ))}
          </SelectField>
          <SelectField label="Motorista" value={form.motorista_id} onChange={(value) => onChangeField("motorista_id", value)}>
            <option value="">Nao definido</option>
            {funcionarios.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>
            ))}
          </SelectField>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <TextField label="Janela inicio" type="datetime-local" value={form.janela_inicio} onChange={(value) => onChangeField("janela_inicio", value)} />
          <TextField label="Janela fim" type="datetime-local" value={form.janela_fim} onChange={(value) => onChangeField("janela_fim", value)} />
          <TextField label="Km estimado" type="number" value={form.km_estimado} onChange={(value) => onChangeField("km_estimado", value)} />
          <TextField label="Valor cobrado" type="number" value={form.valor_cobrado} onChange={(value) => onChangeField("valor_cobrado", value)} />
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <TextField label="Custo estimado" type="number" value={form.custo_estimado} onChange={(value) => onChangeField("custo_estimado", value)} />
          <TextField label="Custo real" type="number" value={form.custo_real} onChange={(value) => onChangeField("custo_real", value)} />
          <TextField label="Origem" value={form.endereco_origem} onChange={(value) => onChangeField("endereco_origem", value)} />
          <TextField label="Destino" value={form.endereco_destino} onChange={(value) => onChangeField("endereco_destino", value)} />
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <ActionButton icon={X} intent="neutral" onClick={onCancel} tone="soft">
            Cancelar
          </ActionButton>
          <ActionButton icon={Plus} intent="create" loading={saving} type="submit">
            Criar taxi dog
          </ActionButton>
        </div>
      </form>
    </Panel>
  );
}

function hora(value) {
  return value ? String(value).slice(11, 16) : "--:--";
}
