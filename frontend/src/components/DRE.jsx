import { Brain, FileText, Info, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { formatarMesLocal, obterPeriodoPresetDRE } from "../utils/drePeriodos";
import MoneyCell from "./ui/MoneyCell";
import NumberCell from "./ui/NumberCell";
import DREView from "./dre/DREView";

const DRE_REQUEST_TIMEOUT_MS = 120000;

const CANAIS_DRE_PADRAO = [
  { id: "loja_fisica", nome: "Loja Física", cor: "blue" },
  { id: "mercado_livre", nome: "Mercado Livre", cor: "yellow" },
  { id: "shopee", nome: "Shopee", cor: "orange" },
  { id: "amazon", nome: "Amazon", cor: "green" },
  { id: "ecommerce", nome: "E-commerce", cor: "purple" },
  { id: "app", nome: "App", cor: "indigo" },
];

const DRE_TABLE_COLUMNS = [
  {
    key: "descricao",
    header: "Descrição",
    render: (linha) => (
      <span className="inline-flex items-center gap-2">
        <span>{linha.descricao}</span>
        {linha.origem && <Info size={14} className="text-gray-400" title={linha.origem} />}
        {linha.detalhavel && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500">
            detalhes
          </span>
        )}
      </span>
    ),
  },
  {
    key: "valor",
    header: "Valor",
    align: "right",
    render: (linha) => <MoneyCell value={linha.valor} zeroAsDash />,
  },
  {
    key: "percentual",
    header: "% Receita",
    align: "right",
    render: (linha) => <NumberCell value={linha.percentual} decimals={2} suffix="%" zeroAsDash />,
  },
];

const DRE_DETAIL_COLUMNS = [
  {
    key: "data",
    header: "Data",
    render: (item, _rowIndex, { formatarData }) => formatarData(item.data),
  },
  {
    key: "descricao",
    header: "Descrição",
    render: (item) => (
      <div>
        <div className="text-sm font-medium text-gray-900">{item.descricao}</div>
        <div className="text-xs text-gray-500">{item.contraparte || item.documento || "-"}</div>
      </div>
    ),
  },
  {
    key: "origem",
    header: "Origem",
    render: (item) => item.origem_label,
  },
  {
    key: "valor",
    header: "Valor",
    align: "right",
    className: "font-semibold",
    render: (item) => <MoneyCell value={item.valor} zeroAsDash />,
  },
];

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
  const [canaisDisponiveis] = useState(CANAIS_DRE_PADRAO);
  const [canaisSelecionados, setCanaisSelecionados] = useState(["loja_fisica"]);

  // Filtros
  const [periodo, setPeriodo] = useState(formatarMesLocal());
  const [mesInicial, setMesInicial] = useState(null);
  const [dataFinal, setDataFinal] = useState(null);

  const normalizarPeriodo = (valor) => {
    if (typeof valor === "string" && /^\d{4}-\d{2}$/.test(valor)) {
      return valor;
    }
    return periodo || formatarMesLocal();
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
        params: {
          ano,
          mes,
          mes_inicial: mesInicial || undefined,
          data_final: dataFinal || undefined,
          canais: canaisParam,
        },
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
        toast.error("Erro ao carregar DRE: " + (error.response?.data?.detail || error.message));
      }
    } finally {
      if (requestId === dreRequestIdRef.current) {
        setLoading(false);
      }
    }
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
          mes_inicial: mesInicial || undefined,
          data_final: dataFinal || undefined,
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
      toast.error("Erro ao carregar detalhes: " + (error.response?.data?.detail || error.message));
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
    setCanaisSelecionados(["loja_fisica"]);
  };

  useEffect(() => {
    const timer = window.setTimeout(() => carregarDRE(periodo), 300);
    return () => clearTimeout(timer);
  }, [periodo, mesInicial, dataFinal, canaisSelecionados]);

  useEffect(
    () => () => {
      dreAbortRef.current?.abort?.();
    },
    [],
  );

  const handlePeriodoPreset = (preset) => {
    const novoPeriodo = obterPeriodoPresetDRE(preset);
    if (!novoPeriodo) return;

    setPeriodo(novoPeriodo.periodo);
    setMesInicial(novoPeriodo.mesInicial);
    setDataFinal(novoPeriodo.dataFinal);
  };

  const handlePeriodoChange = (novoPeriodo) => {
    setPeriodo(novoPeriodo);
    setMesInicial(null);
    setDataFinal(null);
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

  return (
    <DREView
      DRE_DETAIL_COLUMNS={DRE_DETAIL_COLUMNS}
      DRE_TABLE_COLUMNS={DRE_TABLE_COLUMNS}
      DRE_TABS={DRE_TABS}
      abrirDetalhesLinha={abrirDetalhesLinha}
      calcularPercentual={calcularPercentual}
      canaisDisponiveis={canaisDisponiveis}
      canaisSelecionados={canaisSelecionados}
      chatIAAberto={chatIAAberto}
      dados={dados}
      detalhesLinha={detalhesLinha}
      exportarExcel={exportarExcel}
      exportarPDF={exportarPDF}
      fecharDetalhesLinha={fecharDetalhesLinha}
      formatarData={formatarData}
      formatarPercentual={formatarPercentual}
      handlePeriodoPreset={handlePeriodoPreset}
      handlePeriodoChange={handlePeriodoChange}
      linhaDetalhe={linhaDetalhe}
      limparSelecaoCanais={limparSelecaoCanais}
      loading={loading}
      loadingDetalhes={loadingDetalhes}
      modalClassificarOpen={modalClassificarOpen}
      periodo={periodo}
      periodoAcumulado={mesInicial !== null}
      setChatIAAberto={setChatIAAberto}
      setModalClassificarOpen={setModalClassificarOpen}
      setTabAtiva={setTabAtiva}
      tabAtiva={tabAtiva}
      toggleCanal={toggleCanal}
    />
  );
};

export default DRE;
