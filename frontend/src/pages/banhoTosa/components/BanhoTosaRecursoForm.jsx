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
        <TextField label="Nome" value={form.nome} onChange={(value) => onChangeField("nome", value)} help="Identificacao do recurso na agenda e nos relatorios de ocupacao." />
        <label className="block">
          <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Tipo
            <BanhoTosaHelpTooltip text="Define como o recurso entra na capacidade: banheira, mesa, secador, box ou veiculo." />
          </span>
          <select
            value={form.tipo}
            onChange={(event) => onChangeField("tipo", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          >
            <option value="banheira">Banheira</option>
            <option value="mesa_tosa">Mesa de tosa</option>
            <option value="secador">Secador / soprador</option>
            <option value="box">Sala / box</option>
            <option value="veiculo">Taxi dog / veiculo</option>
            <option value="outro">Outro</option>
          </select>
        </label>
        <TextField label="Capacidade simultanea" type="number" value={form.capacidade_simultanea} onChange={(value) => onChangeField("capacidade_simultanea", value)} help="Quantidade de pets/atendimentos que o recurso comporta ao mesmo tempo." />
        <TextField label="Potencia watts" type="number" value={form.potencia_watts} onChange={(value) => onChangeField("potencia_watts", value)} help="Potencia do equipamento para calcular energia por tempo de uso." />
        <TextField label="Manutencao por hora" type="number" value={form.custo_manutencao_hora} onChange={(value) => onChangeField("custo_manutencao_hora", value)} help="Rateio de troca de escova, limpeza, depreciacao ou manutencao do recurso." />
        {editing && (
          <CheckField label="Ativo" checked={form.ativo} onChange={(value) => onChangeField("ativo", value)} />
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

function TextField({ label, value, onChange, type = "text", help }) {
  return (
    <label className="block">
      <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
        <BanhoTosaHelpTooltip text={help} />
      </span>
      <input
        type={type}
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function CheckField({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-orange-500"
      />
      {label}
    </label>
  );
}
