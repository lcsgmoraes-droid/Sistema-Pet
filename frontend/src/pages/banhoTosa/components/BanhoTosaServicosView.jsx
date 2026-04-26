import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaServicoForm, {
  formFromServico,
  initialServicoForm,
  payloadFromServicoForm,
} from "./BanhoTosaServicoForm";
import BanhoTosaServicosTable from "./BanhoTosaServicosTable";

export default function BanhoTosaServicosView({ servicos, onChanged }) {
  const [form, setForm] = useState(initialServicoForm);
  const [editingServico, setEditingServico] = useState(null);
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function editarServico(servico) {
    setEditingServico(servico);
    setForm(formFromServico(servico));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelarEdicao() {
    setEditingServico(null);
    setForm(initialServicoForm);
  }

  async function salvarServico(event) {
    event.preventDefault();
    if (!form.nome.trim()) {
      toast.error("Informe o nome do servico.");
      return;
    }

    setSaving(true);
    try {
      const payload = payloadFromServicoForm(form);
      if (editingServico) {
        await banhoTosaApi.atualizarServico(editingServico.id, payload);
        toast.success("Servico atualizado.");
      } else {
        await banhoTosaApi.criarServico(payload);
        toast.success("Servico criado.");
      }
      cancelarEdicao();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar o servico."));
    } finally {
      setSaving(false);
    }
  }

  async function toggleAtivo(servico) {
    try {
      await banhoTosaApi.atualizarServico(servico.id, { ativo: !servico.ativo });
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar o servico."));
    }
  }

  async function excluirServico(servico) {
    const confirmou = window.confirm(
      `Excluir o servico "${servico.nome}"? Se ele ja tiver historico, o sistema vai apenas desativar.`,
    );
    if (!confirmou) return;

    try {
      const response = await banhoTosaApi.removerServico(servico.id);
      toast.success(response.data?.message || "Servico excluido.");
      if (editingServico?.id === servico.id) {
        cancelarEdicao();
      }
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel excluir o servico."));
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <BanhoTosaServicoForm
        form={form}
        editing={Boolean(editingServico)}
        saving={saving}
        onChangeField={updateField}
        onCancelEdit={cancelarEdicao}
        onSubmit={salvarServico}
      />
      <BanhoTosaServicosTable
        servicos={servicos}
        onEdit={editarServico}
        onDelete={excluirServico}
        onToggleAtivo={toggleAtivo}
      />
    </div>
  );
}
