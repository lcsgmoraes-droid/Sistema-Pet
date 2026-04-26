import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaRecursoForm, {
  formFromRecurso,
  initialRecursoForm,
  payloadFromRecursoForm,
} from "./BanhoTosaRecursoForm";
import BanhoTosaRecursosList from "./BanhoTosaRecursosList";

export default function BanhoTosaRecursosView({ recursos, onChanged }) {
  const [form, setForm] = useState(initialRecursoForm);
  const [editingRecurso, setEditingRecurso] = useState(null);
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function editarRecurso(recurso) {
    setEditingRecurso(recurso);
    setForm(formFromRecurso(recurso));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelarEdicao() {
    setEditingRecurso(null);
    setForm(initialRecursoForm);
  }

  async function salvarRecurso(event) {
    event.preventDefault();
    if (!form.nome.trim()) {
      toast.error("Informe o nome do recurso.");
      return;
    }

    setSaving(true);
    try {
      const payload = payloadFromRecursoForm(form);
      if (editingRecurso) {
        await banhoTosaApi.atualizarRecurso(editingRecurso.id, payload);
        toast.success("Recurso atualizado.");
      } else {
        await banhoTosaApi.criarRecurso(payload);
        toast.success("Recurso cadastrado.");
      }
      cancelarEdicao();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar o recurso."));
    } finally {
      setSaving(false);
    }
  }

  async function toggleAtivo(recurso) {
    try {
      await banhoTosaApi.atualizarRecurso(recurso.id, { ativo: !recurso.ativo });
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar o recurso."));
    }
  }

  async function excluirRecurso(recurso) {
    const confirmou = window.confirm(
      `Excluir o recurso "${recurso.nome}"? Se ele ja tiver historico, o sistema vai apenas desativar.`,
    );
    if (!confirmou) return;

    try {
      const response = await banhoTosaApi.removerRecurso(recurso.id);
      toast.success(response.data?.message || "Recurso excluido.");
      if (editingRecurso?.id === recurso.id) {
        cancelarEdicao();
      }
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel excluir o recurso."));
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <BanhoTosaRecursoForm
        form={form}
        editing={Boolean(editingRecurso)}
        saving={saving}
        onChangeField={updateField}
        onCancelEdit={cancelarEdicao}
        onSubmit={salvarRecurso}
      />
      <BanhoTosaRecursosList
        recursos={recursos}
        onEdit={editarRecurso}
        onDelete={excluirRecurso}
        onToggleAtivo={toggleAtivo}
      />
    </div>
  );
}
