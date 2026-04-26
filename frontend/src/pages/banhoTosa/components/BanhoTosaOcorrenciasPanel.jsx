import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaFotosPanel from "./BanhoTosaFotosPanel";

const initialOcorrencia = {
  tipo: "observacao",
  gravidade: "baixa",
  descricao: "",
  responsavel_id: "",
};

export default function BanhoTosaOcorrenciasPanel({
  atendimentoId,
  funcionarios,
  onChanged,
}) {
  const [ocorrencias, setOcorrencias] = useState([]);
  const [ocorrenciaForm, setOcorrenciaForm] = useState(initialOcorrencia);
  const [saving, setSaving] = useState(false);

  async function carregarDados() {
    if (!atendimentoId) return;
    try {
      const ocorrenciasRes = await banhoTosaApi.listarOcorrenciasAtendimento(atendimentoId);
      setOcorrencias(Array.isArray(ocorrenciasRes.data) ? ocorrenciasRes.data : []);
    } catch {
      setOcorrencias([]);
    }
  }

  useEffect(() => {
    carregarDados();
  }, [atendimentoId]);

  function updateOcorrencia(field, value) {
    setOcorrenciaForm((prev) => ({ ...prev, [field]: value }));
  }

  async function salvarOcorrencia(event) {
    event.preventDefault();
    if (!ocorrenciaForm.descricao.trim()) {
      toast.error("Descreva a ocorrencia.");
      return;
    }
    setSaving(true);
    try {
      await banhoTosaApi.registrarOcorrenciaAtendimento(atendimentoId, {
        ...ocorrenciaForm,
        responsavel_id: ocorrenciaForm.responsavel_id ? Number(ocorrenciaForm.responsavel_id) : null,
      });
      toast.success("Ocorrencia registrada.");
      setOcorrenciaForm(initialOcorrencia);
      await carregarDados();
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel registrar ocorrencia."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-6 grid gap-4 xl:grid-cols-2">
      <section className="rounded-3xl border border-slate-200 bg-white p-5">
        <Header eyebrow="Ocorrencias" title="Registro do atendimento" />
        <form onSubmit={salvarOcorrencia} className="mt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <SelectField label="Tipo" value={ocorrenciaForm.tipo} onChange={(value) => updateOcorrencia("tipo", value)}>
              <option value="observacao">Observacao</option>
              <option value="comportamento">Comportamento</option>
              <option value="saude">Saude</option>
              <option value="acidente">Acidente</option>
            </SelectField>
            <SelectField label="Gravidade" value={ocorrenciaForm.gravidade} onChange={(value) => updateOcorrencia("gravidade", value)}>
              <option value="baixa">Baixa</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
            </SelectField>
            <SelectField label="Responsavel" value={ocorrenciaForm.responsavel_id} onChange={(value) => updateOcorrencia("responsavel_id", value)}>
              <option value="">Nao informado</option>
              {funcionarios.map((pessoa) => (
                <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>
              ))}
            </SelectField>
          </div>
          <textarea
            value={ocorrenciaForm.descricao}
            onChange={(event) => updateOcorrencia("descricao", event.target.value)}
            rows={3}
            placeholder="Ex.: pet chegou com no no pelo, apresentou medo do secador, pequena irritacao encontrada..."
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          />
          <button
            type="submit"
            disabled={saving}
            className="rounded-2xl bg-slate-900 px-5 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
          >
            Registrar ocorrencia
          </button>
        </form>
        <ListaOcorrencias ocorrencias={ocorrencias} />
      </section>

      <BanhoTosaFotosPanel atendimentoId={atendimentoId} onChanged={onChanged} />
    </div>
  );
}

function Header({ eyebrow, title }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">{eyebrow}</p>
      <h3 className="mt-2 text-lg font-black text-slate-900">{title}</h3>
    </div>
  );
}

function ListaOcorrencias({ ocorrencias }) {
  if (ocorrencias.length === 0) {
    return <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">Nenhuma ocorrencia registrada ainda.</p>;
  }
  return (
    <div className="mt-4 space-y-2">
      {ocorrencias.map((item) => (
        <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-black uppercase tracking-[0.14em] text-orange-500">
            {item.tipo} | {item.gravidade}
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-700">{item.descricao}</p>
          {item.responsavel_nome && <p className="mt-1 text-xs text-slate-400">Resp.: {item.responsavel_nome}</p>}
        </div>
      ))}
    </div>
  );
}

function SelectField({ label, value, onChange, children }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100">
        {children}
      </select>
    </label>
  );
}

function TextField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input type="text" value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100" />
    </label>
  );
}
