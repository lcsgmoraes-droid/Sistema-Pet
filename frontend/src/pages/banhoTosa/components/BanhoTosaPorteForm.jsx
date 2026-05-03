import { TextField } from "../../../components/ui/FormField";
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
  multiplicador_pelo_curto: "1",
  multiplicador_pelo_longo: "1.2",
  tempo_extra_pelo_longo_min: "0",
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
    multiplicador_pelo_curto: String(item.multiplicador_pelo_curto ?? "1"),
    multiplicador_pelo_longo: String(item.multiplicador_pelo_longo ?? "1.2"),
    tempo_extra_pelo_longo_min: String(item.tempo_extra_pelo_longo_min || 0),
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
    multiplicador_pelo_curto: toApiDecimal(form.multiplicador_pelo_curto, "1"),
    multiplicador_pelo_longo: toApiDecimal(form.multiplicador_pelo_longo, "1.2"),
    tempo_extra_pelo_longo_min: Number(form.tempo_extra_pelo_longo_min || 0),
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
        <TextField label="Porte" value={form.porte} onChange={(value) => onChangeField("porte", value)} tone="warm" />
        <TextField label="Multiplicador preco" type="number" value={form.multiplicador_preco} onChange={(value) => onChangeField("multiplicador_preco", value)} labelAccessory={<BanhoTosaHelpTooltip text="Ajuste relativo do preco por porte. Exemplo: gigante 2.0 custa o dobro do porte base." />} tone="warm" />
        <TextField label="Peso min kg" type="number" value={form.peso_min_kg} onChange={(value) => onChangeField("peso_min_kg", value)} tone="warm" />
        <TextField label="Peso max kg" type="number" value={form.peso_max_kg} onChange={(value) => onChangeField("peso_max_kg", value)} tone="warm" />
        <TextField label="Agua padrao L" type="number" value={form.agua_padrao_litros} onChange={(value) => onChangeField("agua_padrao_litros", value)} labelAccessory={<BanhoTosaHelpTooltip text="Estimativa usada quando nao houver medicao real do banho." />} tone="warm" />
        <TextField label="Energia padrao kWh" type="number" value={form.energia_padrao_kwh} onChange={(value) => onChangeField("energia_padrao_kwh", value)} labelAccessory={<BanhoTosaHelpTooltip text="Energia media esperada para secagem/equipamentos deste porte." />} tone="warm" />
        <TextField label="Tempo banho min" type="number" value={form.tempo_banho_min} onChange={(value) => onChangeField("tempo_banho_min", value)} labelAccessory={<BanhoTosaHelpTooltip text="Tempo medio de banho para calcular agenda, mao de obra e agua." />} tone="warm" />
        <TextField label="Tempo secagem min" type="number" value={form.tempo_secagem_min} onChange={(value) => onChangeField("tempo_secagem_min", value)} labelAccessory={<BanhoTosaHelpTooltip text="Tempo medio de secagem para energia e ocupacao de recurso." />} tone="warm" />
        <TextField label="Tempo tosa min" type="number" value={form.tempo_tosa_min} onChange={(value) => onChangeField("tempo_tosa_min", value)} labelAccessory={<BanhoTosaHelpTooltip text="Tempo medio de tosa para agenda e mao de obra." />} tone="warm" />
      </div>

      <div className="mt-5 rounded-2xl border border-orange-100 bg-orange-50/70 p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-orange-600">
          Pelagem dentro deste porte
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Use pelo curto como base e ajuste pelo longo com multiplicador e tempo extra.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <TextField label="Mult. pelo curto" type="number" value={form.multiplicador_pelo_curto} onChange={(value) => onChangeField("multiplicador_pelo_curto", value)} labelAccessory={<BanhoTosaHelpTooltip text="Multiplicador de preco quando o pet for classificado como pelo curto." />} tone="warm" />
          <TextField label="Mult. pelo longo" type="number" value={form.multiplicador_pelo_longo} onChange={(value) => onChangeField("multiplicador_pelo_longo", value)} labelAccessory={<BanhoTosaHelpTooltip text="Multiplicador de preco quando o pet for classificado como pelo longo." />} tone="warm" />
          <TextField label="Extra longo min" type="number" value={form.tempo_extra_pelo_longo_min} onChange={(value) => onChangeField("tempo_extra_pelo_longo_min", value)} labelAccessory={<BanhoTosaHelpTooltip text="Minutos somados ao banho, secagem e tosa quando a pelagem for longa." />} tone="warm" />
        </div>
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
