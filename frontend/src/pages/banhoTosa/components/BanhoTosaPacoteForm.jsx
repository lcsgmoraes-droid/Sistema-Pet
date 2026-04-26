import { useEffect, useState } from "react";
import toast from "react-hot-toast";
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
    <form onSubmit={salvar} className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Pacotes
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        {editingPacote ? "Editar pacote" : "Novo pacote"}
      </h2>

      <div className="mt-5 space-y-4">
        <TextField label="Nome" value={form.nome} onChange={(value) => updateField("nome", value)} />
        <TextField label="Descricao" value={form.descricao} onChange={(value) => updateField("descricao", value)} />
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Servico coberto</span>
          <select
            value={form.servico_id}
            onChange={(event) => updateField("servico_id", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          >
            <option value="">Qualquer servico do atendimento</option>
            {servicosDisponiveis.map((servico) => (
              <option key={servico.id} value={servico.id}>
                {servico.nome}
              </option>
            ))}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <TextField label="Creditos" type="number" value={form.quantidade_creditos} onChange={(value) => updateField("quantidade_creditos", value)} />
          <TextField label="Validade dias" type="number" value={form.validade_dias} onChange={(value) => updateField("validade_dias", value)} />
          <TextField label="Preco" type="number" value={form.preco} onChange={(value) => updateField("preco", value)} />
        </div>
        {editingPacote && (
          <CheckField label="Ativo" checked={form.ativo} onChange={(value) => updateField("ativo", value)} />
        )}
      </div>

      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Salvando..." : editingPacote ? "Salvar alteracoes" : "Cadastrar pacote"}
        </button>
        {editingPacote && (
          <button
            type="button"
            onClick={onCancelEdit}
            className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-orange-300 hover:text-orange-700"
          >
            Cancelar edicao
          </button>
        )}
      </div>
    </form>
  );
}

function TextField({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        type={type}
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function CheckField({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-orange-500"
      />
      {label}
    </label>
  );
}
