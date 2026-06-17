import { useState } from "react";
import { Boxes, PlugZap, Plus, RefreshCw, Wrench } from "lucide-react";
import toast from "react-hot-toast";
import ActionButton from "../../../components/ui/ActionButton";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaRecursoForm, {
  formFromRecurso,
  initialRecursoForm,
  payloadFromRecursoForm,
} from "./BanhoTosaRecursoForm";
import BanhoTosaRecursosList from "./BanhoTosaRecursosList";

export default function BanhoTosaRecursosView({ recursos, onChanged }) {
  const [form, setForm] = useState(initialRecursoForm);
  const [editingRecurso, setEditingRecurso] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function editarRecurso(recurso) {
    setEditingRecurso(recurso);
    setForm(formFromRecurso(recurso));
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelarEdicao() {
    setEditingRecurso(null);
    setForm(initialRecursoForm);
    setShowForm(false);
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

  const resumo = montarResumo(recursos);

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton
              icon={Plus}
              intent="create"
              onClick={() => {
                setEditingRecurso(null);
                setForm(initialRecursoForm);
                setShowForm((value) => !value);
              }}
            >
              Novo recurso
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="neutral"
              onClick={() => onChanged(true)}
              tone="soft"
            >
              Atualizar
            </ActionButton>
          </>
        }
        subtitle="Cadastre banheiras, mesas, secadores, boxes e veiculos para agenda, capacidade e custos."
        title="Recursos operacionais"
      />

      <MetricGrid>
        <MetricCard
          icon={<Boxes size={18} />}
          intent="blue"
          label="Recursos"
          value={recursos.length}
        />
        <MetricCard intent="emerald" label="Ativos" value={resumo.ativos} />
        <MetricCard
          icon={<PlugZap size={18} />}
          intent="cyan"
          label="Capacidade total"
          value={formatNumber(resumo.capacidade, 0)}
        />
        <MetricCard
          icon={<Wrench size={18} />}
          intent="violet"
          label="Manutencao/h"
          value={formatCurrency(resumo.manutencaoHora)}
        />
      </MetricGrid>

      {(showForm || editingRecurso) && (
        <BanhoTosaRecursoForm
          form={form}
          editing={Boolean(editingRecurso)}
          saving={saving}
          onChangeField={updateField}
          onCancelEdit={cancelarEdicao}
          onSubmit={salvarRecurso}
        />
      )}

      <BanhoTosaRecursosList
        recursos={recursos}
        onEdit={editarRecurso}
        onDelete={excluirRecurso}
        onToggleAtivo={toggleAtivo}
      />
    </div>
  );
}

function montarResumo(recursos = []) {
  return recursos.reduce(
    (acc, recurso) => {
      if (recurso.ativo) {
        acc.ativos += 1;
        acc.capacidade += Number(recurso.capacidade_simultanea || 0);
      }
      acc.manutencaoHora += Number(recurso.custo_manutencao_hora || 0);
      return acc;
    },
    { ativos: 0, capacidade: 0, manutencaoHora: 0 },
  );
}
