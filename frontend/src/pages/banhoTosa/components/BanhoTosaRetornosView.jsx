import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaRetornoCampanhaPanel from "./BanhoTosaRetornoCampanhaPanel";

const prioridadeClasses = {
  critica: "bg-rose-100 text-rose-700",
  alta: "bg-orange-100 text-orange-700",
  media: "bg-sky-100 text-sky-700",
  baixa: "bg-slate-100 text-slate-600",
};

export default function BanhoTosaRetornosView() {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [filtros, setFiltros] = useState({
    dias: "30",
    sem_banho_dias: "45",
    pacote_vencendo_dias: "15",
  });

  async function carregar() {
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarRetornosSugestoes({
        dias: Number(filtros.dias || 30),
        sem_banho_dias: Number(filtros.sem_banho_dias || 45),
        pacote_vencendo_dias: Number(filtros.pacote_vencendo_dias || 15),
        limit: 300,
      });
      setItens(Array.isArray(response.data?.itens) ? response.data.itens : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar retornos."));
      setItens([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function updateFiltro(field, value) {
    setFiltros((prev) => ({ ...prev, [field]: value }));
  }

  async function avancarRecorrencia(item) {
    if (!item.recorrencia_id) return;
    setProcessando(true);
    try {
      await banhoTosaApi.avancarRetornoRecorrencia(item.recorrencia_id, {});
      toast.success("Recorrencia avancada para o proximo ciclo.");
      await carregar();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel avancar a recorrencia."));
    } finally {
      setProcessando(false);
    }
  }

  const resumo = montarResumo(itens);

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Retencao
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">
              Central de retornos
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Sugestoes geradas por recorrencia, pacote vencendo/saldo baixo e pets sem banho recente.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <NumberField label="Recorrencias ate" value={filtros.dias} onChange={(value) => updateFiltro("dias", value)} />
            <NumberField label="Sem banho ha" value={filtros.sem_banho_dias} onChange={(value) => updateFiltro("sem_banho_dias", value)} />
            <NumberField label="Pacote vence em" value={filtros.pacote_vencendo_dias} onChange={(value) => updateFiltro("pacote_vencendo_dias", value)} />
            <button type="button" onClick={carregar} className="self-end rounded-2xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-700">
              {loading ? "Carregando..." : "Atualizar"}
            </button>
          </div>
        </div>
      </section>

      <BanhoTosaRetornoCampanhaPanel diasAntecedencia={Number(filtros.dias || 30)} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Total" value={itens.length} />
        <Metric label="Criticos" value={resumo.critica} />
        <Metric label="Alta prioridade" value={resumo.alta} />
        <Metric label="Pacotes" value={resumo.pacotes} />
      </div>

      <section className="grid gap-4 xl:grid-cols-2">
        {itens.map((item) => (
          <RetornoCard
            key={item.id}
            item={item}
            disabled={processando}
            onAvancar={avancarRecorrencia}
          />
        ))}
        {!itens.length && (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 xl:col-span-2">
            Nenhum retorno sugerido com os filtros atuais.
          </div>
        )}
      </section>
    </div>
  );
}

function RetornoCard({ item, disabled, onAvancar }) {
  return (
    <article className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${prioridadeClasses[item.prioridade] || prioridadeClasses.baixa}`}>
            {item.prioridade}
          </span>
          <h3 className="mt-3 text-lg font-black text-slate-900">{item.titulo}</h3>
          <p className="mt-1 text-sm font-semibold text-slate-500">
            {item.cliente_nome || `Tutor #${item.cliente_id}`} {item.pet_nome ? `| ${item.pet_nome}` : ""}
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
          {labelTipo(item.tipo)}
        </span>
      </div>
      <p className="mt-4 text-sm text-slate-600">{item.mensagem}</p>
      <p className="mt-2 text-sm font-bold text-slate-900">{item.acao_sugerida}</p>
      <p className="mt-2 text-xs font-semibold text-slate-400">
        Ref.: {formatDate(item.data_referencia)} | {formatDias(item.dias_para_acao)}
      </p>
      {item.recorrencia_id && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAvancar(item)}
          className="mt-4 rounded-2xl bg-orange-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
        >
          Avancar recorrencia
        </button>
      )}
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-900">{value || 0}</p>
    </div>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function montarResumo(itens) {
  return itens.reduce((acc, item) => {
    acc[item.prioridade] = (acc[item.prioridade] || 0) + 1;
    if (String(item.tipo).startsWith("pacote")) acc.pacotes += 1;
    return acc;
  }, { critica: 0, alta: 0, pacotes: 0 });
}

function labelTipo(tipo) {
  const labels = {
    recorrencia: "Recorrencia",
    pacote_vencendo: "Pacote vencendo",
    pacote_saldo_baixo: "Saldo baixo",
    sem_banho: "Sem banho",
  };
  return labels[tipo] || tipo;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

function formatDias(value) {
  if (value === null || value === undefined) return "sem prazo";
  if (value < 0) return `${Math.abs(value)} dia(s) atrasado`;
  if (value === 0) return "hoje";
  return `em ${value} dia(s)`;
}
