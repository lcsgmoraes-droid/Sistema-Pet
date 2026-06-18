import { Plus, Save, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";
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
    <Panel
      actions={
        <ActionButton icon={X} intent="neutral" onClick={onCancelEdit} tone="ghost">
          Fechar
        </ActionButton>
      }
      subtitle="Defina consumo, tempo esperado e ajustes por pelagem para este tamanho."
      title={editing ? "Editar parametro por porte" : "Novo parametro por porte"}
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <TextField
            label="Porte"
            onChange={(value) => onChangeField("porte", value)}
            value={form.porte}
          />
          <TextField
            label="Multiplicador preco"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Ajuste relativo do preco por porte. Exemplo: gigante 2.0 custa o dobro do porte base." />
            }
            onChange={(value) => onChangeField("multiplicador_preco", value)}
            type="number"
            value={form.multiplicador_preco}
          />
          <TextField
            label="Peso min kg"
            onChange={(value) => onChangeField("peso_min_kg", value)}
            type="number"
            value={form.peso_min_kg}
          />
          <TextField
            label="Peso max kg"
            onChange={(value) => onChangeField("peso_max_kg", value)}
            type="number"
            value={form.peso_max_kg}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <TextField
            label="Agua padrao L"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Estimativa usada quando nao houver medicao real do banho." />
            }
            onChange={(value) => onChangeField("agua_padrao_litros", value)}
            type="number"
            value={form.agua_padrao_litros}
          />
          <TextField
            label="Energia padrao kWh"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Energia media esperada para secagem/equipamentos deste porte." />
            }
            onChange={(value) => onChangeField("energia_padrao_kwh", value)}
            type="number"
            value={form.energia_padrao_kwh}
          />
          <TextField
            label="Tempo banho min"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Tempo medio de banho para calcular agenda, mao de obra e agua." />
            }
            onChange={(value) => onChangeField("tempo_banho_min", value)}
            type="number"
            value={form.tempo_banho_min}
          />
          <TextField
            label="Tempo secagem min"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Tempo medio de secagem para energia e ocupacao de recurso." />
            }
            onChange={(value) => onChangeField("tempo_secagem_min", value)}
            type="number"
            value={form.tempo_secagem_min}
          />
          <TextField
            label="Tempo tosa min"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Tempo medio de tosa para agenda e mao de obra." />
            }
            onChange={(value) => onChangeField("tempo_tosa_min", value)}
            type="number"
            value={form.tempo_tosa_min}
          />
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Pelagem dentro deste porte</h3>
            <p className="mt-1 text-sm text-slate-500">
              Use pelo curto como base e ajuste pelo longo com multiplicador e tempo extra.
            </p>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <TextField
              label="Mult. pelo curto"
              labelAccessory={
                <BanhoTosaHelpTooltip text="Multiplicador de preco quando o pet for classificado como pelo curto." />
              }
              onChange={(value) => onChangeField("multiplicador_pelo_curto", value)}
              type="number"
              value={form.multiplicador_pelo_curto}
            />
            <TextField
              label="Mult. pelo longo"
              labelAccessory={
                <BanhoTosaHelpTooltip text="Multiplicador de preco quando o pet for classificado como pelo longo." />
              }
              onChange={(value) => onChangeField("multiplicador_pelo_longo", value)}
              type="number"
              value={form.multiplicador_pelo_longo}
            />
            <TextField
              label="Extra longo min"
              labelAccessory={
                <BanhoTosaHelpTooltip text="Minutos somados ao banho, secagem e tosa quando a pelagem for longa." />
              }
              onChange={(value) => onChangeField("tempo_extra_pelo_longo_min", value)}
              type="number"
              value={form.tempo_extra_pelo_longo_min}
            />
          </div>
        </div>

        {editing && (
          <CheckboxField
            checked={form.ativo}
            label="Ativo"
            onChange={(value) => onChangeField("ativo", value)}
          />
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton intent="neutral" onClick={onCancelEdit} tone="soft">
            Cancelar
          </ActionButton>
          <ActionButton
            icon={editing ? Save : Plus}
            intent={editing ? "edit" : "create"}
            loading={saving}
            type="submit"
          >
            {editing ? "Salvar alteracoes" : "Cadastrar porte"}
          </ActionButton>
        </div>
      </form>
    </Panel>
  );
}
