import { useRef, useState } from "react";
import toast from "react-hot-toast";
import { Plus } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
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
  const [formOpen, setFormOpen] = useState(false);
  const [editingServico, setEditingServico] = useState(null);
  const [saving, setSaving] = useState(false);
  const formRef = useRef(null);

  const ativos = servicos.filter((servico) => servico.ativo).length;
  const pacotes = servicos.filter((servico) => servico.permite_pacote).length;
  const duracaoMedia = calcularDuracaoMedia(servicos);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function scrollToForm() {
    window.setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }

  function novoServico() {
    setEditingServico(null);
    setForm(initialServicoForm);
    setFormOpen(true);
    scrollToForm();
  }

  function editarServico(servico) {
    setEditingServico(servico);
    setForm(formFromServico(servico));
    setFormOpen(true);
    scrollToForm();
  }

  function cancelarEdicao() {
    setEditingServico(null);
    setForm(initialServicoForm);
    setFormOpen(false);
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
    <div className="space-y-4">
      <Panel
        actions={
          <ActionButton icon={Plus} intent="create" onClick={novoServico}>
            Novo servico
          </ActionButton>
        }
        subtitle="Mantenha o catalogo limpo para agenda, fechamento e pacotes."
        title="Servicos de Banho & Tosa"
      >
        <MetricGrid>
          <MetricCard
            intent="blue"
            label="Total"
            subtitle="Servicos cadastrados"
            value={servicos.length}
          />
          <MetricCard
            intent="emerald"
            label="Ativos"
            subtitle="Disponiveis para operacao"
            value={ativos}
          />
          <MetricCard
            intent="violet"
            label="Pacotes"
            subtitle="Permitem venda recorrente"
            value={pacotes}
          />
          <MetricCard
            intent="slate"
            label="Duracao media"
            subtitle="Base da agenda"
            value={`${duracaoMedia} min`}
          />
        </MetricGrid>
      </Panel>

      {formOpen && (
        <div ref={formRef}>
          <BanhoTosaServicoForm
            editing={Boolean(editingServico)}
            form={form}
            onCancelEdit={cancelarEdicao}
            onChangeField={updateField}
            onSubmit={salvarServico}
            saving={saving}
          />
        </div>
      )}

      <BanhoTosaServicosTable
        onDelete={excluirServico}
        onEdit={editarServico}
        onToggleAtivo={toggleAtivo}
        servicos={servicos}
      />
    </div>
  );
}

function calcularDuracaoMedia(servicos) {
  const ativos = servicos.filter((servico) => servico.ativo);
  if (!ativos.length) return 0;
  const total = ativos.reduce(
    (acc, servico) => acc + Number(servico.duracao_padrao_minutos || 0),
    0,
  );
  return Math.round(total / ativos.length);
}
