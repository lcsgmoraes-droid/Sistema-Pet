import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaCustoPanel from "./BanhoTosaCustoPanel";
import BanhoTosaFechamentoPanel from "./BanhoTosaFechamentoPanel";
import BanhoTosaInsumosPanel from "./BanhoTosaInsumosPanel";
import BanhoTosaOcorrenciasPanel from "./BanhoTosaOcorrenciasPanel";
import BanhoTosaPacoteUsoPanel from "./BanhoTosaPacoteUsoPanel";
import BanhoTosaVetAlertas from "./BanhoTosaVetAlertas";

const initialForm = {
  tipo: "banho",
  responsavel_id: "",
  recurso_id: "",
  observacoes: "",
};

export default function BanhoTosaAtendimentoPanel({ atendimentoId, funcionarios, recursos, onChanged }) {
  const [atendimento, setAtendimento] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [custoRefreshSignal, setCustoRefreshSignal] = useState(0);

  async function carregarAtendimento() {
    if (!atendimentoId) return;
    setLoading(true);
    try {
      const response = await banhoTosaApi.obterAtendimento(atendimentoId);
      setAtendimento(response.data || null);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar atendimento."));
      setAtendimento(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregarAtendimento();
  }, [atendimentoId]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function iniciarEtapa(event) {
    event.preventDefault();
    if (!atendimentoId) return;

    setSaving(true);
    try {
      await banhoTosaApi.iniciarEtapa(atendimentoId, {
        tipo: form.tipo,
        responsavel_id: form.responsavel_id ? Number(form.responsavel_id) : null,
        recurso_id: form.recurso_id ? Number(form.recurso_id) : null,
        observacoes: form.observacoes || null,
      });
      toast.success("Etapa iniciada.");
      setForm(initialForm);
      await carregarAtendimento();
      await onChanged(true);
      setCustoRefreshSignal((prev) => prev + 1);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel iniciar etapa."));
    } finally {
      setSaving(false);
    }
  }

  async function finalizarEtapa(etapa) {
    try {
      await banhoTosaApi.finalizarEtapa(atendimentoId, etapa.id, {});
      toast.success("Etapa finalizada.");
      await carregarAtendimento();
      await onChanged(true);
      setCustoRefreshSignal((prev) => prev + 1);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel finalizar etapa."));
    }
  }

  if (!atendimentoId) {
    return (
      <div className="rounded-3xl border border-white/80 bg-white p-6 text-sm text-slate-500 shadow-sm">
        Selecione um atendimento da fila para ver etapas, recursos e tempos.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-3xl border border-white/80 bg-white p-6 text-sm font-semibold text-slate-500 shadow-sm">
        Carregando atendimento...
      </div>
    );
  }

  if (!atendimento) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Ficha operacional
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        {atendimento.pet_nome || `Pet #${atendimento.pet_id}`}
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Tutor: {atendimento.cliente_nome || `#${atendimento.cliente_id}`} | Status: {atendimento.status}
      </p>
      <BanhoTosaVetAlertas perfil={atendimento.perfil_comportamental_snapshot} restricoes={atendimento.restricoes_veterinarias_snapshot} />
      <BanhoTosaPacoteUsoPanel
        atendimento={atendimento}
        onChanged={async () => {
          await carregarAtendimento();
          await onChanged(true);
        }}
      />
      <BanhoTosaFechamentoPanel atendimento={atendimento} onChanged={carregarAtendimento} />

      <form onSubmit={iniciarEtapa} className="mt-6 grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1.2fr_auto]">
        <SelectField label="Etapa" value={form.tipo} onChange={(value) => updateField("tipo", value)}>
          <option value="banho">Banho</option>
          <option value="secagem">Secagem</option>
          <option value="tosa">Tosa</option>
          <option value="higiene">Higiene</option>
          <option value="preparo">Preparo</option>
        </SelectField>
        <SelectField label="Responsavel" value={form.responsavel_id} onChange={(value) => updateField("responsavel_id", value)}>
          <option value="">Sem responsavel</option>
          {funcionarios.map((pessoa) => (
            <option key={pessoa.id} value={pessoa.id}>
              {pessoa.nome}
            </option>
          ))}
        </SelectField>
        <SelectField label="Recurso" value={form.recurso_id} onChange={(value) => updateField("recurso_id", value)}>
          <option value="">Sem recurso</option>
          {recursos.filter((item) => item.ativo).map((recurso) => (
            <option key={recurso.id} value={recurso.id}>
              {recurso.nome}
            </option>
          ))}
        </SelectField>
        <TextField label="Observacoes" value={form.observacoes} onChange={(value) => updateField("observacoes", value)} />
        <button
          type="submit"
          disabled={saving}
          className="self-end rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Iniciando..." : "Iniciar"}
        </button>
      </form>

      <div className="mt-6 space-y-3">
        {(atendimento.etapas || []).map((etapa) => (
          <div key={etapa.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="font-black capitalize text-slate-900">{etapa.tipo}</p>
                <p className="text-sm text-slate-500">
                  Resp.: {etapa.responsavel_nome || "nao informado"} | Recurso: {etapa.recurso_nome || "nao informado"} | Duracao: {etapa.duracao_minutos ?? "-"} min
                </p>
                {etapa.observacoes && (
                  <p className="mt-1 text-sm text-slate-600">{etapa.observacoes}</p>
                )}
              </div>
              {!etapa.fim_em ? (
                <button
                  type="button"
                  onClick={() => finalizarEtapa(etapa)}
                  className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-emerald-600"
                >
                  Finalizar etapa
                </button>
              ) : (
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
                  Finalizada
                </span>
              )}
            </div>
          </div>
        ))}
        {(!atendimento.etapas || atendimento.etapas.length === 0) && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
            Nenhuma etapa registrada ainda.
          </div>
        )}
      </div>

      <BanhoTosaInsumosPanel
        atendimentoId={atendimentoId}
        funcionarios={funcionarios}
        onChanged={async () => {
          await onChanged(true);
          setCustoRefreshSignal((prev) => prev + 1);
        }}
      />

      <BanhoTosaOcorrenciasPanel
        atendimentoId={atendimentoId}
        funcionarios={funcionarios}
        onChanged={carregarAtendimento}
      />

      <BanhoTosaCustoPanel atendimentoId={atendimentoId} refreshSignal={custoRefreshSignal} />
    </div>
  );
}

function SelectField({ label, value, onChange, children }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      >
        {children}
      </select>
    </label>
  );
}

function TextField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
