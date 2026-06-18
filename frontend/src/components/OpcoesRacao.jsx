import { useCallback, useEffect, useState } from "react";
import {
  Baby,
  Beef,
  ChevronRight,
  Dog,
  Edit2,
  Package,
  Pill,
  Plus,
  Save,
  Scale,
  Settings,
  Trash2,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import ActionButton from "./ui/ActionButton";
import EmptyState from "./ui/EmptyState";
import IconActionButton from "./ui/IconActionButton";
import LoadingState from "./ui/LoadingState";
import PageHeader from "./ui/PageHeader";
import Panel from "./ui/Panel";
import SegmentedControl from "./ui/SegmentedControl";
import StatusBadge from "./ui/StatusBadge";
import { getGuiaClassNames } from "../utils/guiaHighlight";

const FIELD_CLASS =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100";

const LABEL_CLASS = "mb-1 block text-sm font-medium text-slate-700";

const abas = [
  { id: "linhas", nome: "Linhas de racao", endpoint: "/opcoes-racao/linhas", icon: Package },
  { id: "portes", nome: "Portes", endpoint: "/opcoes-racao/portes", icon: Dog },
  { id: "fases", nome: "Fases/Publico", endpoint: "/opcoes-racao/fases", icon: Baby },
  { id: "tratamentos", nome: "Tratamentos", endpoint: "/opcoes-racao/tratamentos", icon: Pill },
  { id: "sabores", nome: "Sabores/Proteinas", endpoint: "/opcoes-racao/sabores", icon: Beef },
  {
    id: "apresentacoes",
    nome: "Apresentacoes",
    endpoint: "/opcoes-racao/apresentacoes",
    icon: Scale,
  },
];

function TabLabel({ aba }) {
  const Icon = aba.icon;

  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <Icon className="h-4 w-4" aria-hidden="true" />
      {aba.nome}
    </span>
  );
}

function OpcoesRacao() {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarOpcoesRacao = guiaAtiva === "racao-opcoes";
  const guiaClasses = getGuiaClassNames(destacarOpcoesRacao);
  const [abaAtiva, setAbaAtiva] = useState("linhas");
  const [dados, setDados] = useState({});
  const [loading, setLoading] = useState(false);
  const [editando, setEditando] = useState(null);
  const [formData, setFormData] = useState({ nome: "", descricao: "", ordem: 0, ativo: true });
  const [formPeso, setFormPeso] = useState({ peso_kg: 0, descricao: "", ordem: 0, ativo: true });

  const abaConfig = abas.find((aba) => aba.id === abaAtiva);
  const dadosAba = dados[abaAtiva] || [];
  const AbaIcon = abaConfig.icon;
  const fieldPrefix = `opcoes-racao-${abaAtiva}`;

  const carregarDados = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(abaConfig.endpoint, {
        params: { apenas_ativos: false },
      });
      setDados((prev) => ({ ...prev, [abaAtiva]: response.data }));
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error(`Erro ao carregar ${abaConfig.nome.toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  }, [abaAtiva, abaConfig.endpoint, abaConfig.nome]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const resetForm = () => {
    setFormData({ nome: "", descricao: "", ordem: 0, ativo: true });
    setFormPeso({ peso_kg: 0, descricao: "", ordem: 0, ativo: true });
    setEditando(null);
  };

  const handleEditar = (item) => {
    setEditando(item.id);
    if (abaAtiva === "apresentacoes") {
      setFormPeso({
        peso_kg: item.peso_kg,
        descricao: item.descricao || "",
        ordem: item.ordem || 0,
        ativo: item.ativo,
      });
      return;
    }

    setFormData({
      nome: item.nome,
      descricao: item.descricao || "",
      ordem: item.ordem || 0,
      ativo: item.ativo,
    });
  };

  const handleSalvar = async () => {
    try {
      const payload = abaAtiva === "apresentacoes" ? formPeso : formData;

      if (editando) {
        await api.put(`${abaConfig.endpoint}/${editando}`, payload);
        toast.success("Atualizado com sucesso!");
      } else {
        await api.post(abaConfig.endpoint, payload);
        toast.success("Criado com sucesso!");
      }

      resetForm();
      carregarDados();
    } catch (error) {
      console.error("Erro ao salvar:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar");
    }
  };

  const handleDeletar = async (id) => {
    if (!confirm("Tem certeza que deseja inativar este item?")) return;

    try {
      await api.delete(`${abaConfig.endpoint}/${id}`);
      toast.success("Inativado com sucesso!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao deletar:", error);
      toast.error("Erro ao inativar");
    }
  };

  const trocarAba = (id) => {
    setAbaAtiva(id);
    resetForm();
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      {destacarOpcoesRacao && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: escolha a aba e use o formulario{" "}
          <strong>Adicionar novo</strong> para cadastrar as opcoes de classificacao.
        </div>
      )}

      <PageHeader
        icon={Settings}
        title="Opcoes de classificacao de racoes"
        subtitle="Gerencie os valores usados no cadastro de produtos de racao."
        iconClassName="bg-indigo-50 text-indigo-600"
      />

      <Panel padding="sm">
        <div className="overflow-x-auto">
          <SegmentedControl
            ariaLabel="Opcoes de classificacao de racoes"
            className="min-w-max"
            options={abas.map((aba) => ({
              value: aba.id,
              label: <TabLabel aba={aba} />,
            }))}
            onChange={trocarAba}
            size="md"
            value={abaAtiva}
          />
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel
          className={`lg:col-span-1 ${destacarOpcoesRacao ? guiaClasses.box : ""}`}
          title={editando ? "Editar opcao" : "Adicionar novo"}
          subtitle={abaConfig.nome}
        >
          {abaAtiva === "apresentacoes" ? (
            <div className="space-y-4">
              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-peso`}>
                  Peso (kg) *
                </label>
                <input
                  id={`${fieldPrefix}-peso`}
                  name={`${fieldPrefix}_peso`}
                  type="number"
                  step="0.001"
                  value={formPeso.peso_kg}
                  onChange={(event) =>
                    setFormPeso({ ...formPeso, peso_kg: Number(event.target.value || 0) })
                  }
                  className={FIELD_CLASS}
                  placeholder="Ex: 15.0"
                />
              </div>

              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-descricao`}>
                  Descricao
                </label>
                <input
                  id={`${fieldPrefix}-descricao`}
                  name={`${fieldPrefix}_descricao`}
                  type="text"
                  value={formPeso.descricao}
                  onChange={(event) => setFormPeso({ ...formPeso, descricao: event.target.value })}
                  className={FIELD_CLASS}
                  placeholder="Ex: 15kg"
                />
              </div>

              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-ordem`}>
                  Ordem
                </label>
                <input
                  id={`${fieldPrefix}-ordem`}
                  name={`${fieldPrefix}_ordem`}
                  type="number"
                  value={formPeso.ordem}
                  onChange={(event) =>
                    setFormPeso({
                      ...formPeso,
                      ordem: Number.parseInt(event.target.value || "0", 10),
                    })
                  }
                  className={FIELD_CLASS}
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  name={`${fieldPrefix}_ativo`}
                  type="checkbox"
                  checked={formPeso.ativo}
                  onChange={(event) => setFormPeso({ ...formPeso, ativo: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Ativo
              </label>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-nome`}>
                  Nome *
                </label>
                <input
                  id={`${fieldPrefix}-nome`}
                  name={`${fieldPrefix}_nome`}
                  type="text"
                  value={formData.nome}
                  onChange={(event) => setFormData({ ...formData, nome: event.target.value })}
                  className={FIELD_CLASS}
                  placeholder={`Ex: ${
                    abaAtiva === "linhas"
                      ? "Premium"
                      : abaAtiva === "portes"
                        ? "Pequeno"
                        : "Filhote"
                  }`}
                />
              </div>

              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-descricao`}>
                  Descricao
                </label>
                <textarea
                  id={`${fieldPrefix}-descricao`}
                  name={`${fieldPrefix}_descricao`}
                  value={formData.descricao}
                  onChange={(event) => setFormData({ ...formData, descricao: event.target.value })}
                  className={FIELD_CLASS}
                  rows="2"
                  placeholder="Descricao opcional"
                />
              </div>

              <div>
                <label className={LABEL_CLASS} htmlFor={`${fieldPrefix}-ordem`}>
                  Ordem
                </label>
                <input
                  id={`${fieldPrefix}-ordem`}
                  name={`${fieldPrefix}_ordem`}
                  type="number"
                  value={formData.ordem}
                  onChange={(event) =>
                    setFormData({
                      ...formData,
                      ordem: Number.parseInt(event.target.value || "0", 10),
                    })
                  }
                  className={FIELD_CLASS}
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  name={`${fieldPrefix}_ativo`}
                  type="checkbox"
                  checked={formData.ativo}
                  onChange={(event) => setFormData({ ...formData, ativo: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Ativo
              </label>
            </div>
          )}

          <div className="mt-6 flex gap-2">
            <ActionButton
              onClick={handleSalvar}
              className="flex-1 justify-center"
              icon={Save}
              intent={editando ? "edit" : "create"}
              size="md"
            >
              {editando ? "Atualizar" : "Adicionar"}
            </ActionButton>

            {editando && (
              <IconActionButton
                icon={X}
                intent="neutral"
                onClick={resetForm}
                size="md"
                title="Cancelar edicao"
              />
            )}
          </div>
        </Panel>

        <Panel
          className="lg:col-span-2"
          title={`${abaConfig.nome} cadastrados`}
          subtitle={`${dadosAba.length} registro${dadosAba.length === 1 ? "" : "s"}`}
        >
          {loading ? (
            <LoadingState label="Carregando opcoes..." />
          ) : dadosAba.length === 0 ? (
            <EmptyState
              icon={Plus}
              title="Nenhum item cadastrado"
              description="Use o formulario ao lado para adicionar a primeira opcao."
            />
          ) : (
            <div className="space-y-2">
              {dadosAba.map((item) => (
                <div
                  key={item.id}
                  className={[
                    "flex items-center justify-between gap-3 rounded-lg border p-4 transition",
                    editando === item.id
                      ? "border-indigo-500 bg-indigo-50"
                      : "border-slate-200 hover:border-slate-300",
                    !item.ativo ? "opacity-60" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                        <AbaIcon className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold text-slate-900">
                          {abaAtiva === "apresentacoes"
                            ? `${item.peso_kg}kg${item.descricao ? ` - ${item.descricao}` : ""}`
                            : item.nome}
                        </h3>
                        {item.descricao && abaAtiva !== "apresentacoes" ? (
                          <p className="truncate text-sm text-slate-500">{item.descricao}</p>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <span className="hidden text-xs text-slate-500 sm:inline">
                      Ordem: {item.ordem}
                    </span>
                    {!item.ativo ? <StatusBadge status="inativo" /> : null}

                    <IconActionButton
                      icon={Edit2}
                      intent="info"
                      onClick={() => handleEditar(item)}
                      title="Editar"
                    />

                    <IconActionButton
                      icon={Trash2}
                      intent="delete"
                      onClick={() => handleDeletar(item.id)}
                      title="Inativar"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel className="border-blue-200 bg-blue-50">
        <div className="flex items-start gap-3">
          <ChevronRight className="mt-0.5 h-5 w-5 text-blue-600" aria-hidden="true" />
          <div>
            <h3 className="mb-1 font-medium text-blue-900">Dica</h3>
            <p className="text-sm text-blue-800">
              Os valores cadastrados aqui sao usados no cadastro de produtos e na classificacao
              automatica por IA. Mantenha ativos apenas os valores usados no negocio.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}

export default OpcoesRacao;
