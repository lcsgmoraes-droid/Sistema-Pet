// âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
// Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
// NÃƒO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenÃ¡rio real
// 3. Validar impacto financeiro

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
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
import { usePDVProdutos } from "../hooks/usePDVProdutos";
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

  // ðŸ”’ Controle de visibilidade de dados gerenciais (lucro, margem, custos)
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
    funcionario_id: null, // âœ… FuncionÃ¡rio para comissÃ£o
    entregador_id: null, // ðŸšš Entregador para entrega
    tem_entrega: false,
    entrega: {
      endereco_completo: "",
      taxa_entrega_total: 0,
      taxa_loja: 0,
      taxa_entregador: 0,
      observacoes_entrega: "",
    },
  });

  // Estados de UI
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalCliente, setMostrarModalCliente] = useState(false);
  const [mostrarModalAbrirCaixa, setMostrarModalAbrirCaixa] = useState(false);
  const [mostrarVendasEmAberto, setMostrarVendasEmAberto] = useState(false);
  const [mostrarHistoricoCliente, setMostrarHistoricoCliente] = useState(false);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] =
    useState(false);
  const [mostrarPendenciasEstoque, setMostrarPendenciasEstoque] =
    useState(false);
  const [pendenciasCount, setPendenciasCount] = useState(0);
  const [pendenciasProdutoIds, setPendenciasProdutoIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modoVisualizacao, setModoVisualizacao] = useState(false);
  const [searchVendaQuery, setSearchVendaQuery] = useState("");
  const [caixaKey, setCaixaKey] = useState(0); // Para forÃ§ar recarga do MenuCaixa
  const [temCaixaAberto, setTemCaixaAberto] = useState(false);

  // Estados do modal de endereÃ§o
  const [mostrarModalEndereco, setMostrarModalEndereco] = useState(false);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);

  // Estados do drawer de anÃ¡lise de venda

  // Estados de controle de painÃ©is laterais (UX - FASE 1)
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

  // ðŸ†• Estados fiscais do PDV (PDV-UX-01)
  const [fiscalItens, setFiscalItens] = useState({});
  const [totalImpostos, setTotalImpostos] = useState(0);

  // ðŸ†• Estados para Calculadora de RaÃ§Ã£o no PDV
const [mostrarCalculadoraRacao, setMostrarCalculadoraRacao] = useState(false);
const [racaoIdFechada, setRacaoIdFechada] = useState(null); // ID da raÃ§Ã£o fechada (nÃ£o reabre automÃ¡tico)

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
    buscaProduto,
    buscaProdutoContainerRef,
    copiadoCodigoItem,
    inputProdutoRef,
    itensKitExpandidos,
    mostrarSugestoesProduto,
    produtosSugeridos,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    removerItem,
    selecionarProdutoSugerido,
    toggleKitExpansion,
  } = usePDVProdutos({
    vendaAtual,
    setVendaAtual,
    modoVisualizacao,
    temCaixaAberto,
    recalcularTotais,
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

  // Carregar pendÃªncias quando o cliente mudar
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

  // Verificar se hÃ¡ caixa aberto
  useEffect(() => {
    verificarCaixaAberto();

    // ðŸ”„ Verificar caixa a cada 30 segundos (polling)
    const intervalId = setInterval(() => {
      verificarCaixaAberto();
    }, 30000); // 30 segundos

    return () => clearInterval(intervalId); // Limpar interval ao desmontar
  }, [caixaKey]);

  const verificarCaixaAberto = async () => {
    try {
      const response = await api.get("/caixas/aberto");
      setTemCaixaAberto(!!response.data); // true se houver caixa, false se nÃ£o
    } catch (error) {
      setTemCaixaAberto(false);
    }
  };

  // Adicionar produto Ã  lista de espera direto da busca (estoque zerado)
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
      toast.success(`"${produto.nome}" adicionado Ã  lista de espera!`);
      limparBuscaProduto();
      carregarPendencias();
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Erro ao adicionar Ã  lista de espera",
      );
    }
  };

  // Carregar pendÃªncias de estoque do cliente
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

  // ðŸ†• FunÃ§Ã£o para calcular fiscal de um item (PDV-UX-01)
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

  // ðŸ†• Recalcular fiscal sempre que o carrinho mudar (PDV-UX-01)
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

  // Carregar venda especÃ­fica se vier na URL
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

  // ðŸ†• DETECTAR REDIRECIONAMENTO DO CONTAS A RECEBER
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

  // FunÃ§Ãµes do modal de endereÃ§o
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
        alert("CEP nÃ£o encontrado");
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
      alert("Preencha pelo menos CEP, EndereÃ§o e Cidade");
      return;
    }

    if (!vendaAtual.cliente || !vendaAtual.cliente.id) {
      alert("Selecione um cliente primeiro");
      return;
    }

    try {
      // Buscar dados atuais do cliente
      const clienteAtual = await buscarClientePorId(vendaAtual.cliente.id);

      // Adicionar novo endereÃ§o ao array de enderecos_adicionais
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

      alert("EndereÃ§o adicionado com sucesso!");
      fecharModalEndereco();
    } catch (error) {
      console.error("Erro ao salvar endereÃ§o:", error);
      alert("Erro ao salvar endereÃ§o. Tente novamente.");
    }
  };

  // fluxo de descontos/cupom movido para usePDVDescontos

  const handleNovaVenda = () => {
    if (window.confirm("Descartar venda atual sem salvar?")) {
      limparVenda();
    }
  };

  // carregarVendaEspecifica e handleBuscarVenda movidos para usePDVVendaAtual


  // fluxo de produtos movido para usePDVProdutos

  // ðŸ¥« Abrir modal de calculadora de raÃ§Ã£o manualmente (via botÃ£o flutuante)
  const abrirCalculadoraRacao = () => {
    debugLog("ðŸ” Debug - Itens no carrinho:", vendaAtual.itens);
    debugLog("ðŸ” Debug - Verificando raÃ§Ãµes...");

    vendaAtual.itens.forEach((item, index) => {
      debugLog(`  Item ${index + 1}: ${item.produto_nome}`);
      debugLog(`    - peso_embalagem: ${item.peso_embalagem}`);
      debugLog(`    - classificacao_racao: ${item.classificacao_racao}`);
      debugLog(`    - categoria_id: ${item.categoria_id}`);
      debugLog(`    - categoria_nome: ${item.categoria_nome}`);
      debugLog(`    - Ã‰ raÃ§Ã£o?: ${ehRacao(item)}`);
    });

    const racoes = contarRacoes(vendaAtual.itens);
    debugLog(`ðŸ“Š Total de raÃ§Ãµes encontradas: ${racoes}`);

    if (racoes === 0) {
      toast.error("Nenhuma raÃ§Ã£o no carrinho");
      return;
    }

    setRacaoIdFechada(null); // Limpar raÃ§Ã£o fechada anterior
    setMostrarCalculadoraRacao(true);
  };

  // salvarVenda movido para usePDVSalvarVenda
  // anÃ¡lise, pagamento e pÃ³s-finalizaÃ§Ã£o movidos para usePDVAnalisePagamento

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
        {/* Ãrea Principal */}
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

          {/* ConteÃºdo Principal */}
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
                buscaProduto={buscaProduto}
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




