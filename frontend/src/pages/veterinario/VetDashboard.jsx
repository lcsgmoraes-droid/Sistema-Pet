import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, Calendar, Syringe, BedDouble, TrendingUp, Plus, AlertCircle, Download, Link2 } from "lucide-react";
import { vetApi } from "./vetApi";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

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
  const [calendarioMeta, setCalendarioMeta] = useState(null);
  const [mensagemCalendario, setMensagemCalendario] = useState("");

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

        vetApi
          .obterCalendarioAgendaMeta()
          .then((res) => setCalendarioMeta(res.data || null))
          .catch(() => setCalendarioMeta(null));
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

  async function baixarCalendarioAgenda() {
    try {
      setMensagemCalendario("");
      const resposta = await vetApi.baixarCalendarioAgendaIcs();
      const blob = new Blob([resposta.data], { type: "text/calendar;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "agenda-veterinaria.ics";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Erro ao baixar calendario veterinario", e);
      setMensagemCalendario("Nao foi possivel baixar o calendario agora.");
    }
  }

  async function copiarLinkCalendario() {
    if (!calendarioMeta?.feed_url) return;
    try {
      await navigator.clipboard.writeText(calendarioMeta.feed_url);
      setMensagemCalendario("Link privado copiado para assinar a agenda no celular.");
    } catch (e) {
      console.error("Erro ao copiar link do calendario", e);
      setMensagemCalendario("Nao foi possivel copiar o link automaticamente.");
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

      <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-cyan-900">Agenda no celular</h2>
            <p className="mt-1 text-sm text-cyan-800">
              Use um link privado para assinar sua agenda veterinaria no Google Calendar, Apple Calendar ou Outlook.
            </p>
            {calendarioMeta?.mensagem_escopo && (
              <p className="mt-2 text-xs text-cyan-700">{calendarioMeta.mensagem_escopo}</p>
            )}
            {mensagemCalendario && (
              <p className="mt-2 text-xs font-medium text-cyan-700">{mensagemCalendario}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={baixarCalendarioAgenda}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100"
            >
              <Download size={14} />
              Baixar .ics
            </button>
            <button
              type="button"
              onClick={copiarLinkCalendario}
              disabled={!calendarioMeta?.feed_url}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Link2 size={14} />
              Copiar link privado
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 lg:col-span-3">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-700">Financeiro de procedimentos (30d)</h3>
              <p className="text-xs text-gray-400">Baseado nos insumos realmente vinculados em cada procedimento.</p>
            </div>
            <span className="text-xs font-semibold rounded-full px-2 py-1 bg-emerald-50 text-emerald-700">
              Margem {formatPercent(dados?.margem_percentual_procedimentos_30d ?? 0)}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <ResumoFinanceiroCard titulo="Faturamento" valor={dados?.faturamento_procedimentos_30d ?? 0} cor="text-blue-700" />
            <ResumoFinanceiroCard titulo="Custo" valor={dados?.custo_procedimentos_30d ?? 0} cor="text-amber-700" />
            <ResumoFinanceiroCard titulo="Margem" valor={dados?.margem_procedimentos_30d ?? 0} cor={(dados?.margem_procedimentos_30d ?? 0) < 0 ? "text-red-600" : "text-emerald-700"} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
            <ResumoFinanceiroCard
              titulo={dados?.modelo_operacional_financeiro === "parceiro" ? "Repasse empresa" : "Entrada empresa"}
              valor={
                dados?.modelo_operacional_financeiro === "parceiro"
                  ? dados?.repasse_empresa_procedimentos_30d ?? 0
                  : dados?.entrada_empresa_procedimentos_30d ?? 0
              }
              cor="text-sky-700"
            />
            <ResumoFinanceiroCard
              titulo={dados?.modelo_operacional_financeiro === "parceiro" ? "Líquido veterinário" : "Comissão empresa"}
              valor={
                dados?.modelo_operacional_financeiro === "parceiro"
                  ? dados?.receita_tenant_procedimentos_30d ?? 0
                  : dados?.comissao_empresa_pct_padrao ?? 0
              }
              cor="text-violet-700"
              percentual={dados?.modelo_operacional_financeiro !== "parceiro"}
            />
          </div>
        </div>

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
            <div key={`${item.nome}-${idx}`} className="rounded-lg border border-gray-100 px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-gray-700 truncate">{item.nome}</span>
                <span className="text-xs font-semibold text-blue-700 bg-blue-50 rounded-full px-2 py-0.5">
                  {item.quantidade}
                </span>
              </div>
              {item.valor_total != null && (
                <div className="grid grid-cols-3 gap-2 mt-2 text-[11px]">
                  <span className="text-gray-500">Fat. {formatMoneyBRL(item.valor_total)}</span>
                  <span className="text-amber-700">Custo {formatMoneyBRL(item.custo_total || 0)}</span>
                  <span className={(item.margem_total || 0) < 0 ? "text-red-600" : "text-emerald-700"}>
                    Margem {formatMoneyBRL(item.margem_total || 0)}
                  </span>
                </div>
              )}
              {item.entrada_empresa_total != null && (
                <div className="grid grid-cols-3 gap-2 mt-2 text-[11px]">
                  <span className="text-sky-700">Empresa {formatMoneyBRL(item.entrada_empresa_total || 0)}</span>
                  <span className="text-violet-700">Repasse {formatMoneyBRL(item.repasse_empresa_total || 0)}</span>
                  <span className="text-gray-500">Líquido vet {formatMoneyBRL(item.receita_tenant_total || 0)}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResumoFinanceiroCard({ titulo, valor, cor, percentual = false }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-gray-400">{titulo}</p>
      <p className={`text-2xl font-bold mt-1 ${cor}`}>{percentual ? formatPercent(valor) : formatMoneyBRL(valor)}</p>
    </div>
  );
}
