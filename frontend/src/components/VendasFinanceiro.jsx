import { saveAs } from "file-saver";
import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Calendar,
  ChevronDown,
  ChevronRight,
  CreditCard,
  DollarSign,
  Download,
  FileText,
  Filter,
  Minus,
  Package,
  TrendingUp,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import * as XLSX from "xlsx";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import HistoricoVendasClienteTab from "../pages/Financeiro/HistoricoVendasClienteTab";

const COLUNAS_RELATORIO_VENDAS = [
  { key: "data_venda", label: "Data", value: (v) => v.data_venda || "" },
  { key: "numero_venda", label: "Codigo", value: (v) => v.numero_venda || "" },
  { key: "cliente_nome", label: "Cliente", value: (v) => v.cliente_nome || "" },
  { key: "status", label: "Status", value: (v) => v.status || "" },
  { key: "venda_bruta", label: "Venda Bruta", value: (v) => Number(v.venda_bruta || 0) },
  { key: "taxa_loja", label: "Taxa Loja", value: (v) => Number(v.taxa_loja || 0) },
  { key: "desconto", label: "Desconto", value: (v) => Number(v.desconto || 0) },
  { key: "taxa_entrega", label: "Taxa Entrega", value: (v) => Number(v.taxa_entrega || 0) },
  { key: "taxa_operacional", label: "Taxa Operac.", value: (v) => Number(v.taxa_operacional || 0) },
  { key: "taxa_cartao", label: "Taxa Cartao", value: (v) => Number(v.taxa_cartao || 0) },
  { key: "comissao", label: "Comissao", value: (v) => Number(v.comissao || 0) },
  { key: "imposto", label: "Imposto", value: (v) => Number(v.imposto || 0) },
  { key: "custo_campanha", label: "Custo Campanha", value: (v) => Number(v.custo_campanha || 0) },
  { key: "venda_liquida", label: "Venda Liquida", value: (v) => Number(v.venda_liquida || 0) },
  { key: "custo_produtos", label: "Custo Produtos", value: (v) => Number(v.custo_produtos || 0) },
  { key: "lucro", label: "Lucro", value: (v) => Number(v.lucro || 0) },
  {
    key: "margem_sobre_venda",
    label: "Margem sobre Venda %",
    value: (v) => Number(v.margem_sobre_venda || 0),
  },
  {
    key: "margem_sobre_custo",
    label: "Margem sobre Custo %",
    value: (v) => Number(v.margem_sobre_custo || 0),
  },
];

export default function VendasFinanceiro() {
  const { user } = useAuth();
  const userPermissions = user?.permissions || [];
  const podeVerFinanceiroCompleto =
    user?.is_admin === true || userPermissions.includes("relatorios.financeiro");
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState("resumo");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [filtroSelecionado, setFiltroSelecionado] = useState("");
  const [modoComparacao, setModoComparacao] = useState(false);
  const [periodoComparacao, setPeriodoComparacao] = useState("mes_anterior");

  // Filtros avançados
  const [filtroFuncionario, setFiltroFuncionario] = useState("");
  const [filtroFormaPagamento, setFiltroFormaPagamento] = useState("");
  const [filtroCategoria, setFiltroCategoria] = useState("");
  const [mostrarGraficos, setMostrarGraficos] = useState(true);
  const [tipoComparacao, setTipoComparacao] = useState("financeiro"); // financeiro, formas_pagamento, produtos, funcionarios

  // Estados dos dados
  const [resumo, setResumo] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0,
  });

  const [resumoComparacao, setResumoComparacao] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0,
  });

  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);
  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());

  // Dados de comparação estendidos
  const [formasRecebimentoComparacao, setFormasRecebimentoComparacao] =
    useState([]);
  const [vendasPorGrupoComparacao, setVendasPorGrupoComparacao] = useState([]);
  const [vendasPorFuncionarioComparacao, setVendasPorFuncionarioComparacao] =
    useState([]);

  // Estados para Análise Inteligente
  const [produtosMaisLucrativos, setProdutosMaisLucrativos] = useState([]);
  const [produtosPorCategoria, setProdutosPorCategoria] = useState({});
  const [produtosAnalise, setProdutosAnalise] = useState([]);
  const [alertasInteligentesVendas, setAlertasInteligentesVendas] = useState(
    [],
  );
  const [previsaoProximos7Dias, setPrevisaoProximos7Dias] = useState(0);
  const [menuRelatoriosAberto, setMenuRelatoriosAberto] = useState(false);
  const [modalRelatorioAberto, setModalRelatorioAberto] = useState(false);
  const [ordenacaoRelatorio, setOrdenacaoRelatorio] = useState("data_desc");
  const [colunasRelatorio, setColunasRelatorio] = useState([
    "data_venda",
    "numero_venda",
    "cliente_nome",
    "venda_bruta",
    "venda_liquida",
    "lucro",
    "status",
  ]);

  const toggleVendaExpandida = (vendaId) => {
    const novoSet = new Set(vendasExpandidas);
    if (novoSet.has(vendaId)) {
      novoSet.delete(vendaId);
    } else {
      novoSet.add(vendaId);
    }
    setVendasExpandidas(novoSet);
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor || 0);
  };

  // Helper para garantir números válidos
  const sanitizarNumero = (valor) => {
    if (
      valor === null ||
      valor === undefined ||
      Number.isNaN(Number(valor)) ||
      !Number.isFinite(Number(valor))
    ) {
      return 0;
    }
    return valor;
  };

  const formatarData = (dataStr) => {
    if (!dataStr) return "N/A";
    try {
      // Se já é um objeto Date
      if (dataStr instanceof Date) {
        return dataStr.toLocaleDateString("pt-BR");
      }

      // Se é string ISO (ex: 2026-02-13T23:14:22-03:00)
      // Extrair apenas a parte da data sem fazer conversões de timezone
      if (typeof dataStr === "string" && dataStr.includes("T")) {
        const dateOnly = dataStr.split("T")[0]; // "2026-02-13"
        const [year, month, day] = dateOnly.split("-");
        return `${day}/${month}/${year}`;
      }

      // Tentar parse de ISO string ou formato YYYY-MM-DD
      const data = new Date(dataStr);

      // Verificar se é uma data válida
      if (Number.isNaN(data.getTime())) {
        return "N/A";
      }

      return data.toLocaleDateString("pt-BR");
    } catch {
      return "N/A";
    }
  };

  const filtrarVendasParaRelatorio = (escopo) => {
    if (escopo === "geral") return [...listaVendas];

    return listaVendas.filter((venda) => {
      const funcionario = String(venda.funcionario_nome || venda.funcionario || "");
      const formaPagamento = String(venda.forma_pagamento || venda.pagamento_principal || "");
      const categoria = String(venda.categoria || "");

      const okFuncionario = !filtroFuncionario || funcionario === filtroFuncionario;
      const okForma = !filtroFormaPagamento || formaPagamento === filtroFormaPagamento;
      const okCategoria = !filtroCategoria || categoria === filtroCategoria;

      return okFuncionario && okForma && okCategoria;
    });
  };

  const ordenarVendasRelatorio = (lista, ordenacao) => {
    const copia = [...lista];
    switch (ordenacao) {
      case "data_asc":
        return copia.sort((a, b) => new Date(a.data_venda) - new Date(b.data_venda));
      case "bruta_desc":
        return copia.sort((a, b) => Number(b.venda_bruta || 0) - Number(a.venda_bruta || 0));
      case "bruta_asc":
        return copia.sort((a, b) => Number(a.venda_bruta || 0) - Number(b.venda_bruta || 0));
      case "lucro_desc":
        return copia.sort((a, b) => Number(b.lucro || 0) - Number(a.lucro || 0));
      case "lucro_asc":
        return copia.sort((a, b) => Number(a.lucro || 0) - Number(b.lucro || 0));
      case "data_desc":
      default:
        return copia.sort((a, b) => new Date(b.data_venda) - new Date(a.data_venda));
    }
  };

  const exportarRelatorioListaVendas = ({ escopo }) => {
    const dadosFiltrados = filtrarVendasParaRelatorio(escopo);

    if (!dadosFiltrados.length) {
      toast.error("Nao ha vendas para exportar neste relatorio.");
      return;
    }

    const dadosOrdenados = ordenarVendasRelatorio(dadosFiltrados, ordenacaoRelatorio);
    const chaves = colunasRelatorio;
    const colunas = COLUNAS_RELATORIO_VENDAS.filter((coluna) => chaves.includes(coluna.key));

    if (!colunas.length) {
      toast.error("Selecione pelo menos uma coluna para exportar.");
      return;
    }

    const linhas = dadosOrdenados.map((venda) => {
      const linha = {};
      colunas.forEach((coluna) => {
        const bruto = coluna.value(venda);
        linha[coluna.label] = coluna.key === "data_venda" ? formatarData(bruto) : bruto;
      });
      return linha;
    });

    const ws = XLSX.utils.json_to_sheet(linhas);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Lista de Vendas");

    const dataArquivo = new Date().toISOString().slice(0, 10);
    const sufixo = escopo === "geral" ? "geral" : "filtrado";
    XLSX.writeFile(wb, `vendas_${sufixo}_${dataArquivo}.xlsx`);
    toast.success(`Relatorio gerado com ${linhas.length} venda(s).`);
  };

  const toggleColunaRelatorio = (key) => {
    setColunasRelatorio((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  const CORES_GRAFICOS = [
    "#3B82F6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F97316",
  ];

  // Funções de filtragem
  const aplicarFiltros = (dados, tipo) => {
    if (!dados || dados.length === 0) return dados;

    let dadosFiltrados = [...dados];

    // Filtro por funcionário
    if (filtroFuncionario && tipo === "funcionario") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.funcionario === filtroFuncionario,
      );
    }

    // Filtro por forma de pagamento
    if (filtroFormaPagamento && tipo === "formaPagamento") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.forma_pagamento === filtroFormaPagamento,
      );
    }

    // Filtro por categoria
    if (filtroCategoria && tipo === "categoria") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.categoria === filtroCategoria,
      );
    }

    return dadosFiltrados;
  };

  const formasRecebimentoFiltradas = aplicarFiltros(
    formasRecebimento,
    "formaPagamento",
  );
  const vendasPorFuncionarioFiltradas = aplicarFiltros(
    vendasPorFuncionario,
    "funcionario",
  );
  const produtosDetalhadosFiltrados = aplicarFiltros(
    produtosDetalhados,
    "categoria",
  );

  const CardComVariacao = ({
    titulo,
    valor,
    icone: Icone,
    cor,
    valorAnterior,
  }) => {
    const variacao = calcularVariacao(valor, valorAnterior);
    const cresceu = variacao.percentual > 0;
    const manteve = variacao.percentual === 0;

    return (
      <div className={`${cor} text-white p-4 rounded-lg shadow`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm opacity-90">{titulo}</span>
          <Icone className="w-5 h-5 opacity-80" />
        </div>
        <div className="text-3xl font-bold mb-1">{formatarMoeda(valor)}</div>
        {modoComparacao && valorAnterior !== undefined && (
          <div
            className={`flex items-center gap-1 text-sm ${manteve ? "opacity-70" : ""}`}
          >
            {cresceu && <ArrowUp className="w-4 h-4" />}
            {!cresceu && !manteve && <ArrowDown className="w-4 h-4" />}
            {manteve && <Minus className="w-4 h-4" />}
            <span>{Math.abs(variacao.percentual)}%</span>
          </div>
        )}
      </div>
    );
  };

  const getTextoComparacao = () => {
    switch (periodoComparacao) {
      case "periodo_anterior":
        return "mesmo período anterior";
      case "mes_anterior":
        return "mesmo período do mês anterior";
      case "ano_anterior":
        return "mesmo período do ano anterior";
      default:
        return "período anterior";
    }
  };

  const exportarParaPDF = async () => {
    if (!dataInicio || !dataFim) {
      toast.error("Selecione um período para gerar o relatório");
      return;
    }

    try {
      toast.loading("Gerando PDF...", { id: "pdf" });

      const params = new URLSearchParams({
        data_inicio: dataInicio,
        data_fim: dataFim,
      });

      if (filtroFuncionario) params.append("funcionario", filtroFuncionario);
      if (filtroFormaPagamento)
        params.append("forma_pagamento", filtroFormaPagamento);
      if (filtroCategoria) params.append("categoria", filtroCategoria);

      const response = await api.get(
        `/relatorios/vendas/export/pdf?${params.toString()}`,
        {
          responseType: "blob",
        },
      );

      const url = globalThis.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `relatorio_vendas_${dataInicio}_${dataFim}.pdf`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success("📄 PDF exportado com sucesso!", { id: "pdf" });
    } catch (error) {
      console.error("Erro ao exportar PDF:", error);
      toast.error("Erro ao exportar PDF", { id: "pdf" });
    }
  };

  const exportarParaExcel = () => {
    const wb = XLSX.utils.book_new();

    // Aba Resumo
    const resumoData = [
      ["RELATÓRIO DE VENDAS"],
      ["Período:", `${formatarData(dataInicio)} até ${formatarData(dataFim)}`],
      [""],
      ["Métrica", "Valor"],
      ["Venda Bruta", resumo.venda_bruta],
      ["Taxa de Entrega", resumo.taxa_entrega],
      ["Desconto", resumo.desconto],
      ["Venda Líquida", resumo.venda_liquida],
      ["Em Aberto", resumo.em_aberto],
      ["Quantidade de Vendas", resumo.quantidade_vendas],
    ];
    const wsResumo = XLSX.utils.aoa_to_sheet(resumoData);
    XLSX.utils.book_append_sheet(wb, wsResumo, "Resumo");

    // Aba Vendas por Data
    if (vendasPorData.length > 0) {
      const vendasData = [
        [
          "Data",
          "Qtd",
          "Tkt. Médio",
          "Vl. bruto",
          "Taxa entrega",
          "Desconto",
          "(%)",
          "Vl. líquido",
          "Vl. recebido",
          "Saldo aberto",
        ],
        ...vendasPorData.map((v) => [
          formatarData(v.data),
          v.quantidade,
          v.ticket_medio,
          v.valor_bruto,
          v.taxa_entrega,
          v.desconto,
          v.percentual_desconto,
          v.valor_liquido,
          v.valor_recebido,
          v.saldo_aberto,
        ]),
      ];
      const wsVendas = XLSX.utils.aoa_to_sheet(vendasData);
      XLSX.utils.book_append_sheet(wb, wsVendas, "Vendas por Data");
    }

    // Aba Formas de Recebimento
    if (formasRecebimentoFiltradas.length > 0) {
      const formasData = [
        ["Forma", "Valor pago"],
        ...formasRecebimentoFiltradas.map((f) => [
          f.forma_pagamento,
          f.valor_total,
        ]),
      ];
      const wsFormas = XLSX.utils.aoa_to_sheet(formasData);
      XLSX.utils.book_append_sheet(wb, wsFormas, "Formas Pagamento");
    }

    // Gerar arquivo
    const wbout = XLSX.write(wb, { bookType: "xlsx", type: "binary" });
    const buf = new ArrayBuffer(wbout.length);
    const view = new Uint8Array(buf);
    for (let i = 0; i < wbout.length; i++) {
      view[i] = (wbout.codePointAt(i) ?? 0) & 0xff;
    }
    const fileName = `relatorio_vendas_${dataInicio}_${dataFim}.xlsx`;
    saveAs(new Blob([buf], { type: "application/octet-stream" }), fileName);
  };

  const aplicarFiltroRapido = (filtro) => {
    // Obter data atual sem conversão de timezone
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, "0");
    const dia = String(agora.getDate()).padStart(2, "0");
    const hoje = `${ano}-${mes}-${dia}`;

    let inicio, fim;

    switch (filtro) {
      case "hoje":
        inicio = fim = hoje;
        break;
      case "ontem": {
        const dataOntem = new Date(agora);
        dataOntem.setDate(agora.getDate() - 1);
        const anoOntem = dataOntem.getFullYear();
        const mesOntem = String(dataOntem.getMonth() + 1).padStart(2, "0");
        const diaOntem = String(dataOntem.getDate()).padStart(2, "0");
        inicio = fim = `${anoOntem}-${mesOntem}-${diaOntem}`;
        break;
      }
      case "esta_semana": {
        const diaSemana = agora.getDay(); // 0=domingo, 1=segunda, ..., 6=sábado
        const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1; // Se domingo, volta 6 dias; senão volta (dia-1)
        const primeiroDia = new Date(agora);
        primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
        const anoPri = primeiroDia.getFullYear();
        const mesPri = String(primeiroDia.getMonth() + 1).padStart(2, "0");
        const diaPri = String(primeiroDia.getDate()).padStart(2, "0");
        inicio = `${anoPri}-${mesPri}-${diaPri}`;
        fim = hoje;
        break;
      }
      case "este_mes":
        inicio = `${ano}-${mes}-01`;
        fim = hoje;
        break;
      case "mes_anterior": {
        const mesPassado = new Date(
          agora.getFullYear(),
          agora.getMonth() - 1,
          1,
        );
        const ultimoDia = new Date(agora.getFullYear(), agora.getMonth(), 0);
        const anoMesPass = mesPassado.getFullYear();
        const numeroMesPass = String(mesPassado.getMonth() + 1).padStart(
          2,
          "0",
        );
        const anoUltDia = ultimoDia.getFullYear();
        const mesUltDia = String(ultimoDia.getMonth() + 1).padStart(2, "0");
        const diaUltDia = String(ultimoDia.getDate()).padStart(2, "0");
        inicio = `${anoMesPass}-${numeroMesPass}-01`;
        fim = `${anoUltDia}-${mesUltDia}-${diaUltDia}`;
        break;
      }
      case "ultimos_7_dias": {
        const sete = new Date(agora);
        sete.setDate(agora.getDate() - 7);
        const anoSete = sete.getFullYear();
        const mesSete = String(sete.getMonth() + 1).padStart(2, "0");
        const diaSete = String(sete.getDate()).padStart(2, "0");
        inicio = `${anoSete}-${mesSete}-${diaSete}`;
        fim = hoje;
        break;
      }
      case "ultimos_30_dias": {
        const trinta = new Date(agora);
        trinta.setDate(agora.getDate() - 30);
        const anoTrinta = trinta.getFullYear();
        const mesTrinta = String(trinta.getMonth() + 1).padStart(2, "0");
        const diaTrinta = String(trinta.getDate()).padStart(2, "0");
        inicio = `${anoTrinta}-${mesTrinta}-${diaTrinta}`;
        fim = hoje;
        break;
      }
      case "este_ano":
        inicio = `${ano}-01-01`;
        fim = hoje;
        break;
      default:
        return;
    }

    setDataInicio(inicio);
    setDataFim(fim);
    setFiltroSelecionado(filtro);
  };

  const calcularPeriodoComparacao = () => {
    // Parse manual das datas para evitar problemas de timezone
    const [anoIni, mesIni, diaIni] = dataInicio.split("-").map(Number);
    const [anoFim, mesFim, diaFim] = dataFim.split("-").map(Number);

    const inicio = new Date(anoIni, mesIni - 1, diaIni);
    const fim = new Date(anoFim, mesFim - 1, diaFim);
    const diffDias = Math.floor((fim - inicio) / (1000 * 60 * 60 * 24)) + 1;

    let inicioComp, fimComp;

    switch (periodoComparacao) {
      case "periodo_anterior":
        inicioComp = new Date(inicio);
        inicioComp.setDate(inicio.getDate() - diffDias);
        fimComp = new Date(inicio);
        fimComp.setDate(inicio.getDate() - 1);
        break;
      case "mes_anterior":
        inicioComp = new Date(inicio);
        inicioComp.setMonth(inicio.getMonth() - 1);
        fimComp = new Date(fim);
        fimComp.setMonth(fim.getMonth() - 1);
        break;
      case "ano_anterior":
        inicioComp = new Date(inicio);
        inicioComp.setFullYear(inicio.getFullYear() - 1);
        fimComp = new Date(fim);
        fimComp.setFullYear(fim.getFullYear() - 1);
        break;
      default:
        return { data_inicio: "", data_fim: "" };
    }

    // Formatar manualmente para evitar problemas de timezone
    const anoIniComp = inicioComp.getFullYear();
    const mesIniComp = String(inicioComp.getMonth() + 1).padStart(2, "0");
    const diaIniComp = String(inicioComp.getDate()).padStart(2, "0");

    const anoFimComp = fimComp.getFullYear();
    const mesFimComp = String(fimComp.getMonth() + 1).padStart(2, "0");
    const diaFimComp = String(fimComp.getDate()).padStart(2, "0");

    return {
      data_inicio: `${anoIniComp}-${mesIniComp}-${diaIniComp}`,
      data_fim: `${anoFimComp}-${mesFimComp}-${diaFimComp}`,
    };
  };

  const calcularVariacao = (valorAtual, valorAnterior) => {
    if (!valorAnterior || valorAnterior === 0)
      return { valor: 0, percentual: 0 };
    const diff = valorAtual - valorAnterior;
    const perc = ((diff / valorAnterior) * 100).toFixed(1);
    return { valor: diff, percentual: Number.parseFloat(perc) };
  };

  const carregarDados = async () => {
    if (!podeVerFinanceiroCompleto) return;
    if (!dataInicio || !dataFim) return;

    setLoading(true);

    try {
      const response = await api.get("/relatorios/vendas/relatorio", {
        params: { data_inicio: dataInicio, data_fim: dataFim },
      });
      const data = response.data;

      setResumo(data.resumo || {});
      setVendasPorData(data.vendas_por_data || []);
      setFormasRecebimento(data.formas_recebimento || []);
      setVendasPorFuncionario(data.vendas_por_funcionario || []);
      setVendasPorTipo(data.vendas_por_tipo || []);
      setVendasPorGrupo(data.vendas_por_grupo || []);
      setProdutosDetalhados(data.produtos_detalhados || []);
      setProdutosAnalise(data.produtos_analise || []);
      setListaVendas(data.lista_vendas || []);

      if (modoComparacao || abaAtiva === "comparacao") {
        const periodoComp = calcularPeriodoComparacao();
        const responseComp = await api.get("/relatorios/vendas/relatorio", {
          params: periodoComp,
        });
        setResumoComparacao(responseComp.data.resumo || {});
        setFormasRecebimentoComparacao(
          responseComp.data.formas_recebimento || [],
        );
        setVendasPorGrupoComparacao(responseComp.data.vendas_por_grupo || []);
        setVendasPorFuncionarioComparacao(
          responseComp.data.vendas_por_funcionario || [],
        );
      } else {
        // Limpar dados de comparação quando desativado
        setResumoComparacao({
          venda_bruta: 0,
          taxa_entrega: 0,
          desconto: 0,
          venda_liquida: 0,
          em_aberto: 0,
          quantidade_vendas: 0,
        });
      }
    } catch (error) {
      console.error("Erro ao carregar relatório:", error);
    } finally {
      setLoading(false);
    }
  };

  // Função para calcular análise inteligente
  const calcularAnaliseInteligente = () => {
    if (!produtosAnalise || produtosAnalise.length === 0) {
      setProdutosMaisLucrativos([]);
      setProdutosPorCategoria({});
      setAlertasInteligentesVendas([]);
      setPrevisaoProximos7Dias(0);
      return;
    }

    // Calcular produtos mais lucrativos com margem
    const produtosComMargem = produtosAnalise.map((produto) => {
      const custo = sanitizarNumero(produto.custo_total);
      const preco = sanitizarNumero(produto.valor_total);
      const quantidade = sanitizarNumero(produto.quantidade) || 1;
      const lucro = preco - custo;
      const margem = custo > 0 ? (lucro / custo) * 100 : 0;

      return {
        nome: produto.nome || produto.produto || "Produto sem nome",
        marca: produto.marca || "-",
        quantidade: quantidade,
        custo: sanitizarNumero(custo / quantidade),
        preco: sanitizarNumero(preco / quantidade),
        lucro_total: sanitizarNumero(lucro),
        margem: sanitizarNumero(margem),
        categoria: produto.categoria || "Sem Categoria",
      };
    });

    // Ordenar por lucro total decrescente
    const produtosOrdenadosPorLucro = [...produtosComMargem];
    produtosOrdenadosPorLucro.sort((a, b) => b.lucro_total - a.lucro_total);
    const topProdutos = produtosOrdenadosPorLucro.slice(0, 20);

    setProdutosMaisLucrativos(topProdutos);

    // Agrupar por categoria
    const porCategoria = {};
    produtosComMargem.forEach((produto) => {
      const cat = produto.categoria || "Sem Categoria";
      if (!porCategoria[cat]) {
        porCategoria[cat] = {
          quantidade: 0,
          total: 0,
          margens: [],
        };
      }
      porCategoria[cat].quantidade += produto.quantidade;
      porCategoria[cat].total += produto.preco * produto.quantidade;
      porCategoria[cat].margens.push(produto.margem);
    });

    // Calcular margem média por categoria
    Object.keys(porCategoria).forEach((cat) => {
      const margens = porCategoria[cat].margens;
      const somaMargens = margens.reduce(
        (a, b) => sanitizarNumero(a) + sanitizarNumero(b),
        0,
      );
      porCategoria[cat].margem_media = sanitizarNumero(
        margens.length > 0 ? somaMargens / margens.length : 0,
      );
      delete porCategoria[cat].margens;
    });

    setProdutosPorCategoria(porCategoria);

    const alertas = [];

    const qtdAtual = sanitizarNumero(resumo.quantidade_vendas);
    const qtdAnterior = sanitizarNumero(resumoComparacao.quantidade_vendas);
    if (qtdAnterior > 0 && qtdAtual < qtdAnterior) {
      const queda = Number((((qtdAnterior - qtdAtual) / qtdAnterior) * 100).toFixed(1));
      alertas.push({
        id: "queda-vendas",
        tipo: "critico",
        titulo: "Queda de volume de vendas",
        mensagem: `As vendas cairam ${queda}% em relacao ao periodo comparativo.`,
        recomendacao:
          "Revise campanhas, produtos de entrada e politica de descontos para recuperar volume.",
      });
    }

    const liquidoAtual = sanitizarNumero(resumo.venda_liquida);
    const emAberto = sanitizarNumero(resumo.em_aberto);
    if (liquidoAtual > 0) {
      const percAberto = Number(((emAberto / liquidoAtual) * 100).toFixed(1));
      if (percAberto >= 20) {
        alertas.push({
          id: "recebiveis-abertos",
          tipo: "atencao",
          titulo: "Recebimento em aberto elevado",
          mensagem: `${percAberto}% da venda liquida ainda esta em aberto no periodo.`,
          recomendacao:
            "Priorize cobranca e revise condicoes de pagamento com maior prazo.",
        });
      }
    }

    const baixaMargem = produtosComMargem.filter((produto) => produto.margem < 20).length;
    if (baixaMargem >= 5) {
      alertas.push({
        id: "mix-baixa-margem",
        tipo: "atencao",
        titulo: "Muitos produtos com baixa margem",
        mensagem: `${baixaMargem} produtos vendidos estao com margem abaixo de 20%.`,
        recomendacao:
          "Reprecifique itens de baixo giro/margem e renegocie compra com fornecedor.",
      });
    }

    const altaMargemBaixoVolume = produtosComMargem
      .filter((produto) => produto.margem >= 45 && produto.quantidade <= 3)
      .slice(0, 3);
    if (altaMargemBaixoVolume.length > 0) {
      alertas.push({
        id: "oportunidade-upsell",
        tipo: "oportunidade",
        titulo: "Oportunidade de crescimento",
        mensagem: `Produtos com alta margem e baixo volume: ${altaMargemBaixoVolume.map((p) => p.nome).join(", ")}.`,
        recomendacao:
          "Destacar esses itens no atendimento e criar combo promocional para aumentar giro.",
      });
    }

    const basePrevisao = (vendasPorData || []).slice(-14);
    if (basePrevisao.length > 0) {
      const mediaDiaria =
        basePrevisao.reduce(
          (soma, item) => soma + sanitizarNumero(item.valor_liquido),
          0,
        ) / basePrevisao.length;
      setPrevisaoProximos7Dias(sanitizarNumero(mediaDiaria * 7));
    } else {
      setPrevisaoProximos7Dias(0);
    }

    setAlertasInteligentesVendas(alertas);
  };

  // Recalcular análise quando produtos mudarem
  useEffect(() => {
    if (abaAtiva === "analise") {
      calcularAnaliseInteligente();
    }
  }, [produtosAnalise, abaAtiva, resumo, resumoComparacao, vendasPorData]);

  useEffect(() => {
    if (podeVerFinanceiroCompleto) {
      carregarDados();
    }
  }, [
    dataInicio,
    dataFim,
    modoComparacao,
    periodoComparacao,
    abaAtiva,
    podeVerFinanceiroCompleto,
  ]);

  useEffect(() => {
    if (!podeVerFinanceiroCompleto) {
      setAbaAtiva("historico-cliente");
      setModoComparacao(false);
    }
  }, [podeVerFinanceiroCompleto]);

  // Aplicar filtro "Este mês" ao carregar componente pela primeira vez
  useEffect(() => {
    aplicarFiltroRapido("este_mes");
  }, []); // Roda apenas uma vez ao montar o componente

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Cabeçalho com Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">
            Consulta de Vendas
          </h1>

          {podeVerFinanceiroCompleto ? (
            <div className="flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => setMenuRelatoriosAberto((prev) => !prev)}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span className="font-medium">Relatorios</span>
              </button>

              {menuRelatoriosAberto && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "geral" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
                  >
                    Relatorio geral da lista de vendas
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "filtrado" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio do que filtrei
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      setModalRelatorioAberto(true);
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio personalizado
                  </button>
                </div>
              )}
            </div>
            {/* Botão Exportar PDF */}
            <button
              onClick={exportarParaPDF}
              disabled={!dataInicio || !dataFim}
              title={
                dataInicio && dataFim
                  ? `Exportar PDF de ${formatarData(dataInicio)} até ${formatarData(dataFim)}`
                  : "Selecione um período"
              }
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <FileText className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar PDF</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">
                    ({formatarData(dataInicio)} - {formatarData(dataFim)})
                  </span>
                )}
              </div>
            </button>

            {/* Botão Exportar Excel */}
            <button
              onClick={exportarParaExcel}
              disabled={!dataInicio || !dataFim}
              title={
                dataInicio && dataFim
                  ? `Exportar dados de ${formatarData(dataInicio)} até ${formatarData(dataFim)}`
                  : "Selecione um período"
              }
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar Excel</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">
                    ({formatarData(dataInicio)} - {formatarData(dataFim)})
                  </span>
                )}
              </div>
            </button>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={modoComparacao}
                onChange={(e) => setModoComparacao(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700">
                Comparar com:
              </span>
            </label>

            {modoComparacao && (
              <select
                value={periodoComparacao}
                onChange={(e) => setPeriodoComparacao(e.target.value)}
                className="border rounded px-3 py-2 text-sm bg-blue-50 font-medium"
              >
                <option value="periodo_anterior">
                  Período imediatamente anterior (mesmo nº de dias)
                </option>
                <option value="mes_anterior">
                  Mesmo período do mês passado
                </option>
                <option value="ano_anterior">
                  Mesmo período do ano passado
                </option>
              </select>
            )}
            </div>
          ) : null}
        </div>

        {!podeVerFinanceiroCompleto && (
          <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-700">
            Acesso limitado: você pode consultar apenas a aba Histórico por Cliente.
          </div>
        )}

        {podeVerFinanceiroCompleto && (
          <div className="flex flex-wrap gap-2 mb-4">
          {[
            { id: "hoje", label: "Hoje" },
            { id: "ontem", label: "Ontem" },
            { id: "esta_semana", label: "Esta semana" },
            { id: "este_mes", label: "Este mês" },
            { id: "mes_anterior", label: "Mês anterior" },
            { id: "ultimos_7_dias", label: "Últimos 7 dias" },
            { id: "ultimos_30_dias", label: "Últimos 30 dias" },
            { id: "este_ano", label: "Este ano" },
            { id: "personalizado", label: "Personalizado" },
          ].map((filtro) => (
            <button
              key={filtro.id}
              onClick={() => {
                if (filtro.id === "personalizado") {
                  setFiltroSelecionado("personalizado");
                } else {
                  aplicarFiltroRapido(filtro.id);
                }
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                filtroSelecionado === filtro.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {filtro.label}
            </button>
          ))}
          </div>
        )}

        {podeVerFinanceiroCompleto && filtroSelecionado === "personalizado" && (
          <div className="flex gap-2 items-center mb-4 p-3 bg-gray-50 rounded">
            <Calendar className="w-5 h-5 text-gray-500" />
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="border rounded px-3 py-2"
            />
            <span className="text-gray-600">até</span>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
        )}

        {/* Filtros Avançados */}
        {podeVerFinanceiroCompleto && (
          <div className="flex gap-2 items-center mb-4 p-3 bg-blue-50 rounded border border-blue-200">
          <Filter className="w-5 h-5 text-blue-600" />
          <span className="text-sm font-medium text-gray-700">
            Filtros Avançados:
          </span>

          <select
            value={filtroFuncionario}
            onChange={(e) => setFiltroFuncionario(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todos os funcionários</option>
            {vendasPorFuncionario.map((f) => (
              <option key={`func-${f.funcionario || "sem-nome"}`} value={f.funcionario}>
                {f.funcionario}
              </option>
            ))}
          </select>

          <select
            value={filtroFormaPagamento}
            onChange={(e) => setFiltroFormaPagamento(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as formas</option>
            {formasRecebimento.map((f) => (
              <option key={`forma-${f.forma_pagamento || "sem-forma"}`} value={f.forma_pagamento}>
                {f.forma_pagamento}
              </option>
            ))}
          </select>

          <select
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as categorias</option>
            {produtosDetalhados.map((cat) => (
              <option key={`cat-${cat.categoria || "sem-categoria"}`} value={cat.categoria}>
                {cat.categoria}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              setFiltroFuncionario("");
              setFiltroFormaPagamento("");
              setFiltroCategoria("");
            }}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors"
          >
            Limpar Filtros
          </button>

          <button
            onClick={() => setMostrarGraficos(!mostrarGraficos)}
            className="ml-auto px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <BarChart3 className="w-4 h-4" />
            {mostrarGraficos ? "Ocultar" : "Mostrar"} Gráficos
          </button>
          </div>
        )}

        {/* Abas */}
        <div className="flex gap-2 border-b">
          {podeVerFinanceiroCompleto && (
            <button
              onClick={() => setAbaAtiva("resumo")}
              className={`px-4 py-2 font-medium ${
                abaAtiva === "resumo"
                  ? "border-b-2 border-blue-500 text-blue-600"
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              Resumo
            </button>
          )}
          <button
            onClick={() => setAbaAtiva("historico-cliente")}
            className={`px-4 py-2 font-medium ${
              abaAtiva === "historico-cliente"
                ? "border-b-2 border-purple-500 text-purple-600"
                : "text-gray-600 hover:text-gray-800"
            }`}
          >
            Histórico por Cliente
          </button>
          {podeVerFinanceiroCompleto && (
            <>
              <button
                onClick={() => setAbaAtiva("produtos")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "produtos"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Totais por produto/serviço
              </button>
              <button
                onClick={() => setAbaAtiva("lista")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "lista"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Lista de Vendas
              </button>
              <button
                onClick={() => setAbaAtiva("comparacao")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "comparacao"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Comparação de Períodos
              </button>
              <button
                onClick={() => setAbaAtiva("analise")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "analise"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Análise Inteligente
              </button>
            </>
          )}
        </div>
      </div>

      {/* Conteúdo das Abas */}
      {abaAtiva === "resumo" && (
        <div>
          {/* Banner de Comparação */}
          {modoComparacao && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="text-sm">
                  <span className="font-semibold text-blue-800">
                    Modo Comparação Ativo:
                  </span>
                  <span className="text-blue-700 ml-2">
                    Comparando{" "}
                    <span className="font-medium">
                      {formatarData(dataInicio)} até {formatarData(dataFim)}
                    </span>{" "}
                    com{" "}
                    <span className="font-medium">{getTextoComparacao()}</span>
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Cards de Resumo */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            <CardComVariacao
              titulo="Venda Bruta"
              valor={resumo.venda_bruta}
              icone={DollarSign}
              cor="bg-green-500"
              valorAnterior={resumoComparacao.venda_bruta}
            />
            <CardComVariacao
              titulo="Taxa de Entrega"
              valor={resumo.taxa_entrega}
              icone={Package}
              cor="bg-gray-400"
              valorAnterior={resumoComparacao.taxa_entrega}
            />
            <CardComVariacao
              titulo="Desconto"
              valor={resumo.desconto}
              icone={TrendingUp}
              cor="bg-yellow-500"
              valorAnterior={resumoComparacao.desconto}
            />
            <CardComVariacao
              titulo="Venda Líquida"
              valor={resumo.venda_liquida}
              icone={DollarSign}
              cor="bg-blue-500"
              valorAnterior={resumoComparacao.venda_liquida}
            />
            <CardComVariacao
              titulo="Em Aberto"
              valor={resumo.em_aberto}
              icone={CreditCard}
              cor="bg-red-500"
              valorAnterior={resumoComparacao.em_aberto}
            />
          </div>

          {/* Cards de Análise de Rentabilidade */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-orange-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">
                {formatarMoeda(resumo.custo_total || 0)}
              </div>
              <div className="text-sm">Custo Total</div>
            </div>
            <div className="bg-purple-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">
                {formatarMoeda(resumo.taxa_cartao_total || 0)}
              </div>
              <div className="text-sm">Taxas de Cartão</div>
            </div>
            <div className="bg-green-600 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">
                {formatarMoeda(resumo.lucro_total || 0)}
              </div>
              <div className="text-sm">Lucro Total</div>
            </div>
            <div className="bg-teal-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">
                {resumo.margem_media || 0}%
              </div>
              <div className="text-sm">Margem Média</div>
            </div>
          </div>

          {/* Gráficos */}
          {mostrarGraficos && (
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Gráfico de Vendas por Período */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Vendas no Período
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={vendasPorData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="data"
                      tickFormatter={(value) =>
                        new Date(value).toLocaleDateString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                        })
                      }
                    />
                    <YAxis
                      tickFormatter={(value) =>
                        `R$ ${(value / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip
                      formatter={(value) => formatarMoeda(value)}
                      labelFormatter={(label) => formatarData(label)}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="valor_bruto"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      name="Venda Bruta"
                    />
                    <Line
                      type="monotone"
                      dataKey="valor_liquido"
                      stroke="#10B981"
                      strokeWidth={2}
                      name="Venda Líquida"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Formas de Pagamento - Barras Horizontais */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Formas de Pagamento
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={formasRecebimentoFiltradas}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      tickFormatter={(value) => formatarMoeda(value)}
                    />
                    <YAxis
                      type="category"
                      dataKey="forma_pagamento"
                      width={110}
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip
                      formatter={(value, name, props) => {
                        const total = formasRecebimentoFiltradas.reduce(
                          (sum, item) => sum + item.valor_total,
                          0,
                        );
                        const percent = ((value / total) * 100).toFixed(1);
                        return [
                          `${formatarMoeda(value)} (${percent}%)`,
                          "Valor",
                        ];
                      }}
                      contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        padding: "8px",
                      }}
                    />
                    <Bar
                      dataKey="valor_total"
                      fill="#3B82F6"
                      radius={[0, 8, 8, 0]}
                      label={{
                        position: "right",
                        formatter: (value) => {
                          const total = formasRecebimentoFiltradas.reduce(
                            (sum, item) => sum + item.valor_total,
                            0,
                          );
                          const percent = ((value / total) * 100).toFixed(1);
                          return `${percent}%`;
                        },
                        style: { fontSize: "11px", fontWeight: "bold" },
                      }}
                    >
                      {formasRecebimentoFiltradas.map((entry, index) => (
                        <Cell
                          key={`cell-forma-${entry.forma_pagamento || entry.name || index}`}
                          fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Barras - Top 10 Produtos */}
              <div className="bg-white rounded-lg shadow p-4 col-span-2">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Top 10 Categorias de Produtos
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={produtosDetalhadosFiltrados.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="categoria" />
                    <YAxis
                      tickFormatter={(value) =>
                        `R$ ${(value / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip formatter={(value) => formatarMoeda(value)} />
                    <Legend />
                    <Bar
                      dataKey="total_liquido"
                      fill="#3B82F6"
                      name="Valor Líquido"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Vendas por Data */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
              Vendas por data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Data</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Tkt. Médio</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Taxa entrega</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">(%)</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                    <th className="px-4 py-2 text-right">Vl. recebido</th>
                    <th className="px-4 py-2 text-right">Saldo aberto</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorData.map((item, idx) => (
                    <tr key={`dia-${item.data || idx}`} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2">{formatarData(item.data)}</td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.ticket_medio)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.taxa_entrega)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {item.percentual_desconto}%
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_recebido)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.saldo_aberto)}
                      </td>
                    </tr>
                  ))}
                  {/* TOTAL */}
                  {vendasPorData.length > 0 &&
                    (() => {
                      const totalQtd = vendasPorData.reduce(
                        (sum, item) => sum + item.quantidade,
                        0,
                      );
                      const totalBruto = vendasPorData.reduce(
                        (sum, item) => sum + item.valor_bruto,
                        0,
                      );
                      const totalDesconto = vendasPorData.reduce(
                        (sum, item) => sum + item.desconto,
                        0,
                      );
                      const ticketMedio =
                        totalQtd > 0 ? totalBruto / totalQtd : 0;
                      const percentualDesconto =
                        totalBruto > 0
                          ? ((totalDesconto / totalBruto) * 100).toFixed(1)
                          : 0;

                      return (
                        <tr
                          style={{
                            backgroundColor: "#E5E7EB",
                            color: "#1F2937",
                            fontWeight: "bold",
                          }}
                        >
                          <td className="px-4 py-3">TOTAL</td>
                          <td className="px-4 py-3 text-right">{totalQtd}</td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(ticketMedio)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(totalBruto)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorData.reduce(
                                (sum, item) => sum + item.taxa_entrega,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(totalDesconto)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {percentualDesconto}%
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorData.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorData.reduce(
                                (sum, item) => sum + item.valor_recebido,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorData.reduce(
                                (sum, item) => sum + item.saldo_aberto,
                                0,
                              ),
                            )}
                          </td>
                        </tr>
                      );
                    })()}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grid com outras tabelas */}
          <div className="grid grid-cols-2 gap-6">
            {/* Formas de Recebimento */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Formas de recebimento
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Forma</th>
                    <th className="px-4 py-2 text-right">Valor pago</th>
                  </tr>
                </thead>
                <tbody>
                  {formasRecebimento.map((item, idx) => (
                    <tr key={`forma-row-${item.forma_pagamento || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.forma_pagamento}</td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_total)}
                      </td>
                    </tr>
                  ))}
                  {formasRecebimento.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          formasRecebimento.reduce(
                            (sum, item) => sum + item.valor_total,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Funcionário */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Funcionário
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorFuncionarioFiltradas.map((item, idx) => (
                    <tr key={`func-row-${item.funcionario || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.funcionario}</td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorFuncionarioFiltradas.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {vendasPorFuncionarioFiltradas.reduce(
                          (sum, item) => sum + item.quantidade,
                          0,
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Tipo */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Tipo
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Tipo</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorTipo.map((item, idx) => (
                    <tr key={`tipo-row-${item.tipo || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.tipo}</td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorTipo.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {vendasPorTipo.reduce(
                          (sum, item) => sum + item.quantidade,
                          0,
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Grupo de Produto */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Grupo de produto
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Percentual</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorGrupo.map((item, idx) => (
                    <tr key={`grupo-row-${item.grupo || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.grupo}</td>
                      <td className="px-4 py-2 text-right">
                        {item.percentual}%
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorGrupo.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {modalRelatorioAberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Relatorio Personalizado - Lista de Vendas
              </h3>
              <button
                onClick={() => setModalRelatorioAberto(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className="text-2xl leading-none">×</span>
              </button>
            </div>

            <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
              <div>
                <label
                  htmlFor="ordenacao-relatorio-vendas"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Ordem
                </label>
                <select
                  id="ordenacao-relatorio-vendas"
                  value={ordenacaoRelatorio}
                  onChange={(e) => setOrdenacaoRelatorio(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="data_desc">Data (mais recente primeiro)</option>
                  <option value="data_asc">Data (mais antiga primeiro)</option>
                  <option value="bruta_desc">Venda bruta (maior para menor)</option>
                  <option value="bruta_asc">Venda bruta (menor para maior)</option>
                  <option value="lucro_desc">Lucro (maior para menor)</option>
                  <option value="lucro_asc">Lucro (menor para maior)</option>
                </select>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Colunas</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {COLUNAS_RELATORIO_VENDAS.map((coluna) => (
                    <label
                      key={coluna.key}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={colunasRelatorio.includes(coluna.key)}
                        onChange={() => toggleColunaRelatorio(coluna.key)}
                        className="w-4 h-4 text-indigo-600 rounded"
                      />
                      <span className="text-sm text-gray-700">{coluna.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setModalRelatorioAberto(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  exportarRelatorioListaVendas({ escopo: "filtrado" });
                  setModalRelatorioAberto(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Gerar relatorio
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Aba Produtos Detalhados */}
      {abaAtiva === "produtos" && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Produtos/Serviços
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Produtos/Serviços</th>
                  <th className="px-4 py-2 text-right">Itens</th>
                  <th className="px-4 py-2 text-right">Bruto</th>
                  <th className="px-4 py-2 text-right">Desconto</th>
                  <th className="px-4 py-2 text-right">Líquido</th>
                </tr>
              </thead>
              <tbody>
                {produtosDetalhadosFiltrados.map((categoria, catIdx) => (
                  <React.Fragment key={`cat-group-${catIdx}`}>
                    {/* Linha da Categoria */}
                    <tr
                      key={`cat-${catIdx}`}
                      className="bg-blue-50 font-semibold"
                    >
                      <td className="px-4 py-2">{categoria.categoria}</td>
                      <td className="px-4 py-2 text-right">
                        {categoria.total_quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_liquido)}
                      </td>
                    </tr>

                    {/* Subcategorias */}
                    {categoria.subcategorias &&
                      categoria.subcategorias.map((sub, subIdx) => (
                        <React.Fragment key={`sub-group-${catIdx}-${subIdx}`}>
                          {/* Linha da Subcategoria */}
                          <tr
                            key={`sub-${catIdx}-${subIdx}`}
                            className="bg-gray-50 font-medium"
                          >
                            <td className="px-4 py-2 pl-8">
                              {sub.subcategoria}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {sub.total_quantidade}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_bruto)}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_desconto)}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_liquido)}
                            </td>
                          </tr>

                          {/* Produtos da Subcategoria */}
                          {sub.produtos &&
                            sub.produtos.map((produto, prodIdx) => (
                              <tr
                                key={`prod-${catIdx}-${subIdx}-${prodIdx}`}
                                className="border-b hover:bg-gray-50"
                              >
                                <td className="px-4 py-2 pl-12 text-gray-700">
                                  {produto.produto}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {produto.quantidade}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.valor_bruto)}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.desconto)}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.valor_liquido)}
                                </td>
                              </tr>
                            ))}
                        </React.Fragment>
                      ))}

                    {/* Produtos sem subcategoria */}
                    {categoria.produtos &&
                      categoria.produtos.map((produto, prodIdx) => (
                        <tr
                          key={`prod-${catIdx}-${prodIdx}`}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="px-4 py-2 pl-8 text-gray-700">
                            {produto.produto}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {produto.quantidade}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.valor_bruto)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.desconto)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.valor_liquido)}
                          </td>
                        </tr>
                      ))}
                  </React.Fragment>
                ))}

                {/* TOTAL GERAL */}
                {produtosDetalhados.length > 0 && (
                  <tr
                    style={{
                      backgroundColor: "#E5E7EB",
                      color: "#1F2937",
                      fontWeight: "bold",
                    }}
                  >
                    <td className="px-4 py-3">TOTAL GERAL</td>
                    <td className="px-4 py-3 text-right">
                      {produtosDetalhados.reduce(
                        (sum, cat) => sum + cat.total_quantidade,
                        0,
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_bruto,
                          0,
                        ),
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_desconto,
                          0,
                        ),
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_liquido,
                          0,
                        ),
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba Lista de Vendas */}
      {abaAtiva === "lista" && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Lista de Vendas com Análise de Rentabilidade
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-1 py-2 text-left w-8"></th>
                  <th className="px-1 py-2 text-left">Data</th>
                  <th className="px-1 py-2 text-left">Código</th>
                  <th className="px-1 py-2 text-left">Cliente</th>
                  <th className="px-1 py-2 text-right">Venda Bruta</th>
                  <th className="px-1 py-2 text-right">Tx Loja</th>
                  <th className="px-1 py-2 text-right">Desconto</th>
                  <th className="px-1 py-2 text-right">Tx. Entrega</th>
                  <th className="px-1 py-2 text-right">Tx. Operac.</th>
                  <th className="px-1 py-2 text-right">Tx. Cartão</th>
                  <th className="px-1 py-2 text-right">Comissão</th>
                  <th className="px-1 py-2 text-right">Imposto</th>
                  <th
                    className="px-1 py-2 text-right"
                    title="Cashback / cupons resgatados nesta venda"
                  >
                    Custo Camp.
                  </th>
                  <th className="px-1 py-2 text-right">Líquida</th>
                  <th className="px-1 py-2 text-right">Custo</th>
                  <th className="px-1 py-2 text-right">Lucro</th>
                  <th className="px-1 py-2 text-right">MG Venda</th>
                  <th className="px-1 py-2 text-right">MG Custo</th>
                  <th className="px-1 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {listaVendas.map((venda) => (
                  <React.Fragment key={venda.id}>
                    <tr
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() => toggleVendaExpandida(venda.id)}
                    >
                      <td className="px-1 py-2">
                        {vendasExpandidas.has(venda.id) ? (
                          <ChevronDown className="w-4 h-4 text-gray-600" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-600" />
                        )}
                      </td>
                      <td className="px-1 py-2 whitespace-nowrap">
                        {formatarData(venda.data_venda)}
                      </td>
                      <td className="px-1 py-2 whitespace-nowrap">
                        {venda.numero_venda}
                      </td>
                      <td className="px-1 py-2">{venda.cliente_nome}</td>
                      <td className="px-1 py-2 text-right font-medium whitespace-nowrap">
                        {formatarMoeda(venda.venda_bruta)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-green-700 whitespace-nowrap"
                        title="Taxa de entrega total cobrada do cliente"
                      >
                        +{formatarMoeda(venda.taxa_loja || 0)}
                      </td>
                      <td className="px-1 py-2 text-right text-red-600 whitespace-nowrap">
                        -{formatarMoeda(venda.desconto)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-blue-600 whitespace-nowrap"
                        title="Comissão repassada ao entregador"
                      >
                        -{formatarMoeda(venda.taxa_entrega)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-orange-500 whitespace-nowrap"
                        title="Custo operacional da entrega (empresa)"
                      >
                        -{formatarMoeda(venda.taxa_operacional || 0)}
                      </td>
                      <td className="px-1 py-2 text-right text-purple-600 whitespace-nowrap">
                        -{formatarMoeda(venda.taxa_cartao)}
                      </td>
                      <td className="px-1 py-2 text-right text-blue-600 whitespace-nowrap">
                        -{formatarMoeda(venda.comissao)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-pink-600 whitespace-nowrap"
                        title="Impostos sobre faturamento"
                      >
                        -{formatarMoeda(venda.imposto || 0)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-teal-600 whitespace-nowrap"
                        title="Custo com campanhas (cashback/cupom resgatado)"
                      >
                        {venda.custo_campanha > 0
                          ? `-${formatarMoeda(venda.custo_campanha)}`
                          : "—"}
                      </td>
                      <td className="px-1 py-2 text-right font-medium whitespace-nowrap">
                        {formatarMoeda(venda.venda_liquida)}
                      </td>
                      <td className="px-1 py-2 text-right text-orange-600 whitespace-nowrap">
                        -{formatarMoeda(venda.custo_produtos)}
                      </td>
                      <td
                        className={`px-1 py-2 text-right font-bold whitespace-nowrap ${venda.lucro >= 0 ? "text-green-600" : "text-red-600"}`}
                      >
                        {formatarMoeda(venda.lucro)}
                      </td>
                      <td className="px-1 py-2 text-right whitespace-nowrap">
                        {venda.margem_sobre_venda}%
                      </td>
                      <td className="px-1 py-2 text-right whitespace-nowrap">
                        {venda.margem_sobre_custo}%
                      </td>
                      <td className="px-2 py-2 text-center">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            venda.status === "finalizada"
                              ? "bg-green-100 text-green-800"
                              : venda.status === "baixa_parcial"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {venda.status === "finalizada"
                            ? "Baixada"
                            : venda.status === "baixa_parcial"
                              ? "Parcial"
                              : "Aberta"}
                        </span>
                      </td>
                    </tr>

                    {/* Linha expandida com detalhes dos produtos */}
                    {vendasExpandidas.has(venda.id) &&
                      venda.itens &&
                      venda.itens.length > 0 && (
                        <tr key={`${venda.id}-detalhes`} className="bg-blue-50">
                          <td colSpan="19" className="px-4 py-3">
                            <div className="pl-8">
                              <div className="font-semibold text-gray-700 mb-2">
                                Produtos desta venda:
                              </div>
                              <table className="w-full text-xs">
                                <thead className="bg-blue-100">
                                  <tr>
                                    <th className="px-1 py-1 text-left">
                                      Produto
                                    </th>
                                    <th className="px-1 py-1 text-center">
                                      Qtd
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Preço Unit.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Venda Bruta
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx Loja
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Desconto
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Entr.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Oper.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Cartão
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Comissão
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Imposto
                                    </th>
                                    <th
                                      className="px-1 py-1 text-right"
                                      title="Cashback/cupom rateado neste item"
                                    >
                                      Campanha
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Líquido
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Custo Unit.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Custo Total
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Lucro
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      MG Venda
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      MG Custo
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {venda.itens.map((item, idx) => (
                                    <tr
                                      key={`${venda.id}-item-${item.produto_id || item.produto_nome || idx}`}
                                      className="border-b border-blue-200 hover:bg-blue-100"
                                    >
                                      <td className="px-1 py-1">
                                        {item.produto_nome}
                                      </td>
                                      <td className="px-1 py-1 text-center">
                                        {item.quantidade}
                                      </td>
                                      <td className="px-1 py-1 text-right whitespace-nowrap">
                                        {formatarMoeda(item.preco_unitario)}
                                      </td>
                                      <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                                        {formatarMoeda(item.venda_bruta)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-green-700 whitespace-nowrap">
                                        +{formatarMoeda(item.taxa_loja || 0)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-red-600 whitespace-nowrap">
                                        -{formatarMoeda(item.desconto)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                                        -{formatarMoeda(item.taxa_entrega)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-500 whitespace-nowrap">
                                        -
                                        {formatarMoeda(
                                          item.taxa_operacional || 0,
                                        )}
                                      </td>
                                      <td className="px-1 py-1 text-right text-purple-600 whitespace-nowrap">
                                        -{formatarMoeda(item.taxa_cartao)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                                        -{formatarMoeda(item.comissao)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-pink-600 whitespace-nowrap">
                                        -{formatarMoeda(item.imposto || 0)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-teal-600 whitespace-nowrap">
                                        {(item.campanha || 0) > 0
                                          ? `-${formatarMoeda(item.campanha)}`
                                          : "—"}
                                      </td>
                                      <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                                        {formatarMoeda(item.valor_liquido)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-600 whitespace-nowrap">
                                        {formatarMoeda(item.custo_unitario)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-600 font-medium whitespace-nowrap">
                                        -{formatarMoeda(item.custo_total)}
                                      </td>
                                      <td
                                        className={`px-1 py-1 text-right font-bold whitespace-nowrap ${item.lucro >= 0 ? "text-green-600" : "text-red-600"} cursor-help`}
                                        title={`Lucro unitário: ${formatarMoeda(item.lucro_unitario)}`}
                                      >
                                        {formatarMoeda(item.lucro)}
                                      </td>
                                      <td
                                        className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                                        title={`Margem: ${item.margem_sobre_venda}%`}
                                      >
                                        {item.margem_sobre_venda}%
                                      </td>
                                      <td
                                        className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                                        title={`Markup: ${item.margem_sobre_custo}%`}
                                      >
                                        {item.margem_sobre_custo}%
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba de Comparação */}
      {abaAtiva === "comparacao" && (
        <div>
          {/* Filtro de Tipo de Comparação */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center gap-4">
              <label
                htmlFor="tipo-comparacao-vendas"
                className="text-sm font-medium text-gray-700"
              >
                Tipo de Análise:
              </label>
              <select
                id="tipo-comparacao-vendas"
                value={tipoComparacao}
                onChange={(e) => setTipoComparacao(e.target.value)}
                className="border rounded px-4 py-2 text-sm bg-blue-50 font-medium min-w-[250px]"
              >
                <option value="financeiro">📊 Comparação Financeira</option>
                <option value="formas_pagamento">
                  💳 Por Forma de Pagamento
                </option>
                <option value="produtos">📦 Por Grupo de Produtos</option>
                <option value="funcionarios">👥 Por Funcionário</option>
              </select>

              <div className="ml-auto text-sm text-gray-600">
                <span className="font-medium">Período Atual:</span>{" "}
                {formatarData(dataInicio)} - {formatarData(dataFim)}
              </div>
            </div>
          </div>

          {/* Cards de Comparação - 3 Colunas */}
          {tipoComparacao === "financeiro" && (
            <>
              <div className="grid grid-cols-3 gap-6 mb-6">
                {/* Card 1 - Período Anterior */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-gray-300">
                  <div className="bg-gray-500 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Anterior</h3>
                    <p className="text-xs opacity-90 mt-1">
                      {getTextoComparacao()}
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">
                        Quantidade de Vendas
                      </div>
                      <div className="text-2xl font-bold text-gray-700">
                        {resumoComparacao.quantidade_vendas || 0}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">
                        {formatarMoeda(resumoComparacao.venda_bruta)}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">
                        {formatarMoeda(resumoComparacao.venda_liquida)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">
                        Valor Recebido
                      </div>
                      <div className="text-xl font-bold text-green-600">
                        {formatarMoeda(
                          resumoComparacao.venda_liquida -
                            resumoComparacao.em_aberto || 0,
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 2 - Período Atual */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-blue-500">
                  <div className="bg-blue-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Atual</h3>
                    <p className="text-xs opacity-90 mt-1">
                      {formatarData(dataInicio)} - {formatarData(dataFim)}
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">
                        Quantidade de Vendas
                      </div>
                      <div className="text-2xl font-bold text-gray-700">
                        {resumo.quantidade_vendas || 0}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">
                        {formatarMoeda(resumo.venda_bruta)}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">
                        {formatarMoeda(resumo.venda_liquida)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">
                        Valor Recebido
                      </div>
                      <div className="text-xl font-bold text-green-600">
                        {formatarMoeda(
                          resumo.venda_liquida - resumo.em_aberto || 0,
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 3 - Diferença/Variação */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-green-500">
                  <div className="bg-green-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📈 Diferença</h3>
                    <p className="text-xs opacity-90 mt-1">
                      Variação vs período anterior
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    {(() => {
                      const varQtd = calcularVariacao(
                        resumo.quantidade_vendas,
                        resumoComparacao.quantidade_vendas,
                      );
                      const varBruto = calcularVariacao(
                        resumo.venda_bruta,
                        resumoComparacao.venda_bruta,
                      );
                      const varLiquido = calcularVariacao(
                        resumo.venda_liquida,
                        resumoComparacao.venda_liquida,
                      );
                      const valorRecebidoAtual =
                        resumo.venda_liquida - resumo.em_aberto;
                      const valorRecebidoAnt =
                        resumoComparacao.venda_liquida -
                        resumoComparacao.em_aberto;
                      const varRecebido = calcularVariacao(
                        valorRecebidoAtual,
                        valorRecebidoAnt,
                      );

                      return (
                        <>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Qtd de Vendas
                            </div>
                            <div
                              className={`text-2xl font-bold flex items-center gap-2 ${varQtd.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varQtd.percentual >= 0 ? (
                                <ArrowUp className="w-6 h-6" />
                              ) : (
                                <ArrowDown className="w-6 h-6" />
                              )}
                              {Math.abs(varQtd.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {varQtd.valor >= 0 ? "+" : ""}
                              {varQtd.valor.toFixed(0)} vendas
                            </div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Valor Bruto
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varBruto.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varBruto.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varBruto.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varBruto.valor)}
                            </div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Valor Líquido
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varLiquido.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varLiquido.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varLiquido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varLiquido.valor)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-600">
                              Valor Recebido
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varRecebido.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varRecebido.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varRecebido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varRecebido.valor)}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {/* Gráfico de Barras Comparativo */}
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={[
                      {
                        nome: "Qtd Vendas",
                        Anterior: resumoComparacao.quantidade_vendas || 0,
                        Atual: resumo.quantidade_vendas || 0,
                      },
                      {
                        nome: "Vl. Bruto (mil)",
                        Anterior: (resumoComparacao.venda_bruta || 0) / 1000,
                        Atual: (resumo.venda_bruta || 0) / 1000,
                      },
                      {
                        nome: "Vl. Líquido (mil)",
                        Anterior: (resumoComparacao.venda_liquida || 0) / 1000,
                        Atual: (resumo.venda_liquida || 0) / 1000,
                      },
                      {
                        nome: "Vl. Recebido (mil)",
                        Anterior:
                          (resumoComparacao.venda_liquida -
                            resumoComparacao.em_aberto || 0) / 1000,
                        Atual:
                          (resumo.venda_liquida - resumo.em_aberto || 0) / 1000,
                      },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" />
                    <YAxis />
                    <Tooltip
                      formatter={(value, name) => [
                        name.includes("mil")
                          ? `R$ ${value.toFixed(1)}k`
                          : value.toFixed(0),
                        name,
                      ]}
                    />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#3B82F6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Forma de Pagamento */}
          {tipoComparacao === "formas_pagamento" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Forma de Pagamento
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          Forma de Pagamento
                        </th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {formasRecebimento.map((formaAtual, idx) => {
                        const formaAnt = formasRecebimentoComparacao.find(
                          (f) =>
                            f.forma_pagamento === formaAtual.forma_pagamento,
                        ) || { valor_total: 0 };
                        const variacao = calcularVariacao(
                          formaAtual.valor_total,
                          formaAnt.valor_total,
                        );
                        return (
                          <tr key={`comp-forma-${formaAtual.forma_pagamento || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {formaAtual.forma_pagamento}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(formaAnt.valor_total)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(formaAtual.valor_total)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatarMoeda(variacao.valor)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Forma de Pagamento */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={formasRecebimento.map((f) => ({
                      nome: f.forma_pagamento,
                      Anterior:
                        (formasRecebimentoComparacao.find(
                          (fa) => fa.forma_pagamento === f.forma_pagamento,
                        )?.valor_total || 0) / 1000,
                      Atual: f.valor_total / 1000,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="nome"
                      angle={-15}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      tickFormatter={(value) => `R$ ${value.toFixed(0)}k`}
                    />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#10B981" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Grupo de Produtos */}
          {tipoComparacao === "produtos" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Grupo de Produtos
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Grupo</th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorGrupo.map((grupoAtual, idx) => {
                        const grupoAnt = vendasPorGrupoComparacao.find(
                          (g) => g.grupo === grupoAtual.grupo,
                        ) || { valor_liquido: 0 };
                        const variacao = calcularVariacao(
                          grupoAtual.valor_liquido,
                          grupoAnt.valor_liquido,
                        );
                        return (
                          <tr key={`comp-grupo-${grupoAtual.grupo || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {grupoAtual.grupo}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(grupoAnt.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(grupoAtual.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatarMoeda(variacao.valor)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Pizza Duplo */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Período Anterior
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupoComparacao}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = (
                            (entry.valor_liquido /
                              vendasPorGrupoComparacao.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              )) *
                            100
                          ).toFixed(1);
                          return percent > 5 ? `${percent}%` : "";
                        }}
                      >
                        {vendasPorGrupoComparacao.map((entry, index) => (
                          <Cell
                            key={`cell-grupo-ant-${entry.grupo || index}`}
                            fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Período Atual
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupo}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = (
                            (entry.valor_liquido /
                              vendasPorGrupo.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              )) *
                            100
                          ).toFixed(1);
                          return percent > 5 ? `${percent}%` : "";
                        }}
                      >
                        {vendasPorGrupo.map((entry, index) => (
                          <Cell
                            key={`cell-grupo-atual-${entry.grupo || index}`}
                            fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {/* Comparação por Funcionário */}
          {tipoComparacao === "funcionarios" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Funcionário
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Funcionário</th>
                        <th className="px-4 py-3 text-right">Qtd Ant.</th>
                        <th className="px-4 py-3 text-right">Qtd Atual</th>
                        <th className="px-4 py-3 text-right">Vl. Ant.</th>
                        <th className="px-4 py-3 text-right">Vl. Atual</th>
                        <th className="px-4 py-3 text-center">Variação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorFuncionario.map((funcAtual, idx) => {
                        const funcAnt = vendasPorFuncionarioComparacao.find(
                          (f) => f.funcionario === funcAtual.funcionario,
                        ) || { quantidade: 0, valor_liquido: 0 };
                        const variacao = calcularVariacao(
                          funcAtual.valor_liquido,
                          funcAnt.valor_liquido,
                        );
                        return (
                          <tr key={`comp-func-${funcAtual.funcionario || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {funcAtual.funcionario}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {funcAnt.quantidade}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {funcAtual.quantidade}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(funcAnt.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(funcAtual.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Funcionário */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual - Valor Líquido
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={vendasPorFuncionario.map((f) => ({
                      nome: f.funcionario,
                      Anterior:
                        (vendasPorFuncionarioComparacao.find(
                          (fa) => fa.funcionario === f.funcionario,
                        )?.valor_liquido || 0) / 1000,
                      Atual: f.valor_liquido / 1000,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="nome"
                      angle={-15}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      tickFormatter={(value) => `R$ ${value.toFixed(0)}k`}
                    />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#8B5CF6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}

      {/* Aba de Análise Inteligente */}
      {abaAtiva === "analise" && (
        <div className="space-y-6">
          {/* Indicador de Carregamento */}
          {loading && (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          )}

          {/* Conteúdo da Análise */}
          {!loading && (
            <>
              {/* Header Informativo */}
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
                <div className="flex items-center gap-3 mb-2">
                  <svg
                    className="w-8 h-8"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  <h2 className="text-2xl font-bold">
                    Análise Inteligente de Produtos
                  </h2>
                </div>
                <p className="text-blue-100">
                  Identifique os produtos mais lucrativos e oportunidades de
                  melhoria no seu mix de produtos
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow-md p-4 border border-blue-100">
                  <div className="text-xs text-gray-500 mb-1">Previsao proximos 7 dias</div>
                  <div className="text-2xl font-bold text-blue-700">
                    {formatarMoeda(previsaoProximos7Dias)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Baseado na media diaria dos ultimos dias
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow-md p-4 border border-amber-100">
                  <div className="text-xs text-gray-500 mb-1">Alertas automaticos</div>
                  <div className="text-2xl font-bold text-amber-700">
                    {alertasInteligentesVendas.length}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Atualizados sempre que o periodo ou filtros mudam
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow-md p-4 border border-emerald-100">
                  <div className="text-xs text-gray-500 mb-1">Ticket medio estimado</div>
                  <div className="text-2xl font-bold text-emerald-700">
                    {formatarMoeda(
                      resumo.quantidade_vendas > 0
                        ? resumo.venda_liquida / resumo.quantidade_vendas
                        : 0,
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Periodo atual</div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Alertas Inteligentes Automaticos
                </h3>

                {alertasInteligentesVendas.length === 0 ? (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
                    Nenhum alerta critico no momento. O desempenho esta estavel para o periodo analisado.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {alertasInteligentesVendas.map((alerta) => {
                      const classes =
                        alerta.tipo === "critico"
                          ? "bg-red-50 border-red-200"
                          : alerta.tipo === "oportunidade"
                            ? "bg-blue-50 border-blue-200"
                            : "bg-amber-50 border-amber-200";
                      return (
                        <div key={alerta.id} className={`p-4 rounded-lg border ${classes}`}>
                          <div className="font-semibold text-gray-800">{alerta.titulo}</div>
                          <div className="text-sm text-gray-700 mt-1">{alerta.mensagem}</div>
                          <div className="text-sm text-gray-600 mt-2">
                            <strong>Acao sugerida:</strong> {alerta.recomendacao}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Produtos Mais Lucrativos */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center gap-2 mb-4">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 className="text-lg font-semibold">
                    🏆 Top Produtos por Lucro
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b-2">
                        <th className="text-left py-2 px-2">#</th>
                        <th className="text-left py-2 px-2">Produto</th>
                        <th className="text-left py-2 px-2">Marca</th>
                        <th className="text-right py-2 px-2">Qtd</th>
                        <th className="text-right py-2 px-2">Custo Unit.</th>
                        <th className="text-right py-2 px-2">Preço Venda</th>
                        <th className="text-right py-2 px-2">Margem %</th>
                        <th className="text-right py-2 px-2">Lucro Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {produtosMaisLucrativos.map((produto, index) => (
                        <tr key={`rank-${produto.nome}-${produto.marca || "sem-marca"}`} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-2">
                            <span
                              className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                                index === 0
                                  ? "bg-yellow-100 text-yellow-800"
                                  : index === 1
                                    ? "bg-gray-100 text-gray-800"
                                    : index === 2
                                      ? "bg-orange-100 text-orange-800"
                                      : "bg-blue-50 text-blue-800"
                              }`}
                            >
                              {index + 1}
                            </span>
                          </td>
                          <td className="py-3 px-2 font-medium">
                            {produto.nome}
                          </td>
                          <td className="py-3 px-2 text-gray-600">
                            {produto.marca || "-"}
                          </td>
                          <td className="py-3 px-2 text-right">
                            {sanitizarNumero(produto.quantidade)}
                          </td>
                          <td className="py-3 px-2 text-right text-red-600">
                            {formatarMoeda(sanitizarNumero(produto.custo))}
                          </td>
                          <td className="py-3 px-2 text-right text-green-600">
                            {formatarMoeda(sanitizarNumero(produto.preco))}
                          </td>
                          <td className="py-3 px-2 text-right">
                            <span
                              className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                                sanitizarNumero(produto.margem) >= 50
                                  ? "bg-green-100 text-green-800"
                                  : sanitizarNumero(produto.margem) >= 30
                                    ? "bg-yellow-100 text-yellow-800"
                                    : "bg-red-100 text-red-800"
                              }`}
                            >
                              {sanitizarNumero(produto.margem).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-3 px-2 text-right font-bold text-green-600">
                            {formatarMoeda(
                              sanitizarNumero(produto.lucro_total),
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Análise por Categoria */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                  📊 Desempenho por Categoria
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(produtosPorCategoria).map(
                    ([categoria, dados]) => (
                      <div
                        key={categoria}
                        className="border rounded-lg p-4 hover:shadow-lg transition-shadow"
                      >
                        <div className="font-semibold text-gray-800 mb-2">
                          {categoria}
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Vendas:</span>
                            <span className="font-semibold">
                              {sanitizarNumero(dados.quantidade)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Faturamento:</span>
                            <span className="font-semibold text-green-600">
                              {formatarMoeda(sanitizarNumero(dados.total))}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Margem Média:</span>
                            <span
                              className={`font-semibold ${
                                sanitizarNumero(dados.margem_media) >= 40
                                  ? "text-green-600"
                                  : sanitizarNumero(dados.margem_media) >= 25
                                    ? "text-yellow-600"
                                    : "text-red-600"
                              }`}
                            >
                              {sanitizarNumero(dados.margem_media).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>

              {/* Alertas e Recomendações */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Produtos com Baixa Margem */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <svg
                      className="w-6 h-6 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <h3 className="text-lg font-semibold">
                      ⚠️ Atenção: Margens Baixas
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {produtosMaisLucrativos
                      .filter((p) => sanitizarNumero(p.margem) < 25)
                      .slice(0, 5)
                      .map((produto, index) => (
                        <div
                          key={`margem-baixa-${produto.nome}-${produto.marca || "sem-marca"}`}
                          className="p-3 bg-red-50 rounded-lg border-l-4 border-red-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            Margem:{" "}
                            <span className="font-semibold text-red-600">
                              {sanitizarNumero(produto.margem).toFixed(1)}%
                            </span>
                            {" - "}Revisar preço de custo ou venda
                          </div>
                        </div>
                      ))}
                    {produtosMaisLucrativos.filter(
                      (p) => sanitizarNumero(p.margem) < 25,
                    ).length === 0 && (
                      <div className="text-center text-gray-500 py-4">
                        ✅ Nenhum produto com margem crítica
                      </div>
                    )}
                  </div>
                </div>

                {/* Oportunidades */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <svg
                      className="w-6 h-6 text-blue-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                    <h3 className="text-lg font-semibold">💡 Oportunidades</h3>
                  </div>
                  <div className="space-y-3">
                    {produtosMaisLucrativos
                      .filter(
                        (p) =>
                          sanitizarNumero(p.margem) >= 40 &&
                          sanitizarNumero(p.quantidade) < 10,
                      )
                      .slice(0, 3)
                      .map((produto, index) => (
                        <div
                          key={`oportunidade-${produto.nome}-${produto.marca || "sem-marca"}`}
                          className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-blue-800 mt-1">
                            <strong>
                              Alta margem (
                              {sanitizarNumero(produto.margem).toFixed(1)}%)
                            </strong>{" "}
                            mas poucas vendas (
                            {sanitizarNumero(produto.quantidade)} un.)
                            <br />
                            💬 Considere promover este produto
                          </div>
                        </div>
                      ))}
                    {produtosMaisLucrativos
                      .filter((p) => sanitizarNumero(p.margem) >= 40)
                      .slice(0, 2)
                      .map((produto, index) => (
                        <div
                          key={`camp-${produto.nome || index}`}
                          className="p-3 bg-green-50 rounded-lg border-l-4 border-green-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-green-800 mt-1">
                            <strong>⭐ Campeão de vendas</strong> com excelente
                            margem
                            <br />
                            💬 Mantenha em destaque
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              {/* Gráfico de Margem vs Volume */}
              {mostrarGraficos && produtosMaisLucrativos.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    📈 Margem vs Volume de Vendas
                  </h3>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart
                      data={produtosMaisLucrativos.slice(0, 15).map((p) => ({
                        ...p,
                        margem: sanitizarNumero(p.margem),
                        quantidade: sanitizarNumero(p.quantidade),
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="nome"
                        angle={-45}
                        textAnchor="end"
                        height={120}
                        interval={0}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        yAxisId="left"
                        orientation="left"
                        stroke="#10B981"
                        label={{
                          value: "Margem %",
                          angle: -90,
                          position: "insideLeft",
                        }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#3B82F6"
                        label={{
                          value: "Quantidade",
                          angle: 90,
                          position: "insideRight",
                        }}
                      />
                      <Tooltip />
                      <Legend />
                      <Bar
                        yAxisId="left"
                        dataKey="margem"
                        fill="#10B981"
                        name="Margem %"
                      />
                      <Bar
                        yAxisId="right"
                        dataKey="quantidade"
                        fill="#3B82F6"
                        name="Qtd Vendida"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Aba Histórico por Cliente */}
      {abaAtiva === "historico-cliente" && <HistoricoVendasClienteTab />}
    </div>
  );
}
