import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";

const initialForm = {
  nome: "",
  tipo: "banheira",
  capacidade_simultanea: "1",
  potencia_watts: "",
  custo_manutencao_hora: "0",
};

export default function BanhoTosaRecursosView({ recursos, onChanged }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function criarRecurso(event) {
    event.preventDefault();
    if (!form.nome.trim()) {
      toast.error("Informe o nome do recurso.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.criarRecurso({
        nome: form.nome.trim(),
        tipo: form.tipo,
        capacidade_simultanea: Number(form.capacidade_simultanea || 1),
        potencia_watts: form.potencia_watts ? toApiDecimal(form.potencia_watts) : null,
        custo_manutencao_hora: toApiDecimal(form.custo_manutencao_hora),
        ativo: true,
      });
      toast.success("Recurso cadastrado.");
      setForm(initialForm);
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel criar o recurso."));
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

  return (
    <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <form
        onSubmit={criarRecurso}
        className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
      >
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
          Capacidade
        </p>
        <h2 className="mt-2 text-xl font-black text-slate-900">
          Novo recurso operacional
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Banheiras, mesas, secadores, boxes e veiculos entram aqui para medir gargalo e custo.
        </p>

        <div className="mt-5 space-y-4">
          <TextField label="Nome" value={form.nome} onChange={(value) => updateField("nome", value)} help="Identificacao do recurso na agenda e nos relatorios de ocupacao." />
          <label className="block">
            <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
              Tipo
              <BanhoTosaHelpTooltip text="Define como o recurso entra na capacidade: banheira, mesa, secador, box ou veiculo." />
            </span>
            <select
              value={form.tipo}
              onChange={(event) => updateField("tipo", event.target.value)}
              className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
            >
              <option value="banheira">Banheira</option>
              <option value="mesa_tosa">Mesa de tosa</option>
              <option value="secador">Secador / soprador</option>
              <option value="box">Sala / box</option>
              <option value="veiculo">Taxi dog / veiculo</option>
              <option value="outro">Outro</option>
            </select>
          </label>
          <TextField label="Capacidade simultanea" type="number" value={form.capacidade_simultanea} onChange={(value) => updateField("capacidade_simultanea", value)} help="Quantidade de pets/atendimentos que o recurso comporta ao mesmo tempo." />
          <TextField label="Potencia watts" type="number" value={form.potencia_watts} onChange={(value) => updateField("potencia_watts", value)} help="Potencia do equipamento para calcular energia por tempo de uso." />
          <TextField label="Manutencao por hora" type="number" value={form.custo_manutencao_hora} onChange={(value) => updateField("custo_manutencao_hora", value)} help="Rateio de troca de escova, limpeza, depreciacao ou manutencao do recurso." />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Salvando..." : "Cadastrar recurso"}
        </button>
      </form>

      <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Recursos
            </p>
            <h2 className="mt-2 text-xl font-black text-slate-900">
              Estrutura da operacao
            </h2>
          </div>
          <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
            {recursos.length} itens
          </span>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {recursos.map((recurso) => (
            <div key={recurso.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-black text-slate-900">{recurso.nome}</p>
                  <p className="text-sm capitalize text-slate-500">{recurso.tipo}</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleAtivo(recurso)}
                  className={`rounded-full px-3 py-1 text-xs font-bold ${
                    recurso.ativo
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {recurso.ativo ? "Ativo" : "Inativo"}
                </button>
              </div>
              <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
                <MiniMetric label="Cap." value={recurso.capacidade_simultanea} />
                <MiniMetric label="Watts" value={recurso.potencia_watts || "-"} />
                <MiniMetric label="Manut." value={recurso.custo_manutencao_hora || "0"} />
              </div>
            </div>
          ))}
          {recursos.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500 md:col-span-2">
              Nenhum recurso cadastrado ainda.
            </div>
          )}
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
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function MiniMetric({ label, value }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </p>
      <p className="font-black text-slate-900">{value}</p>
    </div>
  );
}
