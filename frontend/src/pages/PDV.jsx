// ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
// Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
// NÃO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenário real
// 3. Validar impacto financeiro

import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { getProdutosVendaveis } from "../api/produtos";
import PDVDriveAlertBanner from "../components/pdv/PDVDriveAlertBanner";
import PDVAssistenteSidebar from "../components/pdv/PDVAssistenteSidebar";
import PDVClienteCard from "../components/pdv/PDVClienteCard";
import PDVClienteSidebar from "../components/pdv/PDVClienteSidebar";
import PDVAcoesFooterCard from "../components/pdv/PDVAcoesFooterCard";
import PDVComissaoCard from "../components/pdv/PDVComissaoCard";
import PDVEntregaCard from "../components/pdv/PDVEntregaCard";
import PDVHeaderBar from "../components/pdv/PDVHeaderBar";
import PDVInfoBanners from "../components/pdv/PDVInfoBanners";
import PDVModalsLayer from "../components/pdv/PDVModalsLayer";
import PDVModoVisualizacaoBanner from "../components/pdv/PDVModoVisualizacaoBanner";
import PDVObservacoesCard from "../components/pdv/PDVObservacoesCard";
import PDVOportunidadesSidebar from "../components/pdv/PDVOportunidadesSidebar";
import PDVProdutosCard from "../components/pdv/PDVProdutosCard";
import PDVResumoFinanceiroCard from "../components/pdv/PDVResumoFinanceiroCard";
import PDVVendasRecentesSidebar from "../components/pdv/PDVVendasRecentesSidebar";
import { useAuth } from "../contexts/AuthContext";
import { usePDVAnalisePagamento } from "../hooks/usePDVAnalisePagamento";
import { usePDVAssistente } from "../hooks/usePDVAssistente";
import { usePDVCliente } from "../hooks/usePDVCliente";
import { usePDVComissao } from "../hooks/usePDVComissao";
import { usePDVDescontos } from "../hooks/usePDVDescontos";
import { usePDVEntrega } from "../hooks/usePDVEntrega";
import { usePDVOportunidades } from "../hooks/usePDVOportunidades";
import { usePDVSalvarVenda } from "../hooks/usePDVSalvarVenda";
import { usePDVVendasRecentes } from "../hooks/usePDVVendasRecentes";
import { usePDVVendaAtual } from "../hooks/usePDVVendaAtual";
import { usePersistentBooleanState } from "../hooks/usePersistentBooleanState";
import { contarRacoes, ehRacao } from "../helpers/deteccaoRacao";
import { useTour } from "../hooks/useTour";
import { tourPDV } from "../tours/tourDefinitions";
import { debugLog } from "../utils/debug";
import { formatBRL } from "../utils/formatters";
import { getGuiaClassNames } from "../utils/guiaHighlight";

export default function PDV() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const guiaAtiva = searchParams.get("guia");
  const destaqueAbrirCaixa = guiaAtiva === "abrir-caixa";
  const destaqueVenda =
    guiaAtiva === "venda-sem-entrega" ||
    guiaAtiva === "venda-com-entrega" ||
    guiaAtiva === "venda-com-comissao";
  const caixaGuiaClasses = getGuiaClassNames(destaqueAbrirCaixa);
  const vendaGuiaClasses = getGuiaClassNames(destaqueVenda);
  const { user } = useAuth();
  const { iniciarTour } = useTour("pdv", tourPDV, { delay: 1200 });

  // 🔒 Controle de visibilidade de dados gerenciais (lucro, margem, custos)
  const podeVerMargem = user?.is_admin === true;

  // Estado da venda atual
  const [vendaAtual, setVendaAtual] = useState({
    cliente: null,
    pet: null,
    itens: [],
    subtotal: 0,
    desconto_valor: 0,
    desconto_percentual: 0,
    total: 0,
    observacoes: "",
    funcionario_id: null, // ✅ Funcionário para comissão
    entregador_id: null, // 🚚 Entregador para entrega
    tem_entrega: false,
    entrega: {
      endereco_completo: "",
      taxa_entrega_total: 0,
      taxa_loja: 0,
      taxa_entregador: 0,
      observacoes_entrega: "",
    },
  });

  // Estados de busca
  const [buscarProduto, setBuscarProduto] = useState("");
  const [produtosSugeridos, setProdutosSugeridos] = useState([]);
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] = useState(false);

  // Estados de UI
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalCliente, setMostrarModalCliente] = useState(false);
  const [mostrarModalAbrirCaixa, setMostrarModalAbrirCaixa] = useState(false);
  const [mostrarVendasEmAberto, setMostrarVendasEmAberto] = useState(false);
  const [mostrarHistoricoCliente, setMostrarHistoricoCliente] = useState(false);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] =
    useState(false);
  const [copiadoCodigoItem, setCopiadoCodigoItem] = useState("");
  const [mostrarPendenciasEstoque, setMostrarPendenciasEstoque] =
    useState(false);
  const [pendenciasCount, setPendenciasCount] = useState(0);
  const [pendenciasProdutoIds, setPendenciasProdutoIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modoVisualizacao, setModoVisualizacao] = useState(false);
  const [searchVendaQuery, setSearchVendaQuery] = useState("");
  const [caixaKey, setCaixaKey] = useState(0); // Para forçar recarga do MenuCaixa
  const [temCaixaAberto, setTemCaixaAberto] = useState(false);

  // Estados do modal de endereço
  const [mostrarModalEndereco, setMostrarModalEndereco] = useState(false);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);

  // Estados do drawer de análise de venda

  // Estado para controlar expansão de itens KIT no carrinho
  const [itensKitExpandidos, setItensKitExpandidos] = useState({});

  // Estados de controle de painéis laterais (UX - FASE 1)
  const [painelVendasAberto, setPainelVendasAberto] =
    usePersistentBooleanState("pdv_painel_vendas_aberto", false);

  const [painelClienteAberto, setPainelClienteAberto] =
    usePersistentBooleanState("pdv_painel_cliente_aberto", false);

  const {
    buscarCliente,
    setBuscarCliente,
    clientesSugeridos,
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    buscarClientePorCodigoExato,
    selecionarCliente,
    selecionarPet,
    copiarCampoCliente,
    limparClienteSelecionado,
    handleClienteCriadoRapido: handleClienteCriadoRapidoHook,
    recarregarVendasEmAbertoClienteAtual,
  } = usePDVCliente({
    vendaAtual,
    setVendaAtual,
  });

  const {
    vendasRecentes,
    filtroVendas,
    setFiltroVendas,
    filtroStatus,
    setFiltroStatus,
    confirmandoRetirada,
    setConfirmandoRetirada,
    filtroTemEntrega,
    setFiltroTemEntrega,
    buscaNumeroVenda,
    setBuscaNumeroVenda,
    driveAguardando,
    driveAlertVisible,
    carregarVendasRecentes,
    confirmarDriveEntregue,
    abrirConfirmacaoRetirada,
    confirmarRetirada,
    fecharDriveAlert,
  } = usePDVVendasRecentes();

  // 🆕 Estados fiscais do PDV (PDV-UX-01)
  const [fiscalItens, setFiscalItens] = useState({});
  const [totalImpostos, setTotalImpostos] = useState(0);

  // 🆕 Estados para Calculadora de Ração no PDV
const [mostrarCalculadoraRacao, setMostrarCalculadoraRacao] = useState(false);
const [racaoIdFechada, setRacaoIdFechada] = useState(null); // ID da ração fechada (não reabre automático)

  // Refs
  const inputProdutoRef = useRef(null);
  const buscaProdutoContainerRef = useRef(null);
  const ultimoAutoAddProdutoRef = useRef("");
  const ultimoEventoTeclaProdutoMsRef = useRef(0);
  const sequenciaRapidaProdutoRef = useRef(0);
  const leituraScannerDetectadaRef = useRef(false);
  const adicionandoProdutoPorEnterRef = useRef(false);
  const buscaProdutoAtualRef = useRef("");
  const {
    painelAssistenteAberto,
    setPainelAssistenteAberto,
    mensagensAssistente,
    inputAssistente,
    setInputAssistente,
    enviandoAssistente,
    chatAssistenteEndRef,
    alertasCarrinho,
    infosCarrinho,
    enviarMensagemAssistente,
    alternarPainelAssistente,
  } = usePDVAssistente(vendaAtual);
  const {
    painelOportunidadesAberto,
    setPainelOportunidadesAberto,
    opportunities,
    abrirPainelOportunidades,
    adicionarOportunidadeAoCarrinho,
    buscarAlternativaOportunidade,
    ignorarOportunidade,
  } = usePDVOportunidades(vendaAtual, user?.id);
  const {
    entregadores,
    entregadorSelecionado,
    sincronizarEntregadorDaVenda,
    handleToggleTemEntrega,
    handleSelecionarEnderecoEntrega,
    handleEnderecoEntregaChange,
    handleSelecionarEntregador,
    handleTaxaEntregaTotalChange,
    handleTaxaLojaChange,
    handleTaxaEntregadorChange,
    handleObservacoesEntregaChange,
  } = usePDVEntrega(vendaAtual, setVendaAtual);
  const {
    vendaComissionada,
    funcionarioComissao,
    funcionariosSugeridos,
    buscaFuncionario,
    sincronizarComissaoDaVenda,
    handleToggleVendaComissionada,
    handleBuscaFuncionarioFocus,
    handleBuscaFuncionarioChange,
    handleSelecionarFuncionarioComissao,
    handleRemoverFuncionarioComissao,
    limparComissao,
  } = usePDVComissao(setVendaAtual, modoVisualizacao);
  const {
    carregarVendaEspecifica,
    handleBuscarVenda,
    abrirModalPagamento,
    limparVenda,
    reabrirVenda,
  } = usePDVVendaAtual({
    vendaAtual,
    setVendaAtual,
    searchVendaQuery,
    setSearchVendaQuery,
    setLoading,
    setModoVisualizacao,
    setMostrarModalPagamento,
    entregadorSelecionado,
    limparComissao,
    sincronizarComissaoDaVenda,
    sincronizarEntregadorDaVenda,
  });
  const { salvarVenda } = usePDVSalvarVenda({
    vendaAtual,
    loading,
    setLoading,
    temCaixaAberto,
    entregadorSelecionado,
    vendaComissionada,
    funcionarioComissao,
    limparVenda,
    carregarVendasRecentes: () => carregarVendasRecentes(),
  });
  const {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  } = usePDVDescontos({
    vendaAtual,
    setVendaAtual,
  });
  const {
    mostrarAnaliseVenda,
    setMostrarAnaliseVenda,
    dadosAnalise,
    carregandoAnalise,
    analisarVendaComFormasPagamento,
    habilitarEdicao,
    cancelarEdicao,
    excluirVenda,
    mudarStatusParaAberta,
    emitirNotaVendaFinalizada,
    handleConfirmarPagamento,
    handleVendaAtualizadaAposPagamento,
  } = usePDVAnalisePagamento({
    vendaAtual,
    setVendaAtual,
    setLoading,
    modoVisualizacao,
    setModoVisualizacao,
    setMostrarModalPagamento,
    limparVenda,
    carregarVendaEspecifica,
    carregarVendasRecentes: () => carregarVendasRecentes(),
  });

  // Carregar pendências quando o cliente mudar
  useEffect(() => {
    if (vendaAtual.cliente) {
      carregarPendencias();
    }
  }, [vendaAtual.cliente]);

  // Salvar dados do carrinho no sessionStorage para a calculadora universal
  useEffect(() => {
    if (vendaAtual.itens && vendaAtual.itens.length > 0) {
      sessionStorage.setItem(
        "pdv_calculadora_data",
        JSON.stringify({
          itens: vendaAtual.itens,
          clienteId: vendaAtual.cliente?.id || null,
        }),
      );
    } else {
      sessionStorage.removeItem("pdv_calculadora_data");
    }
  }, [vendaAtual.itens, vendaAtual.cliente]);

  // Verificar se há caixa aberto
  useEffect(() => {
    verificarCaixaAberto();

    // 🔄 Verificar caixa a cada 30 segundos (polling)
    const intervalId = setInterval(() => {
      verificarCaixaAberto();
    }, 30000); // 30 segundos

    return () => clearInterval(intervalId); // Limpar interval ao desmontar
  }, [caixaKey]);

  const verificarCaixaAberto = async () => {
    try {
      const response = await api.get("/caixas/aberto");
      setTemCaixaAberto(!!response.data); // true se houver caixa, false se não
    } catch (error) {
      setTemCaixaAberto(false);
    }
  };

  // Adicionar produto à lista de espera direto da busca (estoque zerado)
  const adicionarNaListaEsperaRapido = async (produto, e) => {
    e.stopPropagation();
    if (!vendaAtual.cliente) {
      toast.error("Selecione um cliente primeiro");
      return;
    }
    try {
      await api.post("/pendencias-estoque/", {
        cliente_id: vendaAtual.cliente.id,
        produto_id: produto.id,
        quantidade_desejada: 1,
        prioridade: 1,
        observacoes: null,
      });
      toast.success(`"${produto.nome}" adicionado à lista de espera!`);
      setBuscarProduto("");
      setProdutosSugeridos([]);
      carregarPendencias();
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Erro ao adicionar à lista de espera",
      );
    }
  };

  // Carregar pendências de estoque do cliente
  const carregarPendencias = async () => {
    if (!vendaAtual.cliente) {
      setPendenciasCount(0);
      return;
    }

    try {
      const response = await api.get(
        `/pendencias-estoque/cliente/${vendaAtual.cliente.id}`,
      );
      const todas = Array.isArray(response.data?.pendencias) ? response.data.pendencias : [];
      const pendenciasAtivas = todas.filter(
        (p) => p.status === "pendente" || p.status === "notificado",
      );
      setPendenciasCount(pendenciasAtivas.length);
      setPendenciasProdutoIds(pendenciasAtivas.map((p) => p.produto_id));
    } catch (error) {
      setPendenciasCount(0);
      setPendenciasProdutoIds([]);
    }
  };

  // 🆕 Função para calcular fiscal de um item (PDV-UX-01)
  async function calcularFiscalItem(item) {
    try {
      const payload = {
        produto_id: item.produto_id,
        preco_unitario: item.preco_unitario,
        quantidade: item.quantidade,
      };

      const { data } = await api.post("/pdv/fiscal/calcular", payload);
      return data;
    } catch (error) {
      console.error("Erro ao calcular fiscal:", error);
      return null;
    }
  }

  // 🆕 Recalcular fiscal sempre que o carrinho mudar (PDV-UX-01)
  useEffect(() => {
    async function recalcularFiscal() {
      let impostosTotais = 0;
      const fiscais = {};

      for (const item of vendaAtual.itens) {
        const fiscal = await calcularFiscalItem(item);
        if (fiscal) {
          fiscais[item.produto_id] = fiscal;
          impostosTotais += Number(fiscal.total_impostos);
        }
      }

      setFiscalItens(fiscais);
      setTotalImpostos(impostosTotais.toFixed(2));
    }

    if (vendaAtual.itens && vendaAtual.itens.length > 0) {
      recalcularFiscal();
    } else {
      setFiscalItens({});
      setTotalImpostos(0);
    }
  }, [vendaAtual.itens]);

  // Carregar venda específica se vier na URL
  useEffect(() => {
    const vendaId =
      searchParams.get("venda") ||
      searchParams.get("vendaId") ||
      searchParams.get("venda_id");
    if (vendaId) {
      carregarVendaEspecifica(Number.parseInt(vendaId));
    }
  }, [searchParams]);

  useEffect(() => {
    if (destaqueAbrirCaixa && !temCaixaAberto && !mostrarModalAbrirCaixa) {
      setMostrarModalAbrirCaixa(true);
    }
  }, [destaqueAbrirCaixa, temCaixaAberto, mostrarModalAbrirCaixa]);

  // 🆕 DETECTAR REDIRECIONAMENTO DO CONTAS A RECEBER
  useEffect(() => {
    const vendaId = sessionStorage.getItem("abrirVenda");
    const abrirModal = sessionStorage.getItem("abrirModalPagamento");

    if (vendaId && abrirModal === "true") {
      // Limpa os dados do sessionStorage
      sessionStorage.removeItem("abrirVenda");
      sessionStorage.removeItem("abrirModalPagamento");

      // Carrega a venda e abre o modal
      carregarVendaEspecifica(Number.parseInt(vendaId), true);
    }
  }, []);

  // Funções do modal de endereço
  const abrirModalEnderecoPDV = () => {
    setEnderecoAtual({
      tipo: "entrega",
      apelido: "",
      cep: "",
      endereco: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      estado: "",
    });
    setMostrarModalEndereco(true);
  };

  const fecharModalEndereco = () => {
    setMostrarModalEndereco(false);
    setEnderecoAtual(null);
  };

  const buscarCepModal = async (cep) => {
    if (!cep || cep.length !== 9) return;

    setLoadingCep(true);
    try {
      const response = await fetch(
        `https://viacep.com.br/ws/${cep.replace("-", "")}/json/`,
      );
      const data = await response.json();

      if (data.erro) {
        alert("CEP não encontrado");
        return;
      }

      setEnderecoAtual((prev) => ({
        ...prev,
        endereco: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
      }));
    } catch (error) {
      console.error("Erro ao buscar CEP:", error);
      alert("Erro ao buscar CEP");
    } finally {
      setLoadingCep(false);
    }
  };

  const salvarEnderecoNoCliente = async () => {
    if (
      !enderecoAtual.cep ||
      !enderecoAtual.endereco ||
      !enderecoAtual.cidade
    ) {
      alert("Preencha pelo menos CEP, Endereço e Cidade");
      return;
    }

    if (!vendaAtual.cliente || !vendaAtual.cliente.id) {
      alert("Selecione um cliente primeiro");
      return;
    }

    try {
      // Buscar dados atuais do cliente
      const clienteAtual = await buscarClientePorId(vendaAtual.cliente.id);

      // Adicionar novo endereço ao array de enderecos_adicionais
      const enderecosAdicionais = clienteAtual.enderecos_adicionais || [];
      enderecosAdicionais.push({ ...enderecoAtual });

      // Atualizar cliente no backend
      await api.put(`/clientes/${vendaAtual.cliente.id}`, {
        ...clienteAtual,
        enderecos_adicionais: enderecosAdicionais,
      });

      // Atualizar cliente na venda atual
      const clienteAtualizado = await buscarClientePorId(vendaAtual.cliente.id);
      setVendaAtual({
        ...vendaAtual,
        cliente: clienteAtualizado,
      });

      alert("Endereço adicionado com sucesso!");
      fecharModalEndereco();
    } catch (error) {
      console.error("Erro ao salvar endereço:", error);
      alert("Erro ao salvar endereço. Tente novamente.");
    }
  };

  // fluxo de descontos/cupom movido para usePDVDescontos

  const handleNovaVenda = () => {
    if (window.confirm("Descartar venda atual sem salvar?")) {
      limparVenda();
    }
  };

  // carregarVendaEspecifica e handleBuscarVenda movidos para usePDVVendaAtual

  // Buscar produtos
  useEffect(() => {
    const termoAtual = String(buscarProduto || "").trim();
    buscaProdutoAtualRef.current = termoAtual;

    if (termoAtual.length >= 2) {
      setMostrarSugestoesProduto(true);
      const timer = setTimeout(async () => {
        try {
          const response = await getProdutosVendaveis({ busca: termoAtual });

          // Evita reabrir sugestão com resposta atrasada após Enter/limpeza do campo
          if (buscaProdutoAtualRef.current !== termoAtual) {
            return;
          }

          const produtos = response.data.items || [];

          const termo = termoAtual;
          const termoLower = termo.toLowerCase();
          const matchExato = produtos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          });

          // Leitor costuma enviar Enter após o código; se encontrar match exato,
          // adiciona direto no carrinho para não exigir clique manual.
          if (
            matchExato &&
            ultimoAutoAddProdutoRef.current !== termoLower &&
            leituraScannerDetectadaRef.current &&
            !modoVisualizacao
          ) {
            ultimoAutoAddProdutoRef.current = termoLower;
            adicionarProduto(matchExato);
            leituraScannerDetectadaRef.current = false;
            sequenciaRapidaProdutoRef.current = 0;
            setMostrarSugestoesProduto(false);
            return;
          }

          setProdutosSugeridos(produtos);
        } catch (error) {
          console.error("Erro ao buscar produtos:", error);
          setProdutosSugeridos([]);
        }
      }, 300);
      return () => clearTimeout(timer);
    } else {
      ultimoAutoAddProdutoRef.current = "";
      leituraScannerDetectadaRef.current = false;
      sequenciaRapidaProdutoRef.current = 0;
      setProdutosSugeridos([]);
      setMostrarSugestoesProduto(false);
    }
  }, [buscarProduto, modoVisualizacao]);

  useEffect(() => {
    const handleCliqueFora = (event) => {
      if (!buscaProdutoContainerRef.current) return;
      if (!buscaProdutoContainerRef.current.contains(event.target)) {
        setMostrarSugestoesProduto(false);
      }
    };

    document.addEventListener("mousedown", handleCliqueFora);
    return () => document.removeEventListener("mousedown", handleCliqueFora);
  }, []);

  function registrarPossivelLeituraScanner(evento) {
    if (
      evento.key.length !== 1 ||
      evento.ctrlKey ||
      evento.altKey ||
      evento.metaKey
    ) {
      return;
    }

    const agora = Date.now();
    const delta = agora - ultimoEventoTeclaProdutoMsRef.current;
    ultimoEventoTeclaProdutoMsRef.current = agora;

    if (delta > 0 && delta <= 45) {
      sequenciaRapidaProdutoRef.current += 1;
    } else {
      sequenciaRapidaProdutoRef.current = 1;
    }

    // Leitores de código de barras digitam muito rápido; usuário no teclado não.
    leituraScannerDetectadaRef.current = sequenciaRapidaProdutoRef.current >= 6;
  }

  async function adicionarProdutoViaEnter() {
    const termo = String(buscarProduto || "").trim();
    if (!termo || modoVisualizacao || adicionandoProdutoPorEnterRef.current) {
      return;
    }

    adicionandoProdutoPorEnterRef.current = true;
    try {
      const termoLower = termo.toLowerCase();
      let produtoSelecionado = null;

      if (produtosSugeridos.length > 0) {
        produtoSelecionado =
          produtosSugeridos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          }) || produtosSugeridos[0];
      }

      if (!produtoSelecionado) {
        const response = await getProdutosVendaveis({ busca: termo });
        const produtos = response.data.items || [];
        produtoSelecionado =
          produtos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          }) || produtos[0] || null;
      }

      if (produtoSelecionado) {
        adicionarProduto(produtoSelecionado);
      }
    } catch (error) {
      console.error("Erro ao adicionar produto via Enter:", error);
    } finally {
      leituraScannerDetectadaRef.current = false;
      sequenciaRapidaProdutoRef.current = 0;
      adicionandoProdutoPorEnterRef.current = false;
    }
  }

  const copiarCodigoProdutoCarrinho = (codigo, chaveItem) => {
    if (!codigo) return;
    navigator.clipboard.writeText(String(codigo));
    setCopiadoCodigoItem(chaveItem);
    setTimeout(() => setCopiadoCodigoItem(""), 2000);
  };

  const handleBuscarProdutoChange = (valor) => {
    setBuscarProduto(valor);
    if (!String(valor || "").trim()) {
      setProdutosSugeridos([]);
      setMostrarSugestoesProduto(false);
    }
  };

  const handleBuscarProdutoFocus = () => {
    if (
      String(buscarProduto || "").trim().length >= 2 &&
      produtosSugeridos.length > 0
    ) {
      setMostrarSugestoesProduto(true);
    }
  };

  const handleBuscarProdutoKeyDown = async (e) => {
    registrarPossivelLeituraScanner(e);

    if (e.key === "Enter") {
      e.preventDefault();
      await adicionarProdutoViaEnter();
    }
  };

  const selecionarProdutoSugerido = (produto) => {
    adicionarProduto(produto);
    setMostrarSugestoesProduto(false);
  };

  // Adicionar produto ao carrinho
  const adicionarProduto = (produto) => {
    // 🔒 VALIDAÇÃO CRÍTICA: Verificar se tem caixa aberto ANTES de adicionar produto
    if (!temCaixaAberto) {
      alert(
        "❌ Não é possível adicionar produtos sem caixa aberto. Abra um caixa primeiro.",
      );
      return;
    }

    debugLog("🛒 Produto sendo adicionado:", {
      nome: produto.nome,
      categoria_id: produto.categoria_id,
      categoria_nome: produto.categoria_nome,
      peso_embalagem: produto.peso_embalagem,
      classificacao_racao: produto.classificacao_racao,
    });

    const itemExistente = vendaAtual.itens.find(
      (item) => item.produto_id === produto.id,
    );

    let novosItens;
    if (itemExistente) {
      // Incrementar quantidade
      novosItens = vendaAtual.itens.map((item) =>
        item.produto_id === produto.id
          ? {
              ...item,
              quantidade: item.quantidade + 1,
              subtotal: (item.quantidade + 1) * item.preco_unitario,
            }
          : item,
      );
    } else {
      // Adicionar novo item
      novosItens = [
        ...vendaAtual.itens,
        {
          tipo: "produto",
          produto_id: produto.id,
          produto_nome: produto.nome,
          produto_codigo: produto.codigo || null,
          quantidade: 1,
          preco_unitario: parseFloat(produto.preco_venda),
          desconto_item: 0,
          subtotal: parseFloat(produto.preco_venda),
          pet_id: vendaAtual.pet?.id || null, // Pet selecionado no topo (opcional)
          // Adicionar informações do KIT
          tipo_produto: produto.tipo_produto,
          tipo_kit: produto.tipo_kit,
          composicao_kit: produto.composicao_kit || [],
          // 🆕 Adicionar dados necessários para calculadora de ração
          categoria_id: produto.categoria_id,
          categoria_nome: produto.categoria_nome,
          peso_pacote_kg: produto.peso_liquido || produto.peso_bruto, // Usar peso do produto
          // 🎯 CAMPO PRINCIPAL para identificação de ração (usado pela calculadora antiga)
          peso_embalagem: produto.peso_embalagem,
          classificacao_racao: produto.classificacao_racao,
          estoque_atual: produto.estoque_atual,
          estoque_virtual: produto.estoque_virtual,
        },
      ];
    }

    recalcularTotais(novosItens);
    setBuscarProduto("");
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
    inputProdutoRef.current?.focus();

    // ✅ ABERTURA AUTOMÁTICA DESATIVADA
    // Modal agora abre apenas via botão flutuante (acionado manualmente)
    // Conforme requisito: "NÃO abrir automaticamente ao adicionar item"
  };

  // Alterar quantidade
  const alterarQuantidade = (index, delta) => {
    const novosItens = vendaAtual.itens.map((item, i) => {
      if (i === index) {
        const novaQuantidade = Math.max(1, item.quantidade + delta);
        const subtotalSemDesconto = novaQuantidade * item.preco_unitario;

        let novoDescontoValor = item.desconto_valor || 0;

        // 🆕 LÓGICA CORRIGIDA: Só recalcula se foi desconto PERCENTUAL
        if (
          item.tipo_desconto_aplicado === "percentual" &&
          item.desconto_percentual > 0
        ) {
          // Desconto percentual: recalcular o valor baseado na nova quantidade
          novoDescontoValor =
            (subtotalSemDesconto * item.desconto_percentual) / 100;
        }
        // Se foi desconto em VALOR: mantém o desconto_valor fixo

        const subtotalComDesconto = subtotalSemDesconto - novoDescontoValor;

        return {
          ...item,
          quantidade: novaQuantidade,
          desconto_valor: novoDescontoValor,
          subtotal: subtotalComDesconto,
        };
      }
      return item;
    });
    recalcularTotais(novosItens);
  };

  const atualizarQuantidadeItem = (index, novaQuantidade) => {
    const novosItens = vendaAtual.itens.map((it, i) => {
      if (i === index) {
        const subtotalSemDesconto = novaQuantidade * it.preco_unitario;
        let novoDescontoValor = it.desconto_valor || 0;

        if (
          it.tipo_desconto_aplicado === "percentual" &&
          it.desconto_percentual > 0
        ) {
          novoDescontoValor =
            (subtotalSemDesconto * it.desconto_percentual) / 100;
        }

        return {
          ...it,
          quantidade: novaQuantidade,
          desconto_valor: novoDescontoValor,
          subtotal: subtotalSemDesconto - novoDescontoValor,
        };
      }
      return it;
    });

    recalcularTotais(novosItens);
  };

  const atualizarPetDoItem = (index, petId) => {
    const novosItens = vendaAtual.itens.map((it, i) => {
      if (i === index) {
        return {
          ...it,
          pet_id: petId,
        };
      }
      return it;
    });

    setVendaAtual({
      ...vendaAtual,
      itens: novosItens,
    });
  };

  // 🥫 Abrir modal de calculadora de ração manualmente (via botão flutuante)
  const abrirCalculadoraRacao = () => {
    debugLog("🔍 Debug - Itens no carrinho:", vendaAtual.itens);
    debugLog("🔍 Debug - Verificando rações...");

    vendaAtual.itens.forEach((item, index) => {
      debugLog(`  Item ${index + 1}: ${item.produto_nome}`);
      debugLog(`    - peso_embalagem: ${item.peso_embalagem}`);
      debugLog(`    - classificacao_racao: ${item.classificacao_racao}`);
      debugLog(`    - categoria_id: ${item.categoria_id}`);
      debugLog(`    - categoria_nome: ${item.categoria_nome}`);
      debugLog(`    - É ração?: ${ehRacao(item)}`);
    });

    const racoes = contarRacoes(vendaAtual.itens);
    debugLog(`📊 Total de rações encontradas: ${racoes}`);

    if (racoes === 0) {
      toast.error("Nenhuma ração no carrinho");
      return;
    }

    setRacaoIdFechada(null); // Limpar ração fechada anterior
    setMostrarCalculadoraRacao(true);
  };

  // Remover item
  const removerItem = (index) => {
    const novosItens = vendaAtual.itens.filter((_, i) => i !== index);
    recalcularTotais(novosItens);
  };

  // Alternar expansão do item KIT
  const toggleKitExpansion = (index) => {
    setItensKitExpandidos((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  // salvarVenda movido para usePDVSalvarVenda
  // análise, pagamento e pós-finalização movidos para usePDVAnalisePagamento

  const handleAbrirCaixaSucesso = () => {
    setMostrarModalAbrirCaixa(false);
    setCaixaKey((prev) => prev + 1);
    setTemCaixaAberto(true);
  };

  const handleFecharCalculadoraRacao = () => {
    const racoes = vendaAtual.itens.filter((item) => {
      const nomeCategoria = (item.categoria_nome || "").toLowerCase();
      return (
        nomeCategoria.includes("ra\xe7\xe3o") || nomeCategoria.includes("racao")
      );
    });

    if (racoes.length > 0) {
      setRacaoIdFechada(racoes[racoes.length - 1].produto_id);
    }

    setMostrarCalculadoraRacao(false);
  };

  const handleClienteCriadoRapido = async (cliente) => {
    await handleClienteCriadoRapidoHook(cliente);
    setMostrarModalCliente(false);
  };

  const handleVendasEmAbertoSucesso = () => {
    void recarregarVendasEmAbertoClienteAtual();
  };

  const handleConfirmarCreditoCliente = (novoSaldo) => {
    setVendaAtual((prev) => ({
      ...prev,
      cliente: { ...prev.cliente, credito: novoSaldo },
    }));
    setMostrarModalAdicionarCredito(false);
  };

  return (
    <>
      <PDVDriveAlertBanner
        driveAlertVisible={driveAlertVisible}
        driveAguardando={driveAguardando}
        onClose={fecharDriveAlert}
        onConfirmarEntregue={confirmarDriveEntregue}
      />
      <div className="flex h-screen bg-gray-50" style={driveAlertVisible && driveAguardando.length > 0 ? { paddingTop: '52px' } : {}}>
        {/* Área Principal */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <PDVHeaderBar
            destaqueAbrirCaixa={destaqueAbrirCaixa}
            destaqueVenda={destaqueVenda}
            caixaGuiaClasses={caixaGuiaClasses}
            iniciarTour={iniciarTour}
            searchVendaQuery={searchVendaQuery}
            onSearchVendaQueryChange={setSearchVendaQuery}
            onBuscarVenda={handleBuscarVenda}
            vendaAtual={vendaAtual}
            pendenciasCount={pendenciasCount}
            opportunitiesCount={opportunities.length}
            painelAssistenteAberto={painelAssistenteAberto}
            mensagensAssistenteLength={mensagensAssistente.length}
            onAbrirPendenciasEstoque={() => setMostrarPendenciasEstoque(true)}
            onAbrirOportunidades={() => {
              void abrirPainelOportunidades();
            }}
            onToggleAssistente={() => {
              void alternarPainelAssistente();
            }}
            menuCaixaKey={caixaKey}
            onAbrirCaixa={() => setMostrarModalAbrirCaixa(true)}
            onNavigateMeusCaixas={() => navigate("/meus-caixas")}
            modoVisualizacao={modoVisualizacao}
            loading={loading}
            temCaixaAberto={temCaixaAberto}
            onCancelarEdicao={cancelarEdicao}
            onExcluirVenda={excluirVenda}
            onSalvarVenda={salvarVenda}
            onAbrirModalPagamento={abrirModalPagamento}
          />

          <PDVInfoBanners
            temCaixaAberto={temCaixaAberto}
            modoVisualizacao={modoVisualizacao}
            vendaAtual={vendaAtual}
          />
          <PDVModoVisualizacaoBanner
            ativo={modoVisualizacao}
            vendaAtual={vendaAtual}
            onVoltar={() => {
              setModoVisualizacao(false);
              limparVenda();
            }}
            emitirNotaVendaFinalizada={emitirNotaVendaFinalizada}
            mudarStatusParaAberta={mudarStatusParaAberta}
            habilitarEdicao={habilitarEdicao}
          />

          {/* Conteúdo Principal */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="max-w-5xl mx-auto space-y-4">
              <PDVClienteCard
                buscarCliente={buscarCliente}
                buscarClientePorCodigoExato={buscarClientePorCodigoExato}
                clientesSugeridos={clientesSugeridos}
                copiadoClienteCampo={copiadoClienteCampo}
                destaqueVenda={destaqueVenda}
                modoVisualizacao={modoVisualizacao}
                onAbrirCadastroCliente={() => setMostrarModalCliente(true)}
                onAbrirHistoricoCliente={() => setMostrarHistoricoCliente(true)}
                onAbrirModalAdicionarCredito={() =>
                  setMostrarModalAdicionarCredito(true)
                }
                onAbrirVendasEmAberto={() => setMostrarVendasEmAberto(true)}
                onBuscarClienteChange={setBuscarCliente}
                onCopiarCampoCliente={copiarCampoCliente}
                onRemoverCliente={limparClienteSelecionado}
                onSelecionarCliente={selecionarCliente}
                onSelecionarPet={selecionarPet}
                onTrocarCliente={limparClienteSelecionado}
                saldoCampanhas={saldoCampanhas}
                vendaAtual={vendaAtual}
                vendaGuiaClasses={vendaGuiaClasses}
                vendasEmAbertoInfo={vendasEmAbertoInfo}
              />

              <PDVProdutosCard
                buscaProduto={buscarProduto}
                buscaProdutoContainerRef={buscaProdutoContainerRef}
                copiadoCodigoItem={copiadoCodigoItem}
                inputProdutoRef={inputProdutoRef}
                itensKitExpandidos={itensKitExpandidos}
                modoVisualizacao={modoVisualizacao}
                mostrarSugestoesProduto={mostrarSugestoesProduto}
                onAbrirModalDescontoItem={abrirModalDescontoItem}
                onAdicionarNaListaEsperaRapido={adicionarNaListaEsperaRapido}
                onAlterarQuantidade={alterarQuantidade}
                onAtualizarPetItem={atualizarPetDoItem}
                onAtualizarQuantidadeItem={atualizarQuantidadeItem}
                onBuscarProdutoChange={handleBuscarProdutoChange}
                onBuscarProdutoFocus={handleBuscarProdutoFocus}
                onBuscarProdutoKeyDown={handleBuscarProdutoKeyDown}
                onCopiarCodigoProdutoCarrinho={copiarCodigoProdutoCarrinho}
                onRemoverItem={removerItem}
                onSelecionarProdutoSugerido={selecionarProdutoSugerido}
                onToggleKitExpansion={toggleKitExpansion}
                pendenciasProdutoIds={pendenciasProdutoIds}
                produtosSugeridos={produtosSugeridos}
                vendaAtual={vendaAtual}
              />

              <PDVObservacoesCard
                modoVisualizacao={modoVisualizacao}
                observacoes={vendaAtual.observacoes}
                onObservacoesChange={(observacoes) =>
                  setVendaAtual({
                    ...vendaAtual,
                    observacoes,
                  })
                }
              />

              <PDVEntregaCard
                cliente={vendaAtual.cliente}
                entregadorSelecionado={entregadorSelecionado}
                entregadores={entregadores}
                modoVisualizacao={modoVisualizacao}
                onAbrirModalEndereco={abrirModalEnderecoPDV}
                onEnderecoEntregaChange={handleEnderecoEntregaChange}
                onObservacoesEntregaChange={handleObservacoesEntregaChange}
                onSelecionarEndereco={handleSelecionarEnderecoEntrega}
                onSelecionarEntregador={handleSelecionarEntregador}
                onTaxaEntregaTotalChange={handleTaxaEntregaTotalChange}
                onTaxaEntregadorChange={handleTaxaEntregadorChange}
                onTaxaLojaChange={handleTaxaLojaChange}
                onToggleTemEntrega={handleToggleTemEntrega}
                vendaAtual={vendaAtual}
              />

              {/* Alertas de Pets no Carrinho (fase de vida / alergia) */}
              <PDVResumoFinanceiroCard
                alertasCarrinho={alertasCarrinho}
                codigoCupom={codigoCupom}
                cupomAplicado={cupomAplicado}
                erroCupom={erroCupom}
                loadingCupom={loadingCupom}
                modoVisualizacao={modoVisualizacao}
                onAbrirModalDescontoTotal={abrirModalDescontoTotal}
                onAplicarCupom={aplicarCupom}
                onCodigoCupomChange={handleCodigoCupomChange}
                onCodigoCupomKeyDown={handleCodigoCupomKeyDown}
                onRemoverCupom={removerCupom}
                onRemoverDescontoTotal={removerDescontoTotal}
                totalImpostos={totalImpostos}
                vendaAtual={vendaAtual}
              />

              <PDVComissaoCard
                buscaFuncionario={buscaFuncionario}
                funcionarioComissao={funcionarioComissao}
                funcionariosSugeridos={funcionariosSugeridos}
                modoVisualizacao={modoVisualizacao}
                onBuscaFuncionarioChange={handleBuscaFuncionarioChange}
                onBuscaFuncionarioFocus={handleBuscaFuncionarioFocus}
                onRemoverFuncionario={handleRemoverFuncionarioComissao}
                onSelecionarFuncionario={handleSelecionarFuncionarioComissao}
                onToggleVendaComissionada={handleToggleVendaComissionada}
                vendaComissionada={vendaComissionada}
              />
            </div>

            <PDVAcoesFooterCard
              itensCount={vendaAtual.itens.length}
              loading={loading}
              modoVisualizacao={modoVisualizacao}
              onAbrirModalPagamento={abrirModalPagamento}
              onNovaVenda={handleNovaVenda}
              onSalvarVenda={salvarVenda}
              statusVenda={vendaAtual.status}
              temCaixaAberto={temCaixaAberto}
              vendaId={vendaAtual.id}
            />
          </div>
        </div>

        <PDVClienteSidebar
          clienteId={vendaAtual.cliente?.id}
          painelClienteAberto={painelClienteAberto}
          setPainelClienteAberto={setPainelClienteAberto}
        />

        <PDVVendasRecentesSidebar
          painelVendasAberto={painelVendasAberto}
          setPainelVendasAberto={setPainelVendasAberto}
          filtroVendas={filtroVendas}
          setFiltroVendas={setFiltroVendas}
          filtroStatus={filtroStatus}
          setFiltroStatus={setFiltroStatus}
          filtroTemEntrega={filtroTemEntrega}
          setFiltroTemEntrega={setFiltroTemEntrega}
          buscaNumeroVenda={buscaNumeroVenda}
          setBuscaNumeroVenda={setBuscaNumeroVenda}
          vendasRecentes={vendasRecentes}
          reabrirVenda={reabrirVenda}
          confirmandoRetirada={confirmandoRetirada}
          abrirConfirmacaoRetirada={abrirConfirmacaoRetirada}
          confirmarRetirada={confirmarRetirada}
          setConfirmandoRetirada={setConfirmandoRetirada}
        />

        <PDVOportunidadesSidebar
          aberto={painelOportunidadesAberto && !!vendaAtual.cliente}
          opportunities={opportunities}
          onClose={() => setPainelOportunidadesAberto(false)}
          onAdicionar={adicionarOportunidadeAoCarrinho}
          onAlternativa={buscarAlternativaOportunidade}
          onIgnorar={ignorarOportunidade}
        />

        <PDVAssistenteSidebar
          aberto={painelAssistenteAberto && !!vendaAtual.cliente}
          clienteNome={vendaAtual.cliente?.nome}
          onClose={() => setPainelAssistenteAberto(false)}
          mensagensAssistente={mensagensAssistente}
          enviandoAssistente={enviandoAssistente}
          chatAssistenteEndRef={chatAssistenteEndRef}
          inputAssistente={inputAssistente}
          setInputAssistente={setInputAssistente}
          enviarMensagemAssistente={enviarMensagemAssistente}
        />

        <PDVModalsLayer
          carregandoAnalise={carregandoAnalise}
          dadosAnalise={dadosAnalise}
          enderecoAtual={enderecoAtual}
          itemEditando={itemEditando}
          loadingCep={loadingCep}
          mostrarAnaliseVenda={mostrarAnaliseVenda}
          mostrarCalculadoraRacao={mostrarCalculadoraRacao}
          mostrarHistoricoCliente={mostrarHistoricoCliente}
          mostrarModalAbrirCaixa={mostrarModalAbrirCaixa}
          mostrarModalAdicionarCredito={mostrarModalAdicionarCredito}
          mostrarModalCliente={mostrarModalCliente}
          mostrarModalDescontoItem={mostrarModalDescontoItem}
          mostrarModalDescontoTotal={mostrarModalDescontoTotal}
          mostrarModalEndereco={mostrarModalEndereco}
          mostrarModalPagamento={mostrarModalPagamento}
          mostrarPendenciasEstoque={mostrarPendenciasEstoque}
          mostrarVendasEmAberto={mostrarVendasEmAberto}
          podeVerMargem={podeVerMargem}
          racaoIdFechada={racaoIdFechada}
          setTipoDescontoTotal={setTipoDescontoTotal}
          setValorDescontoTotal={setValorDescontoTotal}
          tipoDescontoTotal={tipoDescontoTotal}
          valorDescontoTotal={valorDescontoTotal}
          vendaAtual={vendaAtual}
          onAbrirCaixaSucesso={handleAbrirCaixaSucesso}
          onAnalisarVenda={
            podeVerMargem ? analisarVendaComFormasPagamento : null
          }
          onAplicarDescontoTotal={aplicarDescontoTotal}
          onBuscarCep={buscarCepModal}
          onChangeEnderecoAtual={setEnderecoAtual}
          onChangeItemEditando={setItemEditando}
          onClienteCriado={handleClienteCriadoRapido}
          onCloseAnalise={() => setMostrarAnaliseVenda(false)}
          onCloseCalculadoraRacao={handleFecharCalculadoraRacao}
          onCloseHistoricoCliente={() => setMostrarHistoricoCliente(false)}
          onCloseModalAbrirCaixa={() => setMostrarModalAbrirCaixa(false)}
          onCloseModalAdicionarCredito={() =>
            setMostrarModalAdicionarCredito(false)
          }
          onCloseModalCliente={() => setMostrarModalCliente(false)}
          onCloseModalDescontoItem={() => setMostrarModalDescontoItem(false)}
          onCloseModalDescontoTotal={() => setMostrarModalDescontoTotal(false)}
          onCloseModalEndereco={fecharModalEndereco}
          onCloseModalPagamento={() => setMostrarModalPagamento(false)}
          onClosePendenciasEstoque={() => setMostrarPendenciasEstoque(false)}
          onCloseVendasEmAberto={() => setMostrarVendasEmAberto(false)}
          onConfirmarCredito={handleConfirmarCreditoCliente}
          onConfirmarPagamento={handleConfirmarPagamento}
          onPendenciaAdicionada={carregarPendencias}
          onRemoverItemEditando={removerItemEditando}
          onSalvarDescontoItem={salvarDescontoItem}
          onSalvarEndereco={salvarEnderecoNoCliente}
          onVendaAtualizada={handleVendaAtualizadaAposPagamento}
          onVendasEmAbertoSucesso={handleVendasEmAbertoSucesso}
        />
      </div>
    </>
  );
}


