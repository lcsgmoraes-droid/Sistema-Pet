import { Plus, Save, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, SelectField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";
import { toApiDecimal } from "../banhoTosaUtils";

export const initialServicoForm = {
  nome: "",
  categoria: "banho",
  descricao: "",
  duracao_padrao_minutos: "60",
  preco_base: "0",
  requer_banho: true,
  requer_tosa: false,
  requer_secagem: true,
  permite_pacote: true,
  ativo: true,
};

export function formFromServico(servico) {
  return {
    nome: servico.nome || "",
    categoria: servico.categoria || "banho",
    descricao: servico.descricao || "",
    duracao_padrao_minutos: String(servico.duracao_padrao_minutos || 60),
    preco_base: String(servico.preco_base ?? "0"),
    requer_banho: Boolean(servico.requer_banho),
    requer_tosa: Boolean(servico.requer_tosa),
    requer_secagem: Boolean(servico.requer_secagem),
    permite_pacote: Boolean(servico.permite_pacote),
    ativo: Boolean(servico.ativo),
  };
}

export function payloadFromServicoForm(form) {
  return {
    ...form,
    nome: form.nome.trim(),
    descricao: form.descricao.trim() || null,
    duracao_padrao_minutos: Number(form.duracao_padrao_minutos || 60),
    preco_base: toApiDecimal(form.preco_base),
  };
}

export default function BanhoTosaServicoForm({
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
      subtitle="Cadastre apenas o necessario para agenda, pacote e fechamento."
      title={editing ? "Editar servico" : "Novo servico"}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <TextField
            label="Nome"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Nome que aparece na agenda, na fila e no fechamento para o PDV." />
            }
            onChange={(value) => onChangeField("nome", value)}
            value={form.nome}
          />
          <SelectField
            label="Categoria"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Agrupa servicos para relatorios e filtros: banho, tosa, combo, higiene ou outro." />
            }
            onChange={(value) => onChangeField("categoria", value)}
            value={form.categoria}
          >
            <option value="banho">Banho</option>
            <option value="tosa">Tosa</option>
            <option value="combo">Combo</option>
            <option value="higiene">Higiene</option>
            <option value="outro">Outro</option>
          </SelectField>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Duracao padrao (min)"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Tempo usado para prever fim do agendamento e ocupacao da equipe." />
            }
            onChange={(value) => onChangeField("duracao_padrao_minutos", value)}
            type="number"
            value={form.duracao_padrao_minutos}
          />
          <TextField
            label="Preco base"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Valor sugerido no agendamento e no fechamento. Pode ser alterado na venda final." />
            }
            onChange={(value) => onChangeField("preco_base", value)}
            type="number"
            value={form.preco_base}
          />
        </div>

        <TextField
          label="Descricao"
          labelAccessory={
            <BanhoTosaHelpTooltip text="Explique o que esta incluso para padronizar a venda e o atendimento." />
          }
          onChange={(value) => onChangeField("descricao", value)}
          value={form.descricao}
        />

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <CheckboxField
            checked={form.requer_banho}
            label="Requer banho"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Marca se o servico consome agua, shampoo e etapa de banho." />
            }
            onChange={(value) => onChangeField("requer_banho", value)}
          />
          <CheckboxField
            checked={form.requer_tosa}
            label="Requer tosa"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Marca se precisa de tosador, mesa ou etapa de tosa." />
            }
            onChange={(value) => onChangeField("requer_tosa", value)}
          />
          <CheckboxField
            checked={form.requer_secagem}
            label="Requer secagem"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Marca se deve considerar secador/soprador no tempo e energia." />
            }
            onChange={(value) => onChangeField("requer_secagem", value)}
          />
          <CheckboxField
            checked={form.permite_pacote}
            label="Permite pacote"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Permite vender creditos recorrentes desse servico." />
            }
            onChange={(value) => onChangeField("permite_pacote", value)}
          />
          <CheckboxField
            checked={form.ativo}
            label="Ativo"
            labelAccessory={
              <BanhoTosaHelpTooltip text="Servicos inativos ficam fora da operacao, mas preservam historico." />
            }
            onChange={(value) => onChangeField("ativo", value)}
          />
        </div>

        <div className="flex justify-end">
          <ActionButton
            icon={editing ? Save : Plus}
            intent={editing ? "edit" : "create"}
            loading={saving}
            size="md"
            type="submit"
          >
            {editing ? "Salvar alteracoes" : "Cadastrar servico"}
          </ActionButton>
        </div>
      </form>
    </Panel>
  );
}
