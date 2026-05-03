import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Save, Send } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { SelectField, TextField } from "../../../components/ui/FormField";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";

const formInicial = {
  nome: "",
  tipo_retorno: "todos",
  canal: "app",
  assunto: "Retorno de {pet_nome}",
  mensagem: "Ola {cliente_nome}, {pet_nome} tem uma sugestao de retorno: {acao_sugerida}",
  ativo: true,
};

const tipos = [
  ["todos", "Todos"],
  ["recorrencia", "Recorrencia"],
  ["pacote_vencendo", "Pacote vencendo"],
  ["pacote_saldo_baixo", "Saldo baixo"],
  ["sem_banho", "Sem banho"],
];

const canais = [
  ["app", "App"],
  ["email", "E-mail"],
];

export default function BanhoTosaRetornoCampanhaPanel({ diasAntecedencia }) {
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState("");
  const [canal, setCanal] = useState("app");
  const [form, setForm] = useState(formInicial);
  const [salvando, setSalvando] = useState(false);
  const [enfileirando, setEnfileirando] = useState(false);

  async function carregarTemplates() {
    try {
      const response = await banhoTosaApi.listarRetornoTemplates({ ativos_only: true });
      setTemplates(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar templates."));
    }
  }

  useEffect(() => {
    carregarTemplates();
  }, []);

  function updateForm(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function selecionarTemplate(value) {
    const escolhido = templates.find((item) => String(item.id) === String(value));
    setTemplateId(value);
    if (escolhido) setCanal(escolhido.canal);
  }

  async function criarTemplate(event) {
    event.preventDefault();
    setSalvando(true);
    try {
      const response = await banhoTosaApi.criarRetornoTemplate(form);
      toast.success("Template de retorno criado.");
      setTemplates((prev) => [...prev, response.data].sort((a, b) => a.nome.localeCompare(b.nome)));
      setTemplateId(String(response.data.id));
      setCanal(response.data.canal);
      setForm(formInicial);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel criar o template."));
    } finally {
      setSalvando(false);
    }
  }

  async function enfileirarCampanha() {
    setEnfileirando(true);
    try {
      const response = await banhoTosaApi.enfileirarNotificacoesRetorno({
        tipos: [],
        dias_antecedencia: Number(diasAntecedencia || 30),
        limit: 200,
        canal,
        template_id: templateId ? Number(templateId) : null,
      });
      const data = response.data || {};
      const semDestino = data.sem_destino ? `, ${data.sem_destino} sem destino` : "";
      toast.success(`${data.enfileirados || 0} retorno(s) enfileirado(s)${semDestino}.`);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel enfileirar a campanha."));
    } finally {
      setEnfileirando(false);
    }
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <Panel
        subtitle="Use template padrao ou selecione uma mensagem segmentada por tipo de retorno."
        title="Disparo de retorno"
      >
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <SelectField label="Template" value={templateId} onChange={selecionarTemplate}>
            <option value="">Padrao automatico</option>
            {templates.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nome} - {labelTipo(item.tipo_retorno)}
              </option>
            ))}
          </SelectField>
          <SelectField label="Canal" value={canal} onChange={setCanal} disabled={Boolean(templateId)}>
            {canais.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </SelectField>
          <ActionButton
            type="button"
            className="self-end"
            icon={Send}
            intent="edit"
            loading={enfileirando}
            onClick={enfileirarCampanha}
          >
            Enfileirar
          </ActionButton>
        </div>
      </Panel>

      <Panel title="Novo template">
        <form onSubmit={criarTemplate}>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <TextField label="Nome" value={form.nome} onChange={(value) => updateForm("nome", value)} required />
            <SelectField label="Tipo" value={form.tipo_retorno} onChange={(value) => updateForm("tipo_retorno", value)}>
              {tipos.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </SelectField>
            <SelectField label="Canal" value={form.canal} onChange={(value) => updateForm("canal", value)}>
              {canais.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </SelectField>
            <TextField label="Assunto" value={form.assunto} onChange={(value) => updateForm("assunto", value)} required />
          </div>
          <label className="mt-3 block">
            <span className="text-xs font-medium text-slate-600">Mensagem</span>
            <textarea
              required
              rows={3}
              value={form.mensagem}
              onChange={(event) => updateForm("mensagem", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
            />
          </label>
          <p className="mt-2 text-xs text-slate-400">
            Variaveis: {"{cliente_nome}"}, {"{pet_nome}"}, {"{servico_nome}"}, {"{pacote_nome}"}, {"{data_referencia}"}, {"{dias_para_acao}"}.
          </p>
          <ActionButton
            type="submit"
            className="mt-4"
            icon={Save}
            intent="create"
            loading={salvando}
          >
            Salvar template
          </ActionButton>
        </form>
      </Panel>
    </section>
  );
}

function labelTipo(tipo) {
  const labels = {
    todos: "Todos",
    recorrencia: "Recorrencia",
    pacote_vencendo: "Pacote vencendo",
    pacote_saldo_baixo: "Saldo baixo",
    sem_banho: "Sem banho",
  };
  return labels[tipo] || tipo;
}
