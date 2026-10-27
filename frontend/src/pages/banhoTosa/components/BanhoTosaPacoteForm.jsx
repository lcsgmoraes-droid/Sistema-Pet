import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputMoeda from "../../../components/v2/InputMoeda/InputMoeda";
import InputQuantidade from "../../../components/v2/InputQuantidade/InputQuantidade";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";

const novoServico = () => ({ servico_id: "", quantidade_creditos: 4 });
const initialForm = () => ({
  nome: "",
  descricao: "",
  servicos: [novoServico()],
  validade_dias: 30,
  preco: 0,
  ativo: true,
});

function formFromPacote(pacote) {
  const servicos = pacote.servicos?.length
    ? pacote.servicos
    : [
        {
          servico_id: pacote.servico_id,
          quantidade_creditos: pacote.quantidade_creditos,
        },
      ];
  return {
    nome: pacote.nome || "",
    descricao: pacote.descricao || "",
    servicos: servicos.map((item) => ({
      servico_id: item.servico_id ? String(item.servico_id) : "",
      quantidade_creditos: Number(item.quantidade_creditos || 1),
    })),
    validade_dias: Number(pacote.validade_dias || 30),
    preco: Number(pacote.preco || 0),
    ativo: Boolean(pacote.ativo),
  };
}

export default function BanhoTosaPacoteForm({
  servicos = [],
  editingPacote,
  onCancelEdit,
  onChanged,
}) {
  const [form, setForm] = useState(() =>
    editingPacote ? formFromPacote(editingPacote) : initialForm(),
  );
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setForm(editingPacote ? formFromPacote(editingPacote) : initialForm());
  }, [editingPacote]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }
  function atualizarServico(index, field, value) {
    setForm((prev) => ({
      ...prev,
      servicos: prev.servicos.map((item, i) => (i === index ? { ...item, [field]: value } : item)),
    }));
  }

  async function salvar(event) {
    event.preventDefault();
    if (!form.nome.trim()) return toast.error("Informe o nome do pacote.");
    if (form.servicos.some((item) => !item.servico_id || !(Number(item.quantidade_creditos) > 0))) {
      return toast.error("Informe o serviço e a quantidade de cada item do pacote.");
    }
    if (
      new Set(form.servicos.map((item) => String(item.servico_id))).size !== form.servicos.length
    ) {
      return toast.error("Cada serviço deve aparecer uma única vez no pacote.");
    }
    if (
      !Number.isInteger(Number(form.validade_dias)) ||
      Number(form.validade_dias) < 1 ||
      Number(form.validade_dias) > 3650
    ) {
      return toast.error("Informe uma validade de 1 a 3650 dias inteiros.");
    }
    setSaving(true);
    try {
      const payload = {
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || null,
        servicos: form.servicos.map((item) => ({
          servico_id: Number(item.servico_id),
          quantidade_creditos: toApiDecimal(item.quantidade_creditos, "1"),
        })),
        quantidade_creditos: toApiDecimal(
          form.servicos.reduce((total, item) => total + Number(item.quantidade_creditos), 0),
        ),
        validade_dias: Number(form.validade_dias),
        preco: toApiDecimal(form.preco),
        ativo: form.ativo,
      };
      if (editingPacote) await banhoTosaApi.atualizarPacote(editingPacote.id, payload);
      else await banhoTosaApi.criarPacote(payload);
      toast.success(editingPacote ? "Pacote atualizado." : "Pacote cadastrado.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível salvar o pacote."));
    } finally {
      setSaving(false);
    }
  }

  const opcoes = servicos
    .filter(
      (item) =>
        (item.ativo && item.permite_pacote) ||
        form.servicos.some((selecionado) => Number(selecionado.servico_id) === item.id),
    )
    .map((item) => ({ value: String(item.id), label: item.nome }));
  return (
    <Panel
      title={editingPacote ? "Editar pacote" : "Novo pacote"}
      subtitle="Defina os serviços e as quantidades incluídas. Novas contratações recebem estas condições."
    >
      <form onSubmit={salvar} className="space-y-4">
        <InputTexto
          id="bt-pacote-nome"
          label="Nome"
          required
          value={form.nome}
          onChange={(value) => updateField("nome", value)}
        />
        <InputTexto
          id="bt-pacote-descricao"
          label="Descrição"
          value={form.descricao}
          onChange={(value) => updateField("descricao", value)}
        />
        <div className="space-y-3">
          {form.servicos.map((item, index) => (
            <div
              key={index}
              className="grid items-end gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700 sm:grid-cols-[1fr_7rem_auto]"
            >
              <InputCombobox
                id={`bt-pacote-servico-${index}`}
                label="Serviço incluído"
                required
                opcoes={opcoes}
                value={item.servico_id}
                onChange={(value) => atualizarServico(index, "servico_id", value)}
              />
              <InputQuantidade
                id={`bt-pacote-quantidade-${index}`}
                label="Quantidade"
                min={1}
                required
                value={item.quantidade_creditos}
                onChange={(value) => atualizarServico(index, "quantidade_creditos", value)}
              />
              <BotaoInteracao
                icon={Trash2}
                tamanho="pequeno"
                disabled={form.servicos.length === 1}
                onClick={() =>
                  updateField(
                    "servicos",
                    form.servicos.filter((_, i) => i !== index),
                  )
                }
              >
                Remover
              </BotaoInteracao>
            </div>
          ))}
          <BotaoInteracao
            icon={Plus}
            tamanho="pequeno"
            onClick={() => updateField("servicos", [...form.servicos, novoServico()])}
          >
            Adicionar serviço
          </BotaoInteracao>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <InputQuantidade
            id="bt-pacote-validade"
            label="Validade em dias"
            min={1}
            required
            value={form.validade_dias}
            onChange={(value) => updateField("validade_dias", value)}
          />
          <InputMoeda
            id="bt-pacote-preco"
            label="Preço do pacote"
            value={form.preco}
            onChange={(value) => updateField("preco", value)}
          />
        </div>
        {editingPacote && (
          <InputCheck
            id="bt-pacote-ativo"
            label="Ativo"
            checked={form.ativo}
            onChange={(value) => updateField("ativo", value)}
          />
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <BotaoCancelar onClick={onCancelEdit} disabled={saving} />
          <BotaoSalva loading={saving}>
            {editingPacote ? "Salvar alterações" : "Cadastrar pacote"}
          </BotaoSalva>
        </div>
      </form>
    </Panel>
  );
}
