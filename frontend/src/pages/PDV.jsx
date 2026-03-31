// ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
// Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
// NÃO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenário real
// 3. Validar impacto financeiro

import {
  CheckCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import { buscarClientePorId, buscarClientes } from "../api/clientes";
import { getProdutosVendaveis } from "../api/produtos";
import { buscarVenda, listarVendas } from "../api/vendas";
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
import { usePDVAssistente } from "../hooks/usePDVAssistente";
import { usePDVComissao } from "../hooks/usePDVComissao";
import { usePDVEntrega } from "../hooks/usePDVEntrega";
import { usePDVOportunidades } from "../hooks/usePDVOportunidades";
import { usePDVSalvarVenda } from "../hooks/usePDVSalvarVenda";
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
  const [buscarCliente, setBuscarCliente] = useState("");
  const [buscarProduto, setBuscarProduto] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
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
  const [copiadoClienteCampo, setCopiadoClienteCampo] = useState("");
  const [copiadoCodigoItem, setCopiadoCodigoItem] = useState("");
  const [mostrarPendenciasEstoque, setMostrarPendenciasEstoque] =
    useState(false);
  const [pendenciasCount, setPendenciasCount] = useState(0);
  const [pendenciasProdutoIds, setPendenciasProdutoIds] = useState([]);
  const [vendasEmAbertoInfo, setVendasEmAbertoInfo] = useState(null);
  const [vendasRecentes, setVendasRecentes] = useState([]);
  const [filtroVendas, setFiltroVendas] = useState("24h");
  const [filtroStatus, setFiltroStatus] = useState("todas");
  const [confirmandoRetirada, setConfirmandoRetirada] = useState({
    vendaId: null,
    nome: "",
  });
  const [filtroTemEntrega, setFiltroTemEntrega] = useState(false);
  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState("");
  const [loading, setLoading] = useState(false);
  const [modoVisualizacao, setModoVisualizacao] = useState(false);
  const [searchVendaQuery, setSearchVendaQuery] = useState("");
  const [caixaKey, setCaixaKey] = useState(0); // Para forçar recarga do MenuCaixa
  const [temCaixaAberto, setTemCaixaAberto] = useState(false);

  // Estados do modal de endereço
  const [mostrarModalEndereco, setMostrarModalEndereco] = useState(false);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);

  // Estados dos modais de desconto
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] =
    useState(false);
  const [itemEditando, setItemEditando] = useState(null);
  const [mostrarModalDescontoTotal, setMostrarModalDescontoTotal] =
    useState(false);
  const [tipoDescontoTotal, setTipoDescontoTotal] = useState("valor");
  const [valorDescontoTotal, setValorDescontoTotal] = useState(0);

  // Estados de cupom de desconto
  const [codigoCupom, setCodigoCupom] = useState("");
  const [cupomAplicado, setCupomAplicado] = useState(null); // {code, discount_applied, message}
  const [loadingCupom, setLoadingCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");
  const [saldoCampanhas, setSaldoCampanhas] = useState(null); // {saldo_cashback, total_carimbos, cupons_ativos}

  const [statusOriginalVenda, setStatusOriginalVenda] = useState(null); // Guardar status antes de reabrir

  // Estados do drawer de análise de venda
  const [mostrarAnaliseVenda, setMostrarAnaliseVenda] = useState(false);
  const [dadosAnalise, setDadosAnalise] = useState(null);
  const [carregandoAnalise, setCarregandoAnalise] = useState(false);

  // Estado para controlar expansão de itens KIT no carrinho
  const [itensKitExpandidos, setItensKitExpandidos] = useState({});

  // 🚗 Estados de Drive pickup
  const [driveAguardando, setDriveAguardando] = useState([]);
  const [driveAlertVisible, setDriveAlertVisible] = useState(false);

  // Estados de controle de painéis laterais (UX - FASE 1)
  const [painelVendasAberto, setPainelVendasAberto] =
    usePersistentBooleanState("pdv_painel_vendas_aberto", false);

  const [painelClienteAberto, setPainelClienteAberto] =
    usePersistentBooleanState("pdv_painel_cliente_aberto", false);

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

  // Carregar vendas recentes
  useEffect(() => {
    carregarVendasRecentes();
  }, [filtroVendas, filtroStatus, filtroTemEntrega, buscaNumeroVenda]);

  // 🚗 Polling drive — verifica a cada 30s se tem clientes esperando no estacionamento
  useEffect(() => {
    const verificarDrive = async () => {
      try {
        const res = await api.get("/ecommerce-drive/aguardando");
        const lista = res.data?.pedidos || [];
        setDriveAguardando(lista);
        setDriveAlertVisible(lista.length > 0);
      } catch {
        // silencioso — não quebrar o PDV se endpoint falhar
      }
    };
    verificarDrive();
    const intervalo = setInterval(verificarDrive, 30000);
    return () => clearInterval(intervalo);
  }, []);

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

  // Funções de desconto individual
  const abrirModalDescontoItem = (item) => {
    setItemEditando({
      ...item,
      preco: item.preco_unitario, // Garantir que preco está definido
      descontoValor: item.desconto_valor || 0,
      descontoPercentual: item.desconto_percentual || 0,
      tipoDesconto: "valor", // Sempre começar com valor (R$)
    });
    setMostrarModalDescontoItem(true);
  };

  const salvarDescontoItem = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      if (item.produto_id === itemEditando.produto_id) {
        const precoUnitario = itemEditando.preco;
        const quantidade = item.quantidade;
        const subtotalSemDesconto = precoUnitario * quantidade;
        let descontoValor = 0;
        let descontoPercentual = 0;

        if (itemEditando.tipoDesconto === "valor") {
          descontoValor = parseFloat(itemEditando.descontoValor) || 0;
          // Calcular percentual sobre o total do item (preço × quantidade)
          descontoPercentual =
            subtotalSemDesconto > 0
              ? (descontoValor / subtotalSemDesconto) * 100
              : 0;
        } else {
          descontoPercentual = parseFloat(itemEditando.descontoPercentual) || 0;
          // Desconto total sobre o item (não por unidade)
          descontoValor = (subtotalSemDesconto * descontoPercentual) / 100;
        }

        const precoComDesconto = precoUnitario - descontoValor / quantidade;
        const subtotal = subtotalSemDesconto - descontoValor;

        return {
          ...item,
          desconto_valor: descontoValor,
          desconto_percentual: descontoPercentual,
          tipo_desconto_aplicado: itemEditando.tipoDesconto, // 🆕 Salvar tipo original
          preco_com_desconto: precoComDesconto,
          subtotal,
        };
      }
      return item;
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  const removerItemEditando = () => {
    vendaAtual.itens.forEach((item, index) => {
      if (item.produto_id === itemEditando?.produto_id) {
        removerItem(index);
      }
    });
    setMostrarModalDescontoItem(false);
  };

  // Funções de desconto total
  const abrirModalDescontoTotal = () => {
    // Pré-popular com o desconto atual (se houver)
    if (vendaAtual.desconto_valor > 0) {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(vendaAtual.desconto_valor);
    } else {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(0);
    }
    setMostrarModalDescontoTotal(true);
  };

  const aplicarDescontoTotal = (tipoDesconto, valor) => {
    const itens = vendaAtual.itens;
    if (itens.length === 0) return;

    // Calcular o total bruto de cada item (preço original × quantidade, sem desconto)
    const subtotaisBrutos = itens.map(
      (item) => (item.preco_unitario || item.preco_venda) * item.quantidade,
    );
    const totalBruto = subtotaisBrutos.reduce((sum, v) => sum + v, 0);

    // Calcular valor total do desconto
    let descontoTotal = 0;
    if (tipoDesconto === "valor") {
      descontoTotal = Math.min(parseFloat(valor) || 0, totalBruto);
    } else {
      const pct = Math.min(parseFloat(valor) || 0, 100);
      descontoTotal = (totalBruto * pct) / 100;
    }

    // Ratear proporcionalmente, ajustando arredondamento no último item
    let descontoAlocado = 0;
    const itensAtualizados = itens.map((item, idx) => {
      const subtotalBrutoItem = subtotaisBrutos[idx];
      let descontoItem;

      if (idx === itens.length - 1) {
        // Último item absorve o restante para evitar erro de centavos
        descontoItem = parseFloat((descontoTotal - descontoAlocado).toFixed(2));
      } else {
        const proporcao = totalBruto > 0 ? subtotalBrutoItem / totalBruto : 0;
        descontoItem = parseFloat((descontoTotal * proporcao).toFixed(2));
        descontoAlocado += descontoItem;
      }

      const descontoPercentual =
        subtotalBrutoItem > 0 ? (descontoItem / subtotalBrutoItem) * 100 : 0;
      const subtotal = subtotalBrutoItem - descontoItem;
      const precoComDesconto =
        item.quantidade > 0 ? subtotal / item.quantidade : 0;

      return {
        ...item,
        desconto_valor: descontoItem,
        desconto_percentual: descontoPercentual,
        tipo_desconto_aplicado: tipoDesconto,
        preco_com_desconto: precoComDesconto,
        subtotal,
      };
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoTotal(false);
  };

  const removerDescontoTotal = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      const subtotalBruto =
        (item.preco_unitario || item.preco_venda) * item.quantidade;
      return {
        ...item,
        desconto_valor: 0,
        desconto_percentual: 0,
        tipo_desconto_aplicado: null,
        preco_com_desconto: item.preco_unitario || item.preco_venda,
        subtotal: subtotalBruto,
      };
    });
    recalcularTotais(itensAtualizados);
  };

  // Cupom de desconto
  const aplicarCupom = async () => {
    const code = codigoCupom.trim().toUpperCase();
    if (!code) return;
    if (vendaAtual.itens.length === 0) {
      setErroCupom("Adicione itens à venda antes de aplicar um cupom.");
      return;
    }
    setLoadingCupom(true);
    setErroCupom("");
    try {
      const res = await api.post(`/campanhas/cupons/${code}/resgatar`, {
        venda_total: vendaAtual.total,
        customer_id: vendaAtual.cliente?.id || null,
      });
      const dados = res.data;
      setCupomAplicado(dados);
      setCodigoCupom("");
      // Aplicar desconto automaticamente
      aplicarDescontoTotal("valor", dados.discount_applied);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao validar cupom";
      setErroCupom(msg);
    } finally {
      setLoadingCupom(false);
    }
  };

  const removerCupom = () => {
    setCupomAplicado(null);
    setCodigoCupom("");
    setErroCupom("");
    removerDescontoTotal();
  };

  const criarEntregaVazia = () => ({
    endereco_completo: "",
    taxa_entrega_total: 0,
    taxa_loja: 0,
    taxa_entregador: 0,
    observacoes_entrega: "",
  });

  const recalcularTotalComEntrega = (subtotal, taxaEntrega) =>
    parseFloat((Number(subtotal || 0) + Number(taxaEntrega || 0)).toFixed(2));

  const handleCodigoCupomChange = (valor) => {
    setCodigoCupom(String(valor || "").toUpperCase());
    setErroCupom("");
  };

  const handleCodigoCupomKeyDown = (e) => {
    if (e.key === "Enter") {
      aplicarCupom();
    }
  };

  const handleNovaVenda = () => {
    if (window.confirm("Descartar venda atual sem salvar?")) {
      limparVenda();
    }
  };

  // 🚗 Confirmar entrega no drive
  const confirmarDriveEntregue = async (pedidoId) => {
    try {
      await api.post(`/ecommerce-drive/pedido/${pedidoId}/entregue`);
      setDriveAguardando((prev) => prev.filter((p) => p.pedido_id !== pedidoId));
      if (driveAguardando.length <= 1) setDriveAlertVisible(false);
    } catch (err) {
      console.error("Erro ao confirmar drive entregue:", err);
    }
  };

  const carregarVendasRecentes = async () => {
    try {
      const hoje = new Date();
      let dataInicio;

      if (filtroVendas === "24h") {
        dataInicio = new Date(hoje.getTime() - 24 * 60 * 60 * 1000);
      } else if (filtroVendas === "7d") {
        dataInicio = new Date(hoje.getTime() - 7 * 24 * 60 * 60 * 1000);
      } else {
        dataInicio = new Date(hoje.getTime() - 30 * 24 * 60 * 60 * 1000);
      }

      const params = {
        data_inicio: dataInicio.toISOString().split("T")[0],
        data_fim: hoje.toISOString().split("T")[0],
        per_page: 50, // Aumentado para 50
      };

      // Busca por número da venda tem prioridade
      if (buscaNumeroVenda.trim()) {
        params.busca = buscaNumeroVenda.trim();
        // Remover filtros de data quando buscar por número
        delete params.data_inicio;
        delete params.data_fim;
      } else {
        if (filtroStatus === "pago") {
          params.status = "finalizada";
        } else if (filtroStatus === "aberta") {
          params.status = "aberta";
        }
        // 'todas' não adiciona filtro de status

        // Filtro de tem entrega - só adicionar se estiver marcado
        if (filtroTemEntrega === true) {
          params.tem_entrega = true;
        }
      }

      debugLog("📊 Parâmetros de busca de vendas:", params);
      const resultado = await listarVendas(params);

      setVendasRecentes(resultado.vendas || []);
    } catch (error) {
      console.error("Erro ao carregar vendas:", error);
    }
  };

  const abrirConfirmacaoRetirada = (e, vendaId) => {
    e.stopPropagation();
    setConfirmandoRetirada({ vendaId, nome: "" });
  };

  const confirmarRetirada = async (e, vendaId) => {
    e.stopPropagation();
    try {
      await api.post(`/vendas/${vendaId}/marcar-entregue`, {
        retirado_por: confirmandoRetirada.nome.trim() || null,
      });
      setConfirmandoRetirada({ vendaId: null, nome: "" });
      carregarVendasRecentes();
    } catch (error) {
      console.error("Erro ao confirmar retirada:", error);
    }
  };

  // carregarVendaEspecifica e handleBuscarVenda movidos para usePDVVendaAtual

  // Buscar clientes
  useEffect(() => {
    if (buscarCliente.length >= 1) {
      const timer = setTimeout(async () => {
        try {
          // Se a busca for telefone, usa só dígitos para bater com qualquer máscara.
          // Se for nome/texto, mantém como foi digitado.
          const termoOriginal = buscarCliente.trim();
          const termoDigitos = termoOriginal.replace(/\D/g, "");
          const termoBusca = termoDigitos.length >= 8 ? termoDigitos : termoOriginal;
          const clientes = await buscarClientes({
            search: termoBusca,
            limit: 20,
          });
          setClientesSugeridos(clientes || []);
        } catch (error) {
          console.error("Erro ao buscar clientes:", error);
          setClientesSugeridos([]);
        }
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setClientesSugeridos([]);
    }
  }, [buscarCliente]);

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

  function buscarClientePorCodigoExato(termo) {
    const termoLimpo = String(termo || "").trim().toLowerCase();
    if (!termoLimpo) return null;

    // Quando a busca for numérica, prioriza ID exato do cliente.
    const porId = clientesSugeridos.find(
      (cliente) => String(cliente?.id || "").trim().toLowerCase() === termoLimpo,
    );
    if (porId) return porId;

    // Em seguida, tenta código exato.
    return clientesSugeridos.find(
      (cliente) =>
        String(cliente?.codigo || "").trim().toLowerCase() === termoLimpo,
    );
  }

  // Selecionar cliente
  const selecionarCliente = async (cliente) => {
    setVendaAtual({ ...vendaAtual, cliente, pet: null });
    setBuscarCliente("");
    setClientesSugeridos([]);
    setSaldoCampanhas(null);

    // Garante dados completos (telefone/celular/codigo) no card principal do PDV.
    try {
      const clienteCompleto = await buscarClientePorId(cliente.id);
      if (clienteCompleto) {
        setVendaAtual((prev) => ({
          ...prev,
          cliente: {
            ...prev.cliente,
            ...clienteCompleto,
          },
        }));
      }
    } catch (_) {
      // Segue com os dados resumidos para não travar o fluxo do caixa.
    }

    // Verificar se cliente tem vendas em aberto
    try {
      const response = await api.get(
        `/clientes/${cliente.id}/vendas-em-aberto`,
      );
      if (response.data.resumo.total_vendas > 0) {
        setVendasEmAbertoInfo(response.data.resumo);
      } else {
        setVendasEmAbertoInfo(null);
      }
    } catch (error) {
      console.error("Erro ao verificar vendas em aberto:", error);
      setVendasEmAbertoInfo(null);
    }

    // Buscar saldo de campanhas (cashback + carimbos + cupons ativos)
    try {
      const res = await api.get(`/campanhas/clientes/${cliente.id}/saldo`);
      setSaldoCampanhas(res.data);
    } catch (_) {
      // Silencioso — campanhas são opcionais
    }
  };

  const copiarCampoCliente = (valor, campo) => {
    if (!valor) return;
    navigator.clipboard.writeText(String(valor));
    setCopiadoClienteCampo(campo);
    setTimeout(() => setCopiadoClienteCampo(""), 2000);
  };

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

  // Selecionar pet
  const selecionarPet = (pet) => {
    setVendaAtual({ ...vendaAtual, pet });
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

  // Recalcular totais
  const recalcularTotais = (itens) => {
    const subtotal = itens.reduce((sum, item) => sum + item.subtotal, 0);

    // Somar todos os descontos individuais dos itens
    // NOTA: desconto_valor JÁ É O TOTAL do desconto para o item (não precisa multiplicar por quantidade)
    const descontoItens = itens.reduce((sum, item) => {
      return sum + (item.desconto_valor || 0);
    }, 0);

    // Calcular total bruto (subtotal + descontos aplicados)
    const totalBruto = subtotal + descontoItens;
    const descontoPercentual =
      totalBruto > 0 ? (descontoItens / totalBruto) * 100 : 0;

    const taxaEntrega = vendaAtual.tem_entrega
      ? vendaAtual.entrega?.taxa_entrega_total || 0
      : 0;
    // O subtotal já tem o desconto aplicado (soma dos item.subtotal que já considera desconto individual)
    // Então o total final é: subtotal + taxa de entrega
    const total = subtotal + taxaEntrega;

    setVendaAtual({
      ...vendaAtual,
      itens,
      subtotal,
      desconto_valor: descontoItens,
      desconto_percentual: descontoPercentual,
      total,
    });
  };

  // salvarVenda movido para usePDVSalvarVenda

  const buscarAnaliseVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto para ver a análise");
      return;
    }

    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: vendaAtual.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo,
        })),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: vendaAtual.forma_pagamento_id || null,
        parcelas: vendaAtual.parcelas || 1,
        vendedor_id: vendaAtual.funcionario_id, // Single source of truth
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  // Analisar venda existente pelo ID
  const analisarVenda = async (vendaId) => {
    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      // Buscar dados da venda
      const vendaResponse = await api.get(`/vendas/${vendaId}`);
      const venda = vendaResponse.data;

      // Fazer análise com os dados da venda
      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: venda.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo,
        })),
        desconto: venda.desconto_valor || 0,
        taxa_entrega: venda.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: venda.forma_pagamento_id || null,
        parcelas: venda.parcelas || 1,
        vendedor_id: venda.vendedor_id || null,
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  // Analisar venda com múltiplas formas de pagamento (do modal)
  const analisarVendaComFormasPagamento = async (formasPagamento) => {
    debugLog("🔍 DEBUG formasPagamento recebidas:", formasPagamento);

    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      debugLog("💰 Enviando análise com múltiplas formas:", formasPagamento);

      // Fazer análise com os dados da venda atual E MÚLTIPLAS FORMAS
      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: vendaAtual.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo,
        })),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        formas_pagamento: formasPagamento, // ARRAY de formas de pagamento
        vendedor_id: vendaAtual.funcionario_id, // Single source of truth
      });

      debugLog("✅ Resposta da análise:", response.data);
      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  // abrirModalPagamento, limparVenda e reabrirVenda movidos para usePDVVendaAtual

  // Habilitar edição de venda
  const habilitarEdicao = () => {
    setModoVisualizacao(false);
  };

  // Cancelar edição e voltar ao modo visualização
  const cancelarEdicao = async () => {
    if (!vendaAtual.id) {
      limparVenda();
      return;
    }

    // SEMPRE restaurar status original ao sair sem salvar (descarta alterações)
    if (statusOriginalVenda && vendaAtual.status !== statusOriginalVenda) {
      try {
        setLoading(true);

        // Restaurar status original (perder alterações não salvas)
        await api.patch(`/vendas/${vendaAtual.id}/status`, {
          status: statusOriginalVenda,
        });

        debugLog(
          `✅ Status restaurado para: ${statusOriginalVenda} (alterações descartadas)`,
        );
      } catch (error) {
        console.error("Erro ao restaurar status:", error);
      } finally {
        setLoading(false);
      }
    }

    // Limpar estados e voltar para nova venda
    setStatusOriginalVenda(null);
    limparVenda();
  };

  // Excluir venda
  const excluirVenda = async () => {
    if (!vendaAtual.id) return;

    const confirmar = window.confirm(
      "Deseja realmente excluir esta venda?\n\nEsta ação não pode ser desfeita e o estoque será devolvido.",
    );

    if (!confirmar) return;

    try {
      setLoading(true);
      await api.delete(`/vendas/${vendaAtual.id}`);

      // Limpar venda e recarregar lista
      limparVenda();
      carregarVendasRecentes();

      alert("Venda excluída com sucesso!");
    } catch (error) {
      console.error("Erro ao excluir venda:", error);

      // Tratamento amigável de erros estruturados
      const errorData = error.response?.data?.detail;

      if (errorData && typeof errorData === "object") {
        // Erro estruturado com passos
        let mensagem = `❌ ${errorData.erro || "Erro ao excluir venda"}\n\n`;
        mensagem += `${errorData.mensagem || ""}\n\n`;

        if (errorData.solucao) {
          mensagem += `💡 Solução:\n${errorData.solucao}\n\n`;
        }

        if (errorData.passos && Array.isArray(errorData.passos)) {
          mensagem += `📋 Passos para resolver:\n`;
          errorData.passos.forEach((passo) => {
            mensagem += `${passo}\n`;
          });
        }

        if (errorData.rota_id) {
          mensagem += `\n🚚 Rota ID: ${errorData.rota_id}`;
          if (errorData.rota_status) {
            mensagem += ` (${errorData.rota_status})`;
          }
        }

        alert(mensagem);
      } else if (typeof errorData === "string") {
        // Erro simples (string)
        alert(errorData);
      } else {
        // Fallback
        alert("Erro ao excluir venda. Verifique se não há vínculos pendentes.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Reabrir venda finalizada (mudar status para aberta)
  // Mudar status de venda finalizada para aberta (permitir edição/exclusão)
  const mudarStatusParaAberta = async () => {
    if (!vendaAtual.id) return;

    const confirmar = window.confirm(
      'Deseja reabrir esta venda?\n\nOs pagamentos serão mantidos e o status mudará para "aberta".',
    );

    if (!confirmar) return;

    // Guardar status original ANTES de modificar
    setStatusOriginalVenda(vendaAtual.status);

    try {
      setLoading(true);

      // Chamar rota de reabrir venda
      await api.post(`/vendas/${vendaAtual.id}/reabrir`);

      // Recarregar venda COMPLETA do servidor
      const vendaAtualizada = await buscarVenda(vendaAtual.id);

      // Buscar cliente completo se houver
      let clienteCompleto = null;
      if (vendaAtualizada.cliente_id) {
        clienteCompleto = await buscarClientePorId(vendaAtualizada.cliente_id);
      }

      // Atualizar estado com TODOS os dados
      setVendaAtual({
        id: vendaAtualizada.id,
        numero_venda: vendaAtualizada.numero_venda,
        data_venda: vendaAtualizada.data_venda,
        cliente: clienteCompleto, // ✅ Cliente completo com enderecos_adicionais
        pet: null,
        itens: vendaAtualizada.itens || [],
        subtotal: parseFloat(vendaAtualizada.subtotal || vendaAtualizada.total),
        desconto_valor: parseFloat(vendaAtualizada.desconto_valor || 0),
        desconto_percentual: parseFloat(
          vendaAtualizada.desconto_percentual || 0,
        ),
        total: parseFloat(vendaAtualizada.total),
        observacoes: vendaAtualizada.observacoes || "",
        status: "aberta", // Garantir status correto
        tem_entrega: vendaAtualizada.tem_entrega || false,
        entrega: {
          endereco_completo: vendaAtualizada.endereco_entrega || "",
          endereco_id: vendaAtualizada.endereco_id || null,
          taxa_entrega_total: parseFloat(
            parseFloat(vendaAtualizada.taxa_entrega || 0).toFixed(2),
          ),
          taxa_loja: parseFloat(
            parseFloat(vendaAtualizada.taxa_loja || 0).toFixed(2),
          ),
          taxa_entregador: parseFloat(
            parseFloat(vendaAtualizada.taxa_entregador || 0).toFixed(2),
          ),
          observacoes_entrega: vendaAtualizada.observacoes_entrega || "",
          distancia_km: vendaAtualizada.distancia_km || 0,
          valor_por_km: vendaAtualizada.valor_por_km || 0,
          loja_origem: vendaAtualizada.loja_origem || "",
          status_entrega: vendaAtualizada.status_entrega || "pendente",
        },
      });

      // Desativar modo visualização para permitir edição
      setModoVisualizacao(false);

      alert(
        "Venda reaberta com sucesso! Agora você pode editá-la.\n\nATENÇÃO: Se você não fizer alterações e sair, a venda voltará ao status anterior.",
      );
    } catch (error) {
      console.error("Erro ao reabrir venda:", error);
      alert(error.response?.data?.detail || "Erro ao reabrir venda");
    } finally {
      setLoading(false);
    }
  };

  const emitirNotaVendaFinalizada = async () => {
    if (!vendaAtual.id) return;

    let tipoNota = "nfce";
    if (vendaAtual.cliente?.cnpj) {
      const emitirNfe = window.confirm(
        "Cliente tem CNPJ.\n\nClique OK para emitir NF-e (Empresa)\nClique Cancelar para emitir NFC-e (Cupom).",
      );
      tipoNota = emitirNfe ? "nfe" : "nfce";
    }

    const confirmar = window.confirm(
      `Confirma emitir ${tipoNota === "nfe" ? "NF-e" : "NFC-e"} para esta venda finalizada?`,
    );
    if (!confirmar) return;

    try {
      setLoading(true);
      await api.post("/nfe/emitir", {
        venda_id: vendaAtual.id,
        tipo_nota: tipoNota,
      });

      await carregarVendaEspecifica(vendaAtual.id);
      toast.success(`${tipoNota === "nfe" ? "NF-e" : "NFC-e"} emitida com sucesso!`);
    } catch (error) {
      console.error("Erro ao emitir nota da venda finalizada:", error);
      alert(error.response?.data?.detail || "Erro ao emitir nota fiscal");
    } finally {
      setLoading(false);
    }
  };

  const carregarPagamentosDaVenda = async (vendaId) => {
    try {
      const responsePagamentos = await api.get(`/vendas/${vendaId}/pagamentos`);
      return {
        pagamentos: responsePagamentos.data.pagamentos || [],
        totalPago: responsePagamentos.data.total_pago || 0,
      };
    } catch (error) {
      console.error("Erro ao buscar pagamentos:", error);
      return {
        pagamentos: [],
        totalPago: 0,
      };
    }
  };

  const recarregarVendaAtualComPagamentos = async (vendaId) => {
    const vendaAtualizada = await buscarVenda(vendaId);
    const { pagamentos, totalPago } = await carregarPagamentosDaVenda(vendaId);

    setVendaAtual({
      ...vendaAtualizada,
      pagamentos,
      total_pago: totalPago,
    });

    return vendaAtualizada;
  };

  const handleConfirmarPagamento = async () => {
    setMostrarModalPagamento(false);

    if (modoVisualizacao && vendaAtual.id) {
      try {
        const vendaAtualizada = await recarregarVendaAtualComPagamentos(
          vendaAtual.id,
        );
        debugLog("\u2705 Venda recarregada:", vendaAtualizada);
      } catch (error) {
        console.error("Erro ao recarregar venda:", error);
      }
    } else {
      limparVenda();
    }

    carregarVendasRecentes();
    setCaixaKey((prev) => prev + 1);
  };

  const handleVendaAtualizadaAposPagamento = async () => {
    if (!vendaAtual.id) {
      return;
    }

    const vendaAtualizada = await recarregarVendaAtualComPagamentos(
      vendaAtual.id,
    );
    setModoVisualizacao(
      vendaAtualizada.status === "finalizada" ||
        vendaAtualizada.status === "baixa_parcial",
    );
    carregarVendasRecentes();
  };

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

  const handleClienteCriadoRapido = (cliente) => {
    selecionarCliente(cliente);
    setMostrarModalCliente(false);
  };

  const handleVendasEmAbertoSucesso = () => {
    api
      .get(`/clientes/${vendaAtual.cliente.id}/vendas-em-aberto`)
      .then((response) => {
        if (response.data.resumo.total_vendas > 0) {
          setVendasEmAbertoInfo(response.data.resumo);
        } else {
          setVendasEmAbertoInfo(null);
        }
      })
      .catch(() => setVendasEmAbertoInfo(null));
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
        onClose={() => setDriveAlertVisible(false)}
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
                onRemoverCliente={() => {
                  setVendaAtual({
                    ...vendaAtual,
                    cliente: null,
                    pet: null,
                  });
                  setSaldoCampanhas(null);
                }}
                onSelecionarCliente={selecionarCliente}
                onSelecionarPet={selecionarPet}
                onTrocarCliente={() => {
                  setVendaAtual({
                    ...vendaAtual,
                    cliente: null,
                    pet: null,
                  });
                  setVendasEmAbertoInfo(null);
                  setSaldoCampanhas(null);
                }}
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


