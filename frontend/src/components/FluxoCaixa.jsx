import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  RefreshCw,
  Brain,
  AlertTriangle,
  Sparkles,
  Landmark,
} from "lucide-react";
import ChatIAModal from "./ChatIAModal";
import ProjecoesIA from "./ProjecoesIA";
import AlertasIA from "./AlertasIA";
import { safeArray } from "../utils/safeArray";
import ActionButton from "./ui/ActionButton";
import DataTable from "./ui/DataTable";
import LoadingState from "./ui/LoadingState";
import MetricCard from "./ui/MetricCard";
import MetricGrid from "./ui/MetricGrid";
import MoneyCell, { formatMoneyCellValue } from "./ui/MoneyCell";
import ModuleTabs from "./ui/ModuleTabs";
import PageHeader from "./ui/PageHeader";
import StatusBadge from "./ui/StatusBadge";

const FLUXO_CAIXA_TABS = [
  {
    id: "movimentacoes",
    label: (
      <span className="inline-flex items-center gap-2">
        <DollarSign className="h-5 w-5" />
        Movimentações
      </span>
    ),
  },
  {
    id: "projecoes",
    label: (
      <span className="inline-flex items-center gap-2">
        <Brain className="h-5 w-5" />
        Projeções IA
        <Sparkles className="h-4 w-4" />
      </span>
    ),
  },
  {
    id: "alertas",
    label: (
      <span className="inline-flex items-center gap-2">
        <AlertTriangle className="h-5 w-5" />
        Alertas IA
        <Sparkles className="h-4 w-4" />
      </span>
    ),
  },
];

const FluxoCaixa = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);

  // Tabs
  const [tabAtiva, setTabAtiva] = useState("movimentacoes"); // movimentacoes, projecoes, alertas

  // Modal Chat IA
  const [chatIAAberto, setChatIAAberto] = useState(false);

  // Filtros
  const obterDataLocal = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const dia = String(hoje.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  };

  const obterPrimeiroDiaMes = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    return `${ano}-${mes}-01`;
  };

  const [filtros, setFiltros] = useState({
    data_inicio: obterPrimeiroDiaMes(), // Primeiro dia do mês
    data_fim: obterDataLocal(), // Dia atual
    conta_bancaria_id: null,
    agrupamento: "dia", // dia, semana, mes
  });

  // Novos filtros de tipo
  const [filtroTipo, setFiltroTipo] = useState("todos"); // todos, entradas, saidas
  const [filtroStatus, setFiltroStatus] = useState("todos"); // todos, realizado, previsto

  const [contasBancarias, setContasBancarias] = useState([]);
  const [periodoExpandido, setPeriodoExpandido] = useState(null);
  const [apenasComLancamentos, setApenasComLancamentos] = useState(false);
  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState("");

  useEffect(() => {
    carregarContasBancarias();
    carregarFluxoCaixa();
  }, []);

  const carregarContasBancarias = async () => {
    try {
      const response = await api.get(`/contas-bancarias`);
      setContasBancarias(response.data);
    } catch (error) {
      console.error("Erro ao carregar contas bancárias:", error);
    }
  };

  const carregarFluxoCaixa = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
        agrupamento: filtros.agrupamento,
      });

      if (filtros.conta_bancaria_id) {
        params.append("conta_bancaria_id", filtros.conta_bancaria_id);
      }

      // Adicionar filtro de número de venda se preenchido
      if (buscaNumeroVenda) {
        params.append("numero_venda", buscaNumeroVenda);
      }

      const response = await api.get(`/financeiro/fluxo-caixa?${params}`);

      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar fluxo de caixa:", error);
      toast.error(
        `Erro ao carregar fluxo de caixa: ${error.response?.data?.detail || error.message}`,
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodoPreset = (preset) => {
    const hoje = new Date();
    let inicio, fim;

    switch (preset) {
      case "7dias":
        inicio = new Date(hoje.setDate(hoje.getDate() - 7));
        fim = new Date();
        break;
      case "30dias":
        inicio = new Date(hoje.setDate(hoje.getDate() - 30));
        fim = new Date();
        break;
      case "mes_atual":
        inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
        break;
      case "proximo_mes":
        inicio = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
        fim = new Date(hoje.getFullYear(), hoje.getMonth() + 2, 0);
        break;
      default:
        return;
    }

    const novosFiltros = {
      ...filtros,
      data_inicio: inicio.toISOString().split("T")[0],
      data_fim: fim.toISOString().split("T")[0],
    };

    setFiltros(novosFiltros);

    // Recarregar dados com novos filtros
    setTimeout(() => carregarFluxoCaixa(), 100);
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const movimentoEhEntrada = (tipo) => {
    return ["entrada", "credito", "crédito"].includes(String(tipo || "").toLowerCase());
  };

  const movimentoEhSaida = (tipo) => {
    return ["saida", "saída", "debito", "débito"].includes(String(tipo || "").toLowerCase());
  };

  const getMovimentacoesDoPeriodo = (periodo) => {
    if (!dados) return [];

    return dados.movimentacoes.filter((mov) => {
      const dataMovFormatada = new Date(mov.data);
      const dataInicio = new Date(periodo.data_inicio);
      const dataFim = new Date(periodo.data_fim);
      const dentroDataPeriodo = dataMovFormatada >= dataInicio && dataMovFormatada <= dataFim;

      if (!dentroDataPeriodo) return false;

      // Filtro por tipo (entrada/saída)
      if (filtroTipo === "entradas" && !movimentoEhEntrada(mov.tipo)) return false;
      if (filtroTipo === "saidas" && !movimentoEhSaida(mov.tipo)) return false;

      // Filtro por status (realizado/previsto)
      if (filtroStatus === "realizado" && mov.status !== "realizado") return false;
      if (filtroStatus === "previsto" && mov.status !== "previsto") return false;

      // Filtro por busca de número de venda
      if (buscaNumeroVenda) {
        const descricao = mov.descricao || "";
        const numeroVenda = mov.numero_venda || "";
        const busca = buscaNumeroVenda.toLowerCase();

        return numeroVenda.toLowerCase().includes(busca) || descricao.toLowerCase().includes(busca);
      }

      return true;
    });
  };

  const periodosFluxo = safeArray(dados?.periodos).filter((periodo) => {
    if (!apenasComLancamentos) return true;
    return (
      periodo.realizado_entradas > 0 ||
      periodo.realizado_saidas > 0 ||
      periodo.previsto_entradas > 0 ||
      periodo.previsto_saidas > 0
    );
  });

  const fluxoColumns = [
    {
      key: "periodo",
      header: "Periodo",
      className: "font-medium text-gray-900",
      render: (periodo) => periodo.data,
    },
    {
      key: "previsto_entradas",
      header: "Entradas previstas",
      align: "right",
      className: "bg-green-50 text-gray-700",
      render: (periodo) => <MoneyCell value={periodo.previsto_entradas} zeroAsDash />,
    },
    {
      key: "realizado_entradas",
      header: "Entradas realizadas",
      align: "right",
      className: "bg-green-100 font-bold text-green-700",
      render: (periodo) => <MoneyCell value={periodo.realizado_entradas} zeroAsDash />,
    },
    {
      key: "previsto_saidas",
      header: "Saidas previstas",
      align: "right",
      className: "bg-red-50 text-gray-700",
      render: (periodo) => <MoneyCell value={periodo.previsto_saidas} zeroAsDash />,
    },
    {
      key: "realizado_saidas",
      header: "Saidas realizadas",
      align: "right",
      className: "bg-red-100 font-bold text-red-700",
      render: (periodo) => <MoneyCell value={periodo.realizado_saidas} zeroAsDash />,
    },
    {
      key: "saldo_realizado",
      header: "Saldo realizado",
      align: "right",
      className: (periodo) =>
        `bg-blue-50 font-bold ${periodo.realizado_saldo >= 0 ? "text-green-700" : "text-red-700"}`,
      render: (periodo) => <MoneyCell value={periodo.realizado_saldo} zeroAsDash />,
    },
    {
      key: "saldo_previsto",
      header: "Saldo previsto",
      align: "right",
      className: (periodo) =>
        `bg-blue-50 ${periodo.previsto_saldo >= 0 ? "text-green-600" : "text-red-600"}`,
      render: (periodo) => <MoneyCell value={periodo.previsto_saldo} zeroAsDash />,
    },
    {
      key: "acoes",
      header: "",
      align: "right",
      render: (periodo) => {
        const periodoId = periodo.data;
        const isExpandido = periodoExpandido === periodoId;
        const movimentacoes = getMovimentacoesDoPeriodo(periodo);

        return (
          <ActionButton
            intent="neutral"
            tone="ghost"
            size="xs"
            disabled={movimentacoes.length === 0}
            onClick={() => setPeriodoExpandido(isExpandido ? null : periodoId)}
          >
            {isExpandido ? "Ocultar" : "Detalhes"}
          </ActionButton>
        );
      },
    },
  ];

  if (loading && !dados) {
    return <LoadingState className="min-h-screen" label="Carregando fluxo de caixa..." />;
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              onClick={() => navigate("/financeiro/ajuste-saldos")}
              intent="neutral"
              tone="soft"
              size="md"
              icon={Landmark}
            >
              Ajustar saldos
            </ActionButton>
            <ActionButton
              onClick={() => setChatIAAberto(true)}
              intent="neutral"
              tone="soft"
              size="md"
              icon={Brain}
            >
              Chat IA
            </ActionButton>
          </>
        }
        icon={DollarSign}
        subtitle="Previsto vs realizado, com lançamentos automáticos de contas a pagar e receber"
        title="Fluxo de Caixa"
      />

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        {/* Campo de busca por número de venda */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            🔢 Buscar por Número da Venda
          </label>
          <input
            type="text"
            placeholder="Digite o número da venda (ex: 202601100007) e pressione Enter"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            value={buscaNumeroVenda}
            onChange={(e) => setBuscaNumeroVenda(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                carregarFluxoCaixa();
              }
            }}
          />
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Visualização</label>
            <select
              value={filtros.agrupamento}
              onChange={(e) => setFiltros({ ...filtros, agrupamento: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="dia">📅 Diário</option>
              <option value="semana">📊 Semanal</option>
              <option value="mes">📈 Mensal</option>
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Movimentação
            </label>
            <select
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="todos">📊 Todas</option>
              <option value="entradas">💰 Apenas Entradas</option>
              <option value="saidas">💸 Apenas Saídas</option>
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="todos">📋 Todos</option>
              <option value="realizado">✅ Apenas Realizados</option>
              <option value="previsto">📅 Apenas Previstos</option>
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Início</label>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Fim</label>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Conta Bancária</label>
            <select
              value={filtros.conta_bancaria_id || ""}
              onChange={(e) =>
                setFiltros({ ...filtros, conta_bancaria_id: e.target.value || null })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todas as Contas</option>
              {safeArray(contasBancarias).map((conta) => (
                <option key={conta.id} value={conta.id}>
                  {conta.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end gap-2">
            <ActionButton onClick={carregarFluxoCaixa} intent="neutral" icon={RefreshCw} size="md">
              Atualizar
            </ActionButton>
          </div>
        </div>

        {/* Banner de Filtros Ativos */}
        {(filtroTipo !== "todos" || filtroStatus !== "todos") && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-blue-800 font-medium">🔍 Filtros ativos:</span>
              {filtroTipo !== "todos" && (
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {filtroTipo === "entradas" ? "💰 Apenas Entradas" : "💸 Apenas Saídas"}
                </span>
              )}
              {filtroStatus !== "todos" && (
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {filtroStatus === "realizado" ? "✅ Apenas Realizados" : "📅 Apenas Previstos"}
                </span>
              )}
            </div>
            <ActionButton
              onClick={() => {
                setFiltroTipo("todos");
                setFiltroStatus("todos");
              }}
              intent="neutral"
              tone="ghost"
              size="sm"
            >
              Limpar filtros
            </ActionButton>
          </div>
        )}

        {/* Presets rápidos */}
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          <ActionButton
            onClick={() => handlePeriodoPreset("7dias")}
            intent="neutral"
            tone="soft"
            size="xs"
          >
            Últimos 7 dias
          </ActionButton>
          <ActionButton
            onClick={() => handlePeriodoPreset("30dias")}
            intent="neutral"
            tone="soft"
            size="xs"
          >
            Últimos 30 dias
          </ActionButton>
          <ActionButton
            onClick={() => handlePeriodoPreset("mes_atual")}
            intent="neutral"
            tone="soft"
            size="xs"
          >
            Mês Atual
          </ActionButton>
          <ActionButton
            onClick={() => handlePeriodoPreset("proximo_mes")}
            intent="neutral"
            tone="soft"
            size="xs"
          >
            Próximo Mês
          </ActionButton>

          <div className="ml-auto flex items-center gap-2 bg-blue-50 px-3 py-2 rounded border border-blue-200">
            <input
              type="checkbox"
              id="apenasComLancamentos"
              checked={apenasComLancamentos}
              onChange={(e) => setApenasComLancamentos(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
            <label
              htmlFor="apenasComLancamentos"
              className="text-sm font-medium text-blue-700 cursor-pointer"
            >
              📊 Apenas dias com lançamentos
            </label>
          </div>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <ModuleTabs
          active={tabAtiva}
          ariaLabel="Abas do fluxo de caixa"
          className="px-4 pt-2"
          onChange={setTabAtiva}
          tabs={FLUXO_CAIXA_TABS}
        />
      </div>

      {/* Conteúdo das Tabs */}
      {tabAtiva === "projecoes" && <ProjecoesIA />}

      {tabAtiva === "alertas" && <AlertasIA />}

      {tabAtiva === "movimentacoes" && dados && (
        <>
          {/* Cards de Resumo */}
          <MetricGrid>
            <MetricCard
              intent="blue"
              icon={<DollarSign className="h-5 w-5" />}
              label="Saldo Inicial"
              value={<MoneyCell value={dados.saldo_inicial} zeroAsDash />}
            />

            <MetricCard
              intent="emerald"
              icon={<TrendingUp className="h-5 w-5" />}
              label="Total Realizado (Entradas)"
              value={<MoneyCell value={dados.total_realizado_entradas} zeroAsDash />}
              subtitle={`Previsto: ${formatarMoeda(dados.total_previsto_entradas)}`}
            />

            <MetricCard
              intent="red"
              icon={<TrendingDown className="h-5 w-5" />}
              label="Total Realizado (Saidas)"
              value={<MoneyCell value={dados.total_realizado_saidas} zeroAsDash />}
              subtitle={`Previsto: ${formatarMoeda(dados.total_previsto_saidas)}`}
            />

            <MetricCard
              intent={dados.saldo_final >= 0 ? "blue" : "red"}
              icon={<DollarSign className="h-5 w-5" />}
              label="Saldo Final Realizado"
              value={<MoneyCell value={dados.saldo_final} zeroAsDash />}
              subtitle={`Previsto: ${formatarMoeda(dados.saldo_previsto_final)}`}
            />
          </MetricGrid>

          {/* Tabela de fluxo */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <DataTable
              columns={fluxoColumns}
              data={periodosFluxo}
              emptyMessage="Nenhuma movimentação encontrada para o período selecionado"
              getRowKey={(periodo) => periodo.data}
              isRowExpanded={(periodo) =>
                periodoExpandido === periodo.data && getMovimentacoesDoPeriodo(periodo).length > 0
              }
              renderExpandedRow={(periodo, _rowIndex, colSpan) => {
                const movimentacoes = getMovimentacoesDoPeriodo(periodo);
                return (
                  <tr className="bg-gray-50">
                    <td colSpan={colSpan} className="px-4 py-4">
                      <div className="space-y-2">
                        <h4 className="font-bold text-gray-700">Movimentações detalhadas</h4>
                        {safeArray(movimentacoes).map((mov, movIdx) => (
                          <div
                            key={`${mov.id || mov.descricao || "mov"}-${movIdx}`}
                            className={`flex items-center justify-between gap-3 rounded border-l-2 p-2 ${
                              mov.status === "previsto"
                                ? "border-yellow-400 bg-yellow-50"
                                : "border-blue-400 bg-white"
                            }`}
                          >
                            <div className="min-w-0 flex-1">
                              <span className="font-medium">{mov.descricao}</span>
                              <span className="ml-2 text-xs text-gray-500">({mov.categoria})</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <StatusBadge
                                status={mov.status === "previsto" ? "pendente" : "recebido"}
                                size="xs"
                              >
                                {mov.status === "previsto" ? "Previsto" : "Realizado"}
                              </StatusBadge>
                              <span
                                className={`font-bold ${movimentoEhEntrada(mov.tipo) ? "text-green-600" : "text-red-600"}`}
                              >
                                <MoneyCell
                                  value={mov.valor}
                                  sign={movimentoEhEntrada(mov.tipo) ? "+" : "-"}
                                  absolute
                                />
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              }}
              tableClassName="min-w-[1080px]"
              theadClassName="bg-gray-50"
              tbodyClassName="divide-y divide-gray-200 bg-white"
            />
          </div>
        </>
      )}

      <ChatIAModal
        isOpen={chatIAAberto}
        onClose={() => setChatIAAberto(false)}
        contexto={{
          tipo: "Fluxo de Caixa",
          filtros,
          dados,
        }}
      />

      {/* Fluxo de Caixa é apenas visualização - lançamentos vêm de Contas a Pagar/Receber */}
    </div>
  );
};

export default FluxoCaixa;
