import { toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";

export const initialPorteForm = {
  porte: "",
  peso_min_kg: "",
  peso_max_kg: "",
  agua_padrao_litros: "0",
  energia_padrao_kwh: "0",
  tempo_banho_min: "0",
  tempo_secagem_min: "0",
  tempo_tosa_min: "0",
  multiplicador_preco: "1",
  ativo: true,
};

export function formFromParametroPorte(item) {
  return {
    porte: item.porte || "",
    peso_min_kg: item.peso_min_kg ? String(item.peso_min_kg) : "",
    peso_max_kg: item.peso_max_kg ? String(item.peso_max_kg) : "",
    agua_padrao_litros: String(item.agua_padrao_litros ?? "0"),
    energia_padrao_kwh: String(item.energia_padrao_kwh ?? "0"),
    tempo_banho_min: String(item.tempo_banho_min || 0),
    tempo_secagem_min: String(item.tempo_secagem_min || 0),
    tempo_tosa_min: String(item.tempo_tosa_min || 0),
    multiplicador_preco: String(item.multiplicador_preco ?? "1"),
    ativo: Boolean(item.ativo),
  };
}

export function payloadFromPorteForm(form) {
  return {
    porte: form.porte.trim(),
    peso_min_kg: form.peso_min_kg ? toApiDecimal(form.peso_min_kg) : null,
    peso_max_kg: form.peso_max_kg ? toApiDecimal(form.peso_max_kg) : null,
    agua_padrao_litros: toApiDecimal(form.agua_padrao_litros),
    energia_padrao_kwh: toApiDecimal(form.energia_padrao_kwh),
    tempo_banho_min: Number(form.tempo_banho_min || 0),
    tempo_secagem_min: Number(form.tempo_secagem_min || 0),
    tempo_tosa_min: Number(form.tempo_tosa_min || 0),
    multiplicador_preco: toApiDecimal(form.multiplicador_preco, "1"),
    ativo: Boolean(form.ativo),
  };
}

export default function BanhoTosaPorteForm({
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
        Portes
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        {editing ? "Editar parametro por porte" : "Novo parametro por porte"}
      </h2>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <TextField label="Porte" value={form.porte} onChange={(value) => onChangeField("porte", value)} />
        <TextField label="Multiplicador preco" type="number" value={form.multiplicador_preco} onChange={(value) => onChangeField("multiplicador_preco", value)} help="Ajuste relativo do preco por porte. Exemplo: gigante 2.0 custa o dobro do porte base." />
        <TextField label="Peso min kg" type="number" value={form.peso_min_kg} onChange={(value) => onChangeField("peso_min_kg", value)} />
        <TextField label="Peso max kg" type="number" value={form.peso_max_kg} onChange={(value) => onChangeField("peso_max_kg", value)} />
        <TextField label="Agua padrao L" type="number" value={form.agua_padrao_litros} onChange={(value) => onChangeField("agua_padrao_litros", value)} help="Estimativa usada quando nao houver medicao real do banho." />
        <TextField label="Energia padrao kWh" type="number" value={form.energia_padrao_kwh} onChange={(value) => onChangeField("energia_padrao_kwh", value)} help="Energia media esperada para secagem/equipamentos deste porte." />
        <TextField label="Tempo banho min" type="number" value={form.tempo_banho_min} onChange={(value) => onChangeField("tempo_banho_min", value)} help="Tempo medio de banho para calcular agenda, mao de obra e agua." />
        <TextField label="Tempo secagem min" type="number" value={form.tempo_secagem_min} onChange={(value) => onChangeField("tempo_secagem_min", value)} help="Tempo medio de secagem para energia e ocupacao de recurso." />
        <TextField label="Tempo tosa min" type="number" value={form.tempo_tosa_min} onChange={(value) => onChangeField("tempo_tosa_min", value)} help="Tempo medio de tosa para agenda e mao de obra." />
      </div>

      {editing && (
        <div className="mt-4">
          <CheckField label="Ativo" checked={form.ativo} onChange={(value) => onChangeField("ativo", value)} />
        </div>
      )}

      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
        >
          {saving ? "Salvando..." : editing ? "Salvar alteracoes" : "Cadastrar porte"}
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
