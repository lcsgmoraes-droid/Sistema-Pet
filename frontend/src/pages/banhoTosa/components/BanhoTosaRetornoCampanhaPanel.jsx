import { useEffect, useState } from "react";
import toast from "react-hot-toast";
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
      <div className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-orange-500">
          Campanhas
        </p>
        <h3 className="mt-2 text-lg font-black text-slate-900">
          Disparo de retorno
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Use template padrao ou selecione uma mensagem segmentada por tipo de retorno.
        </p>

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
          <button
            type="button"
            disabled={enfileirando}
            onClick={enfileirarCampanha}
            className="self-end rounded-2xl bg-slate-900 px-4 py-3 text-sm font-bold text-white disabled:opacity-60"
          >
            {enfileirando ? "Enfileirando..." : "Enfileirar"}
          </button>
        </div>
      </div>

      <form onSubmit={criarTemplate} className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
          Novo template
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <InputField label="Nome" value={form.nome} onChange={(value) => updateForm("nome", value)} required />
          <SelectField label="Tipo" value={form.tipo_retorno} onChange={(value) => updateForm("tipo_retorno", value)}>
            {tipos.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </SelectField>
          <SelectField label="Canal" value={form.canal} onChange={(value) => updateForm("canal", value)}>
            {canais.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </SelectField>
          <InputField label="Assunto" value={form.assunto} onChange={(value) => updateForm("assunto", value)} required />
        </div>
        <label className="mt-3 block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Mensagem</span>
          <textarea
            required
            rows={3}
            value={form.mensagem}
            onChange={(event) => updateForm("mensagem", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          />
        </label>
        <p className="mt-2 text-xs text-slate-400">
          Variaveis: {"{cliente_nome}"}, {"{pet_nome}"}, {"{servico_nome}"}, {"{pacote_nome}"}, {"{data_referencia}"}, {"{dias_para_acao}"}.
        </p>
        <button
          type="submit"
          disabled={salvando}
          className="mt-4 rounded-2xl bg-orange-500 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
        >
          {salvando ? "Salvando..." : "Salvar template"}
        </button>
      </form>
    </section>
  );
}

function InputField({ label, value, onChange, required = false }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function SelectField({ label, value, onChange, children, disabled = false }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <select
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100 disabled:opacity-60"
      >
        {children}
      </select>
    </label>
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
