import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";

const initialForm = {
  nome: "",
  categoria: "banho",
  descricao: "",
  duracao_padrao_minutos: "60",
  requer_banho: true,
  requer_tosa: false,
  requer_secagem: true,
  permite_pacote: true,
  ativo: true,
};

export default function BanhoTosaServicosView({ servicos, onChanged }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function criarServico(event) {
    event.preventDefault();
    if (!form.nome.trim()) {
      toast.error("Informe o nome do servico.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.criarServico({
        ...form,
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || null,
        duracao_padrao_minutos: Number(form.duracao_padrao_minutos || 60),
      });
      toast.success("Servico criado.");
      setForm(initialForm);
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel criar o servico."));
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

  return (
    <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <form
        onSubmit={criarServico}
        className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
      >
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
          Catalogo
        </p>
        <h2 className="mt-2 text-xl font-black text-slate-900">
          Novo servico
        </h2>

        <div className="mt-5 space-y-4">
          <TextField label="Nome" value={form.nome} onChange={(value) => updateField("nome", value)} help="Nome que aparece na agenda, na fila e no fechamento para o PDV." />
          <label className="block">
            <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
              Categoria
              <BanhoTosaHelpTooltip text="Agrupa servicos para relatorios e filtros: banho, tosa, combo, higiene ou outro." />
            </span>
            <select
              value={form.categoria}
              onChange={(event) => updateField("categoria", event.target.value)}
              className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
            >
              <option value="banho">Banho</option>
              <option value="tosa">Tosa</option>
              <option value="combo">Combo</option>
              <option value="higiene">Higiene</option>
              <option value="outro">Outro</option>
            </select>
          </label>
          <TextField label="Duracao padrao (min)" type="number" value={form.duracao_padrao_minutos} onChange={(value) => updateField("duracao_padrao_minutos", value)} help="Tempo usado para prever fim do agendamento e ocupacao da equipe." />
          <TextField label="Descricao" value={form.descricao} onChange={(value) => updateField("descricao", value)} help="Explique o que esta incluso para padronizar a venda e o atendimento." />

          <div className="grid gap-2 sm:grid-cols-2">
            <CheckField label="Requer banho" checked={form.requer_banho} onChange={(value) => updateField("requer_banho", value)} help="Marca se o servico consome agua, shampoo e etapa de banho." />
            <CheckField label="Requer tosa" checked={form.requer_tosa} onChange={(value) => updateField("requer_tosa", value)} help="Marca se precisa de tosador, mesa ou etapa de tosa." />
            <CheckField label="Requer secagem" checked={form.requer_secagem} onChange={(value) => updateField("requer_secagem", value)} help="Marca se deve considerar secador/soprador no tempo e energia." />
            <CheckField label="Permite pacote" checked={form.permite_pacote} onChange={(value) => updateField("permite_pacote", value)} help="Permite vender creditos recorrentes desse servico." />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Salvando..." : "Cadastrar servico"}
        </button>
      </form>

      <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Servicos
            </p>
            <h2 className="mt-2 text-xl font-black text-slate-900">
              Lista operacional
            </h2>
          </div>
          <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
            {servicos.length} itens
          </span>
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Servico</th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3">Duracao</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {servicos.map((servico) => (
                <tr key={servico.id}>
                  <td className="px-4 py-3 font-bold text-slate-900">{servico.nome}</td>
                  <td className="px-4 py-3 text-slate-600">{servico.categoria}</td>
                  <td className="px-4 py-3 text-slate-600">{servico.duracao_padrao_minutos} min</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => toggleAtivo(servico)}
                      className={`rounded-full px-3 py-1 text-xs font-bold ${
                        servico.ativo
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {servico.ativo ? "Ativo" : "Inativo"}
                    </button>
                  </td>
                </tr>
              ))}
              {servicos.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={4}>
                    Nenhum servico cadastrado ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TextField({ label, value, onChange, type = "text", help }) {
  return (
    <label className="block">
      <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
        <BanhoTosaHelpTooltip text={help} />
      </span>
      <input
        type={type}
        title={help || label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function CheckField({ label, checked, onChange, help }) {
  return (
    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700" title={help || label}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-orange-500"
      />
      {label}
      <BanhoTosaHelpTooltip text={help} />
    </label>
  );
}
