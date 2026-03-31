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
import { buscarVenda, criarVenda, listarVendas } from "../api/vendas";
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
import { usePersistentBooleanState } from "../hooks/usePersistentBooleanState";
import { contarRacoes, ehRacao } from "../helpers/deteccaoRacao";
import { useTour } from "../hooks/useTour";
import { tourPDV } from "../tours/tourDefinitions";
import { debugLog, debugWarn } from "../utils/debug";
import { formatBRL, formatMoneyBRL } from "../utils/formatters";
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

  // Estado de comissão
  const [vendaComissionada, setVendaComissionada] = useState(false);
  const [funcionarioComissao, setFuncionarioComissao] = useState(null);
  const [funcionariosSugeridos, setFuncionariosSugeridos] = useState([]);
  const [buscaFuncionario, setBuscaFuncionario] = useState(""); // Texto de busca
  const [statusOriginalVenda, setStatusOriginalVenda] = useState(null); // Guardar status antes de reabrir

  // 🚚 Estados para Entregadores e Custo Operacional (DECLARAR ANTES DOS useEffects)
  const [entregadores, setEntregadores] = useState([]);
  const [entregadorSelecionado, setEntregadorSelecionado] = useState(null);
  const [custoOperacionalEntrega, setCustoOperacionalEntrega] = useState(0);

  // ✅ Sincronizar funcionario_id com vendaAtual sempre que mudar
  useEffect(() => {
    setVendaAtual((prev) => ({
      ...prev,
      funcionario_id: funcionarioComissao?.id || null,
    }));
  }, [funcionarioComissao]);

  // ✅ Sincronizar entregador_id com vendaAtual sempre que mudar
  useEffect(() => {
    const novoEntregadorId = entregadorSelecionado?.id || null;
    if (!novoEntregadorId) {
      return;
    }

    debugLog("🔄 Sincronizando entregador_id:", novoEntregadorId);
    setVendaAtual((prev) => {
      if (prev.entregador_id === novoEntregadorId) {
        return prev;
      }
      return {
        ...prev,
        entregador_id: novoEntregadorId,
      };
    });
  }, [entregadorSelecionado]);

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

  // Estado de Oportunidades Inteligentes (D4 - Backend Integration)
  // ✅ RULE: Oportunidades só aparecem com cliente selecionado
  const [painelOportunidadesAberto, setPainelOportunidadesAberto] =
    useState(false);
  const [opportunities, setOpportunities] = useState([]);

  // === ASSISTENTE IA DO PDV ===
  const [painelAssistenteAberto, setPainelAssistenteAberto] = useState(false);
  const [mensagensAssistente, setMensagensAssistente] = useState([]);
  const [inputAssistente, setInputAssistente] = useState('');
  const [enviandoAssistente, setEnviandoAssistente] = useState(false);
  const chatAssistenteEndRef = useRef(null);
  const [alertasCarrinho, setAlertasCarrinho] = useState([]);  // alertas proativos
  const [infosCarrinho, setInfosCarrinho] = useState([]);      // infos de duração

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

  // Carregar pendências quando o cliente mudar
  useEffect(() => {
    if (vendaAtual.cliente) {
      carregarPendencias();
    }
  }, [vendaAtual.cliente]);

  // Resetar chat do assistente e alertas quando cliente mudar
  useEffect(() => {
    setMensagensAssistente([]);
    setInputAssistente('');
    setAlertasCarrinho([]);
    setInfosCarrinho([]);
  }, [vendaAtual.cliente?.id]);

  // Auto-scroll chat para o final
  useEffect(() => {
    chatAssistenteEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensagensAssistente]);

  // Verificar alertas proativos quando os itens do carrinho mudam
  useEffect(() => {
    if (vendaAtual.cliente?.id && vendaAtual.itens?.length > 0) {
      const timer = setTimeout(() => {
        verificarAlertasCarrinho(vendaAtual.cliente.id, vendaAtual.itens);
      }, 800);
      return () => clearTimeout(timer);
    } else {
      setAlertasCarrinho([]);
      setInfosCarrinho([]);
    }
  }, [vendaAtual.itens, vendaAtual.cliente?.id]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // 🚚 Carregar entregadores disponíveis ao iniciar
  useEffect(() => {
    // debugLog('⭐⭐⭐ useEffect de entregadores RODANDO! ⭐⭐⭐');
    carregarEntregadores();
  }, []);

  const carregarEntregadores = async () => {
    // debugLog('🔥🔥🔥 INICIANDO carregarEntregadores 🔥🔥🔥');
    try {
      // debugLog('📦 Fazendo request para /clientes...');
      const response = await api.get("/clientes/", {
        params: {
          is_entregador: true,
          incluir_inativos: false,
          limit: 100,
        },
      });

      // debugLog('✅ Response recebido:', response.data);
      // A API retorna um objeto paginado: {items: Array, total: number, skip: number, limit: number}
      let entregadoresList =
        response.data.items || response.data.clientes || response.data || [];

      // Garantir que é um array
      if (!Array.isArray(entregadoresList)) {
        console.error("❌ Resposta da API não é um array:", entregadoresList);
        entregadoresList = [];
      }

      // debugLog('📋 Total de entregadores carregados:', entregadoresList.length);
      // debugLog('📋 Lista completa:', entregadoresList);
      setEntregadores(entregadoresList);

      // Pré-selecionar entregador padrão
      const entregadorPadrao = entregadoresList.find((e) => {
        // debugLog('🔍 Verificando entregador:', e.nome, 'entregador_padrao:', e.entregador_padrao);
        return e.entregador_padrao === true;
      });

      // debugLog('🔍 Resultado da busca do padrão:', entregadorPadrao);

      if (entregadorPadrao) {
        // debugLog('🎯🎯🎯 ENTREGADOR PADRÃO ENCONTRADO:', entregadorPadrao.nome, 'ID:', entregadorPadrao.id);
        setEntregadorSelecionado(entregadorPadrao);
        // ✅ Setar IMEDIATAMENTE no vendaAtual também (evitar race condition)
        setVendaAtual((prev) => {
          // debugLog('💾 Setando entregador_id no vendaAtual:', entregadorPadrao.id);
          return {
            ...prev,
            entregador_id: entregadorPadrao.id,
          };
        });
        calcularCustoOperacional(entregadorPadrao);
      } else {
        // console.error('❌❌❌ NENHUM ENTREGADOR PADRÃO ENCONTRADO!');
      }
    } catch (error) {
      console.error("Erro ao carregar entregadores:", error);
      toast.error("Erro ao carregar lista de entregadores");
    }
  };

  // 🚚 Calcular custo operacional baseado no entregador selecionado
  const calcularCustoOperacional = async (entregador) => {
    if (!entregador) {
      setCustoOperacionalEntrega(0);
      return;
    }

    let custo = 0;

    // Modelo 1: Taxa Fixa
    if (
      entregador.modelo_custo_entrega === "taxa_fixa" &&
      entregador.taxa_fixa_entrega
    ) {
      custo = Number(entregador.taxa_fixa_entrega);
    }
    // Modelo 2: Por KM (precisaria da distância - por enquanto usar taxa fixa ou 0)
    else if (
      entregador.modelo_custo_entrega === "por_km" &&
      entregador.valor_por_km_entrega
    ) {
      // TODO: Integrar com cálculo de distância da API de mapas
      // Por enquanto, assumir 0 ou usar valor fixo como fallback
      custo = 0;
      // debugLog('⚠️ Modelo por KM requer cálculo de distância');
    }
    // Modelo 3: Rateio RH (buscar do backend)
    else if (
      entregador.modelo_custo_entrega === "rateio_rh" &&
      entregador.controla_rh
    ) {
      try {
        // Buscar custo calculado pelo backend
        const response = await api.get(
          `/entregadores/${entregador.id}/custo-operacional`,
        );
        custo = response.data.custo_por_entrega || 0;
      } catch (error) {
        console.error("Erro ao buscar custo RH:", error);
        // Fallback: usar custo_rh_ajustado se disponível
        custo = entregador.custo_rh_ajustado || 0;
      }
    }
    // Fallback: buscar da configuração global
    else {
      try {
        const response = await api.get("/configuracoes/entregas");
        custo = response.data.taxa_fixa || 0;
      } catch (error) {
        console.error("Erro ao buscar configuração de entrega:", error);
        custo = 10; // Valor padrão
      }
    }

    setCustoOperacionalEntrega(custo);
  };

  // 🚚 Atualizar custo operacional quando entregador mudar
  useEffect(() => {
    if (vendaAtual.tem_entrega && entregadorSelecionado) {
      calcularCustoOperacional(entregadorSelecionado);
    } else {
      setCustoOperacionalEntrega(0);
    }
  }, [entregadorSelecionado, vendaAtual.tem_entrega]);

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

  // Buscar oportunidades do backend (D4 - Backend Integration)
  const buscarOportunidades = async (vendaId) => {
    const clienteId = vendaAtual.cliente?.id;
    if (!clienteId) {
      setOpportunities([]);
      return;
    }

    try {
      // Se há venda salva: usa endpoint por venda (exclui itens já no carrinho)
      // Se não há venda salva ainda: usa endpoint direto por cliente
      const url = vendaId
        ? `/internal/pdv/oportunidades/${vendaId}`
        : `/internal/pdv/oportunidades-cliente/${clienteId}`;

      const response = await api.get(url);
      const data = response.data;

      // Extrair oportunidades da resposta
      if (data && Array.isArray(data.oportunidades)) {
        setOpportunities(data.oportunidades);
      } else {
        setOpportunities([]);
      }
    } catch (error) {
      // Fail-safe: erro silencioso, apenas limpa lista
      setOpportunities([]);
    }
  };

  // Carrega resumo do cliente para o assistente IA
  const carregarInfoCliente = async (clienteId) => {
    if (!clienteId) return;
    try {
      const res = await api.get(`/clientes/${clienteId}/info-pdv`);
      const info = res.data;
      const pets = info.pets?.map(p => p.nome).join(', ') || 'Nenhum';
      const ultimaCompra = info.resumo_financeiro?.ultima_compra;
      const topProdutos = info.sugestoes?.slice(0, 3).map(s => s.nome).join(', ') || 'Nenhum';
      const oportunidades = info.oportunidades || [];
      let autoMsg = `Resumo de **${info.cliente?.nome}**:\n`;
      autoMsg += `🛒 ${info.resumo_financeiro?.numero_compras || 0} compras — ticket médio: ${formatMoneyBRL(info.resumo_financeiro?.ticket_medio || 0)}\n`;
      if (ultimaCompra?.data) {
        autoMsg += `📅 Última compra: ${ultimaCompra.data} (${formatMoneyBRL(ultimaCompra.valor || 0)})\n`;
      }
      if (pets !== 'Nenhum') autoMsg += `🐾 Pets: ${pets}\n`;
      autoMsg += `⭐ Favoritos: ${topProdutos}\n`;
      if (oportunidades.length > 0) {
        autoMsg += `\n⚠️ ${oportunidades.length} produto(s) para reabastecer:\n`;
        oportunidades.slice(0, 3).forEach(op => {
          autoMsg += `• ${op.produto_nome} (${op.dias_atraso}d atrasado)\n`;
        });
      }
      autoMsg += '\nPergunta sobre este cliente?';
      setMensagensAssistente([{ role: 'assistant', texto: autoMsg }]);
    } catch {
      setMensagensAssistente([{ role: 'assistant', texto: 'Não foi possível carregar o histórico. Pode me perguntar qualquer coisa!' }]);
    }
  };

  // Verifica alertas proativos do carrinho (fase de vida, alergias, duração)
  const verificarAlertasCarrinho = async (clienteId, itens) => {
    if (!clienteId || !itens || itens.length === 0) {
      setAlertasCarrinho([]);
      setInfosCarrinho([]);
      return;
    }
    try {
      const payload = {
        itens: itens.map(i => ({
          produto_id: i.produto_id || null,
          produto_nome: i.produto_nome || i.nome || '',
          quantidade: i.quantidade || 1,
          preco_unitario: i.preco_unitario || 0,
        }))
      };
      const res = await api.post(`/clientes/${clienteId}/alertas-carrinho`, payload);
      setAlertasCarrinho(res.data.alertas || []);
      setInfosCarrinho(res.data.infos || []);
    } catch {
      // silencioso
    }
  };

  // Envia mensagem para o chat IA do cliente (passa carrinho junto)
  const enviarMensagemAssistente = async () => {
    const msg = inputAssistente.trim();
    if (!msg || !vendaAtual.cliente?.id || enviandoAssistente) return;
    setMensagensAssistente(prev => [...prev, { role: 'user', texto: msg }]);
    setInputAssistente('');
    setEnviandoAssistente(true);
    try {
      const carrinhoPayload = vendaAtual.itens?.map(i => ({
        produto_id: i.produto_id || null,
        produto_nome: i.produto_nome || i.nome || '',
        quantidade: i.quantidade || 1,
        preco_unitario: i.preco_unitario || 0,
      })) || [];
      const res = await api.post(`/clientes/${vendaAtual.cliente.id}/chat-pdv`, {
        mensagem: msg,
        carrinho: carrinhoPayload,
      });
      setMensagensAssistente(prev => [...prev, { role: 'assistant', texto: res.data.resposta }]);
    } catch {
      setMensagensAssistente(prev => [...prev, { role: 'assistant', texto: 'Erro ao responder. Tente novamente.' }]);
    } finally {
      setEnviandoAssistente(false);
    }
  };

  // Registrar evento de oportunidade (D5 - Event Tracking)
  // Fire-and-forget: não aguarda resposta, não bloqueia UI
  const registrarEventoOportunidade = async (eventType, oportunidade) => {
    try {
      // Payload mínimo para tracking
      const payload = {
        opportunity_id: oportunidade.id,
        event_type: eventType,
        user_id: user?.id,
        contexto: "PDV",
        extra_data: {
          produto_origem_id: oportunidade.produto_origem_id || null,
          produto_sugerido_id: oportunidade.produto_sugerido_id || null,
          tipo_oportunidade: oportunidade.tipo || null,
          venda_id: vendaAtual.id || null,
        },
      };

      // Fire-and-forget: não aguarda resposta
      api.post("/internal/pdv/eventos-oportunidade", payload).catch(() => {
        // Erro silencioso - nunca afeta UX
      });
    } catch (error) {
      // Fail-safe: erro silencioso
    }
  };

  function adicionarOportunidadeAoCarrinho(oportunidade) {
    registrarEventoOportunidade("oportunidade_convertida", oportunidade);
    debugLog("Adicionar ao carrinho:", oportunidade.id);
  }

  function buscarAlternativaOportunidade(oportunidade) {
    registrarEventoOportunidade("oportunidade_refinada", oportunidade);
    debugLog("Buscar alternativa:", oportunidade.id);
  }

  function ignorarOportunidade(oportunidade) {
    registrarEventoOportunidade("oportunidade_rejeitada", oportunidade);
    setOpportunities((prev) => prev.filter((item) => item.id !== oportunidade.id));
  }

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

  const carregarFuncionariosComissao = async (busca = "") => {
    try {
      const response = await api.get("/comissoes/configuracoes/funcionarios");
      const funcionarios = response.data.data || [];
      const termo = String(busca || "").trim().toLowerCase();
      const filtrados = termo
        ? funcionarios.filter((f) => f.nome.toLowerCase().includes(termo))
        : funcionarios;

      setFuncionariosSugeridos(filtrados);
      return filtrados;
    } catch (error) {
      console.error("Erro ao buscar funcionários:", error);
      setFuncionariosSugeridos([]);
      return [];
    }
  };

  const handleToggleVendaComissionada = (checked) => {
    setVendaComissionada(checked);
    if (!checked) {
      setFuncionarioComissao(null);
      setBuscaFuncionario("");
      setFuncionariosSugeridos([]);
    }
  };

  const handleBuscaFuncionarioFocus = async () => {
    if (!modoVisualizacao) {
      await carregarFuncionariosComissao();
    }
  };

  const handleBuscaFuncionarioChange = async (valor) => {
    setBuscaFuncionario(valor);
    await carregarFuncionariosComissao(valor);
  };

  const handleSelecionarFuncionarioComissao = (func) => {
    setFuncionarioComissao(func);
    setFuncionariosSugeridos([]);
    setBuscaFuncionario("");
  };

  const handleRemoverFuncionarioComissao = () => {
    setFuncionarioComissao(null);
    setBuscaFuncionario("");
  };

  const handleNovaVenda = () => {
    if (window.confirm("Descartar venda atual sem salvar?")) {
      limparVenda();
    }
  };

  const handleToggleTemEntrega = (temEntrega) => {
    setVendaAtual((prev) => {
      const taxaEntrega = temEntrega ? prev.entrega?.taxa_entrega_total || 0 : 0;
      return {
        ...prev,
        tem_entrega: temEntrega,
        total: recalcularTotalComEntrega(prev.subtotal, taxaEntrega),
        entrega: temEntrega ? prev.entrega : criarEntregaVazia(),
      };
    });
  };

  const handleSelecionarEnderecoEntrega = (enderecoCompleto) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: enderecoCompleto,
      },
    }));
  };

  const handleEnderecoEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: valor,
      },
    }));
  };

  const handleSelecionarEntregador = (entregadorId) => {
    const entregador = entregadores.find(
      (ent) => ent.id === parseInt(entregadorId, 10),
    );

    setEntregadorSelecionado(entregador || null);
    setVendaAtual((prev) => ({
      ...prev,
      entregador_id: entregador?.id || null,
    }));

    if (entregador) {
      calcularCustoOperacional(entregador);
    }
  };

  const handleTaxaEntregaTotalChange = (valor) => {
    const total = parseFloat(valor) || 0;
    const totalArredondado = parseFloat(total.toFixed(2));

    setVendaAtual((prev) => {
      const taxaLojaAtual = prev.entrega?.taxa_loja || 0;
      const taxaEntregadorCalculada = parseFloat(
        (totalArredondado - taxaLojaAtual).toFixed(2),
      );

      return {
        ...prev,
        total: recalcularTotalComEntrega(
          prev.subtotal,
          prev.tem_entrega ? totalArredondado : 0,
        ),
        entrega: {
          ...prev.entrega,
          taxa_entrega_total: totalArredondado,
          taxa_loja: parseFloat(taxaLojaAtual.toFixed(2)),
          taxa_entregador: taxaEntregadorCalculada,
        },
      };
    });
  };

  const handleTaxaLojaChange = (valor) => {
    const taxaLoja = parseFloat(valor) || 0;
    const taxaLojaArredondada = parseFloat(taxaLoja.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaEntregadorArredondada = parseFloat(
        (total - taxaLojaArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_loja: taxaLojaArredondada,
          taxa_entregador: taxaEntregadorArredondada,
        },
      };
    });
  };

  const handleTaxaEntregadorChange = (valor) => {
    const taxaEntregador = parseFloat(valor) || 0;
    const taxaEntregadorArredondada = parseFloat(taxaEntregador.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaLojaArredondada = parseFloat(
        (total - taxaEntregadorArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_entregador: taxaEntregadorArredondada,
          taxa_loja: taxaLojaArredondada,
        },
      };
    });
  };

  const handleObservacoesEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        observacoes_entrega: valor,
      },
    }));
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

  const carregarVendaEspecifica = async (
    vendaId,
    abrirModalPagamento = false,
  ) => {
    try {
      setLoading(true);
      const venda = await buscarVenda(vendaId);

      if (!venda) {
        alert("Venda não encontrada");
        return;
      }

      // Carregar cliente se existir
      let clienteCompleto = null;
      if (venda.cliente_id) {
        try {
          clienteCompleto = await buscarClientePorId(venda.cliente_id);
        } catch (error) {
          console.error("Erro ao buscar cliente:", error);
        }
      }

      // Buscar pagamentos da venda
      let pagamentosVenda = [];
      let totalPago = 0;
      try {
        const responsePagamentos = await api.get(
          `/vendas/${vendaId}/pagamentos`,
        );
        pagamentosVenda = responsePagamentos.data.pagamentos || [];
        totalPago = responsePagamentos.data.total_pago || 0;
      } catch (error) {
        console.error("Erro ao buscar pagamentos:", error);
      }

      // 🆕 CARREGAR DADOS DE COMISSÃO se existir funcionario_id
      debugLog("🔍 Venda carregada - funcionario_id:", venda.funcionario_id);
      let funcionarioCarregado = null;
      if (venda.funcionario_id) {
        try {
          // Buscar dados do funcionário
          const responseFuncionarios = await api.get(
            "/comissoes/configuracoes/funcionarios",
          );
          const funcionarios = responseFuncionarios.data?.data || [];
          debugLog("📋 Funcionários disponíveis:", funcionarios);
          funcionarioCarregado = funcionarios.find(
            (f) => f.id === venda.funcionario_id,
          );

          if (funcionarioCarregado) {
            setVendaComissionada(true);
            setFuncionarioComissao(funcionarioCarregado);
            debugLog(
              "✅ Funcionário comissão carregado:",
              funcionarioCarregado,
            );
          } else {
            debugWarn(
              "⚠️ Funcionário ID",
              venda.funcionario_id,
              "não encontrado na lista",
            );
          }
        } catch (error) {
          console.error("Erro ao carregar funcionário de comissão:", error);
        }
      } else {
        debugLog(
          "ℹ️ Venda sem funcionario_id - limpando estados de comissão",
        );
        // Se não tem funcionario_id, limpar estados de comissão
        setVendaComissionada(false);
        setFuncionarioComissao(null);
        setBuscaFuncionario("");
      }

      // Montar estado da venda
      const vendaCarregada = {
        id: venda.id,
        numero_venda: venda.numero_venda, // ✅ ADICIONADO
        status: venda.status,
        data_venda: venda.data_venda, // ✅ ADICIONADO
        cliente: clienteCompleto,
        pet: null,
        itens: venda.itens || [],
        subtotal: venda.subtotal || 0,
        desconto_valor: venda.desconto_valor || 0,
        desconto_percentual: venda.desconto_percentual || 0,
        total: venda.total || 0,
        observacoes: venda.observacoes || "",
        funcionario_id: venda.funcionario_id || null, // ✅ Funcionário de comissão
        entregador_id: venda.entregador_id || null, // ✅ Entregador
        tem_entrega: venda.tem_entrega || false,
        entrega: venda.entrega || {
          endereco_completo: "",
          taxa_entrega_total: 0,
          taxa_loja: 0,
          taxa_entregador: 0,
          observacoes_entrega: "",
        },
        pagamentos: pagamentosVenda,
        total_pago: totalPago,
      };

      setVendaAtual(vendaCarregada);
      setModoVisualizacao(true); // Modo leitura para venda existente

      // 🚚 Sincronizar entregador selecionado se a venda tem entregador
      if (venda.entregador_id) {
        debugLog("🔍 Venda tem entregador_id:", venda.entregador_id);
        try {
          // Buscar entregador direto da API (evita race condition com array entregadores)
          const responseEntregador = await api.get(
            `/clientes/${venda.entregador_id}`,
          );
          const entregadorCarregado = responseEntregador.data;

          if (entregadorCarregado && entregadorCarregado.is_entregador) {
            debugLog("✅ Entregador carregado:", entregadorCarregado.nome);
            setEntregadorSelecionado(entregadorCarregado);
            calcularCustoOperacional(entregadorCarregado);
          } else {
            debugWarn(
              "⚠️ Cliente ID",
              venda.entregador_id,
              "não é um entregador válido",
            );
          }
        } catch (error) {
          console.error("❌ Erro ao carregar entregador:", error);
          // Se falhar, tentar do array como fallback
          const entregador = entregadores.find(
            (e) => e.id === venda.entregador_id,
          );
          if (entregador) {
            debugLog(
              "✅ Entregador encontrado no array (fallback):",
              entregador.nome,
            );
            setEntregadorSelecionado(entregador);
            calcularCustoOperacional(entregador);
          }
        }
      } else {
        debugLog(
          "ℹ️ Venda sem entregador_id - limpando entregadorSelecionado",
        );
        setEntregadorSelecionado(null);
      }

      // 🆕 Se foi solicitado, abre o modal de pagamento após carregar
      if (abrirModalPagamento) {
        setTimeout(() => {
          setMostrarModalPagamento(true);
        }, 500); // Pequeno delay para garantir que tudo foi renderizado
      }
    } catch (error) {
      console.error("Erro ao carregar venda:", error);
      if (error.response?.status === 404) {
        alert("Venda não encontrada. Pode ter sido cancelada ou excluída.");
      } else {
        alert(
          "Erro ao carregar venda: " + (error.message || "Erro desconhecido"),
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // Buscar venda por número ou termo de busca
  const handleBuscarVenda = async () => {
    if (!searchVendaQuery.trim()) return;

    try {
      setLoading(true);

      // Extrair apenas números da query (exemplo: "VEN-0011" -> "0011")
      const numeroLimpo = searchVendaQuery.replace(/\D/g, "");

      if (!numeroLimpo) {
        alert("Digite um número de venda válido");
        setLoading(false);
        return;
      }

      debugLog("🔍 Buscando venda com número:", numeroLimpo);

      // Buscar diretamente usando o parâmetro 'busca' do backend
      const resultado = await listarVendas({
        busca: numeroLimpo,
        per_page: 50,
      });

      debugLog("📊 Vendas encontradas:", resultado.vendas?.length);

      if (!resultado.vendas || resultado.vendas.length === 0) {
        alert(`Nenhuma venda encontrada com "${numeroLimpo}"`);
        setLoading(false);
        return;
      }

      // Se encontrou apenas uma, carregar direto
      if (resultado.vendas.length === 1) {
        await carregarVendaEspecifica(resultado.vendas[0].id);
        setSearchVendaQuery(""); // Limpar campo após buscar
        return;
      }

      // Se encontrou múltiplas, mostrar lista para escolher
      const escolha = resultado.vendas
        .slice(0, 10) // Mostrar no máximo 10
        .map(
          (v, i) =>
            `${i + 1}. ${v.numero_venda} - ${v.cliente_nome || "Sem cliente"} - ${v.status}`,
        )
        .join("\n");

      const numeroEscolhido = prompt(
        `Encontradas ${resultado.vendas.length} vendas. Digite o número da opção:\n\n${escolha}`,
      );

      const indice = parseInt(numeroEscolhido) - 1;
      if (indice >= 0 && indice < resultado.vendas.length) {
        await carregarVendaEspecifica(resultado.vendas[indice].id);
        setSearchVendaQuery(""); // Limpar campo após buscar
      }
    } catch (error) {
      console.error("Erro ao buscar venda:", error);
      alert("Erro ao buscar venda: " + (error.message || "Erro desconhecido"));
    } finally {
      setLoading(false);
    }
  };

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

  // Salvar venda (rascunho)
  const salvarVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto ou serviço");
      return;
    }

    // 🔒 VALIDAÇÃO CRÍTICA: Verificar se tem caixa aberto
    if (!temCaixaAberto) {
      alert(
        "❌ Não é possível salvar venda sem caixa aberto. Abra um caixa primeiro.",
      );
      return;
    }

    if (loading) return; // Proteger contra duplo-clique

    setLoading(true);
    try {
      const entregadorIdResolvido =
        vendaAtual.entregador_id || entregadorSelecionado?.id || null;

      // Se a venda já existe (foi reaberta), atualizar ao invés de criar
      if (vendaAtual.id) {
        // Atualizar venda existente
        await api.put(`/vendas/${vendaAtual.id}`, {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id, // ✅ Single source of truth
          itens: vendaAtual.itens.map((item) => ({
            tipo: item.tipo,
            produto_id: item.produto_id,
            servico_descricao: item.servico_descricao,
            quantidade: item.quantidade,
            preco_unitario: item.preco_unitario || item.preco_venda,
            desconto_item: 0,
            subtotal: item.subtotal,
            lote_id: item.lote_id,
            pet_id: item.pet_id || vendaAtual.pet?.id,
          })),
          desconto_valor: 0, // Descontos já aplicados nos itens
          desconto_percentual: 0,
          observacoes: vendaAtual.observacoes,
          tem_entrega: vendaAtual.tem_entrega,
          taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
          endereco_entrega: vendaAtual.entrega?.endereco_completo,
          observacoes_entrega: vendaAtual.entrega?.observacoes_entrega,
          distancia_km: vendaAtual.entrega?.distancia_km,
          valor_por_km: vendaAtual.entrega?.valor_por_km,
          loja_origem: vendaAtual.entrega?.loja_origem,
          entregador_id: entregadorIdResolvido,
        });

        debugLog("🚨 DEBUG - Payload sendo enviado:", {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: entregadorIdResolvido,
          vendaAtual_completo: vendaAtual,
        });

        // Buscar pagamentos atualizados
        let totalPago = 0;
        try {
          const responsePagamentos = await api.get(
            `/vendas/${vendaAtual.id}/pagamentos`,
          );
          totalPago = responsePagamentos.data.total_pago || 0;
        } catch (error) {
          console.error("Erro ao buscar pagamentos:", error);
        }

        // Recalcular e atualizar status baseado nos pagamentos
        const totalVenda = vendaAtual.total;
        let novoStatus = "aberta";

        if (totalPago >= totalVenda - 0.01) {
          novoStatus = "finalizada";
        } else if (totalPago > 0) {
          novoStatus = "baixa_parcial";
        }

        // Atualizar status se necessário
        if (vendaAtual.status !== novoStatus) {
          await api.patch(`/vendas/${vendaAtual.id}/status`, {
            status: novoStatus,
          });
          debugLog(
            `✅ Status atualizado: ${vendaAtual.status} → ${novoStatus}`,
          );
        }

        alert("Venda atualizada com sucesso!");

        // Limpar PDV para nova venda
        limparVenda();
      } else {
        // Criar nova venda
        debugLog("🚀 CRIANDO VENDA - Versão 2.0 - DESCONTOS ZERADOS");
        debugLog("Desconto valor:", 0);
        debugLog("Desconto percentual:", 0);
        debugLog("✅ Checkbox Venda Comissionada:", vendaComissionada);
        debugLog("💼 Funcionário Comissão:", funcionarioComissao);
        debugLog(
          "📋 Funcionário ID enviado:",
          funcionarioComissao?.id || null,
        );

        if (vendaComissionada && !funcionarioComissao) {
          console.error(
            "⚠️ ERRO: Checkbox marcado mas funcionário não selecionado!",
          );
        }

        // 🚚 Calcular percentuais de taxa de entrega
        const taxaTotal = vendaAtual.entrega?.taxa_entrega_total || 0;
        const taxaLoja = vendaAtual.entrega?.taxa_loja || 0;
        const taxaEntregador = vendaAtual.entrega?.taxa_entregador || 0;
        const percentualLoja =
          taxaTotal > 0 ? (taxaLoja / taxaTotal) * 100 : 100;
        const percentualEntregador =
          taxaTotal > 0 ? (taxaEntregador / taxaTotal) * 100 : 0;

        const payloadVenda = {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id, // ✅ Usar do vendaAtual (sincronizado via useEffect)
          itens: vendaAtual.itens.map((item) => ({
            tipo: item.tipo,
            produto_id: item.produto_id,
            servico_descricao: item.servico_descricao,
            quantidade: item.quantidade,
            preco_unitario: item.preco_unitario || item.preco_venda,
            desconto_item: 0, // ZERADO - desconto já está no subtotal
            subtotal: item.subtotal, // Já vem com desconto aplicado
            lote_id: item.lote_id,
            pet_id: item.pet_id || vendaAtual.pet?.id,
          })),
          desconto_valor: 0, // CORREÇÃO APLICADA: Descontos já nos itens
          desconto_percentual: 0, // CORREÇÃO APLICADA: Não aplicar desconto novamente
          observacoes: vendaAtual.observacoes,
          tem_entrega: vendaAtual.tem_entrega,
          taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
          percentual_taxa_loja: percentualLoja,
          percentual_taxa_entregador: percentualEntregador,
          endereco_entrega: vendaAtual.entrega?.endereco_completo,
          observacoes_entrega: vendaAtual.entrega?.observacoes_entrega,
          distancia_km: vendaAtual.entrega?.distancia_km,
          valor_por_km: vendaAtual.entrega?.valor_por_km,
          loja_origem: vendaAtual.entrega?.loja_origem,
          entregador_id: entregadorIdResolvido,
        };

        debugLog(
          "📦 PAYLOAD COMPLETO antes de enviar:",
          JSON.stringify(payloadVenda, null, 2),
        );
        debugLog("🚚 Dados de entrega:", {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: entregadorIdResolvido,
          entregadorSelecionado: entregadorSelecionado?.id,
          vendaAtual_completo: vendaAtual,
        });
        debugLog("💰 Percentuais calculados:", {
          taxaTotal,
          taxaLoja,
          taxaEntregador,
          percentualLoja: `${percentualLoja.toFixed(2)}%`,
          percentualEntregador: `${percentualEntregador.toFixed(2)}%`,
        });

        await criarVenda(payloadVenda);

        alert("Venda salva com sucesso!");
        limparVenda();
      }

      carregarVendasRecentes();
    } catch (error) {
      console.error("❌ Erro ao salvar venda:", error);
      console.error("❌ Resposta do servidor:", error.response?.data);
      console.error("❌ Status:", error.response?.status);
      console.error("❌ Headers:", error.response?.headers);
      const errorDetail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        "Erro ao salvar venda";
      console.error("❌ Detalhes do erro:", errorDetail);
      alert(`Erro ao salvar venda: ${errorDetail}`);
    } finally {
      setLoading(false);
    }
  };

  // Buscar análise da venda
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

  // Abrir modal de pagamento
  const abrirModalPagamento = () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto ou serviço");
      return;
    }

    // Bloquear se a venda estiver finalizada (sem NF) ou pago_nf (com NF)
    if (vendaAtual.status === "finalizada" || vendaAtual.status === "pago_nf") {
      alert(
        'Esta venda está finalizada. Clique em "Reabrir Venda" para modificar.',
      );
      return;
    }

    setMostrarModalPagamento(true);
  };

  // Limpar venda
  const limparVenda = () => {
    setVendaAtual({
      cliente: null,
      pet: null,
      itens: [],
      subtotal: 0,
      desconto_valor: 0,
      desconto_percentual: 0,
      total: 0,
      observacoes: "",
      funcionario_id: null, // ✅ Limpar funcionário de comissão
      entregador_id: entregadorSelecionado?.id || null, // 🚚 Manter entregador padrão
      tem_entrega: false,
      entrega: {
        endereco_completo: "",
        taxa_entrega_total: 0,
        taxa_loja: 0,
        taxa_entregador: 0,
        observacoes_entrega: "",
      },
    });
    setVendaComissionada(false); // Desmarcar checkbox
    setFuncionarioComissao(null); // Limpar funcionário de comissão
    setBuscaFuncionario(""); // Limpar texto de busca
    setModoVisualizacao(false);
  };

  // Reabrir venda ao clicar (modo visualização)
  const reabrirVenda = async (venda) => {
    try {
      // Buscar detalhes completos da venda (incluindo itens)
      const vendaCompleta = await buscarVenda(venda.id);

      // Se tem cliente, buscar seus dados completos (incluindo pets)
      let clienteCompleto = null;
      if (vendaCompleta.cliente_id) {
        clienteCompleto = await buscarClientePorId(vendaCompleta.cliente_id);
      }

      // Buscar pagamentos da venda
      let pagamentosVenda = [];
      let totalPago = 0;
      try {
        const responsePagamentos = await api.get(
          `/vendas/${venda.id}/pagamentos`,
        );
        pagamentosVenda = responsePagamentos.data.pagamentos || [];
        totalPago = responsePagamentos.data.total_pago || 0;
      } catch (error) {
        console.error("Erro ao buscar pagamentos:", error);
      }

      // 🆕 CARREGAR DADOS DE COMISSÃO se existir funcionario_id
      debugLog(
        "🔍 Venda carregada - funcionario_id:",
        vendaCompleta.funcionario_id,
      );
      if (vendaCompleta.funcionario_id) {
        try {
          const responseFuncionarios = await api.get(
            "/comissoes/configuracoes/funcionarios",
          );
          const funcionarios = responseFuncionarios.data?.data || [];
          const funcionarioCarregado = funcionarios.find(
            (f) => f.id === vendaCompleta.funcionario_id,
          );

          if (funcionarioCarregado) {
            setVendaComissionada(true);
            setFuncionarioComissao(funcionarioCarregado);
            debugLog(
              "✅ Funcionário comissão carregado:",
              funcionarioCarregado,
            );
          } else {
            debugWarn(
              "⚠️ Funcionário ID",
              vendaCompleta.funcionario_id,
              "não encontrado na lista",
            );
          }
        } catch (error) {
          console.error("Erro ao carregar funcionário de comissão:", error);
        }
      } else {
        debugLog(
          "ℹ️ Venda sem funcionario_id - limpando estados de comissão",
        );
        setVendaComissionada(false);
        setFuncionarioComissao(null);
        setBuscaFuncionario("");
      }

      // Carregar dados da venda no PDV em modo visualização
      const vendaParaSetar = {
        id: vendaCompleta.id,
        numero_venda: vendaCompleta.numero_venda,
        data_venda: vendaCompleta.data_venda,
        cliente: clienteCompleto,
        pet: null,
        itens: vendaCompleta.itens || [],
        subtotal: parseFloat(vendaCompleta.subtotal || vendaCompleta.total),
        desconto_valor: parseFloat(vendaCompleta.desconto_valor || 0),
        desconto_percentual: parseFloat(vendaCompleta.desconto_percentual || 0),
        total: parseFloat(vendaCompleta.total),
        observacoes: vendaCompleta.observacoes || "",
        status: vendaCompleta.status,
        tem_entrega: vendaCompleta.tem_entrega || false,
        entregador_id: vendaCompleta.entregador_id || null,
        entrega: {
          endereco_completo: vendaCompleta.endereco_entrega || "",
          endereco_id: vendaCompleta.endereco_id || null,
          taxa_entrega_total: parseFloat(
            parseFloat(vendaCompleta.taxa_entrega || 0).toFixed(2),
          ),
          taxa_loja: parseFloat(
            parseFloat(vendaCompleta.entrega?.taxa_loja || 0).toFixed(2),
          ),
          taxa_entregador: parseFloat(
            parseFloat(vendaCompleta.entrega?.taxa_entregador || 0).toFixed(2),
          ),
          observacoes_entrega: vendaCompleta.observacoes_entrega || "",
          distancia_km: vendaCompleta.distancia_km || 0,
          valor_por_km: vendaCompleta.valor_por_km || 0,
          loja_origem: vendaCompleta.loja_origem || "",
          status_entrega: vendaCompleta.status_entrega || "pendente",
        },
        pagamentos: pagamentosVenda,
        total_pago: totalPago,
      };

      setVendaAtual(vendaParaSetar);

      // Ativar modo visualização (travado)
      setModoVisualizacao(true);

      // Scroll para o topo
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      console.error("Erro ao reabrir venda:", error);
      alert("Erro ao carregar os dados da venda");
    }
  };

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
              setPainelOportunidadesAberto(true);
              buscarOportunidades(vendaAtual.id || null);
            }}
            onToggleAssistente={() => {
              const abrindo = !painelAssistenteAberto;
              setPainelAssistenteAberto(abrindo);
              if (abrindo && mensagensAssistente.length === 0) {
                carregarInfoCliente(vendaAtual.cliente.id);
              }
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

