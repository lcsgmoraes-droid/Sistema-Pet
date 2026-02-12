// ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
// Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
// NÃO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenário real
// 3. Validar impacto financeiro

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ShoppingCart,
  User,
  Search,
  Plus,
  Minus,
  Trash2,
  Save,
  CreditCard,
  X,
  Clock,
  DollarSign,
  Package,
  AlertCircle,
  CheckCircle,
  Filter,
  Wallet,
  Printer,
  Receipt,
  History,
  AlertTriangle,
  BarChart2,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Layers,
  Star,
  RefreshCw,
  Scale,
  Calculator,
  Bell
} from 'lucide-react';
import { criarVenda, finalizarVenda, listarVendas, buscarVenda } from '../api/vendas';
import { getProdutos, getProdutosVendaveis } from '../api/produtos';
import { buscarClientes, buscarClientePorId, criarCliente, buscarRacas } from '../api/clientes';
import { useAuth } from '../contexts/AuthContext';
import ModalPagamento from '../components/ModalPagamento';
import ModalAbrirCaixa from '../components/ModalAbrirCaixa';
import MenuCaixa from '../components/MenuCaixa';
import ImprimirCupom from '../components/ImprimirCupom';
import VendasEmAberto from '../components/pdv/VendasEmAberto';
import HistoricoCliente from '../components/pdv/HistoricoCliente';
import ClienteInfoWidget from '../components/ClienteInfoWidget';
import AnaliseVendaDrawer from '../components/AnaliseVendaDrawer';
import ModalCalculadoraRacaoPDV from '../components/pdv/ModalCalculadoraRacaoPDV';
import ModalPendenciasEstoque from '../components/pdv/ModalPendenciasEstoque';
import api from '../api';
import { formatarVariacao, nomeCompletoVariacao } from '../utils/variacoes';
import { ehRacao, contarRacoes, obterUltimaRacao } from '../helpers/deteccaoRacao';
import toast from 'react-hot-toast';

export default function PDV() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  
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
    observacoes: '',
    funcionario_id: null,  // ✅ Funcionário para comissão
    entregador_id: null,  // 🚚 Entregador para entrega
    tem_entrega: false,
    entrega: {
      endereco_completo: '',
      taxa_entrega_total: 0,
      taxa_loja: 0,
      taxa_entregador: 0,
      observacoes_entrega: ''
    }
  });

  // Estados de busca
  const [buscarCliente, setBuscarCliente] = useState('');
  const [buscarProduto, setBuscarProduto] = useState('');
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const [produtosSugeridos, setProdutosSugeridos] = useState([]);

  // Estados de UI
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalCliente, setMostrarModalCliente] = useState(false);
  const [mostrarModalAbrirCaixa, setMostrarModalAbrirCaixa] = useState(false);
  const [mostrarVendasEmAberto, setMostrarVendasEmAberto] = useState(false);
  const [mostrarHistoricoCliente, setMostrarHistoricoCliente] = useState(false);
  const [mostrarPendenciasEstoque, setMostrarPendenciasEstoque] = useState(false);
  const [pendenciasCount, setPendenciasCount] = useState(0);
  const [vendasEmAbertoInfo, setVendasEmAbertoInfo] = useState(null);
  const [vendasRecentes, setVendasRecentes] = useState([]);
  const [filtroVendas, setFiltroVendas] = useState('24h');
  const [filtroStatus, setFiltroStatus] = useState('todas');
  const [filtroTemEntrega, setFiltroTemEntrega] = useState(false);
  const [loading, setLoading] = useState(false);
  const [modoVisualizacao, setModoVisualizacao] = useState(false);
  const [searchVendaQuery, setSearchVendaQuery] = useState('');
  const [caixaKey, setCaixaKey] = useState(0); // Para forçar recarga do MenuCaixa
  const [temCaixaAberto, setTemCaixaAberto] = useState(false);
  
  // Estados do modal de endereço
  const [mostrarModalEndereco, setMostrarModalEndereco] = useState(false);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);
  
  // Estados dos modais de desconto
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] = useState(false);
  const [itemEditando, setItemEditando] = useState(null);
  const [mostrarModalDescontoTotal, setMostrarModalDescontoTotal] = useState(false);
  const [tipoDescontoTotal, setTipoDescontoTotal] = useState('valor');
  const [valorDescontoTotal, setValorDescontoTotal] = useState(0);
  
  // Estado de comissão
  const [vendaComissionada, setVendaComissionada] = useState(false);
  const [funcionarioComissao, setFuncionarioComissao] = useState(null);
  const [funcionariosSugeridos, setFuncionariosSugeridos] = useState([]);
  const [buscaFuncionario, setBuscaFuncionario] = useState('');  // Texto de busca
  const [statusOriginalVenda, setStatusOriginalVenda] = useState(null);  // Guardar status antes de reabrir
  
  // 🚚 Estados para Entregadores e Custo Operacional (DECLARAR ANTES DOS useEffects)
  const [entregadores, setEntregadores] = useState([]);
  const [entregadorSelecionado, setEntregadorSelecionado] = useState(null);
  const [custoOperacionalEntrega, setCustoOperacionalEntrega] = useState(0);
  
  // ✅ Sincronizar funcionario_id com vendaAtual sempre que mudar
  useEffect(() => {
    setVendaAtual(prev => ({
      ...prev,
      funcionario_id: funcionarioComissao?.id || null
    }));
  }, [funcionarioComissao]);

  // ✅ Sincronizar entregador_id com vendaAtual sempre que mudar
  useEffect(() => {
    console.log('🔄 Sincronizando entregador_id:', entregadorSelecionado?.id || null);
    setVendaAtual(prev => ({
      ...prev,
      entregador_id: entregadorSelecionado?.id || null
    }));
  }, [entregadorSelecionado]);

  // Estados do drawer de análise de venda
  const [mostrarAnaliseVenda, setMostrarAnaliseVenda] = useState(false);
  const [dadosAnalise, setDadosAnalise] = useState(null);
  const [carregandoAnalise, setCarregandoAnalise] = useState(false);
  
  // Estado para controlar expansão de itens KIT no carrinho
  const [itensKitExpandidos, setItensKitExpandidos] = useState({});

  // Estados de controle de painéis laterais (UX - FASE 1)
  const [painelVendasAberto, setPainelVendasAberto] = useState(() => {
    const saved = localStorage.getItem('pdv_painel_vendas_aberto');
    return saved ? JSON.parse(saved) : false;
  });
  
  const [painelClienteAberto, setPainelClienteAberto] = useState(() => {
    const saved = localStorage.getItem('pdv_painel_cliente_aberto');
    return saved ? JSON.parse(saved) : false;
  });

  // Estado de Oportunidades Inteligentes (D4 - Backend Integration)
  // ✅ RULE: Oportunidades só aparecem com cliente selecionado
  const [painelOportunidadesAberto, setPainelOportunidadesAberto] = useState(false);
  const [opportunities, setOpportunities] = useState([]);

  // 🆕 Estados fiscais do PDV (PDV-UX-01)
  const [fiscalItens, setFiscalItens] = useState({});
  const [totalImpostos, setTotalImpostos] = useState(0);

  // 🆕 Estados para Calculadora de Ração no PDV
  const [mostrarCalculadoraRacao, setMostrarCalculadoraRacao] = useState(false);
  const [racaoIdFechada, setRacaoIdFechada] = useState(null); // ID da ração fechada (não reabre automático)

  // Refs
  const inputProdutoRef = useRef(null);

  // Persistir estado dos painéis no localStorage
  useEffect(() => {
    localStorage.setItem('pdv_painel_vendas_aberto', JSON.stringify(painelVendasAberto));
  }, [painelVendasAberto]);

  // Carregar pendências quando o cliente mudar
  useEffect(() => {
    if (vendaAtual.cliente) {
      carregarPendencias();
    }
  }, [vendaAtual.cliente]);

  // Salvar dados do carrinho no sessionStorage para a calculadora universal
  useEffect(() => {
    if (vendaAtual.itens && vendaAtual.itens.length > 0) {
      sessionStorage.setItem('pdv_calculadora_data', JSON.stringify({
        itens: vendaAtual.itens,
        clienteId: vendaAtual.cliente?.id || null
      }));
    } else {
      sessionStorage.removeItem('pdv_calculadora_data');
    }
  }, [vendaAtual.itens, vendaAtual.cliente]);

  useEffect(() => {
    localStorage.setItem('pdv_painel_cliente_aberto', JSON.stringify(painelClienteAberto));
  }, [painelClienteAberto]);

  // Verificar se há caixa aberto
  useEffect(() => {
    verificarCaixaAberto();
  }, [caixaKey]);

  const verificarCaixaAberto = async () => {
    try {
      const response = await api.get('/caixas/aberto');
      setTemCaixaAberto(!!response.data); // true se houver caixa, false se não
    } catch (error) {
      setTemCaixaAberto(false);
    }
  };
  
  // 🚚 Carregar entregadores disponíveis ao iniciar
  useEffect(() => {
    // console.log('⭐⭐⭐ useEffect de entregadores RODANDO! ⭐⭐⭐');
    carregarEntregadores();
  }, []);
  
  const carregarEntregadores = async () => {
    // console.log('🔥🔥🔥 INICIANDO carregarEntregadores 🔥🔥🔥');
    try {
      // console.log('📦 Fazendo request para /clientes...');
      const response = await api.get('/clientes', {
        params: {
          is_entregador: true,
          incluir_inativos: false,
          limit: 100
        }
      });
      
      // console.log('✅ Response recebido:', response.data);
      const entregadoresList = response.data.clientes || response.data || [];
      // console.log('📋 Total de entregadores carregados:', entregadoresList.length);
      // console.log('📋 Lista completa:', entregadoresList);
      setEntregadores(entregadoresList);
      
      // Pré-selecionar entregador padrão
      const entregadorPadrao = entregadoresList.find(e => {
        // console.log('🔍 Verificando entregador:', e.nome, 'entregador_padrao:', e.entregador_padrao);
        return e.entregador_padrao === true;
      });
      
      // console.log('🔍 Resultado da busca do padrão:', entregadorPadrao);
      
      if (entregadorPadrao) {
        // console.log('🎯🎯🎯 ENTREGADOR PADRÃO ENCONTRADO:', entregadorPadrao.nome, 'ID:', entregadorPadrao.id);
        setEntregadorSelecionado(entregadorPadrao);
        // ✅ Setar IMEDIATAMENTE no vendaAtual também (evitar race condition)
        setVendaAtual(prev => {
          // console.log('💾 Setando entregador_id no vendaAtual:', entregadorPadrao.id);
          return {
            ...prev,
            entregador_id: entregadorPadrao.id
          };
        });
        calcularCustoOperacional(entregadorPadrao);
      } else {
        // console.error('❌❌❌ NENHUM ENTREGADOR PADRÃO ENCONTRADO!');
      }
    } catch (error) {
      console.error('Erro ao carregar entregadores:', error);
      toast.error('Erro ao carregar lista de entregadores');
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
    if (entregador.modelo_custo_entrega === 'taxa_fixa' && entregador.taxa_fixa_entrega) {
      custo = Number(entregador.taxa_fixa_entrega);
    }
    // Modelo 2: Por KM (precisaria da distância - por enquanto usar taxa fixa ou 0)
    else if (entregador.modelo_custo_entrega === 'por_km' && entregador.valor_por_km_entrega) {
      // TODO: Integrar com cálculo de distância da API de mapas
      // Por enquanto, assumir 0 ou usar valor fixo como fallback
      custo = 0;
      // console.log('⚠️ Modelo por KM requer cálculo de distância');
    }
    // Modelo 3: Rateio RH (buscar do backend)
    else if (entregador.modelo_custo_entrega === 'rateio_rh' && entregador.controla_rh) {
      try {
        // Buscar custo calculado pelo backend
        const response = await api.get(`/entregadores/${entregador.id}/custo-operacional`);
        custo = response.data.custo_por_entrega || 0;
      } catch (error) {
        console.error('Erro ao buscar custo RH:', error);
        // Fallback: usar custo_rh_ajustado se disponível
        custo = entregador.custo_rh_ajustado || 0;
      }
    }
    // Fallback: buscar da configuração global
    else {
      try {
        const response = await api.get('/configuracoes/entregas');
        custo = response.data.taxa_fixa || 0;
      } catch (error) {
        console.error('Erro ao buscar configuração de entrega:', error);
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

  // Carregar pendências de estoque do cliente
  const carregarPendencias = async () => {
    if (!vendaAtual.cliente) {
      setPendenciasCount(0);
      return;
    }
    
    try {
      const response = await api.get(`/pendencias-estoque/cliente/${vendaAtual.cliente.id}`);
      const pendenciasAtivas = response.data.filter(p => p.status === 'pendente' || p.status === 'notificado');
      setPendenciasCount(pendenciasAtivas.length);
    } catch (error) {
      setPendenciasCount(0);
    }
  };

  // Buscar oportunidades do backend (D4 - Backend Integration)
  const buscarOportunidades = async (vendaId) => {
    if (!vendaId || !vendaAtual.cliente) {
      setOpportunities([]);
      return;
    }
    
    try {
      const response = await api.get(`/internal/pdv/oportunidades/${vendaId}`);
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
          venda_id: vendaAtual.id || null
        }
      };
      
      // Fire-and-forget: não aguarda resposta
      api.post('/internal/pdv/eventos-oportunidade', payload).catch(() => {
        // Erro silencioso - nunca afeta UX
      });
    } catch (error) {
      // Fail-safe: erro silencioso
    }
  };

  // 🆕 Função para calcular fiscal de um item (PDV-UX-01)
  async function calcularFiscalItem(item) {
    try {
      const payload = {
        produto_id: item.produto_id,
        preco_unitario: item.preco_unitario,
        quantidade: item.quantidade
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
  }, [filtroVendas, filtroStatus, filtroTemEntrega]);

  // Carregar venda específica se vier na URL
  useEffect(() => {
    const vendaId = searchParams.get('venda');
    if (vendaId) {
      carregarVendaEspecifica(parseInt(vendaId));
    }
  }, [searchParams]);

  // 🆕 DETECTAR REDIRECIONAMENTO DO CONTAS A RECEBER
  useEffect(() => {
    const vendaId = sessionStorage.getItem('abrirVenda');
    const abrirModal = sessionStorage.getItem('abrirModalPagamento');
    
    if (vendaId && abrirModal === 'true') {
      // Limpa os dados do sessionStorage
      sessionStorage.removeItem('abrirVenda');
      sessionStorage.removeItem('abrirModalPagamento');
      
      // Carrega a venda e abre o modal
      carregarVendaEspecifica(parseInt(vendaId), true);
    }
  }, []);

  // Funções do modal de endereço
  const abrirModalEnderecoPDV = () => {
    setEnderecoAtual({
      tipo: 'entrega',
      apelido: '',
      cep: '',
      endereco: '',
      numero: '',
      complemento: '',
      bairro: '',
      cidade: '',
      estado: ''
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
      const response = await fetch(`https://viacep.com.br/ws/${cep.replace('-', '')}/json/`);
      const data = await response.json();

      if (data.erro) {
        alert('CEP não encontrado');
        return;
      }

      setEnderecoAtual(prev => ({
        ...prev,
        endereco: data.logradouro || '',
        bairro: data.bairro || '',
        cidade: data.localidade || '',
        estado: data.uf || ''
      }));
    } catch (error) {
      console.error('Erro ao buscar CEP:', error);
      alert('Erro ao buscar CEP');
    } finally {
      setLoadingCep(false);
    }
  };

  const salvarEnderecoNoCliente = async () => {
    if (!enderecoAtual.cep || !enderecoAtual.endereco || !enderecoAtual.cidade) {
      alert('Preencha pelo menos CEP, Endereço e Cidade');
      return;
    }

    if (!vendaAtual.cliente || !vendaAtual.cliente.id) {
      alert('Selecione um cliente primeiro');
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
        enderecos_adicionais: enderecosAdicionais
      });

      // Atualizar cliente na venda atual
      const clienteAtualizado = await buscarClientePorId(vendaAtual.cliente.id);
      setVendaAtual({
        ...vendaAtual,
        cliente: clienteAtualizado
      });

      alert('Endereço adicionado com sucesso!');
      fecharModalEndereco();
    } catch (error) {
      console.error('Erro ao salvar endereço:', error);
      alert('Erro ao salvar endereço. Tente novamente.');
    }
  };

  // Funções de desconto individual
  const abrirModalDescontoItem = (item) => {
    setItemEditando({
      ...item,
      preco: item.preco_unitario, // Garantir que preco está definido
      descontoValor: item.desconto_valor || 0,
      descontoPercentual: item.desconto_percentual || 0,
      tipoDesconto: 'valor' // Sempre começar com valor (R$)
    });
    setMostrarModalDescontoItem(true);
  };

  const salvarDescontoItem = () => {
    const itensAtualizados = vendaAtual.itens.map(item => {
      if (item.produto_id === itemEditando.produto_id) {
        const precoUnitario = itemEditando.preco;
        const quantidade = item.quantidade;
        const subtotalSemDesconto = precoUnitario * quantidade;
        let descontoValor = 0;
        let descontoPercentual = 0;

        if (itemEditando.tipoDesconto === 'valor') {
          descontoValor = parseFloat(itemEditando.descontoValor) || 0;
          // Calcular percentual sobre o total do item (preço × quantidade)
          descontoPercentual = subtotalSemDesconto > 0 ? (descontoValor / subtotalSemDesconto) * 100 : 0;
        } else {
          descontoPercentual = parseFloat(itemEditando.descontoPercentual) || 0;
          // Desconto total sobre o item (não por unidade)
          descontoValor = (subtotalSemDesconto * descontoPercentual) / 100;
        }

        const precoComDesconto = precoUnitario - (descontoValor / quantidade);
        const subtotal = subtotalSemDesconto - descontoValor;

        return {
          ...item,
          desconto_valor: descontoValor,
          desconto_percentual: descontoPercentual,
          tipo_desconto_aplicado: itemEditando.tipoDesconto, // 🆕 Salvar tipo original
          preco_com_desconto: precoComDesconto,
          subtotal
        };
      }
      return item;
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  // Funções de desconto total
  const abrirModalDescontoTotal = () => {
    setMostrarModalDescontoTotal(true);
  };

  const aplicarDescontoTotal = (tipoDesconto, valor) => {
    const subtotal = vendaAtual.subtotal;
    let desconto = 0;
    let descontoPercentual = 0;

    if (tipoDesconto === 'valor') {
      desconto = parseFloat(valor) || 0;
      descontoPercentual = subtotal > 0 ? (desconto / subtotal) * 100 : 0;
    } else {
      descontoPercentual = parseFloat(valor) || 0;
      desconto = (subtotal * descontoPercentual) / 100;
    }

    const taxaEntrega = vendaAtual.tem_entrega ? (vendaAtual.entrega?.taxa_entrega_total || 0) : 0;
    const total = subtotal - desconto + taxaEntrega;

    setVendaAtual({
      ...vendaAtual,
      desconto_valor: desconto,
      desconto_percentual: descontoPercentual,
      total
    });

    setMostrarModalDescontoTotal(false);
  };

  const carregarVendasRecentes = async () => {
    try {
      const hoje = new Date();
      let dataInicio;

      if (filtroVendas === '24h') {
        dataInicio = new Date(hoje.getTime() - 24 * 60 * 60 * 1000);
      } else if (filtroVendas === '7d') {
        dataInicio = new Date(hoje.getTime() - 7 * 24 * 60 * 60 * 1000);
      } else {
        dataInicio = new Date(hoje.getTime() - 30 * 24 * 60 * 60 * 1000);
      }

      const params = {
        data_inicio: dataInicio.toISOString().split('T')[0],
        data_fim: hoje.toISOString().split('T')[0],
        per_page: 10
      };

      if (filtroStatus === 'pago') {
        params.status = 'finalizada';
      } else if (filtroStatus === 'aberta') {
        params.status = 'aberta';
      }
      // 'todas' não adiciona filtro de status
      
      // Filtro de tem entrega - só adicionar se estiver marcado
      if (filtroTemEntrega === true) {
        params.tem_entrega = true;
      }

      // console.log('Parâmetros de busca:', params);
      const resultado = await listarVendas(params);
      // console.log('Vendas encontradas:', resultado.vendas?.length);

      setVendasRecentes(resultado.vendas || []);
    } catch (error) {
      console.error('Erro ao carregar vendas:', error);
    }
  };

  const carregarVendaEspecifica = async (vendaId, abrirModalPagamento = false) => {
    try {
      setLoading(true);
      const venda = await buscarVenda(vendaId);
      
      if (!venda) {
        alert('Venda não encontrada');
        return;
      }

      // Carregar cliente se existir
      let clienteCompleto = null;
      if (venda.cliente_id) {
        try {
          clienteCompleto = await buscarClientePorId(venda.cliente_id);
        } catch (error) {
          console.error('Erro ao buscar cliente:', error);
        }
      }

      // Buscar pagamentos da venda
      let pagamentosVenda = [];
      let totalPago = 0;
      try {
        const responsePagamentos = await api.get(`/vendas/${vendaId}/pagamentos`);
        pagamentosVenda = responsePagamentos.data.pagamentos || [];
        totalPago = responsePagamentos.data.total_pago || 0;
      } catch (error) {
        console.error('Erro ao buscar pagamentos:', error);
      }

      // 🆕 CARREGAR DADOS DE COMISSÃO se existir funcionario_id
      console.log('🔍 Venda carregada - funcionario_id:', venda.funcionario_id);
      let funcionarioCarregado = null;
      if (venda.funcionario_id) {
        try {
          // Buscar dados do funcionário
          const responseFuncionarios = await api.get('/comissoes/configuracoes/funcionarios');
          const funcionarios = responseFuncionarios.data?.data || [];
          console.log('📋 Funcionários disponíveis:', funcionarios);
          funcionarioCarregado = funcionarios.find(f => f.id === venda.funcionario_id);
          
          if (funcionarioCarregado) {
            setVendaComissionada(true);
            setFuncionarioComissao(funcionarioCarregado);
            console.log('✅ Funcionário comissão carregado:', funcionarioCarregado);
          } else {
            console.warn('⚠️ Funcionário ID', venda.funcionario_id, 'não encontrado na lista');
          }
        } catch (error) {
          console.error('Erro ao carregar funcionário de comissão:', error);
        }
      } else {
        console.log('ℹ️ Venda sem funcionario_id - limpando estados de comissão');
        // Se não tem funcionario_id, limpar estados de comissão
        setVendaComissionada(false);
        setFuncionarioComissao(null);
        setBuscaFuncionario('');
      }

      // Montar estado da venda
      const vendaCarregada = {
        id: venda.id,
        numero_venda: venda.numero_venda,  // ✅ ADICIONADO
        status: venda.status,
        data_venda: venda.data_venda,  // ✅ ADICIONADO
        cliente: clienteCompleto,
        pet: null,
        itens: venda.itens || [],
        subtotal: venda.subtotal || 0,
        desconto_valor: venda.desconto_valor || 0,
        desconto_percentual: venda.desconto_percentual || 0,
        total: venda.total || 0,
        observacoes: venda.observacoes || '',
        funcionario_id: venda.funcionario_id || null,  // ✅ Funcionário de comissão
        entregador_id: venda.entregador_id || null,  // ✅ Entregador
        tem_entrega: venda.tem_entrega || false,
        entrega: venda.entrega || {
          endereco_completo: '',
          taxa_entrega_total: 0,
          taxa_loja: 0,
          taxa_entregador: 0,
          observacoes_entrega: ''
        },
        pagamentos: pagamentosVenda,
        total_pago: totalPago
      };

      setVendaAtual(vendaCarregada);
      setModoVisualizacao(true); // Modo leitura para venda existente
      
      // 🚚 Sincronizar entregador selecionado se a venda tem entregador
      if (venda.entregador_id) {
        console.log('🔍 Venda tem entregador_id:', venda.entregador_id);
        try {
          // Buscar entregador direto da API (evita race condition com array entregadores)
          const responseEntregador = await api.get(`/clientes/${venda.entregador_id}`);
          const entregadorCarregado = responseEntregador.data;
          
          if (entregadorCarregado && entregadorCarregado.is_entregador) {
            console.log('✅ Entregador carregado:', entregadorCarregado.nome);
            setEntregadorSelecionado(entregadorCarregado);
            calcularCustoOperacional(entregadorCarregado);
          } else {
            console.warn('⚠️ Cliente ID', venda.entregador_id, 'não é um entregador válido');
          }
        } catch (error) {
          console.error('❌ Erro ao carregar entregador:', error);
          // Se falhar, tentar do array como fallback
          const entregador = entregadores.find(e => e.id === venda.entregador_id);
          if (entregador) {
            console.log('✅ Entregador encontrado no array (fallback):', entregador.nome);
            setEntregadorSelecionado(entregador);
            calcularCustoOperacional(entregador);
          }
        }
      } else {
        console.log('ℹ️ Venda sem entregador_id - limpando entregadorSelecionado');
        setEntregadorSelecionado(null);
      }
      
      // 🆕 Se foi solicitado, abre o modal de pagamento após carregar
      if (abrirModalPagamento) {
        setTimeout(() => {
          setMostrarModalPagamento(true);
        }, 500); // Pequeno delay para garantir que tudo foi renderizado
      }
      
    } catch (error) {
      console.error('Erro ao carregar venda:', error);
      alert('Erro ao carregar venda: ' + (error.message || 'Erro desconhecido'));
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
      const numeroLimpo = searchVendaQuery.replace(/\D/g, '');
      
      if (!numeroLimpo) {
        alert('Digite um número de venda válido');
        setLoading(false);
        return;
      }
      
      console.log('🔍 Buscando venda com número:', numeroLimpo);
      
      // Buscar diretamente usando o parâmetro 'busca' do backend
      const resultado = await listarVendas({ 
        busca: numeroLimpo,
        per_page: 50
      });
      
      console.log('📊 Vendas encontradas:', resultado.vendas?.length);
      
      if (!resultado.vendas || resultado.vendas.length === 0) {
        alert(`Nenhuma venda encontrada com "${numeroLimpo}"`);
        setLoading(false);
        return;
      }
      
      // Se encontrou apenas uma, carregar direto
      if (resultado.vendas.length === 1) {
        await carregarVendaEspecifica(resultado.vendas[0].id);
        setSearchVendaQuery(''); // Limpar campo após buscar
        return;
      }
      
      // Se encontrou múltiplas, mostrar lista para escolher
      const escolha = resultado.vendas
        .slice(0, 10) // Mostrar no máximo 10
        .map((v, i) => `${i + 1}. ${v.numero_venda} - ${v.cliente_nome || 'Sem cliente'} - ${v.status}`)
        .join('\n');
      
      const numeroEscolhido = prompt(
        `Encontradas ${resultado.vendas.length} vendas. Digite o número da opção:\n\n${escolha}`
      );
      
      const indice = parseInt(numeroEscolhido) - 1;
      if (indice >= 0 && indice < resultado.vendas.length) {
        await carregarVendaEspecifica(resultado.vendas[indice].id);
        setSearchVendaQuery(''); // Limpar campo após buscar
      }
      
    } catch (error) {
      console.error('Erro ao buscar venda:', error);
      alert('Erro ao buscar venda: ' + (error.message || 'Erro desconhecido'));
    } finally {
      setLoading(false);
    }
  };

  // Buscar clientes
  useEffect(() => {
    if (buscarCliente.length >= 2) {
      const timer = setTimeout(async () => {
        try {
          const clientes = await buscarClientes({ search: buscarCliente });
          setClientesSugeridos(clientes || []);
        } catch (error) {
          console.error('Erro ao buscar clientes:', error);
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
    if (buscarProduto.length >= 2) {
      const timer = setTimeout(async () => {
        try {
          const response = await getProdutosVendaveis({ busca: buscarProduto });
          const produtos = response.data.items || [];
          setProdutosSugeridos(produtos);
        } catch (error) {
          console.error('Erro ao buscar produtos:', error);
          setProdutosSugeridos([]);
        }
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setProdutosSugeridos([]);
    }
  }, [buscarProduto]);

  // Selecionar cliente
  const selecionarCliente = async (cliente) => {
    setVendaAtual({ ...vendaAtual, cliente, pet: null });
    setBuscarCliente('');
    setClientesSugeridos([]);
    
    // Verificar se cliente tem vendas em aberto
    try {
      const response = await api.get(`/clientes/${cliente.id}/vendas-em-aberto`);
      if (response.data.resumo.total_vendas > 0) {
        setVendasEmAbertoInfo(response.data.resumo);
      } else {
        setVendasEmAbertoInfo(null);
      }
    } catch (error) {
      console.error('Erro ao verificar vendas em aberto:', error);
      setVendasEmAbertoInfo(null);
    }
  };

  // Selecionar pet
  const selecionarPet = (pet) => {
    setVendaAtual({ ...vendaAtual, pet });
  };

  // Adicionar produto ao carrinho
  const adicionarProduto = (produto) => {
    console.log('🛒 Produto sendo adicionado:', {
      nome: produto.nome,
      categoria_id: produto.categoria_id,
      categoria_nome: produto.categoria_nome,
      peso_embalagem: produto.peso_embalagem,
      classificacao_racao: produto.classificacao_racao
    });
    
    const itemExistente = vendaAtual.itens.find(
      (item) => item.produto_id === produto.id
    );

    let novosItens;
    if (itemExistente) {
      // Incrementar quantidade
      novosItens = vendaAtual.itens.map((item) =>
        item.produto_id === produto.id
          ? {
              ...item,
              quantidade: item.quantidade + 1,
              subtotal: (item.quantidade + 1) * item.preco_unitario
            }
          : item
      );
    } else {
      // Adicionar novo item
      novosItens = [
        ...vendaAtual.itens,
        {
          tipo: 'produto',
          produto_id: produto.id,
          produto_nome: produto.nome,
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
          classificacao_racao: produto.classificacao_racao
        }
      ];
    }

    recalcularTotais(novosItens);
    setBuscarProduto('');
    setProdutosSugeridos([]);
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
        if (item.tipo_desconto_aplicado === 'percentual' && item.desconto_percentual > 0) {
          // Desconto percentual: recalcular o valor baseado na nova quantidade
          novoDescontoValor = (subtotalSemDesconto * item.desconto_percentual) / 100;
        }
        // Se foi desconto em VALOR: mantém o desconto_valor fixo
        
        const subtotalComDesconto = subtotalSemDesconto - novoDescontoValor;
        
        return {
          ...item,
          quantidade: novaQuantidade,
          desconto_valor: novoDescontoValor,
          subtotal: subtotalComDesconto
        };
      }
      return item;
    });
    recalcularTotais(novosItens);
  };

  // 🥫 Abrir modal de calculadora de ração manualmente (via botão flutuante)
  const abrirCalculadoraRacao = () => {
    console.log('🔍 Debug - Itens no carrinho:', vendaAtual.itens);
    console.log('🔍 Debug - Verificando rações...');
    
    vendaAtual.itens.forEach((item, index) => {
      console.log(`  Item ${index + 1}: ${item.produto_nome}`);
      console.log(`    - peso_embalagem: ${item.peso_embalagem}`);
      console.log(`    - classificacao_racao: ${item.classificacao_racao}`);
      console.log(`    - categoria_id: ${item.categoria_id}`);
      console.log(`    - categoria_nome: ${item.categoria_nome}`);
      console.log(`    - É ração?: ${ehRacao(item)}`);
    });
    
    const racoes = contarRacoes(vendaAtual.itens);
    console.log(`📊 Total de rações encontradas: ${racoes}`);
    
    if (racoes === 0) {
      toast.error('Nenhuma ração no carrinho');
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
    setItensKitExpandidos(prev => ({
      ...prev,
      [index]: !prev[index]
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
    const descontoPercentual = totalBruto > 0 ? (descontoItens / totalBruto) * 100 : 0;

    const taxaEntrega = vendaAtual.tem_entrega ? (vendaAtual.entrega?.taxa_entrega_total || 0) : 0;
    // O subtotal já tem o desconto aplicado (soma dos item.subtotal que já considera desconto individual)
    // Então o total final é: subtotal + taxa de entrega
    const total = subtotal + taxaEntrega;

    setVendaAtual({
      ...vendaAtual,
      itens,
      subtotal,
      desconto_valor: descontoItens,
      desconto_percentual: descontoPercentual,
      total
    });
  };

  // Salvar venda (rascunho)
  const salvarVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert('Adicione pelo menos um produto ou serviço');
      return;
    }

    if (loading) return; // Proteger contra duplo-clique
    
    setLoading(true);
    try {
      // Se a venda já existe (foi reaberta), atualizar ao invés de criar
      if (vendaAtual.id) {
        // Atualizar venda existente
        await api.put(`/vendas/${vendaAtual.id}`, {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id,  // ✅ Single source of truth
          itens: vendaAtual.itens.map(item => ({
            tipo: item.tipo,
            produto_id: item.produto_id,
            servico_descricao: item.servico_descricao,
            quantidade: item.quantidade,
            preco_unitario: item.preco_unitario || item.preco_venda,
            desconto_item: 0,
            subtotal: item.subtotal,
            lote_id: item.lote_id,
            pet_id: item.pet_id || vendaAtual.pet?.id
          })),
          desconto_valor: 0,  // Descontos já aplicados nos itens
          desconto_percentual: 0,
          observacoes: vendaAtual.observacoes,
          tem_entrega: vendaAtual.tem_entrega,
          taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
          endereco_entrega: vendaAtual.entrega?.endereco_completo,
          observacoes_entrega: vendaAtual.entrega?.observacoes_entrega,
          distancia_km: vendaAtual.entrega?.distancia_km,
          valor_por_km: vendaAtual.entrega?.valor_por_km,
          loja_origem: vendaAtual.entrega?.loja_origem,
          entregador_id: vendaAtual.entregador_id
        });
        
        console.log('🚨 DEBUG - Payload sendo enviado:', {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: vendaAtual.entregador_id,
          vendaAtual_completo: vendaAtual
        });
        
        // Buscar pagamentos atualizados
        let totalPago = 0;
        try {
          const responsePagamentos = await api.get(`/vendas/${vendaAtual.id}/pagamentos`);
          totalPago = responsePagamentos.data.total_pago || 0;
        } catch (error) {
          console.error('Erro ao buscar pagamentos:', error);
        }
        
        // Recalcular e atualizar status baseado nos pagamentos
        const totalVenda = vendaAtual.total;
        let novoStatus = 'aberta';
        
        if (totalPago >= totalVenda - 0.01) {
          novoStatus = 'finalizada';
        } else if (totalPago > 0) {
          novoStatus = 'baixa_parcial';
        }
        
        // Atualizar status se necessário
        if (vendaAtual.status !== novoStatus) {
          await api.patch(`/vendas/${vendaAtual.id}/status`, { status: novoStatus });
          console.log(`✅ Status atualizado: ${vendaAtual.status} → ${novoStatus}`);
        }
        
        alert('Venda atualizada com sucesso!');
        
        // Limpar PDV para nova venda
        limparVenda();
        
      } else {
        // Criar nova venda
        console.log('🚀 CRIANDO VENDA - Versão 2.0 - DESCONTOS ZERADOS');
        console.log('Desconto valor:', 0);
        console.log('Desconto percentual:', 0);
        console.log('✅ Checkbox Venda Comissionada:', vendaComissionada);
        console.log('💼 Funcionário Comissão:', funcionarioComissao);
        console.log('📋 Funcionário ID enviado:', funcionarioComissao?.id || null);
        
        if (vendaComissionada && !funcionarioComissao) {
          console.error('⚠️ ERRO: Checkbox marcado mas funcionário não selecionado!');
        }
        
        // 🚚 Calcular percentuais de taxa de entrega
        const taxaTotal = vendaAtual.entrega?.taxa_entrega_total || 0;
        const taxaLoja = vendaAtual.entrega?.taxa_loja || 0;
        const taxaEntregador = vendaAtual.entrega?.taxa_entregador || 0;
        const percentualLoja = taxaTotal > 0 ? ((taxaLoja / taxaTotal) * 100) : 100;
        const percentualEntregador = taxaTotal > 0 ? ((taxaEntregador / taxaTotal) * 100) : 0;

        const payloadVenda = {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id,  // ✅ Usar do vendaAtual (sincronizado via useEffect)
          itens: vendaAtual.itens.map(item => ({
            tipo: item.tipo,
            produto_id: item.produto_id,
            servico_descricao: item.servico_descricao,
            quantidade: item.quantidade,
            preco_unitario: item.preco_unitario || item.preco_venda,
            desconto_item: 0,  // ZERADO - desconto já está no subtotal
            subtotal: item.subtotal,  // Já vem com desconto aplicado
            lote_id: item.lote_id,
            pet_id: item.pet_id || vendaAtual.pet?.id
          })),
          desconto_valor: 0,  // CORREÇÃO APLICADA: Descontos já nos itens
          desconto_percentual: 0,  // CORREÇÃO APLICADA: Não aplicar desconto novamente
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
          entregador_id: vendaAtual.entregador_id
        };

        console.log('📦 PAYLOAD COMPLETO antes de enviar:', JSON.stringify(payloadVenda, null, 2));
        console.log('🚚 Dados de entrega:', {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: vendaAtual.entregador_id,
          entregadorSelecionado: entregadorSelecionado?.id,
          vendaAtual_completo: vendaAtual
        });
        console.log('💰 Percentuais calculados:', {
          taxaTotal,
          taxaLoja,
          taxaEntregador,
          percentualLoja: `${percentualLoja.toFixed(2)}%`,
          percentualEntregador: `${percentualEntregador.toFixed(2)}%`
        });

        await criarVenda(payloadVenda);

        alert('Venda salva com sucesso!');
        limparVenda();
      }
      
      carregarVendasRecentes();
    } catch (error) {
      console.error('❌ Erro ao salvar venda:', error);
      console.error('❌ Resposta do servidor:', error.response?.data);
      console.error('❌ Status:', error.response?.status);
      console.error('❌ Headers:', error.response?.headers);
      const errorDetail = error.response?.data?.detail || error.response?.data?.message || 'Erro ao salvar venda';
      console.error('❌ Detalhes do erro:', errorDetail);
      alert(`Erro ao salvar venda: ${errorDetail}`);
    } finally {
      setLoading(false);
    }
  };

  // Buscar análise da venda
  const buscarAnaliseVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert('Adicione pelo menos um produto para ver a análise');
      return;
    }

    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      const response = await api.post('/formas-pagamento/analisar-venda', {
        items: vendaAtual.itens.map(item => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo
        })),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: vendaAtual.forma_pagamento_id || null,
        parcelas: vendaAtual.parcelas || 1,
        vendedor_id: vendaAtual.funcionario_id  // Single source of truth
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error('Erro ao buscar análise:', error);
      alert('Erro ao carregar análise da venda');
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
      const response = await api.post('/formas-pagamento/analisar-venda', {
        items: venda.itens.map(item => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo
        })),
        desconto: venda.desconto_valor || 0,
        taxa_entrega: venda.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: venda.forma_pagamento_id || null,
        parcelas: venda.parcelas || 1,
        vendedor_id: venda.vendedor_id || null
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error('Erro ao buscar análise:', error);
      alert('Erro ao carregar análise da venda');
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  // Analisar venda com múltiplas formas de pagamento (do modal)
  const analisarVendaComFormasPagamento = async (formasPagamento) => {
    console.log('🔍 DEBUG formasPagamento recebidas:', formasPagamento);
    
    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      console.log('💰 Enviando análise com múltiplas formas:', formasPagamento);

      // Fazer análise com os dados da venda atual E MÚLTIPLAS FORMAS
      const response = await api.post('/formas-pagamento/analisar-venda', {
        items: vendaAtual.itens.map(item => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade,
          preco_venda: item.preco_unitario || item.preco_venda,
          custo: item.custo
        })),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        formas_pagamento: formasPagamento,  // ARRAY de formas de pagamento
        vendedor_id: vendaAtual.funcionario_id  // Single source of truth
      });

      console.log('✅ Resposta da análise:', response.data);
      setDadosAnalise(response.data);
    } catch (error) {
      console.error('Erro ao buscar análise:', error);
      alert('Erro ao carregar análise da venda');
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  // Abrir modal de pagamento
  const abrirModalPagamento = () => {
    if (vendaAtual.itens.length === 0) {
      alert('Adicione pelo menos um produto ou serviço');
      return;
    }
    
    // Bloquear se a venda estiver finalizada (sem NF) ou pago_nf (com NF)
    if (vendaAtual.status === 'finalizada' || vendaAtual.status === 'pago_nf') {
      alert('Esta venda está finalizada. Clique em "Reabrir Venda" para modificar.');
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
      observacoes: '',
      funcionario_id: null,  // ✅ Limpar funcionário de comissão
      entregador_id: entregadorSelecionado?.id || null,  // 🚚 Manter entregador padrão
      tem_entrega: false,
      entrega: {
        endereco_completo: '',
        taxa_entrega_total: 0,
        taxa_loja: 0,
        taxa_entregador: 0,
        observacoes_entrega: ''
      }
    });
    setVendaComissionada(false);  // Desmarcar checkbox
    setFuncionarioComissao(null);  // Limpar funcionário de comissão
    setBuscaFuncionario('');  // Limpar texto de busca
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
        const responsePagamentos = await api.get(`/vendas/${venda.id}/pagamentos`);
        pagamentosVenda = responsePagamentos.data.pagamentos || [];
        totalPago = responsePagamentos.data.total_pago || 0;
      } catch (error) {
        console.error('Erro ao buscar pagamentos:', error);
      }

      // 🆕 CARREGAR DADOS DE COMISSÃO se existir funcionario_id
      console.log('🔍 Venda carregada - funcionario_id:', vendaCompleta.funcionario_id);
      if (vendaCompleta.funcionario_id) {
        try {
          const responseFuncionarios = await api.get('/comissoes/configuracoes/funcionarios');
          const funcionarios = responseFuncionarios.data?.data || [];
          const funcionarioCarregado = funcionarios.find(f => f.id === vendaCompleta.funcionario_id);
          
          if (funcionarioCarregado) {
            setVendaComissionada(true);
            setFuncionarioComissao(funcionarioCarregado);
            console.log('✅ Funcionário comissão carregado:', funcionarioCarregado);
          } else {
            console.warn('⚠️ Funcionário ID', vendaCompleta.funcionario_id, 'não encontrado na lista');
          }
        } catch (error) {
          console.error('Erro ao carregar funcionário de comissão:', error);
        }
      } else {
        console.log('ℹ️ Venda sem funcionario_id - limpando estados de comissão');
        setVendaComissionada(false);
        setFuncionarioComissao(null);
        setBuscaFuncionario('');
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
        observacoes: vendaCompleta.observacoes || '',
        status: vendaCompleta.status,
        tem_entrega: vendaCompleta.tem_entrega || false,
        entregador_id: vendaCompleta.entregador_id || null,
        entrega: {
          endereco_completo: vendaCompleta.endereco_entrega || '',
          endereco_id: vendaCompleta.endereco_id || null,
          taxa_entrega_total: parseFloat((parseFloat(vendaCompleta.taxa_entrega || 0)).toFixed(2)),
          taxa_loja: parseFloat((parseFloat(vendaCompleta.entrega?.taxa_loja || 0)).toFixed(2)),
          taxa_entregador: parseFloat((parseFloat(vendaCompleta.entrega?.taxa_entregador || 0)).toFixed(2)),
          observacoes_entrega: vendaCompleta.observacoes_entrega || '',
          distancia_km: vendaCompleta.distancia_km || 0,
          valor_por_km: vendaCompleta.valor_por_km || 0,
          loja_origem: vendaCompleta.loja_origem || '',
          status_entrega: vendaCompleta.status_entrega || 'pendente'
        },
        pagamentos: pagamentosVenda,
        total_pago: totalPago
      };
      
      setVendaAtual(vendaParaSetar);

      // Ativar modo visualização (travado)
      setModoVisualizacao(true);

      // Scroll para o topo
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      console.error('Erro ao reabrir venda:', error);
      alert('Erro ao carregar os dados da venda');
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
        await api.patch(`/vendas/${vendaAtual.id}`, {
          status: statusOriginalVenda
        });
        
        console.log(`✅ Status restaurado para: ${statusOriginalVenda} (alterações descartadas)`);
      } catch (error) {
        console.error('Erro ao restaurar status:', error);
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
      'Deseja realmente excluir esta venda?\n\nEsta ação não pode ser desfeita e o estoque será devolvido.'
    );
    
    if (!confirmar) return;
    
    try {
      setLoading(true);
      await api.delete(`/vendas/${vendaAtual.id}`);
      
      // Limpar venda e recarregar lista
      limparVenda();
      carregarVendasRecentes();
      
      alert('Venda excluída com sucesso!');
    } catch (error) {
      console.error('Erro ao excluir venda:', error);
      
      // Tratamento amigável de erros estruturados
      const errorData = error.response?.data?.detail;
      
      if (errorData && typeof errorData === 'object') {
        // Erro estruturado com passos
        let mensagem = `❌ ${errorData.erro || 'Erro ao excluir venda'}\n\n`;
        mensagem += `${errorData.mensagem || ''}\n\n`;
        
        if (errorData.solucao) {
          mensagem += `💡 Solução:\n${errorData.solucao}\n\n`;
        }
        
        if (errorData.passos && Array.isArray(errorData.passos)) {
          mensagem += `📋 Passos para resolver:\n`;
          errorData.passos.forEach(passo => {
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
      } else if (typeof errorData === 'string') {
        // Erro simples (string)
        alert(errorData);
      } else {
        // Fallback
        alert('Erro ao excluir venda. Verifique se não há vínculos pendentes.');
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
      'Deseja reabrir esta venda?\n\nOs pagamentos serão mantidos e o status mudará para "aberta".'
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
        desconto_percentual: parseFloat(vendaAtualizada.desconto_percentual || 0),
        total: parseFloat(vendaAtualizada.total),
        observacoes: vendaAtualizada.observacoes || '',
        status: 'aberta', // Garantir status correto
        tem_entrega: vendaAtualizada.tem_entrega || false,
        entrega: {
          endereco_completo: vendaAtualizada.endereco_entrega || '',
          endereco_id: vendaAtualizada.endereco_id || null,
          taxa_entrega_total: parseFloat((parseFloat(vendaAtualizada.taxa_entrega || 0)).toFixed(2)),
          taxa_loja: parseFloat((parseFloat(vendaAtualizada.taxa_loja || 0)).toFixed(2)),
          taxa_entregador: parseFloat((parseFloat(vendaAtualizada.taxa_entregador || 0)).toFixed(2)),
          observacoes_entrega: vendaAtualizada.observacoes_entrega || '',
          distancia_km: vendaAtualizada.distancia_km || 0,
          valor_por_km: vendaAtualizada.valor_por_km || 0,
          loja_origem: vendaAtualizada.loja_origem || '',
          status_entrega: vendaAtualizada.status_entrega || 'pendente'
        }
      });
      
      // Desativar modo visualização para permitir edição
      setModoVisualizacao(false);
      
      alert('Venda reaberta com sucesso! Agora você pode editá-la.\n\nATENÇÃO: Se você não fizer alterações e sair, a venda voltará ao status anterior.');
    } catch (error) {
      console.error('Erro ao reabrir venda:', error);
      alert(error.response?.data?.detail || 'Erro ao reabrir venda');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex h-screen bg-gray-50">
      {/* Área Principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <ShoppingCart className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Ponto de Venda</h1>
                <p className="text-sm text-gray-500">
                  {new Date().toLocaleDateString('pt-BR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </p>
              </div>
              
              {/* Busca Rápida de Venda */}
              <div className="flex items-center gap-2 ml-6">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Buscar venda (Ex: 0011)"
                    value={searchVendaQuery}
                    onChange={(e) => setSearchVendaQuery(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && searchVendaQuery.trim()) {
                        handleBuscarVenda();
                      }
                    }}
                    className="pl-10 pr-4 py-2 w-64 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  />
                  <Search className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" />
                </div>
                <button
                  onClick={handleBuscarVenda}
                  disabled={!searchVendaQuery.trim() || loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Buscar
                </button>
              </div>
            </div>

            {/* Ações rápidas */}
            <div className="flex items-center space-x-3">
              {/* Botão Pendências de Estoque */}
              {vendaAtual.cliente && (
                <button
                  onClick={() => setMostrarPendenciasEstoque(true)}
                  className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-orange-50 border-2 border-orange-400 rounded-lg transition-colors relative"
                  title="Lista de espera - Produtos sem estoque"
                >
                  <Bell className="w-5 h-5 text-orange-500" />
                  {pendenciasCount > 0 && (
                    <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
                      {pendenciasCount}
                    </span>
                  )}
                </button>
              )}
              
              {/* Botão Oportunidades Inteligentes - D4 Backend Integration */}
              {/* ✅ RULE: Botão só aparece se cliente selecionado */}
              {vendaAtual.cliente && (
                <button
                  onClick={() => {
                    setPainelOportunidadesAberto(true);
                    // Buscar oportunidades ao abrir painel (D4 - async, non-blocking)
                    if (vendaAtual.id) {
                      buscarOportunidades(vendaAtual.id);
                    }
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-yellow-50 border-2 border-yellow-400 rounded-lg transition-colors"
                  title="Ver oportunidades de venda"
                >
                  <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                  {opportunities.length > 0 && (
                    <span className="font-semibold text-yellow-600">
                      {Math.min(opportunities.length, 6)}
                    </span>
                  )}
                </button>
              )}

              {/* Menu de Controle de Caixa */}
              <MenuCaixa 
                key={caixaKey} 
                onAbrirCaixa={() => setMostrarModalAbrirCaixa(true)} 
              />

              {/* Botão Meus Caixas */}
              <button
                onClick={() => navigate('/meus-caixas')}
                className="flex items-center space-x-2 px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors"
                title="Ver histórico de caixas"
              >
                <Wallet className="w-5 h-5" />
                <span>Meus Caixas</span>
              </button>

              {/* Botões quando está editando uma venda existente */}
              {!modoVisualizacao && vendaAtual.id && (
                <>
                  <button
                    onClick={cancelarEdicao}
                    disabled={loading}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <X className="w-5 h-5" />
                    <span>Cancelar Edição</span>
                  </button>
                  <button
                    onClick={excluirVenda}
                    disabled={loading}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Trash2 className="w-5 h-5" />
                    <span>Excluir</span>
                  </button>
                </>
              )}

              <button
                onClick={salvarVenda}
                disabled={loading || modoVisualizacao || !temCaixaAberto}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title={!temCaixaAberto ? '🔒 Caixa fechado - Abra o caixa para salvar vendas' : 'Salvar venda atual'}
              >
                <Save className="w-5 h-5" />
                <span>Salvar</span>
                {!temCaixaAberto && <span className="text-xs">🔒</span>}
              </button>
              <button
                onClick={abrirModalPagamento}
                disabled={loading || vendaAtual.status === 'finalizada' || vendaAtual.status === 'pago_nf' || !temCaixaAberto}
                className="flex items-center space-x-2 px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title={!temCaixaAberto ? '🔒 Caixa fechado - Abra o caixa para registrar recebimentos' : 'Registrar pagamento da venda'}
              >
                <CreditCard className="w-5 h-5" />
                <span>Registrar Recebimento</span>
                {!temCaixaAberto && <span className="text-xs">🔒</span>}
              </button>
            </div>
          </div>
        </div>

        {/* Alerta de Caixa Fechado */}
        {!temCaixaAberto && !modoVisualizacao && (
          <div className="bg-red-50 border-b border-red-200 px-6 py-3">
            <div className="flex items-center justify-center max-w-5xl mx-auto">
              <div className="flex items-center space-x-2 text-red-800">
                <AlertCircle className="w-5 h-5" />
                <span className="font-bold text-lg">🔒 CAIXA FECHADO</span>
                <span className="text-sm">
                  - É necessário abrir o caixa para registrar vendas e recebimentos
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 🆕 NÚMERO DA VENDA - Aparece quando venda tem ID */}
        {vendaAtual.id && vendaAtual.numero_venda && (
          <div className="bg-blue-50 border-b border-blue-200 px-4 py-1.5">
            <div className="flex items-center justify-between max-w-5xl mx-auto">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-blue-800">Venda:</span>
                <div className="flex items-center gap-1.5 bg-white px-2 py-0.5 rounded border border-blue-300">
                  <span className="font-bold text-blue-700 text-sm">#{vendaAtual.numero_venda}</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(vendaAtual.numero_venda);
                      const btn = event.target.closest('button');
                      const originalText = btn.innerHTML;
                      btn.innerHTML = '✓';
                      btn.classList.add('text-green-600');
                      setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.classList.remove('text-green-600');
                      }, 1500);
                    }}
                    className="text-blue-600 hover:text-blue-800 transition-colors text-xs"
                    title="Copiar número da venda"
                  >
                    📋
                  </button>
                </div>
              </div>
              {vendaAtual.data_venda && (
                <span className="text-xs text-blue-600">
                  {new Date(vendaAtual.data_venda).toLocaleDateString('pt-BR')}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Alerta de Modo Visualização */}
        {modoVisualizacao && (
          <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-3">
            <div className="flex items-center justify-between max-w-5xl mx-auto">
              <div className="flex items-center space-x-2 text-yellow-800">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">
                  Modo Visualização - Venda {vendaAtual.status === 'finalizada' ? 'Finalizada' : 
                    vendaAtual.status === 'baixa_parcial' ? 'com Baixa Parcial' : 'Aberta'}
                </span>
                <span className="text-sm">
                  (Clique em Editar para modificar)
                </span>
              </div>
              <div className="flex items-center gap-2">
                {/* Botão Imprimir (sempre visível em modo visualização) */}
                <ImprimirCupom venda={vendaAtual} />
                
                {/* Botão Voltar - Fecha a visualização sem salvar */}
                <button
                  onClick={() => {
                    setModoVisualizacao(false);
                    limparVenda();
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                >
                  <X className="w-4 h-4" />
                  Voltar
                </button>
                
                {/* Botão Reabrir: aparece para vendas finalizadas ou parcialmente pagas */}
                {(vendaAtual.status === 'finalizada' || vendaAtual.status === 'baixa_parcial') && (
                  <button
                    onClick={mudarStatusParaAberta}
                    className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors"
                  >
                    <AlertCircle className="w-4 h-4" />
                    Reabrir Venda
                  </button>
                )}
                
                {/* Botão Editar: SÓ para vendas abertas */}
                {vendaAtual.status === 'aberta' && (
                  <button
                    onClick={habilitarEdicao}
                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium transition-colors"
                  >
                    Editar
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Conteúdo Principal */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-5xl mx-auto space-y-4">
            {/* Card Cliente */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <User className="w-5 h-5 mr-2 text-blue-600" />
                  Cliente
                </h2>
                {vendaAtual.cliente && !modoVisualizacao && (
                  <button
                    onClick={() => setVendaAtual({ ...vendaAtual, cliente: null, pet: null })}
                    className="text-sm text-red-600 hover:text-red-700"
                  >
                    Remover
                  </button>
                )}
              </div>

              {!vendaAtual.cliente ? (
                <div className="space-y-3">
                  <div className="relative">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 relative">
                        <input
                          type="text"
                          value={buscarCliente}
                          onChange={(e) => setBuscarCliente(e.target.value)}
                          placeholder="Digite nome, CPF ou telefone do cliente..."
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          disabled={modoVisualizacao}
                        />
                        <Search className="w-5 h-5 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2" />
                      </div>
                      <button
                        onClick={() => setMostrarModalCliente(true)}
                        disabled={modoVisualizacao}
                        className="flex items-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Plus className="w-5 h-5" />
                        <span>Novo</span>
                      </button>
                    </div>

                    {/* Sugestões de clientes */}
                    {clientesSugeridos.length > 0 && (
                      <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                        {clientesSugeridos.map((cliente) => (
                          <button
                            key={cliente.id}
                            onClick={() => selecionarCliente(cliente)}
                            className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
                          >
                            <div className="font-medium text-gray-900">{cliente.nome}</div>
                            <div className="text-sm text-gray-500">
                              {cliente.cpf && `CPF: ${cliente.cpf}`}
                              {cliente.telefone && ` • ${cliente.telefone}`}
                            </div>
                            {cliente.pets && cliente.pets.length > 0 && (
                              <div className="text-xs text-blue-600 mt-1">
                                {cliente.pets.length} pet(s)
                              </div>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {buscarCliente.length >= 2 && clientesSugeridos.length === 0 && (
                    <div className="text-sm text-gray-500 text-center py-2">
                      Nenhum cliente encontrado
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-blue-900">{vendaAtual.cliente.nome}</div>
                        <div className="text-sm text-blue-700 mt-1">
                          {vendaAtual.cliente.cpf && `CPF: ${vendaAtual.cliente.cpf}`}
                          {vendaAtual.cliente.telefone && ` • Tel: ${vendaAtual.cliente.telefone}`}
                        </div>
                      </div>
                    </div>

                    {/* Exibir Crédito Disponível */}
                    {vendaAtual.cliente.credito > 0 && (
                      <div className="mt-3 pt-3 border-t border-blue-300">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Wallet className="w-4 h-4 text-green-600" />
                            <span className="text-sm font-medium text-gray-700">Crédito Disponível:</span>
                          </div>
                          <span className="text-lg font-bold text-green-600">
                            R$ {parseFloat(vendaAtual.cliente.credito || 0).toFixed(2).replace('.', ',')}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">
                          💡 Este crédito pode ser usado como forma de pagamento
                        </p>
                      </div>
                    )}

                    {/* Badge de Vendas em Aberto */}
                    {vendasEmAbertoInfo && vendasEmAbertoInfo.total_vendas > 0 && (
                      <div className="mt-3 pt-3 border-t border-blue-300">
                        <div className="flex items-center justify-between p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-yellow-600" />
                            <div>
                              <div className="text-sm font-medium text-yellow-900">
                                {vendasEmAbertoInfo.total_vendas} venda(s) em aberto
                              </div>
                              <div className="text-xs text-yellow-700">
                                Total: R$ {vendasEmAbertoInfo.total_em_aberto.toFixed(2)}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => setMostrarVendasEmAberto(true)}
                            className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-medium rounded transition-colors"
                          >
                            Ver Vendas
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Botões de Ação */}
                    <div className="mt-3 pt-3 border-t border-blue-300 flex gap-2">
                      <button
                        onClick={() => setMostrarHistoricoCliente(true)}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
                      >
                        <History className="w-4 h-4" />
                        Histórico
                      </button>
                      {!modoVisualizacao && (
                        <button
                          onClick={() => {
                            setVendaAtual({ ...vendaAtual, cliente: null, pet: null });
                            setVendasEmAbertoInfo(null);
                          }}
                          className="px-4 py-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
                        >
                          Trocar
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Seleção de Pet */}
                  {vendaAtual.cliente.pets && vendaAtual.cliente.pets.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Pet (opcional)
                      </label>
                      <select
                        value={vendaAtual.pet?.id || ''}
                        onChange={(e) => {
                          const pet = vendaAtual.cliente.pets.find(p => p.id === parseInt(e.target.value));
                          selecionarPet(pet || null);
                        }}
                        disabled={modoVisualizacao}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                      >
                        <option value="">Sem pet específico</option>
                        {vendaAtual.cliente.pets.map((pet) => (
                          <option key={pet.id} value={pet.id}>
                            {pet.codigo} - {pet.nome} ({pet.especie}{pet.raca && ` - ${pet.raca}`})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Card Produtos */}
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center">
                <Package className="w-5 h-5 mr-2 text-blue-600" />
                Produtos e Serviços
              </h2>

              {/* Buscar produto */}
              <div className="relative mb-4">
                <div className="flex items-center">
                  <input
                    ref={inputProdutoRef}
                    type="text"
                    value={buscarProduto}
                    onChange={(e) => setBuscarProduto(e.target.value)}
                    placeholder="Digite o nome do produto, código de barras ou serviço..."
                    disabled={modoVisualizacao}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                    autoFocus={!modoVisualizacao}
                  />
                  <Search className="w-5 h-5 text-gray-400 absolute right-3" />
                </div>

                {/* Sugestões de produtos */}
                {produtosSugeridos.length > 0 && (
                  <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {produtosSugeridos.map((produto) => (
                      <button
                        key={produto.id}
                        onClick={() => adicionarProduto(produto)}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            {/* 🔒 SPRINT 2: Exibir variações formatadas */}
                            <div className="font-medium text-gray-900">{produto.nome}</div>
                            {produto.tipo_produto === 'VARIACAO' && formatarVariacao(produto) && (
                              <div className="text-xs text-blue-600 font-medium mt-0.5">
                                🔹 {formatarVariacao(produto)}
                              </div>
                            )}
                            <div className="text-sm text-gray-500">
                              {produto.codigo && `Cód: ${produto.codigo}`}
                              {/* KIT VIRTUAL usa estoque_virtual, outros usam estoque_atual */}
                              {(produto.tipo_produto === 'KIT' && produto.tipo_kit === 'VIRTUAL'
                                ? produto.estoque_virtual !== undefined && ` • Estoque: ${produto.estoque_virtual}`
                                : produto.estoque_atual !== undefined && ` • Estoque: ${produto.estoque_atual}`
                              )}
                            </div>
                          </div>
                          <div className="text-lg font-semibold text-green-600">
                            R$ {parseFloat(produto.preco_venda).toFixed(2)}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Lista de itens */}
              {vendaAtual.itens.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Nenhum item adicionado</p>
                  <p className="text-sm mt-1">Busque e adicione produtos ou serviços</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {vendaAtual.itens.map((item, index) => {
                    const isKit = item.tipo_produto === 'KIT';
                    const isExpanded = itensKitExpandidos[index];
                    const hasComposicao = isKit && item.composicao_kit && item.composicao_kit.length > 0;
                    
                    return (
                      <div
                        key={index}
                        className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-400 space-y-3 transition-colors"
                      >
                        <div 
                          className="flex items-center justify-between cursor-pointer"
                          onClick={() => !modoVisualizacao && abrirModalDescontoItem(item)}
                        >
                          <div className="flex-1 flex items-start gap-2">
                            {/* Ícone de expansão para KIT */}
                            {hasComposicao && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleKitExpansion(index);
                                }}
                                className="mt-1 text-gray-500 hover:text-blue-600 transition-colors"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="w-5 h-5" />
                                ) : (
                                  <ChevronRight className="w-5 h-5" />
                                )}
                              </button>
                            )}
                            
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <div className="font-medium text-gray-900">{item.produto_nome}</div>
                                {/* Badge KIT */}
                                {isKit && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                                    <Layers className="w-3 h-3" />
                                    KIT
                                  </span>
                                )}
                              </div>
                              <div className="text-sm text-gray-500">
                                {item.quantidade} Unidade{item.quantidade !== 1 ? 's' : ''} x R$ {item.preco_unitario.toFixed(2)}
                                {item.desconto_valor > 0 && (
                                  <span className="text-orange-600 ml-1">
                                    com R$ {item.desconto_valor.toFixed(2)} de desconto
                                  </span>
                                )}
                              </div>
                              
                              {/* 🆕 Impostos do item (PDV-UX-01) - OCULTO: Cálculos continuam no backend para o cupom fiscal */}
                              {/* {fiscalItens[item.produto_id] && (
                                <div className="mt-2 p-2 bg-blue-50 rounded text-xs space-y-1">
                                  <div className="flex justify-between">
                                    <span className="text-gray-600">ICMS:</span>
                                    <span className="font-medium">R$ {fiscalItens[item.produto_id].icms}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-600">ICMS ST:</span>
                                    <span className="font-medium">R$ {fiscalItens[item.produto_id].icms_st}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-600">PIS:</span>
                                    <span className="font-medium">R$ {fiscalItens[item.produto_id].pis}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-600">COFINS:</span>
                                    <span className="font-medium">R$ {fiscalItens[item.produto_id].cofins}</span>
                                  </div>
                                  <div className="flex justify-between pt-1 border-t border-blue-200">
                                    <span className="text-gray-700 font-semibold">Total Impostos:</span>
                                    <span className="font-semibold text-blue-700">R$ {fiscalItens[item.produto_id].total_impostos}</span>
                                  </div>
                                </div>
                              )} */}
                            </div>
                          </div>

                          <div className="flex items-center space-x-4" onClick={(e) => e.stopPropagation()}>
                            {/* Controle de quantidade */}
                            <div className="flex items-center space-x-2 bg-white border border-gray-300 rounded-lg">
                              <button
                                onClick={() => alterarQuantidade(index, -1)}
                                disabled={modoVisualizacao}
                                className="p-2 hover:bg-gray-100 rounded-l-lg disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <Minus className="w-4 h-4" />
                              </button>
                              <input
                                type="number"
                                value={item.quantidade}
                                onChange={(e) => {
                                  const novaQuantidade = parseFloat(e.target.value) || 0;
                                  const novosItens = vendaAtual.itens.map((it, i) => {
                                    if (i === index) {
                                      const quantidadeAjustada = Math.max(0.001, novaQuantidade);
                                      const subtotalSemDesconto = quantidadeAjustada * it.preco_unitario;
                                      
                                      let novoDescontoValor = it.desconto_valor || 0;
                                      
                                      // 🆕 LÓGICA CORRIGIDA: Só recalcula se foi desconto PERCENTUAL
                                      if (it.tipo_desconto_aplicado === 'percentual' && it.desconto_percentual > 0) {
                                        // Desconto percentual: recalcular o valor baseado na nova quantidade
                                        novoDescontoValor = (subtotalSemDesconto * it.desconto_percentual) / 100;
                                      }
                                      // Se foi desconto em VALOR: mantém o desconto_valor fixo
                                      
                                      const subtotalComDesconto = subtotalSemDesconto - novoDescontoValor;
                                      
                                      return {
                                        ...it,
                                        quantidade: quantidadeAjustada,
                                        desconto_valor: novoDescontoValor,
                                        subtotal: subtotalComDesconto
                                      };
                                    }
                                    return it;
                                  });
                                  recalcularTotais(novosItens);
                                }}
                                disabled={modoVisualizacao}
                                step="0.001"
                                min="0.001"
                                className="w-20 px-2 py-1 text-center font-medium border-none focus:ring-0 disabled:bg-gray-50"
                              />
                              <button
                                onClick={() => alterarQuantidade(index, 1)}
                                disabled={modoVisualizacao}
                                className="p-2 hover:bg-gray-100 rounded-r-lg disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <Plus className="w-4 h-4" />
                              </button>
                            </div>

                            {/* Subtotal */}
                            <div className="text-lg font-semibold text-gray-900 w-24 text-right">
                              R$ {item.subtotal.toFixed(2)}
                            </div>

                            {/* Remover */}
                            <button
                              onClick={() => removerItem(index)}
                              disabled={modoVisualizacao}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                        
                        {/* Composição do KIT (expandível) */}
                        {hasComposicao && isExpanded && (
                          <div className="ml-7 mt-3 p-3 bg-white rounded-lg border border-gray-200">
                            <div className="text-xs font-semibold text-gray-600 uppercase mb-2">
                              Composição do KIT
                            </div>
                            <div className="space-y-1.5">
                              {item.composicao_kit.map((componente, compIndex) => (
                                <div 
                                  key={compIndex}
                                  className="flex items-center justify-between text-sm py-1.5 px-2 rounded hover:bg-gray-50"
                                >
                                  <div className="flex items-center gap-2">
                                    <Package className="w-4 h-4 text-gray-400" />
                                    <span className="text-gray-700">{componente.produto_nome}</span>
                                  </div>
                                  <span className="text-gray-500 font-medium">
                                    {componente.quantidade}x
                                  </span>
                                </div>
                              ))}
                            </div>
                            <div className="mt-2 text-xs text-gray-500 italic">
                              Componentes apenas informativos (não editáveis)
                            </div>
                          </div>
                        )}
                        
                        {/* Seleção de Pet por item */}
                        {vendaAtual.cliente?.pets && vendaAtual.cliente.pets.length > 0 && (
                          <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
                            <label className="text-sm font-medium text-gray-600 w-16">Pet:</label>
                            <select
                              value={item.pet_id || ''}
                              onChange={(e) => {
                                const novosItens = vendaAtual.itens.map((it, i) => {
                                  if (i === index) {
                                    return {
                                      ...it,
                                      pet_id: e.target.value ? parseInt(e.target.value) : null
                                    };
                                  }
                                  return it;
                                });
                                setVendaAtual({ ...vendaAtual, itens: novosItens });
                              }}
                              disabled={modoVisualizacao}
                              className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                            >
                              <option value="">Não especificado</option>
                              {vendaAtual.cliente.pets.map((pet) => (
                                <option key={pet.id} value={pet.id}>
                                  {pet.codigo} - {pet.nome}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Card Observações */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Observações</h2>
              <textarea
                value={vendaAtual.observacoes || ''}
                onChange={(e) =>
                  setVendaAtual({ ...vendaAtual, observacoes: e.target.value })
                }
                placeholder="Observações da venda (opcional)..."
                disabled={modoVisualizacao}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                rows={3}
              />
            </div>

            {/* Card Entrega */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Entrega</h2>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={vendaAtual.tem_entrega}
                    onChange={(e) => {
                      const temEntrega = e.target.checked;
                      const taxaEntrega = temEntrega ? (vendaAtual.entrega?.taxa_entrega_total || 0) : 0;
                      // O subtotal já tem o desconto aplicado, então só precisamos somar a taxa de entrega
                      const novoTotal = vendaAtual.subtotal + taxaEntrega;
                      setVendaAtual({ 
                        ...vendaAtual, 
                        tem_entrega: temEntrega,
                        total: novoTotal,
                        entrega: temEntrega ? vendaAtual.entrega : {
                          endereco_completo: '',
                          taxa_entrega_total: 0,
                          taxa_loja: 0,
                          taxa_entregador: 0,
                          observacoes_entrega: ''
                        }
                      });
                    }}
                    disabled={modoVisualizacao}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
                  />
                  <span className="text-sm font-medium text-gray-700">Tem entrega?</span>
                </label>
              </div>

              {vendaAtual.tem_entrega && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Endereço Completo *
                    </label>
                    
                    {/* Sugestões de endereços cadastrados */}
                    {vendaAtual.cliente && (
                      <div className="mb-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-sm font-medium text-blue-900">Endereços cadastrados:</p>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              abrirModalEnderecoPDV();
                            }}
                            disabled={modoVisualizacao}
                            className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Plus size={14} />
                            Adicionar Endereço
                          </button>
                        </div>
                        <div className="space-y-2">
                          {/* Endereço Principal do Cadastro - SEMPRE mostrar */}
                          {(vendaAtual.cliente.endereco || vendaAtual.cliente.cidade) && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const enderecoCompleto = `${vendaAtual.cliente.endereco}${vendaAtual.cliente.numero ? ', ' + vendaAtual.cliente.numero : ''}${vendaAtual.cliente.complemento ? ' - ' + vendaAtual.cliente.complemento : ''}, ${vendaAtual.cliente.bairro}, ${vendaAtual.cliente.cidade}/${vendaAtual.cliente.estado}`;
                                setVendaAtual({
                                  ...vendaAtual,
                                  entrega: { ...vendaAtual.entrega, endereco_completo: enderecoCompleto }
                                });
                              }}
                              disabled={modoVisualizacao}
                              className="w-full text-left px-3 py-2 bg-white hover:bg-blue-100 border border-blue-300 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <span className="font-medium text-blue-700">🏠 Cadastro Principal:</span>{' '}
                              <span className="text-gray-700">{vendaAtual.cliente.endereco}, {vendaAtual.cliente.numero} - {vendaAtual.cliente.bairro}</span>
                            </button>
                          )}
                          
                          {/* Endereços Adicionais */}
                          {vendaAtual.cliente.enderecos_adicionais && vendaAtual.cliente.enderecos_adicionais.map((end, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const enderecoCompleto = `${end.endereco}, ${end.numero}${end.complemento ? ' - ' + end.complemento : ''}, ${end.bairro}, ${end.cidade}/${end.estado}`;
                                setVendaAtual({
                                  ...vendaAtual,
                                  entrega: { ...vendaAtual.entrega, endereco_completo: enderecoCompleto }
                                });
                              }}
                              disabled={modoVisualizacao}
                              className="w-full text-left px-3 py-2 bg-white hover:bg-blue-100 border border-blue-300 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded mr-2 ${
                                end.tipo === 'entrega' ? 'bg-blue-100 text-blue-800' :
                                end.tipo === 'cobranca' ? 'bg-green-100 text-green-800' :
                                end.tipo === 'comercial' ? 'bg-purple-100 text-purple-800' :
                                end.tipo === 'residencial' ? 'bg-orange-100 text-orange-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {end.tipo === 'entrega' ? '📦' :
                                 end.tipo === 'cobranca' ? '💰' :
                                 end.tipo === 'comercial' ? '🏢' :
                                 end.tipo === 'residencial' ? '🏠' : '📍'}
                                {' '}{end.apelido || end.tipo}
                              </span>
                              <span className="text-gray-700">{end.endereco}, {end.numero} - {end.bairro}</span>
                            </button>
                          ))}
                          
                          {!vendaAtual.cliente.endereco && (!vendaAtual.cliente.enderecos_adicionais || vendaAtual.cliente.enderecos_adicionais.length === 0) && (
                            <p className="text-sm text-gray-600 italic">Nenhum endereço cadastrado. Clique em "+ Adicionar Endereço"</p>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <textarea
                      value={vendaAtual.entrega?.endereco_completo ?? ''}
                      onChange={(e) =>
                        setVendaAtual({
                          ...vendaAtual,
                          entrega: { ...vendaAtual.entrega, endereco_completo: e.target.value }
                        })
                      }
                      placeholder="Rua, número, complemento, bairro, cidade..."
                      disabled={modoVisualizacao}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                      rows={3}
                    />
                  </div>
                  
                  {/* 🚚 Seletor de Entregador */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Entregador
                    </label>
                    <select
                      value={entregadorSelecionado?.id || ''}
                      onChange={(e) => {
                        const entregador = entregadores.find(ent => ent.id === parseInt(e.target.value));
                        setEntregadorSelecionado(entregador);
                        setVendaAtual({
                          ...vendaAtual,
                          entregador_id: entregador?.id || null
                        });
                        if (entregador) {
                          calcularCustoOperacional(entregador);
                        }
                      }}
                      disabled={modoVisualizacao}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                    >
                      <option value="">Selecione um entregador</option>
                      {entregadores.map(entregador => (
                        <option key={entregador.id} value={entregador.id}>
                          {entregador.nome_fantasia || entregador.nome}
                          {entregador.entregador_padrao && ' (Padrão)'}
                        </option>
                      ))}
                    </select>
                    {entregadorSelecionado && (
                      <p className="text-xs text-gray-500 mt-1">
                        Modelo: {
                          entregadorSelecionado.modelo_custo_entrega === 'taxa_fixa' ? '💵 Taxa Fixa' :
                          entregadorSelecionado.modelo_custo_entrega === 'por_km' ? '🚗 Por KM' :
                          entregadorSelecionado.modelo_custo_entrega === 'rateio_rh' ? '👔 Rateio RH' :
                          '⚙️ Configuração Global'
                        }
                      </p>
                    )}
                  </div>

                  {/* Taxas de Entrega */}
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Taxa de Entrega Total
                      </label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                          onChange={(e) => {
                            const total = parseFloat(e.target.value) || 0;
                            const totalArredondado = parseFloat(total.toFixed(2));
                            const taxaLojaAtual = vendaAtual.entrega?.taxa_loja || 0;
                            const taxaEntregadorCalculada = parseFloat((total - taxaLojaAtual).toFixed(2));
                            const novaVenda = {
                              ...vendaAtual,
                              entrega: { 
                                ...vendaAtual.entrega, 
                                taxa_entrega_total: totalArredondado,
                                taxa_loja: parseFloat(taxaLojaAtual.toFixed(2)),
                                taxa_entregador: taxaEntregadorCalculada
                              }
                            };
                            const taxaEntrega = novaVenda.tem_entrega ? totalArredondado : 0;
                            // O subtotal já tem o desconto aplicado, então só precisamos somar a taxa de entrega
                            const novoTotal = parseFloat((novaVenda.subtotal + taxaEntrega).toFixed(2));
                            setVendaAtual({ ...novaVenda, total: novoTotal });
                          }}
                          disabled={modoVisualizacao}
                          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Taxa Loja
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                            value={parseFloat((vendaAtual.entrega?.taxa_loja ?? 0).toFixed(2))}
                            onChange={(e) => {
                              const taxaLoja = parseFloat(e.target.value) || 0;
                              const total = vendaAtual.entrega?.taxa_entrega_total || 0;
                              const taxaLojaArredondada = parseFloat(taxaLoja.toFixed(2));
                              const taxaEntregadorArredondada = parseFloat((total - taxaLoja).toFixed(2));
                              setVendaAtual({
                                ...vendaAtual,
                                entrega: { 
                                  ...vendaAtual.entrega, 
                                  taxa_loja: taxaLojaArredondada,
                                  taxa_entregador: taxaEntregadorArredondada
                                }
                              });
                            }}
                            disabled={modoVisualizacao}
                            className="w-full pl-12 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Taxa Entregador
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                            value={parseFloat((vendaAtual.entrega?.taxa_entregador ?? 0).toFixed(2))}
                            onChange={(e) => {
                              const taxaEntregador = parseFloat(e.target.value) || 0;
                              const total = vendaAtual.entrega?.taxa_entrega_total || 0;
                              const taxaEntregadorArredondada = parseFloat(taxaEntregador.toFixed(2));
                              const taxaLojaArredondada = parseFloat((total - taxaEntregador).toFixed(2));
                              setVendaAtual({
                                ...vendaAtual,
                                entrega: { 
                                  ...vendaAtual.entrega, 
                                  taxa_entregador: taxaEntregadorArredondada,
                                  taxa_loja: taxaLojaArredondada
                                }
                              });
                            }}
                            disabled={modoVisualizacao}
                            className="w-full pl-12 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                          />
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-gray-500 italic">
                      Preencha a taxa total e depois divida entre loja e entregador. Ao alterar uma, a outra é calculada automaticamente.
                    </p>
                    
                    {/* 💼 Indicador de Custo Operacional (dinâmico) */}
                    {entregadorSelecionado && custoOperacionalEntrega > 0 && (
                      <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-amber-600">💼</span>
                            <span className="text-sm font-medium text-amber-900">Custo Operacional</span>
                          </div>
                          <span className="text-sm font-semibold text-amber-700">
                            R$ {custoOperacionalEntrega.toFixed(2)}
                          </span>
                        </div>
                        <p className="text-xs text-amber-600 mt-1 italic">
                          {entregadorSelecionado.nome_fantasia || entregadorSelecionado.nome} - 
                          {entregadorSelecionado.modelo_custo_entrega === 'taxa_fixa' && ' Taxa Fixa'}
                          {entregadorSelecionado.modelo_custo_entrega === 'por_km' && ' Valor por KM'}
                          {entregadorSelecionado.modelo_custo_entrega === 'rateio_rh' && ' Rateio de RH'}
                          {' '}(não aparece no cupom)
                        </p>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Observações da Entrega
                    </label>
                    <textarea
                      value={vendaAtual.entrega?.observacoes_entrega ?? ''}
                      onChange={(e) =>
                        setVendaAtual({
                          ...vendaAtual,
                          entrega: { ...vendaAtual.entrega, observacoes_entrega: e.target.value }
                        })
                      }
                      placeholder="Horário preferencial, ponto de referência..."
                      disabled={modoVisualizacao}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                      rows={2}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Resumo dos Totais */}
            {vendaAtual.itens.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <div className="space-y-3">
                  <div className="flex justify-between text-gray-600">
                    <span>Total bruto:</span>
                    <span className="font-medium">R$ {(vendaAtual.subtotal + vendaAtual.desconto_valor).toFixed(2)}</span>
                  </div>
                  
                  {/* Desconto com botão de edição */}
                  {vendaAtual.desconto_valor > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-orange-600">
                        {((vendaAtual.desconto_valor / (vendaAtual.subtotal + vendaAtual.desconto_valor)) * 100).toFixed(2)}% de desconto:
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-orange-600">
                          R$ {vendaAtual.desconto_valor.toFixed(2)}
                        </span>
                        <button
                          onClick={abrirModalDescontoTotal}
                          disabled={modoVisualizacao}
                          className="p-1 text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50"
                          title="Aplicar desconto"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between text-gray-600">
                    <span>Total:</span>
                    <span className="font-medium">R$ {vendaAtual.subtotal.toFixed(2)}</span>
                  </div>
                  
                  {vendaAtual.tem_entrega && (
                    <div className="flex justify-between text-blue-600">
                      <span>Taxa de Entrega:</span>
                      <span className="font-medium">
                        + R$ {(vendaAtual.entrega?.taxa_entrega_total || 0).toFixed(2)}
                      </span>
                    </div>
                  )}

                  {/* Total da Venda */}
                  <div className="border-t pt-3">
                    <div className="flex justify-between text-lg font-bold text-gray-900">
                      <span>Total da Venda:</span>
                      <span>R$ {vendaAtual.total.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* 🆕 Total de Impostos (PDV-UX-01) */}
                  {totalImpostos > 0 && (
                    <div className="flex justify-between text-sm text-blue-600 bg-blue-50 p-2 rounded">
                      <span className="font-medium">Total de Impostos:</span>
                      <span className="font-semibold">R$ {totalImpostos}</span>
                    </div>
                  )}

                  {/* Mostrar pagamentos já realizados se houver */}
                  {vendaAtual.total_pago > 0 && (
                    <>
                      <div className="flex justify-between text-green-600 border-t pt-3">
                        <span className="font-medium">(-) Valor Pago:</span>
                        <span className="font-semibold">
                          R$ {vendaAtual.total_pago.toFixed(2)}
                        </span>
                      </div>
                      
                      {/* Saldo restante */}
                      <div className="flex justify-between text-2xl font-bold border-t-2 pt-3">
                        <span className={vendaAtual.total - vendaAtual.total_pago > 0 ? "text-orange-600" : "text-green-600"}>
                          {vendaAtual.total - vendaAtual.total_pago > 0 ? "Saldo Restante:" : "Totalmente Pago:"}
                        </span>
                        <span className={vendaAtual.total - vendaAtual.total_pago > 0 ? "text-orange-600" : "text-green-600"}>
                          R$ {Math.max(0, vendaAtual.total - vendaAtual.total_pago).toFixed(2)}
                        </span>
                      </div>
                    </>
                  )}

                  {/* Se não houver pagamentos, mostrar total normal */}
                  {!vendaAtual.total_pago && (
                    <div className="border-t pt-3">
                      <div className="flex justify-between text-2xl font-bold text-gray-900">
                        <span>Total:</span>
                        <span className="text-green-600">R$ {vendaAtual.total.toFixed(2)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Card Comissão */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Comissão</h2>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={vendaComissionada}
                    onChange={(e) => {
                      setVendaComissionada(e.target.checked);
                      if (!e.target.checked) {
                        setFuncionarioComissao(null);
                      }
                    }}
                    disabled={modoVisualizacao}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
                  />
                  <span className="text-sm font-medium text-gray-700">Venda comissionada?</span>
                </label>
              </div>

              {vendaComissionada && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Funcionário/Veterinário * <span className="text-xs text-gray-500">(apenas com comissão configurada)</span>
                  </label>
                  
                  {!funcionarioComissao ? (
                    <>
                      <input
                        type="text"
                        value={buscaFuncionario}
                        placeholder="Buscar funcionário ou veterinário..."
                        disabled={modoVisualizacao}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                        onFocus={async () => {
                          // Ao focar, mostrar todos os funcionários com comissão
                          if (!modoVisualizacao) {
                            try {
                              const response = await api.get('/comissoes/configuracoes/funcionarios');
                              setFuncionariosSugeridos(response.data.data || []);
                            } catch (error) {
                              console.error('Erro ao buscar funcionários:', error);
                            }
                          }
                        }}
                        onChange={async (e) => {
                          const busca = e.target.value;
                          setBuscaFuncionario(busca);
                          
                          try {
                            // Buscar apenas funcionários/veterinários com comissão configurada
                            const response = await api.get('/comissoes/configuracoes/funcionarios');
                            const funcionarios = response.data.data || [];
                            
                            // Filtrar por nome se houver busca
                            const filtrados = busca 
                              ? funcionarios.filter(f => 
                                  f.nome.toLowerCase().includes(busca.toLowerCase())
                                )
                              : funcionarios;
                            
                            setFuncionariosSugeridos(filtrados);
                          } catch (error) {
                            console.error('Erro ao buscar funcionários:', error);
                          }
                        }}
                      />
                      
                      {funcionariosSugeridos.length > 0 && (
                        <div className="mt-2 border border-gray-200 rounded-lg max-h-48 overflow-y-auto">
                          {funcionariosSugeridos.map(func => (
                            <button
                              key={func.id}
                              onClick={() => {
                                setFuncionarioComissao(func);
                                setFuncionariosSugeridos([]);
                                setBuscaFuncionario('');  // Limpar busca
                              }}
                              className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b last:border-b-0"
                            >
                              <div className="font-medium">{func.nome}</div>
                              <div className="text-xs text-gray-500 capitalize">{func.cargo}</div>
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="p-4 bg-green-50 border-2 border-green-300 rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex-shrink-0 w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-bold">
                          {funcionarioComissao.nome.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-semibold text-green-900">{funcionarioComissao.nome}</div>
                          <div className="text-sm text-green-700 capitalize">{funcionarioComissao.cargo}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setFuncionarioComissao(null);
                          setBuscaFuncionario('');
                        }}
                        disabled={modoVisualizacao}
                        className="p-2 text-green-600 hover:bg-green-100 rounded-lg transition-colors disabled:cursor-not-allowed"
                        title="Remover seleção"
                      >
                        <X size={20} />
                      </button>
                    </div>
                  )}
                  
                  <p className="text-xs text-gray-500 mt-2">
                    ℹ️ A comissão será calculada automaticamente conforme configurado no módulo de comissões
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Botões de Ação - Duplicados no final para facilitar acesso */}
          {vendaAtual.itens.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              {!temCaixaAberto && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-center">
                  <div className="flex items-center space-x-2 text-red-700">
                    <AlertCircle className="w-5 h-5" />
                    <span className="text-sm font-medium">
                      🔒 Caixa fechado - Use o botão "Abrir Caixa" no topo da página para continuar
                    </span>
                  </div>
                </div>
              )}
              <div className="flex items-center justify-end gap-3">
                {/* Botão Nova Venda - Limpar sem salvar */}
                {vendaAtual.itens.length > 0 && !vendaAtual.id && (
                  <button
                    onClick={() => {
                      if (window.confirm('Descartar venda atual sem salvar?')) {
                        limparVenda();
                      }
                    }}
                    disabled={loading || modoVisualizacao}
                    className="flex items-center space-x-2 px-4 py-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-red-200"
                    title="Descartar venda atual e começar uma nova"
                  >
                    <X className="w-5 h-5" />
                    <span className="font-medium">Nova Venda</span>
                  </button>
                )}
                
                <button
                  onClick={salvarVenda}
                  disabled={loading || modoVisualizacao || !temCaixaAberto}
                  className="flex items-center space-x-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title={!temCaixaAberto ? '🔒 Caixa fechado - Abra o caixa para salvar vendas' : 'Salvar venda atual'}
                >
                  <Save className="w-5 h-5" />
                  <span className="font-medium">Salvar Venda</span>
                  {!temCaixaAberto && <span className="text-xs">🔒</span>}
                </button>
                <button
                  onClick={abrirModalPagamento}
                  disabled={loading || vendaAtual.status === 'finalizada' || vendaAtual.status === 'pago_nf' || !temCaixaAberto}
                  className="flex items-center space-x-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                  title={!temCaixaAberto ? '🔒 Caixa fechado - Abra o caixa para registrar recebimentos' : 'Registrar pagamento da venda'}
                >
                  <CreditCard className="w-5 h-5" />
                  <span>Registrar Recebimento</span>
                  {!temCaixaAberto && <span className="text-xs">🔒</span>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Widget de Informações do Cliente */}
      {vendaAtual.cliente && painelClienteAberto && (
        <div className="w-80 bg-gray-50 border-l flex flex-col overflow-hidden">
          <ClienteInfoWidget clienteId={vendaAtual.cliente.id} />
        </div>
      )}
      
      {/* Botão para expandir/recolher painel do cliente */}
      {vendaAtual.cliente && (
        <button
          onClick={() => setPainelClienteAberto(!painelClienteAberto)}
          className="fixed right-0 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-l-lg shadow-lg transition-all z-10"
          style={{ right: painelClienteAberto ? '320px' : '0' }}
          title={painelClienteAberto ? 'Recolher informações do cliente' : 'Expandir informações do cliente'}
        >
          {painelClienteAberto ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <User className="w-5 h-5" />
          )}
        </button>
      )
      }

      {/* Barra Lateral - Vendas Recentes */}
      {painelVendasAberto && (
        <div className="w-52 bg-white border-l flex flex-col">
          <div className="p-3 border-b">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-900 flex items-center">
                <Clock className="w-4 h-4 mr-2 text-blue-600" />
                Vendas Recentes
              </h2>
              <button
                onClick={() => setPainelVendasAberto(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="Fechar painel"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

          {/* Filtro de período */}
          <div className="flex space-x-1 mb-3">
            {['24h', '7d', '30d'].map((periodo) => (
              <button
                key={periodo}
                onClick={() => setFiltroVendas(periodo)}
                className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  filtroVendas === periodo
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {periodo === '24h' && 'Últimas 24h'}
                {periodo === '7d' && '7 dias'}
                {periodo === '30d' && '30 dias'}
              </button>
            ))}
          </div>

          {/* Filtro de status */}
          <div className="flex space-x-1 mb-2">
            {[
              { id: 'todas', label: 'Todas' },
              { id: 'pago', label: 'Pago' },
              { id: 'aberta', label: 'Aberta' }
            ].map((status) => (
              <button
                key={status.id}
                onClick={() => setFiltroStatus(status.id)}
                className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  filtroStatus === status.id
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {status.label}
              </button>
            ))}
          </div>
          
          {/* Filtro Tem Entrega */}
          <label className="flex items-center gap-2 cursor-pointer p-2 hover:bg-gray-50 rounded-lg">
            <input
              type="checkbox"
              checked={filtroTemEntrega}
              onChange={(e) => setFiltroTemEntrega(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-700">Apenas com entrega</span>
          </label>
        </div>

        {/* Lista de vendas */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {vendasRecentes.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs">Nenhuma venda encontrada</p>
            </div>
          ) : (
            vendasRecentes.map((venda) => (
              <div
                key={venda.id}
                onClick={() => reabrirVenda(venda)}
                className="bg-gray-50 rounded-lg p-2.5 border border-gray-200 hover:border-blue-300 cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between mb-1.5">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      {venda.cliente_nome || 'Cliente não informado'}
                    </div>
                    <div className="text-xs text-gray-500">#{venda.numero_venda}</div>
                  </div>
                  <div className="text-right ml-2 flex-shrink-0">
                    {venda.status === 'baixa_parcial' ? (
                      <>
                        <div className="text-[10px] text-gray-500">Pago</div>
                        <div className="text-xs font-semibold text-green-600">
                          R$ {(venda.valor_pago || 0).toFixed(2)}
                        </div>
                        <div className="text-[10px] text-gray-500 mt-0.5">
                          de R$ {(venda.total || 0).toFixed(2)}
                        </div>
                      </>
                    ) : (
                      <div className="text-sm font-semibold text-green-600">
                        R$ {(venda.total || 0).toFixed(2)}
                      </div>
                    )}
                    <div
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full mt-1 inline-block ${
                        venda.status === 'pago_nf'
                          ? 'bg-emerald-100 text-emerald-700'
                          : venda.status === 'finalizada'
                          ? 'bg-green-100 text-green-700'
                          : venda.status === 'baixa_parcial'
                          ? 'bg-blue-100 text-blue-700'
                          : venda.status === 'aberta'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {venda.status === 'pago_nf' && 'Pago NF'}
                      {venda.status === 'finalizada' && 'Pago'}
                      {venda.status === 'baixa_parcial' && 'Parcial'}
                      {venda.status === 'aberta' && 'Aberta'}
                      {venda.status === 'cancelada' && 'Cancelada'}
                    </div>
                  </div>
                </div>
                <div className="text-[10px] text-gray-500">
                  {new Date(venda.data_venda).toLocaleString('pt-BR', { 
                    day: '2-digit', 
                    month: '2-digit', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      )}
      
      {/* Painel de Oportunidades Inteligentes - D4 Backend Integration */}
      {/* ✅ RULE: Painel só aparece se cliente selecionado */}
      {painelOportunidadesAberto && vendaAtual.cliente && (
        <div className="fixed inset-0 z-40">
          {/* Sidebar direita - sem overlay */}
          <div className="absolute top-0 right-0 w-80 h-full bg-gray-50 border-l border-gray-300 shadow-lg flex flex-col animate-in slide-in-from-right duration-200">
            {/* Header - discreto */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-300 bg-white">
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-gray-600" />
                <h2 className="text-sm font-medium text-gray-700">Oportunidades</h2>
              </div>
              <button
                onClick={() => setPainelOportunidadesAberto(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {/* Conteúdo - estilo lista discreta */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {opportunities.slice(0, 5).map((opp) => (
                <div
                  key={opp.id}
                  className="p-3 bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                >
                  <h3 className="text-xs font-medium text-gray-900 mb-1">{opp.titulo}</h3>
                  <p className="text-xs text-gray-700 mb-2 leading-relaxed">{opp.descricao_curta}</p>
                  
                  {/* Ações discretas - 3 colunas - D5: Event Tracking */}
                  <div className="flex items-center justify-between gap-2 text-xs mt-2">
                    <button
                      onClick={() => {
                        // D5: Registrar evento CONVERTIDA (fire-and-forget)
                        registrarEventoOportunidade('oportunidade_convertida', opp);
                        // TODO: Adicionar produto ao carrinho
                        console.log('Adicionar ao carrinho:', opp.id);
                      }}
                      className="flex items-center gap-1 text-green-500 hover:text-green-600 transition-colors whitespace-nowrap font-medium"
                      title="Adicionar ao carrinho"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Adicionar</span>
                    </button>
                    <button
                      onClick={() => {
                        // D5: Registrar evento REFINADA (fire-and-forget)
                        registrarEventoOportunidade('oportunidade_refinada', opp);
                        // TODO: Mostrar alternativas
                        console.log('Buscar alternativa:', opp.id);
                      }}
                      className="text-orange-600 hover:text-orange-700 transition-colors whitespace-nowrap flex-1 text-center font-medium"
                      title="Ver alternativa"
                    >
                      Alternativa
                    </button>
                    <button
                      onClick={() => {
                        // D5: Registrar evento REJEITADA (fire-and-forget)
                        registrarEventoOportunidade('oportunidade_rejeitada', opp);
                        // Remover da lista local
                        setOpportunities(prev => prev.filter(o => o.id !== opp.id));
                      }}
                      className="flex items-center gap-1 text-red-500 hover:text-red-600 transition-colors whitespace-nowrap font-medium"
                      title="Ignorar sugestão"
                    >
                      <span>Ignorar</span>
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}

              {opportunities.length === 0 && (
                <div className="flex items-center justify-center py-8 text-gray-400">
                  <p className="text-xs">Nenhuma oportunidade disponível</p>
                </div>
              )}
            </div>

            {/* Footer - Info discreto */}
            <div className="px-4 py-2 border-t border-gray-200 bg-white">
              <p className="text-[10px] text-gray-400 text-center">
                {opportunities.length > 0 ? `${Math.min(opportunities.length, 6)} oportunidades` : ''}
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Botão para expandir/recolher painel de vendas */}
      <button
        onClick={() => setPainelVendasAberto(!painelVendasAberto)}
        className="fixed right-0 bottom-20 bg-blue-600 hover:bg-blue-700 text-white rounded-l-lg shadow-lg transition-all z-10 flex items-center gap-1"
        style={{ 
          right: painelVendasAberto ? '208px' : '0',
          padding: painelVendasAberto ? '6px' : '6px 8px'
        }}
        title={painelVendasAberto ? 'Recolher vendas recentes' : 'Expandir vendas recentes'}
      >
        {painelVendasAberto ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <>
            <ChevronLeft className="w-4 h-4" />
            <span className="text-[10px] font-medium whitespace-nowrap">Vendas</span>
          </>
        )}
      </button>

      {/* Modal de Pagamento */}
      {mostrarModalPagamento && (
        <ModalPagamento
          venda={vendaAtual}
          onClose={() => setMostrarModalPagamento(false)}
          onAnalisarVenda={podeVerMargem ? analisarVendaComFormasPagamento : null}
          onConfirmar={async () => {
            setMostrarModalPagamento(false);
            
            // Se está em modo visualização, recarregar a venda ao invés de limpar
            if (modoVisualizacao && vendaAtual.id) {
              try {
                // Recarregar venda atualizada do servidor
                const response = await api.get(`/vendas/${vendaAtual.id}`);
                const vendaAtualizada = response.data;
                
                // Buscar pagamentos atualizados
                let pagamentosVenda = [];
                let totalPago = 0;
                try {
                  const responsePagamentos = await api.get(`/vendas/${vendaAtual.id}/pagamentos`);
                  pagamentosVenda = responsePagamentos.data.pagamentos || [];
                  totalPago = responsePagamentos.data.total_pago || 0;
                } catch (error) {
                  console.error('Erro ao buscar pagamentos:', error);
                }
                
                setVendaAtual({
                  ...vendaAtualizada,
                  pagamentos: pagamentosVenda,
                  total_pago: totalPago
                });
                
                console.log('✅ Venda recarregada:', vendaAtualizada);
              } catch (error) {
                console.error('Erro ao recarregar venda:', error);
              }
            } else {
              // Venda nova, limpar normalmente
              limparVenda();
            }
            
            carregarVendasRecentes();
            // Forçar recarga do MenuCaixa para atualizar saldo
            setCaixaKey(prev => prev + 1);
          }}
          onVendaAtualizada={async () => {
            // Recarregar venda após exclusão de pagamentos
            if (vendaAtual.id) {
              const vendaAtualizada = await buscarVenda(vendaAtual.id);
              
              // Buscar pagamentos atualizados
              let pagamentosVenda = [];
              let totalPago = 0;
              try {
                const responsePagamentos = await api.get(`/vendas/${vendaAtual.id}/pagamentos`);
                pagamentosVenda = responsePagamentos.data.pagamentos || [];
                totalPago = responsePagamentos.data.total_pago || 0;
              } catch (error) {
                console.error('Erro ao buscar pagamentos:', error);
              }
              
              setVendaAtual({
                ...vendaAtualizada,
                pagamentos: pagamentosVenda,
                total_pago: totalPago
              });
              setModoVisualizacao(vendaAtualizada.status === 'finalizada' || vendaAtualizada.status === 'baixa_parcial');
              carregarVendasRecentes(); // Atualizar lista de vendas também
            }
          }}
        />
      )}

      {/* Modal de Abrir Caixa */}
      {mostrarModalAbrirCaixa && (
        <ModalAbrirCaixa
          onClose={() => setMostrarModalAbrirCaixa(false)}
          onSucesso={() => {
            setMostrarModalAbrirCaixa(false);
            // Forçar recarga do MenuCaixa
            setCaixaKey(prev => prev + 1);
            // Atualizar estado de caixa aberto
            setTemCaixaAberto(true);
          }}
        />
      )}

      {/* 🆕 Modal da Calculadora de Ração no PDV */}
      {mostrarCalculadoraRacao && (
        <ModalCalculadoraRacaoPDV
          isOpen={mostrarCalculadoraRacao}
          itensCarrinho={vendaAtual.itens}
          racaoIdFechada={racaoIdFechada}
          onClose={() => {
            // Marcar última ração como fechada para não reabre automático
            const racoes = vendaAtual.itens.filter(item => {
              const nomeCategoria = (item.categoria_nome || '').toLowerCase();
              return nomeCategoria.includes('ração') || nomeCategoria.includes('racao');
            });
            if (racoes.length > 0) {
              setRacaoIdFechada(racoes[racoes.length - 1].produto_id);
            }
            setMostrarCalculadoraRacao(false);
          }}
        />
      )}

      {/* Modal de Pendências de Estoque */}
      {mostrarPendenciasEstoque && vendaAtual.cliente && (
        <ModalPendenciasEstoque
          isOpen={mostrarPendenciasEstoque}
          onClose={() => setMostrarPendenciasEstoque(false)}
          clienteId={vendaAtual.cliente.id}
          onPendenciaAdicionada={() => carregarPendencias()}
        />
      )}

      {/* Modal de Cadastro Rápido de Cliente */}
      {mostrarModalCliente && (
        <ModalCadastroCliente
          onClose={() => setMostrarModalCliente(false)}
          onClienteCriado={(cliente) => {
            selecionarCliente(cliente);
            setMostrarModalCliente(false);
          }}
        />
      )}

      {/* Modal de Endereço Adicional */}
      {mostrarModalEndereco && enderecoAtual && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            {/* Header do Modal */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
              <h3 className="text-xl font-bold text-gray-900">
                Adicionar Novo Endereço ao Cliente
              </h3>
              <button
                onClick={fecharModalEndereco}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            {/* Conteúdo do Modal */}
            <div className="p-6 space-y-4">
              {/* Tipo e Apelido */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Endereço *
                  </label>
                  <select
                    value={enderecoAtual.tipo}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, tipo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  >
                    <option value="entrega">📦 Entrega</option>
                    <option value="cobranca">💰 Cobrança</option>
                    <option value="comercial">🏢 Comercial</option>
                    <option value="residencial">🏠 Residencial</option>
                    <option value="trabalho">📍 Trabalho</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Apelido (opcional)
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.apelido}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, apelido: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Ex: Casa da mãe, Escritório, Loja"
                  />
                </div>
              </div>

              {/* CEP */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CEP *
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={enderecoAtual.cep}
                      onChange={(e) => {
                        const value = e.target.value.replace(/\D/g, '');
                        const formatted = value.length > 5 ? `${value.slice(0, 5)}-${value.slice(5, 8)}` : value;
                        setEnderecoAtual({...enderecoAtual, cep: formatted});
                      }}
                      onBlur={(e) => buscarCepModal(e.target.value)}
                      maxLength="9"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="00000-000"
                    />
                    {loadingCep && (
                      <div className="absolute right-2 top-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Endereço e Número */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Endereço *
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.endereco}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, endereco: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Rua, Avenida, etc."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.numero}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, numero: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="123"
                  />
                </div>
              </div>

              {/* Complemento e Bairro */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Complemento
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.complemento}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, complemento: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Apto, Bloco, Sala..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bairro
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.bairro}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, bairro: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Centro, Jardim..."
                  />
                </div>
              </div>

              {/* Cidade e Estado */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cidade *
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.cidade}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, cidade: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="São Paulo"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estado
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.estado}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, estado: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    maxLength="2"
                    placeholder="SP"
                  />
                </div>
              </div>

              <p className="text-xs text-gray-500">* Campos obrigatórios</p>
            </div>

            {/* Footer do Modal */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={fecharModalEndereco}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={salvarEnderecoNoCliente}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Salvar Endereço
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Desconto Individual no Item */}
      {mostrarModalDescontoItem && itemEditando && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-900">
                Alterar item da venda
              </h3>
              <button
                onClick={() => setMostrarModalDescontoItem(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-semibold text-gray-900">{itemEditando.produto_nome}</h4>
                <p className="text-sm text-gray-600">Código: {itemEditando.produto_codigo}</p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Preço <span className="text-red-600">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-2.5 text-gray-500">R$</span>
                    <input
                      type="number"
                      step="0.01"
                      value={itemEditando.preco}
                      onChange={(e) => setItemEditando({...itemEditando, preco: parseFloat(e.target.value) || 0})}
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quantidade
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    value={itemEditando.quantidade}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Subtotal
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-2.5 text-gray-500">R$</span>
                    <input
                      type="text"
                      value={(itemEditando.preco * itemEditando.quantidade).toFixed(2)}
                      readOnly
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tipo de desconto
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setItemEditando({...itemEditando, tipoDesconto: 'valor', descontoPercentual: 0})}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                      itemEditando.tipoDesconto === 'valor'
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                    }`}
                  >
                    R$
                  </button>
                  <button
                    onClick={() => setItemEditando({...itemEditando, tipoDesconto: 'percentual', descontoValor: 0})}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                      itemEditando.tipoDesconto === 'percentual'
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                    }`}
                  >
                    %
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Valor do desconto
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-gray-500">
                    {itemEditando.tipoDesconto === 'valor' ? 'R$' : '%'}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={itemEditando.tipoDesconto === 'valor' ? itemEditando.descontoValor : itemEditando.descontoPercentual}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      if (itemEditando.tipoDesconto === 'valor') {
                        setItemEditando({...itemEditando, descontoValor: val});
                      } else {
                        setItemEditando({...itemEditando, descontoPercentual: val});
                      }
                    }}
                    className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-700">Total bruto</span>
                  <span className="font-medium">R$ {(itemEditando.preco * itemEditando.quantidade).toFixed(2)}</span>
                </div>
                {(itemEditando.descontoValor > 0 || itemEditando.descontoPercentual > 0) && (
                  <>
                    <div className="flex justify-between text-sm text-red-600 mt-1">
                      <span>Desconto</span>
                      <span className="font-medium">
                        - R$ {itemEditando.tipoDesconto === 'valor' 
                          ? itemEditando.descontoValor.toFixed(2)
                          : ((itemEditando.preco * itemEditando.quantidade * itemEditando.descontoPercentual) / 100).toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm text-orange-600 mt-1">
                      <span>
                        {itemEditando.tipoDesconto === 'percentual' && `${itemEditando.descontoPercentual.toFixed(2)}% de desconto`}
                        {itemEditando.tipoDesconto === 'valor' && `${((itemEditando.descontoValor / (itemEditando.preco * itemEditando.quantidade)) * 100).toFixed(2)}% de desconto`}
                      </span>
                    </div>
                  </>
                )}
                <div className="flex justify-between font-bold text-lg mt-2 pt-2 border-t border-blue-200">
                  <span>Total líquido</span>
                  <span className="text-green-600">
                    R$ {(
                      itemEditando.preco * itemEditando.quantidade - 
                      (itemEditando.tipoDesconto === 'valor' 
                        ? itemEditando.descontoValor
                        : (itemEditando.preco * itemEditando.quantidade * itemEditando.descontoPercentual) / 100)
                    ).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-between gap-3">
              <button
                onClick={() => setMostrarModalDescontoItem(false)}
                className="flex-1 px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Fechar
              </button>
              <button
                onClick={() => {
                  const novosItens = vendaAtual.itens.map(it => {
                    if (it.produto_id === itemEditando.produto_id) {
                      removerItem(vendaAtual.itens.indexOf(it));
                    }
                    return it;
                  }).filter(Boolean);
                  setMostrarModalDescontoItem(false);
                }}
                className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Remover
              </button>
              <button
                onClick={salvarDescontoItem}
                className="flex-1 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Desconto Total */}
      {mostrarModalDescontoTotal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-900">
                💰 Aplicar desconto
              </h3>
              <button
                onClick={() => setMostrarModalDescontoTotal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Total bruto</div>
                <div className="text-2xl font-bold text-gray-900">
                  R$ {vendaAtual.subtotal.toFixed(2)}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tipo de desconto
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTipoDescontoTotal('valor')}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                      tipoDescontoTotal === 'valor'
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                    }`}
                  >
                    R$
                  </button>
                  <button
                    onClick={() => setTipoDescontoTotal('percentual')}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-colors ${
                      tipoDescontoTotal === 'percentual'
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                    }`}
                  >
                    %
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Valor
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-3 text-gray-500">
                    {tipoDescontoTotal === 'valor' ? 'R$' : '%'}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    value={valorDescontoTotal}
                    onChange={(e) => setValorDescontoTotal(parseFloat(e.target.value) || 0)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">Desconto</span>
                  <span className="text-red-600 font-medium">
                    - R$ {tipoDescontoTotal === 'valor' 
                      ? valorDescontoTotal.toFixed(2)
                      : (vendaAtual.subtotal * valorDescontoTotal / 100).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-baseline border-t border-blue-200 pt-2 mt-2">
                  <span className="text-sm text-gray-700">Total líquido</span>
                  <span className="text-2xl font-bold text-green-600">
                    R$ {(tipoDescontoTotal === 'valor' 
                      ? vendaAtual.subtotal - valorDescontoTotal
                      : vendaAtual.subtotal - (vendaAtual.subtotal * valorDescontoTotal / 100)
                    ).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => setMostrarModalDescontoTotal(false)}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Fechar
              </button>
              <button
                onClick={() => aplicarDescontoTotal(tipoDescontoTotal, valorDescontoTotal)}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Aplicar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Vendas em Aberto */}
      {mostrarVendasEmAberto && vendaAtual.cliente && (
        <VendasEmAberto
          clienteId={vendaAtual.cliente.id}
          clienteNome={vendaAtual.cliente.nome}
          onClose={() => setMostrarVendasEmAberto(false)}
          onSucesso={() => {
            // Recarregar info de vendas em aberto
            api.get(`/clientes/${vendaAtual.cliente.id}/vendas-em-aberto`)
              .then(response => {
                if (response.data.resumo.total_vendas > 0) {
                  setVendasEmAbertoInfo(response.data.resumo);
                } else {
                  setVendasEmAbertoInfo(null);
                }
              })
              .catch(() => setVendasEmAbertoInfo(null));
          }}
        />
      )}

      {/* Modal de Histórico do Cliente */}
      {mostrarHistoricoCliente && vendaAtual.cliente && (
        <HistoricoCliente
          clienteId={vendaAtual.cliente.id}
          clienteNome={vendaAtual.cliente.nome}
          onClose={() => setMostrarHistoricoCliente(false)}
        />
      )}

      {/* Drawer de Análise de Venda - APENAS PARA ADMIN */}
      {podeVerMargem && (
        <AnaliseVendaDrawer
          mostrar={mostrarAnaliseVenda}
          onFechar={() => setMostrarAnaliseVenda(false)}
          dados={dadosAnalise}
          carregando={carregandoAnalise}
        />
      )}
    </div>
    </>
  );
}

// Modal simples de cadastro de cliente
function ModalCadastroCliente({ onClose, onClienteCriado }) {
  const [formData, setFormData] = useState({
    nome: '',
    telefone: '',
    cpf: '',
    email: ''
  });
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.nome || !formData.telefone) {
      setErro('Nome e telefone são obrigatórios');
      return;
    }

    setLoading(true);
    setErro('');

    try {
      const response = await fetch('/clientes/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          ...formData,
          tipo_cadastro: 'cliente',
          tipo_pessoa: 'PF'
        })
      });

      if (!response.ok) throw new Error('Erro ao criar cliente');

      const cliente = await response.json();
      onClienteCriado(cliente);
    } catch (error) {
      console.error('Erro:', error);
      setErro('Erro ao cadastrar cliente');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold text-gray-900">Cadastro Rápido</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {erro && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {erro}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome * 
            </label>
            <input
              type="text"
              value={formData.nome}
              onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Telefone *
            </label>
            <input
              type="tel"
              value={formData.telefone}
              onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
              placeholder="(00) 00000-0000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              CPF
            </label>
            <input
              type="text"
              value={formData.cpf}
              onChange={(e) => setFormData({ ...formData, cpf: e.target.value })}
              placeholder="000.000.000-00"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              E-mail
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="cliente@email.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Cadastrando...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  <span>Cadastrar</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

