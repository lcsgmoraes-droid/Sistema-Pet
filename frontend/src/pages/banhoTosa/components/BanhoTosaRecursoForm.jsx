import { Save, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, SelectField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";
import { toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";

export const initialRecursoForm = {
  nome: "",
  tipo: "banheira",
  capacidade_simultanea: "1",
  potencia_watts: "",
  custo_manutencao_hora: "0",
  ativo: true,
};

export function formFromRecurso(recurso) {
  return {
    nome: recurso.nome || "",
    tipo: recurso.tipo || "banheira",
    capacidade_simultanea: String(recurso.capacidade_simultanea || 1),
    potencia_watts: recurso.potencia_watts ? String(recurso.potencia_watts) : "",
    custo_manutencao_hora: String(recurso.custo_manutencao_hora ?? "0"),
    ativo: Boolean(recurso.ativo),
  };
}

export function payloadFromRecursoForm(form) {
  return {
    nome: form.nome.trim(),
    tipo: form.tipo,
    capacidade_simultanea: Number(form.capacidade_simultanea || 1),
    potencia_watts: form.potencia_watts ? toApiDecimal(form.potencia_watts) : null,
    custo_manutencao_hora: toApiDecimal(form.custo_manutencao_hora),
    ativo: Boolean(form.ativo),
  };
}

export default function BanhoTosaRecursoForm({
  form,
  editing,
  saving,
  onChangeField,
  onCancelEdit,
  onSubmit,
}) {
  return (
    <Panel
      title={editing ? "Editar recurso operacional" : "Novo recurso operacional"}
      subtitle="Recursos entram na agenda, no calculo de capacidade e no custo operacional."
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <TextField label="Nome" value={form.nome} onChange={(value) => onChangeField("nome", value)} labelAccessory={<BanhoTosaHelpTooltip text="Identificacao do recurso na agenda e nos relatorios de ocupacao." />} />
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField label="Tipo" value={form.tipo} onChange={(value) => onChangeField("tipo", value)} labelAccessory={<BanhoTosaHelpTooltip text="Define como o recurso entra na capacidade: banheira, mesa, secador, box ou veiculo." />}>
          <option value="banheira">Banheira</option>
          <option value="mesa_tosa">Mesa de tosa</option>
          <option value="secador">Secador / soprador</option>
          <option value="box">Sala / box</option>
          <option value="veiculo">Taxi dog / veiculo</option>
          <option value="outro">Outro</option>
          </SelectField>
          <TextField label="Capacidade simultanea" type="number" value={form.capacidade_simultanea} onChange={(value) => onChangeField("capacidade_simultanea", value)} labelAccessory={<BanhoTosaHelpTooltip text="Quantidade de pets/atendimentos que o recurso comporta ao mesmo tempo." />} />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="Potencia watts" type="number" value={form.potencia_watts} onChange={(value) => onChangeField("potencia_watts", value)} labelAccessory={<BanhoTosaHelpTooltip text="Potencia do equipamento para calcular energia por tempo de uso." />} />
          <TextField label="Manutencao por hora" type="number" value={form.custo_manutencao_hora} onChange={(value) => onChangeField("custo_manutencao_hora", value)} labelAccessory={<BanhoTosaHelpTooltip text="Rateio de troca de escova, limpeza, depreciacao ou manutencao do recurso." />} />
        </div>
        {editing && (
          <CheckboxField label="Ativo" checked={form.ativo} onChange={(value) => onChangeField("ativo", value)} />
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton icon={X} intent="neutral" onClick={onCancelEdit} tone="soft">
            Cancelar
          </ActionButton>
          <ActionButton icon={Save} intent={editing ? "edit" : "create"} loading={saving} type="submit">
            {editing ? "Salvar alteracoes" : "Cadastrar recurso"}
          </ActionButton>
        </div>
      </form>
    </Panel>
  );
}
