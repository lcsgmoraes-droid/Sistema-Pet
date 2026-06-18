import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { CalendarPlus, RefreshCw, Repeat2, StepForward } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import EmptyState from "../../../components/ui/EmptyState";
import { TextField } from "../../../components/ui/FormField";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import PetAvatar from "../../../components/ui/PetAvatar";
import PetIdentity from "../../../components/ui/PetIdentity";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaRetornoCampanhaPanel from "./BanhoTosaRetornoCampanhaPanel";

const prioridadeClasses = {
  critica: "border-red-200 bg-red-50 text-red-700",
  alta: "border-amber-200 bg-amber-50 text-amber-700",
  media: "border-blue-200 bg-blue-50 text-blue-700",
  baixa: "border-slate-200 bg-slate-50 text-slate-600",
};

export default function BanhoTosaRetornosView() {
  const navigate = useNavigate();
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
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar reagendamentos."));
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
    <div className="space-y-4">
      <Panel
        actions={
          <ActionButton
            icon={RefreshCw}
            intent="neutral"
            loading={loading}
            onClick={carregar}
            tone="soft"
          >
            Atualizar
          </ActionButton>
        }
        subtitle="Oportunidades para abrir um novo agendamento a partir de recorrencias, pacotes e pets sem banho recente."
        title="Reagendar clientes"
      >
        <div className="grid gap-3 md:grid-cols-3">
          <TextField
            label="Recorrencias ate"
            type="number"
            value={filtros.dias}
            onChange={(value) => updateFiltro("dias", value)}
          />
          <TextField
            label="Sem banho ha"
            type="number"
            value={filtros.sem_banho_dias}
            onChange={(value) => updateFiltro("sem_banho_dias", value)}
          />
          <TextField
            label="Pacote vence em"
            type="number"
            value={filtros.pacote_vencendo_dias}
            onChange={(value) => updateFiltro("pacote_vencendo_dias", value)}
          />
        </div>
      </Panel>

      <MetricGrid>
        <MetricCard
          icon={<Repeat2 size={18} />}
          intent="blue"
          label="Sugestoes"
          value={itens.length}
        />
        <MetricCard intent="red" label="Criticas" value={resumo.critica} />
        <MetricCard intent="amber" label="Alta prioridade" value={resumo.alta} />
        <MetricCard intent="emerald" label="Pacotes" value={resumo.pacotes} />
      </MetricGrid>

      <BanhoTosaRetornoCampanhaPanel diasAntecedencia={Number(filtros.dias || 30)} />

      <section className="grid gap-3 xl:grid-cols-2">
        {itens.map((item) => (
          <RetornoCard
            key={item.id}
            disabled={processando}
            item={item}
            onAgendar={() => navigate("/banho-tosa/agenda")}
            onAvancar={avancarRecorrencia}
          />
        ))}
        {!itens.length && !loading ? (
          <EmptyState
            className="xl:col-span-2"
            description="Ajuste os filtros ou aguarde novos atendimentos concluirem para gerar oportunidades."
            icon={CalendarPlus}
            title="Nenhuma sugestao para reagendar"
          />
        ) : null}
      </section>
    </div>
  );
}

function RetornoCard({ disabled, item, onAgendar, onAvancar }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <PetAvatar
            alt={item.pet_nome || "Pet"}
            name={item.pet_nome || item.cliente_nome}
            size="md"
            url={item.pet_foto_url}
          />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate text-sm font-semibold text-slate-900">{item.titulo}</h3>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-medium ${prioridadeClasses[item.prioridade] || prioridadeClasses.baixa}`}
              >
                {labelPrioridade(item.prioridade)}
              </span>
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-slate-600">
              <CustomerIdentity
                codeLabel="Cod. tutor"
                fallback={`Tutor #${item.cliente_id || "-"}`}
                layout="inline"
                nameClassName="font-medium text-slate-700"
                record={item}
              />
              {item.pet_nome || item.pet_id ? (
                <>
                  <span>/</span>
                  <PetIdentity
                    fallback={`Pet #${item.pet_id || "-"}`}
                    layout="inline"
                    nameClassName="font-medium text-slate-700"
                    record={item}
                  />
                </>
              ) : null}
            </p>
            <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.mensagem}</p>
          </div>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          {labelTipo(item.tipo)}
        </span>
      </div>

      <div className="mt-3 grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[1fr_auto] sm:items-center">
        <div>
          <p className="text-sm font-medium text-slate-900">{item.acao_sugerida}</p>
          <p className="mt-1 text-xs text-slate-500">
            Ref.: {formatDate(item.data_referencia)} | {formatDias(item.dias_para_acao)}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {item.recorrencia_id ? (
            <ActionButton
              disabled={disabled}
              icon={StepForward}
              intent="edit"
              onClick={() => onAvancar(item)}
              tone="soft"
            >
              Avancar ciclo
            </ActionButton>
          ) : null}
          <ActionButton icon={CalendarPlus} intent="create" onClick={onAgendar}>
            Agendar
          </ActionButton>
        </div>
      </div>
    </article>
  );
}

function montarResumo(itens) {
  return itens.reduce(
    (acc, item) => {
      acc[item.prioridade] = (acc[item.prioridade] || 0) + 1;
      if (String(item.tipo).startsWith("pacote")) acc.pacotes += 1;
      return acc;
    },
    { critica: 0, alta: 0, pacotes: 0 },
  );
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

function labelPrioridade(prioridade) {
  const labels = {
    critica: "Critica",
    alta: "Alta",
    media: "Media",
    baixa: "Baixa",
  };
  return labels[prioridade] || prioridade;
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
