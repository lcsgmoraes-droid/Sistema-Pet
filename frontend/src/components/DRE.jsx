import {
  Brain,
  CheckCircle,
  DollarSign,
  Download,
  FileText,
  Info,
  MessageCircle,
  Percent,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import AnaliseInteligente from "./AnaliseInteligente";
import ChatIAModal from "./ChatIAModal";
import ClassificarLancamentosModal from "./ClassificarLancamentosModal";
import ExtratoBancario from "./ExtratoBancario";
import { actionButtonClasses } from "./ui/actionStyles";
import MetricCard from "./ui/MetricCard";
import MetricGrid from "./ui/MetricGrid";
import MoneyCell, { formatMoneyCellValue } from "./ui/MoneyCell";
import ModuleTabs from "./ui/ModuleTabs";
import NumberCell from "./ui/NumberCell";

const DRE_REQUEST_TIMEOUT_MS = 120000;

const DRE_TABS = [
  {
    id: "demonstrativo",
    label: (
      <span className="inline-flex items-center gap-2">
        <FileText size={18} />
        Demonstrativo
      </span>
    ),
  },
  {
    id: "extrato",
    label: (
      <span className="inline-flex items-center gap-2">
        <Upload size={18} />
        Extrato Bancário
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-bold text-green-700">
          IA
        </span>
      </span>
    ),
  },
  {
    id: "analise",
    label: (
      <span className="inline-flex items-center gap-2">
        <Brain size={18} />
        Análise Inteligente
        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-700">
          EM BREVE
        </span>
      </span>
    ),
  },
];

const DRE = () => {
  // Controle de tabs
  const [tabAtiva, setTabAtiva] = useState("demonstrativo"); // demonstrativo, extrato, analise

  // Modal Chat IA
  const [chatIAAberto, setChatIAAberto] = useState(false);

  // Modal Classificar DRE
  const [modalClassificarOpen, setModalClassificarOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);
  const [linhaDetalhe, setLinhaDetalhe] = useState(null);
  const [detalhesLinha, setDetalhesLinha] = useState(null);
  const [loadingDetalhes, setLoadingDetalhes] = useState(false);
  const dreAbortRef = useRef(null);
  const dreRequestIdRef = useRef(0);

  // Canais de venda (ABA 7)
  const [canaisDisponiveis] = useState([
    { id: "loja_fisica", nome: "Loja Física", cor: "blue" },
    { id: "mercado_livre", nome: "Mercado Livre", cor: "yellow" },
    { id: "shopee", nome: "Shopee", cor: "orange" },
    { id: "amazon", nome: "Amazon", cor: "green" },
    { id: "ecommerce", nome: "E-commerce", cor: "purple" },
    { id: "app", nome: "App", cor: "indigo" },
  ]);
  const [canaisSelecionados, setCanaisSelecionados] = useState(["loja_fisica"]); // Loja Física por padrão

  // Filtros
  const obterDataLocal = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    return `${ano}-${mes}`;
  };

  const [periodo, setPeriodo] = useState(obterDataLocal());

  const normalizarPeriodo = (valor) => {
    if (typeof valor === "string" && /^\d{4}-\d{2}$/.test(valor)) {
      return valor;
    }
    return periodo || obterDataLocal();
  };

  const carregarDRE = async (periodoAlvo = periodo) => {
    const requestId = dreRequestIdRef.current + 1;
    dreRequestIdRef.current = requestId;
    dreAbortRef.current?.abort?.();
    const controller = new AbortController();
    dreAbortRef.current = controller;
    setLoading(true);
    try {
      const [ano, mes] = normalizarPeriodo(periodoAlvo).split("-");

      // Enviar os canais selecionados para o backend
      const canaisParam = canaisSelecionados.join(",");

      const response = await api.get(`/financeiro/dre/canais`, {
        params: { ano, mes, canais: canaisParam },
        timeout: DRE_REQUEST_TIMEOUT_MS,
        signal: controller.signal,
      });

      if (requestId === dreRequestIdRef.current) {
        setDados(response.data);
      }
    } catch (error) {
      if (error.code === "ERR_CANCELED" || error.name === "CanceledError") {
        return;
      }
      console.error("Erro ao carregar DRE:", error);
      if (requestId === dreRequestIdRef.current) {
        toast.error(
          "Erro ao carregar DRE: " +
            (error.response?.data?.detail || error.message),
        );
      }
    } finally {
      if (requestId === dreRequestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const formatarPercentual = (valor) => {
    return `${(valor || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  };

  const formatarData = (valor) => {
    if (!valor) return "-";
    const data = new Date(`${valor}T00:00:00`);
    if (Number.isNaN(data.getTime())) return valor;
    return data.toLocaleDateString("pt-BR");
  };

  const calcularPercentual = (valor, total) => {
    if (!total || total === 0) return 0;
    return (valor / total) * 100;
  };

  const fecharDetalhesLinha = () => {
    setLinhaDetalhe(null);
    setDetalhesLinha(null);
    setLoadingDetalhes(false);
  };

  const abrirDetalhesLinha = async (linha, page = 1) => {
    if (!linha?.detalhavel || !linha?.campo || !linha?.canal) return;

    setLinhaDetalhe(linha);
    setLoadingDetalhes(true);
    try {
      const [ano, mes] = normalizarPeriodo(periodo).split("-");
      const response = await api.get(`/financeiro/dre/canais/detalhes`, {
        params: {
          ano,
          mes,
          canal: linha.canal,
          campo: linha.campo,
          page,
          page_size: 30,
        },
        timeout: DRE_REQUEST_TIMEOUT_MS,
      });
      setDetalhesLinha(response.data);
    } catch (error) {
      console.error("Erro ao carregar detalhes da DRE:", error);
      toast.error(
        "Erro ao carregar detalhes: " +
          (error.response?.data?.detail || error.message),
      );
    } finally {
      setLoadingDetalhes(false);
    }
  };

  // Funções para gerenciar canais
  const toggleCanal = (canalId) => {
    setCanaisSelecionados((prev) => {
      const novosCanais = prev.includes(canalId)
        ? prev.filter((id) => id !== canalId)
        : [...prev, canalId];

      return novosCanais;
    });
  };

  const limparSelecaoCanais = () => {
    setCanaisSelecionados([]);
  };

  useEffect(() => {
    const timer = window.setTimeout(() => carregarDRE(periodo), 300);
    return () => clearTimeout(timer);
  }, [periodo, canaisSelecionados]);

  useEffect(
    () => () => {
      dreAbortRef.current?.abort?.();
    },
    [],
  );

  const handlePeriodoPreset = (preset) => {
    const hoje = new Date();
    let novaData;

    switch (preset) {
      case "mes_atual":
        novaData = obterDataLocal();
        break;
      case "mes_anterior":
        const mesPassado = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
        novaData = `${mesPassado.getFullYear()}-${String(mesPassado.getMonth() + 1).padStart(2, "0")}`;
        break;
      case "ano_atual":
        novaData = `${hoje.getFullYear()}-01`;
        break;
      default:
        return;
    }

    setPeriodo(novaData);
  };

  const exportarPDF = async () => {
    try {
      const [ano, mes] = normalizarPeriodo(periodo).split("-");
      toast.loading("Gerando PDF...", { id: "pdf" });

      const response = await api.get(`/financeiro/dre/export/pdf`, {
        params: { ano, mes },
        responseType: "blob",
        timeout: DRE_REQUEST_TIMEOUT_MS,
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `dre_${mes}_${ano}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success("ðŸ“„ PDF exportado com sucesso!", { id: "pdf" });
    } catch (error) {
      console.error("Erro ao exportar PDF:", error);
      toast.error("Erro ao exportar PDF", { id: "pdf" });
    }
  };

  const exportarExcel = async () => {
    try {
      const [ano, mes] = normalizarPeriodo(periodo).split("-");
      toast.loading("Gerando Excel...", { id: "excel" });

      const response = await api.get(`/financeiro/dre/export/excel`, {
        params: { ano, mes },
        responseType: "blob",
        timeout: DRE_REQUEST_TIMEOUT_MS,
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `dre_${mes}_${ano}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success("ðŸ“Š Excel exportado com sucesso!", { id: "excel" });
    } catch (error) {
      console.error("Erro ao exportar Excel:", error);
      toast.error("Erro ao exportar Excel", { id: "excel" });
    }
  };

  if (loading && !dados) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4" size={48} />
          <p className="text-gray-600">Carregando DRE...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-3 md:space-y-6 md:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 md:text-3xl">
            📊 DRE - Demonstração do Resultado
          </h1>
          <p className="text-gray-600 mt-1">
            Análise gerencial de receitas, custos e lucro
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setModalClassificarOpen(true)}
            className={actionButtonClasses({ intent: "edit", tone: "solid", size: "sm", className: "shadow-sm" })}
            title="Classificar lançamentos no DRE"
          >
            <span className="text-base">🏷️</span>
            <span className="font-medium">Classificar</span>
          </button>
          <button
            onClick={() => setChatIAAberto(true)}
            className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm", className: "shadow-sm" })}
            title="Consultar Especialista IA"
          >
            <MessageCircle size={20} />
            <span className="font-medium">Chat IA</span>
            <Sparkles size={16} className="animate-pulse" />
          </button>
          <button
            onClick={exportarPDF}
            className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm" })}
            title="Exportar para PDF"
          >
            <FileText size={18} />
            PDF
          </button>
          <button
            onClick={exportarExcel}
            className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm" })}
            title="Exportar para Excel"
          >
            <Download size={18} />
            Excel
          </button>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <ModuleTabs
        active={tabAtiva}
        ariaLabel="Abas da DRE"
        onChange={setTabAtiva}
        tabs={DRE_TABS}
      />

      {/* Conteúdo da Tab Demonstrativo */}
      {tabAtiva === "demonstrativo" && (
        <>
          {/* Filtros */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap items-end gap-3 md:gap-4">
              {/* Botões de período rápido */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handlePeriodoPreset("mes_atual")}
                  className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm" })}
                >
                  Mês Atual
                </button>
                <button
                  onClick={() => handlePeriodoPreset("mes_anterior")}
                  className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm" })}
                >
                  Mês Anterior
                </button>
                <button
                  onClick={() => handlePeriodoPreset("ano_atual")}
                  className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "sm" })}
                >
                  Ano Atual
                </button>
              </div>

              <div className="min-w-[260px] flex-1">
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Período (Mês/Ano)
                </label>
                <input
                  type="month"
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  className="h-[38px] w-full rounded-md border border-gray-300 px-3 py-2"
                />
              </div>
            </div>
          </div>

          {/* Conteúdo do DRE */}
          {dados && (
            <div className="space-y-6">
              {/* Cards de Resumo */}
              <MetricGrid>
                <MetricCard
                  intent="emerald"
                  icon={<TrendingUp className="h-5 w-5" />}
                  label="Receita Bruta"
                  value={<MoneyCell value={dados.totais?.receita_bruta || 0} />}
                  subtitle="Base de cálculo"
                />
                <MetricCard
                  intent="red"
                  icon={<TrendingDown className="h-5 w-5" />}
                  label="CMV"
                  value={<MoneyCell value={dados.totais?.cmv || 0} />}
                  subtitle={`${formatarPercentual(
                    calcularPercentual(
                      dados.totais?.cmv,
                      dados.totais?.receita_bruta,
                    ),
                  )} da receita`}
                />
                <MetricCard
                  intent="blue"
                  icon={<DollarSign className="h-5 w-5" />}
                  label="Lucro Bruto"
                  value={<MoneyCell value={dados.totais?.lucro_bruto || 0} />}
                  subtitle="Após custos"
                />
                <MetricCard
                  intent="violet"
                  icon={<Percent className="h-5 w-5" />}
                  label="Margem Bruta"
                  value={<NumberCell value={dados.totais?.margem_bruta || 0} decimals={2} suffix="%" />}
                  subtitle="Rentabilidade"
                />
              </MetricGrid>

              {/* Seletor de Canais - ABA 7 */}
              <div className="bg-white rounded-lg shadow p-4 md:p-6">
                <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <CheckCircle size={20} className="text-blue-600" />
                      Análise por Canal de Vendas
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Selecione os canais para adicionar suas métricas na tabela
                      DRE
                    </p>
                  </div>
                  {canaisSelecionados.length > 0 && (
                    <button
                      onClick={limparSelecaoCanais}
                      className={actionButtonClasses({ intent: "neutral", tone: "ghost", size: "xs" })}
                    >
                      Limpar Seleção
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {canaisDisponiveis.map((canal) => {
                    const selecionado = canaisSelecionados.includes(canal.id);
                    const corClasses = {
                      blue: selecionado
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100",
                      yellow: selecionado
                        ? "bg-yellow-500 text-white border-yellow-500"
                        : "bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100",
                      orange: selecionado
                        ? "bg-orange-500 text-white border-orange-500"
                        : "bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100",
                      green: selecionado
                        ? "bg-green-600 text-white border-green-600"
                        : "bg-green-50 text-green-700 border-green-200 hover:bg-green-100",
                      purple: selecionado
                        ? "bg-purple-600 text-white border-purple-600"
                        : "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100",
                      indigo: selecionado
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100",
                    };

                    return (
                      <button
                        key={canal.id}
                        onClick={() => toggleCanal(canal.id)}
                        className={`${corClasses[canal.cor]} border-2 rounded-lg p-3 transition-all duration-200 transform md:p-4 ${
                          selecionado
                            ? "scale-105 shadow-lg"
                            : "hover:scale-102"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{canal.nome}</span>
                          {selecionado && (
                            <CheckCircle size={20} className="flex-shrink-0" />
                          )}
                        </div>
                        {selecionado && (
                          <div className="text-xs mt-1 opacity-90">
                            Ativo na tabela
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>

                {canaisSelecionados.length > 0 && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Brain
                        size={18}
                        className="text-blue-600 flex-shrink-0 mt-0.5"
                      />
                      <div className="text-sm text-blue-800">
                        <span className="font-semibold">
                          {canaisSelecionados.length} canal(is) selecionado(s).
                        </span>{" "}
                        As métricas de cada canal serão adicionadas na tabela
                        DRE abaixo com suas respectivas receitas, custos e
                        lucros.
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Tabela DRE Detalhada */}
              <div className="overflow-hidden rounded-lg bg-white shadow">
                <div className="overflow-x-auto">
                <table className="min-w-[760px] w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Descrição
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Valor
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        % Receita
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {/* Renderizar linhas vindas da API */}
                    {dados?.linhas?.map((linha, idx) => {
                      // Classes de estilo baseadas no nÃ­vel e tipo
                      const ehTotal = linha.nivel === 0;
                      const ehSubitem = linha.nivel === 1;
                      const podeDetalhar = Boolean(linha.detalhavel);

                      // Background baseado na cor do canal
                      const bgStyle =
                        linha.cor_bg !== "#ffffff"
                          ? { backgroundColor: linha.cor_bg }
                          : {};

                      // Cor do texto
                      const textStyle = { color: linha.cor };

                      return (
                        <tr
                          key={idx}
                          style={bgStyle}
                          title={
                            podeDetalhar
                              ? "Clique para ver os lancamentos desta linha"
                              : linha.origem || undefined
                          }
                          onClick={() => abrirDetalhesLinha(linha)}
                          className={`${ehTotal ? "font-bold" : ""} ${
                            podeDetalhar
                              ? "cursor-pointer hover:brightness-[0.98]"
                              : linha.origem
                                ? "cursor-help hover:brightness-[0.98]"
                                : ""
                          }`}
                        >
                          <td
                            className={`px-6 py-3 ${ehSubitem ? "pl-12" : ""} ${ehTotal ? "font-bold" : ""}`}
                            style={textStyle}
                          >
                            <span className="inline-flex items-center gap-2">
                              <span>{linha.descricao}</span>
                              {linha.origem && (
                                <Info
                                  size={14}
                                  className="text-gray-400"
                                  title={linha.origem}
                                />
                              )}
                              {podeDetalhar && (
                                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500">
                                  detalhes
                                </span>
                              )}
                            </span>
                          </td>
                          <td
                            className={`px-6 py-3 text-right ${ehTotal ? "font-bold" : ""}`}
                            style={textStyle}
                          >
                            <MoneyCell value={linha.valor} zeroAsDash />
                          </td>
                          <td
                            className={`px-6 py-3 text-right ${ehTotal ? "font-bold" : ""}`}
                            style={textStyle}
                          >
                            <NumberCell value={linha.percentual} decimals={2} suffix="%" zeroAsDash />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                </div>
              </div>

              {/* Seletor de Canais (removido - nÃ£o necessÃ¡rio com novo endpoint) */}
              {canaisSelecionados.length === 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    ðŸ’¡ A DRE agora mostra automaticamente todos os canais com
                    vendas no perÃ­odo selecionado.
                  </p>
                </div>
              )}
            </div>
          )}

          {!dados && !loading && (
            <div className="bg-gray-50 rounded-lg p-12 text-center">
              <FileText className="mx-auto mb-4 text-gray-400" size={64} />
              <p className="text-gray-600 text-lg">
                Selecione um período para visualizar a DRE
              </p>
            </div>
          )}
        </>
      )}

      {/* Conteúdo da Tab Extrato Bancário */}
      {tabAtiva === "extrato" && <ExtratoBancario />}

      {/* Conteúdo da Tab Análise Inteligente */}
      {tabAtiva === "analise" && (
        <AnaliseInteligente
          dados={dados}
          periodo={{ mes: periodo.mes, ano: periodo.ano }}
        />
      )}

      {/* Modal Chat IA */}
      <ChatIAModal
        isOpen={chatIAAberto}
        onClose={() => setChatIAAberto(false)}
        contexto={{
          tipo: "DRE",
          periodo: `${periodo.mes}/${periodo.ano}`,
          valor: dados?.lucro_liquido,
          dados: dados,
        }}
      />

      {/* Modal Classificar DRE */}
      <ClassificarLancamentosModal
        isOpen={modalClassificarOpen}
        onClose={() => setModalClassificarOpen(false)}
      />

      {linhaDetalhe && (
        <div
          className="fixed inset-0 z-[70] bg-slate-900/30"
          onClick={fecharDetalhesLinha}
        >
          <aside
            className="fixed inset-x-0 bottom-0 max-h-[86dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[760px] md:rounded-none"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex h-full flex-col">
              <div className="border-b border-gray-200 p-4 md:p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Lancamentos da DRE
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-gray-900 md:text-xl">
                      {linhaDetalhe.descricao}
                    </h2>
                    <p className="mt-1 text-sm text-gray-600">
                      {detalhesLinha?.periodo || periodo} • {linhaDetalhe.canal_nome}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={fecharDetalhesLinha}
                    className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                    aria-label="Fechar detalhes"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">
                      Total da linha
                    </p>
                    <p className="mt-1 text-lg font-bold text-gray-900">
                      <MoneyCell value={detalhesLinha?.total ?? linhaDetalhe.valor} />
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">
                      Lancamentos
                    </p>
                    <p className="mt-1 text-lg font-bold text-gray-900">
                      <NumberCell value={detalhesLinha?.total_itens} zeroAsDash />
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase text-gray-500">
                      Fonte
                    </p>
                    <p className="mt-1 text-sm font-semibold text-gray-800">
                      {detalhesLinha?.items?.[0]?.origem_label || "Aguardando dados"}
                    </p>
                  </div>
                </div>

                {detalhesLinha?.origem && (
                  <p className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
                    {detalhesLinha.origem}
                  </p>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 md:p-5">
                {loadingDetalhes ? (
                  <div className="flex h-48 items-center justify-center text-gray-500">
                    <RefreshCw className="mr-2 animate-spin" size={18} />
                    Carregando lancamentos...
                  </div>
                ) : (detalhesLinha?.items || []).length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
                    Nenhum lancamento encontrado para esta linha no periodo.
                  </div>
                ) : (
                  <>
                    <div className="hidden overflow-hidden rounded-lg border border-gray-200 md:block">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                              Data
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                              Descricao
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                              Origem
                            </th>
                            <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">
                              Valor
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                          {detalhesLinha.items.map((item) => (
                            <tr key={item.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-gray-700">
                                {formatarData(item.data)}
                              </td>
                              <td className="px-4 py-3">
                                <div className="text-sm font-medium text-gray-900">
                                  {item.descricao}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {item.contraparte || item.documento || "-"}
                                </div>
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {item.origem_label}
                              </td>
                              <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                                <MoneyCell value={item.valor} zeroAsDash />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="space-y-3 md:hidden">
                      {detalhesLinha.items.map((item) => (
                        <div
                          key={item.id}
                          className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-medium text-gray-500">
                                {formatarData(item.data)} • {item.origem_label}
                              </p>
                              <h3 className="mt-1 text-sm font-semibold text-gray-900">
                                {item.descricao}
                              </h3>
                              {item.contraparte && (
                                <p className="mt-1 text-xs text-gray-500">
                                  {item.contraparte}
                                </p>
                              )}
                            </div>
                            <p className="shrink-0 text-sm font-bold text-gray-900">
                              <MoneyCell value={item.valor} zeroAsDash />
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {detalhesLinha && detalhesLinha.pages > 1 && (
                <div className="flex items-center justify-between border-t border-gray-200 p-4 text-sm">
                  <button
                    type="button"
                    disabled={loadingDetalhes || detalhesLinha.page <= 1}
                    onClick={() => abrirDetalhesLinha(linhaDetalhe, detalhesLinha.page - 1)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="text-gray-600">
                    Pagina {detalhesLinha.page} de {detalhesLinha.pages}
                  </span>
                  <button
                    type="button"
                    disabled={loadingDetalhes || detalhesLinha.page >= detalhesLinha.pages}
                    onClick={() => abrirDetalhesLinha(linhaDetalhe, detalhesLinha.page + 1)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Proxima
                  </button>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
};

export default DRE;
