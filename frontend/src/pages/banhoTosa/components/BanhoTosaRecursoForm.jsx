import { CheckboxField, SelectField, TextField } from "../../../components/ui/FormField";
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
    <form
      onSubmit={onSubmit}
      className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
    >
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Capacidade
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        {editing ? "Editar recurso operacional" : "Novo recurso operacional"}
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Banheiras, mesas, secadores, boxes e veiculos entram aqui para medir gargalo e custo.
      </p>

      <div className="mt-5 space-y-4">
        <TextField label="Nome" value={form.nome} onChange={(value) => onChangeField("nome", value)} labelAccessory={<BanhoTosaHelpTooltip text="Identificacao do recurso na agenda e nos relatorios de ocupacao." />} tone="warm" />
        <SelectField label="Tipo" value={form.tipo} onChange={(value) => onChangeField("tipo", value)} labelAccessory={<BanhoTosaHelpTooltip text="Define como o recurso entra na capacidade: banheira, mesa, secador, box ou veiculo." />} tone="warm">
          <option value="banheira">Banheira</option>
          <option value="mesa_tosa">Mesa de tosa</option>
          <option value="secador">Secador / soprador</option>
          <option value="box">Sala / box</option>
          <option value="veiculo">Taxi dog / veiculo</option>
          <option value="outro">Outro</option>
        </SelectField>
        <TextField label="Capacidade simultanea" type="number" value={form.capacidade_simultanea} onChange={(value) => onChangeField("capacidade_simultanea", value)} labelAccessory={<BanhoTosaHelpTooltip text="Quantidade de pets/atendimentos que o recurso comporta ao mesmo tempo." />} tone="warm" />
        <TextField label="Potencia watts" type="number" value={form.potencia_watts} onChange={(value) => onChangeField("potencia_watts", value)} labelAccessory={<BanhoTosaHelpTooltip text="Potencia do equipamento para calcular energia por tempo de uso." />} tone="warm" />
        <TextField label="Manutencao por hora" type="number" value={form.custo_manutencao_hora} onChange={(value) => onChangeField("custo_manutencao_hora", value)} labelAccessory={<BanhoTosaHelpTooltip text="Rateio de troca de escova, limpeza, depreciacao ou manutencao do recurso." />} tone="warm" />
        {editing && (
          <CheckboxField label="Ativo" checked={form.ativo} onChange={(value) => onChangeField("ativo", value)} tone="warm" />
        )}
      </div>

      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Salvando..." : editing ? "Salvar alteracoes" : "Cadastrar recurso"}
        </button>
        {editing && (
          <button
            type="button"
            onClick={onCancelEdit}
            className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-orange-300 hover:text-orange-700"
          >
            Cancelar edicao
          </button>
        )}
      </div>
    </form>
  );
}
