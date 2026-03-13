import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, Calendar, Syringe, BedDouble, TrendingUp, Plus, AlertCircle } from "lucide-react";
import { vetApi } from "./vetApi";

const statusColor = {
  aguardando: "bg-yellow-100 text-yellow-800",
  em_atendimento: "bg-blue-100 text-blue-800",
  finalizado: "bg-green-100 text-green-800",
  cancelado: "bg-gray-100 text-gray-600",
};

const statusLabel = {
  aguardando: "Aguardando",
  em_atendimento: "Em atendimento",
  finalizado: "Finalizado",
  cancelado: "Cancelado",
};

export default function VetDashboard() {
  const navigate = useNavigate();
  const [dados, setDados] = useState(null);
  const [relatorio, setRelatorio] = useState(null);
  const [agendamentos, setAgendamentos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    async function carregar() {
      try {
        setCarregando(true);
        setErro(null);
        const hoje = new Date().toISOString().slice(0, 10);
        const [dashRes, agRes, relRes] = await Promise.allSettled([
          vetApi.dashboard(),
          vetApi.listarAgendamentos({ data_inicio: hoje, data_fim: hoje }),
          vetApi.relatorioClinico({ dias: 30, top: 5 }),
        ]);

        if (dashRes.status !== "fulfilled" || agRes.status !== "fulfilled") {
          throw new Error("Falha ao carregar dados principais do painel veterinário.");
        }

        setDados(dashRes.value.data);
        setAgendamentos(agRes.value.data?.items ?? agRes.value.data ?? []);

        if (relRes.status === "fulfilled") {
          setRelatorio(relRes.value.data);
        } else {
          console.warn("Relatório clínico indisponível no momento", relRes.reason);
          setRelatorio(null);
        }
      } catch (e) {
        console.error("Erro ao carregar painel veterinário", e);
        setErro("Não foi possível carregar o painel veterinário.");
      } finally {
        setCarregando(false);
      }
    }
    carregar();
  }, []);

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (erro) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertCircle size={20} />
          <span>{erro}</span>
        </div>
      </div>
    );
  }

  const cards = [
    {
      label: "Consultas hoje",
      valor: dados?.consultas_hoje ?? 0,
      icon: Calendar,
      cor: "from-blue-500 to-blue-600",
    },
    {
      label: "Em atendimento",
      valor: dados?.em_atendimento ?? 0,
      icon: Stethoscope,
      cor: "from-green-500 to-green-600",
    },
    {
      label: "Internados",
      valor: dados?.internados ?? 0,
      icon: BedDouble,
      cor: "from-purple-500 to-purple-600",
    },
    {
      label: "Vacinas vencendo (30d)",
      valor: dados?.vacinas_vencendo_30d ?? 0,
      icon: Syringe,
      cor: "from-orange-500 to-orange-600",
    },
    {
      label: "Consultas este mês",
      valor: dados?.consultas_mes ?? 0,
      icon: TrendingUp,
      cor: "from-teal-500 to-teal-600",
    },
    {
      label: "Retornos pendentes",
      valor: dados?.retornos_pendentes ?? 0,
      icon: AlertCircle,
      cor: "from-rose-500 to-rose-600",
    },
    {
      label: "Taxa de retorno (30d)",
      valor: `${dados?.taxa_retorno_30d ?? 0}%`,
      icon: TrendingUp,
      cor: "from-indigo-500 to-indigo-600",
    },
    {
      label: "Tempo médio de atendimento",
      valor: `${dados?.tempo_medio_atendimento_min ?? 0} min`,
      icon: Stethoscope,
      cor: "from-cyan-500 to-cyan-600",
    },
  ];

  async function exportarCsvRelatorio() {
    try {
      setExportando(true);
      const resposta = await vetApi.exportarRelatorioClinicoCsv({ dias: 30, top: 5 });
      const blob = new Blob([resposta.data], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "relatorio_clinico_veterinario_30d.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Erro ao exportar relatório clínico", e);
      setErro("Não foi possível exportar o relatório clínico.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-xl">
            <Stethoscope size={24} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Painel Veterinário</h1>
            <p className="text-sm text-gray-500">Visão geral do dia</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportarCsvRelatorio}
            disabled={exportando}
            className="bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
          >
            {exportando ? "Exportando..." : "Exportar relatório (CSV)"}
          </button>
          <button
            onClick={() => navigate("/veterinario/consultas/nova")}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            Nova consulta
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-4">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div
              key={c.label}
              className={`bg-gradient-to-br ${c.cor} rounded-xl p-4 text-white shadow-sm`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon size={20} className="opacity-80" />
              </div>
              <p className="text-3xl font-bold">{c.valor}</p>
              <p className="text-xs opacity-80 mt-1">{c.label}</p>
            </div>
          );
        })}
      </div>

      {/* Agenda do dia */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-700 flex items-center gap-2">
            <Calendar size={16} />
            Agenda de hoje
          </h2>
          <button
            onClick={() => navigate("/veterinario/agenda")}
            className="text-sm text-blue-600 hover:underline"
          >
            Ver completa →
          </button>
        </div>

        {agendamentos.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            Nenhum agendamento para hoje.
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {agendamentos.slice(0, 10).map((ag) => (
              <button
                key={ag.id}
                type="button"
                className="flex w-full items-center gap-4 px-5 py-3 text-left hover:bg-gray-50 transition-colors"
                onClick={() => {
                  if (ag.consulta_id) navigate(`/veterinario/consultas/${ag.consulta_id}`);
                  else navigate("/veterinario/agenda");
                }}
              >
                <span className="text-sm font-mono text-gray-500 w-12">
                  {ag.data_hora?.slice(11, 16)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}
                  </p>
                  <p className="text-xs text-gray-400 truncate">{ag.motivo ?? "—"}</p>
                </div>
                {ag.emergencia && (
                  <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                    <AlertCircle size={10} />
                    Emergência
                  </span>
                )}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    statusColor[ag.status] ?? "bg-gray-100 text-gray-600"
                  }`}
                >
                  {statusLabel[ag.status] ?? ag.status}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {renderTopListCard(
          "Top diagnósticos (30d)",
          relatorio?.top_diagnosticos ?? [],
          "Sem diagnósticos registrados no período.",
        )}
        {renderTopListCard(
          "Top procedimentos (30d)",
          relatorio?.top_procedimentos ?? [],
          "Sem procedimentos registrados no período.",
        )}
        {renderTopListCard(
          "Top medicamentos (30d)",
          relatorio?.top_medicamentos ?? [],
          "Sem medicamentos prescritos no período.",
        )}
      </div>

      {/* Atalhos rápidos */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Agenda", path: "/veterinario/agenda", icon: Calendar },
          { label: "Vacinas a vencer", path: "/veterinario/vacinas", icon: Syringe },
          { label: "Internações", path: "/veterinario/internacoes", icon: BedDouble },
          { label: "Catálogos", path: "/veterinario/catalogo", icon: TrendingUp },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
            >
              <Icon size={18} className="text-blue-500" />
              <span className="text-sm font-medium text-gray-700">{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function renderTopListCard(title, itens, vazio) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      {itens.length === 0 ? (
        <p className="text-xs text-gray-400">{vazio}</p>
      ) : (
        <div className="space-y-2">
          {itens.map((item, idx) => (
            <div key={`${item.nome}-${idx}`} className="flex items-center justify-between gap-3">
              <span className="text-sm text-gray-700 truncate">{item.nome}</span>
              <span className="text-xs font-semibold text-blue-700 bg-blue-50 rounded-full px-2 py-0.5">
                {item.quantidade}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
