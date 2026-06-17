import { useEffect, useState } from "react";
import { Save, X } from "lucide-react";
import toast from "react-hot-toast";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, SelectField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";

const initialForm = {
  nome: "",
  descricao: "",
  servico_id: "",
  quantidade_creditos: "4",
  validade_dias: "90",
  preco: "0",
  ativo: true,
};

function formFromPacote(pacote) {
  return {
    nome: pacote.nome || "",
    descricao: pacote.descricao || "",
    servico_id: pacote.servico_id ? String(pacote.servico_id) : "",
    quantidade_creditos: String(pacote.quantidade_creditos ?? "1"),
    validade_dias: String(pacote.validade_dias || 30),
    preco: String(pacote.preco ?? "0"),
    ativo: Boolean(pacote.ativo),
  };
}

function payloadFromPacoteForm(form) {
  return {
    nome: form.nome.trim(),
    descricao: form.descricao.trim() || null,
    servico_id: form.servico_id ? Number(form.servico_id) : null,
    quantidade_creditos: toApiDecimal(form.quantidade_creditos, "1"),
    validade_dias: Number(form.validade_dias || 30),
    preco: toApiDecimal(form.preco),
    ativo: Boolean(form.ativo),
  };
}

export default function BanhoTosaPacoteForm({
  servicos = [],
  editingPacote,
  onCancelEdit,
  onChanged,
}) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(editingPacote ? formFromPacote(editingPacote) : initialForm);
  }, [editingPacote?.id]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function salvar(event) {
    event.preventDefault();
    if (!form.nome.trim()) {
      toast.error("Informe o nome do pacote.");
      return;
    }

    setSaving(true);
    try {
      const payload = payloadFromPacoteForm(form);
      if (editingPacote) {
        await banhoTosaApi.atualizarPacote(editingPacote.id, payload);
        toast.success("Pacote atualizado.");
      } else {
        await banhoTosaApi.criarPacote(payload);
        toast.success("Pacote cadastrado.");
      }
      setForm(initialForm);
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar o pacote."));
    } finally {
      setSaving(false);
    }
  }

  const servicosDisponiveis = servicos.filter(
    (item) => (item.ativo && item.permite_pacote) || item.id === Number(form.servico_id),
  );

  return (
    <Panel
      title={editingPacote ? "Editar pacote" : "Novo pacote"}
      subtitle="Defina creditos, validade e servico coberto."
    >
      <form onSubmit={salvar} className="space-y-4">
        <TextField
          label="Nome"
          value={form.nome}
          onChange={(value) => updateField("nome", value)}
        />
        <TextField
          label="Descricao"
          value={form.descricao}
          onChange={(value) => updateField("descricao", value)}
        />
        <SelectField
          label="Servico coberto"
          value={form.servico_id}
          onChange={(value) => updateField("servico_id", value)}
        >
          <option value="">Qualquer servico do atendimento</option>
          {servicosDisponiveis.map((servico) => (
            <option key={servico.id} value={servico.id}>
              {servico.nome}
            </option>
          ))}
        </SelectField>
        <div className="grid gap-3 sm:grid-cols-3">
          <TextField
            label="Creditos"
            type="number"
            value={form.quantidade_creditos}
            onChange={(value) => updateField("quantidade_creditos", value)}
          />
          <TextField
            label="Validade dias"
            type="number"
            value={form.validade_dias}
            onChange={(value) => updateField("validade_dias", value)}
          />
          <TextField
            label="Preco"
            type="number"
            value={form.preco}
            onChange={(value) => updateField("preco", value)}
          />
        </div>
        {editingPacote && (
          <CheckboxField
            label="Ativo"
            checked={form.ativo}
            onChange={(value) => updateField("ativo", value)}
          />
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton icon={X} intent="neutral" onClick={onCancelEdit} tone="soft">
            Cancelar
          </ActionButton>
          <ActionButton
            icon={Save}
            intent={editingPacote ? "edit" : "create"}
            loading={saving}
            type="submit"
          >
            {editingPacote ? "Salvar alteracoes" : "Cadastrar pacote"}
          </ActionButton>
        </div>
      </form>
    </Panel>
  );
}
