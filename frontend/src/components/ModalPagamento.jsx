import { useCallback, useState, useEffect, useRef } from 'react';
import {
  X,
  CreditCard,
  Wallet,
  CheckCircle,
  AlertCircle,
  BarChart2,
} from 'lucide-react';

import { finalizarVenda, criarVenda, atualizarVenda } from '../api/vendas';
import { verificarEstoqueNegativo } from '../api/alertasEstoque';
import StatusMargemIndicador from './StatusMargemIndicador';
import api from '../api';
import CurrencyInput from './CurrencyInput';
import ModalAdicionarCredito from './ModalAdicionarCredito';
import ModalPerguntaNFe from './ModalPerguntaNFe';
import ModalPagamentoResumoLateral from './ModalPagamentoResumoLateral';
import PaymentMethodIcon from './PaymentMethodIcon';
import useRevealFloatingPanel from '../hooks/useRevealFloatingPanel';
import { formatMoneyBRL } from '../utils/formatters';
import {
  emitirNotaFiscalAssistida,
  extrairMensagemNFe,
} from '../utils/nfeFiscalAssistida';
import { montarPayloadVenda } from '../utils/pdvVendaPayload';
import { useModulos } from '../contexts/ModulosContext';
import {
  BANDEIRAS_CARTAO,
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularCustoTotalItensVenda,
  calcularResumoRecebimento,
  descreverCupomMargem,
  devePerguntarNotaFiscal,
  ehFormaPagamentoPix,
  avaliarEstadoJustificativaMargem,
  extrairCorIndicadorMargem,
  montarFormasPagamentoAnalise,
  montarCupomParaFinalizar,
  montarItensParaVerificarEstoqueNegativo,
  montarMensagemEstoqueNegativo,
  montarObservacoesComJustificativaMargem,
  montarFallbackSimulacaoParcelamento,
  montarPagamentoAVista,
  montarPagamentoRecebido,
  montarPagamentoSimuladoParcelamento,
  montarPagamentosMargem,
  montarPayloadAnaliseMargem,
  montarVendaParaPersistirComCupom,
  normalizarResultadoSimulacaoParcelamento,
  obterCorParcelamentoAtual,
  obterCorVisualParcelamento,
  obterEstiloVisualParcelamento,
  resolverFaixasParcelamentoDaForma,
  validarPagamentoParaAdicionar,
} from './modalPagamentoUtils';

export default function ModalPagamento({
  venda,
  cupomAplicado,
  onClose,
  onConfirmar,
  onVendaAtualizada,
  onAnalisarVenda,
}) {
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo('campanhas');
  const [pagamentos, setPagamentos] = useState([]);
  const [pagamentosExistentes, setPagamentosExistentes] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [operadoras, setOperadoras] = useState([]); // 🆕 Operadoras de cartão
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null); // 🆕 Operadora selecionada
  const [formaPagamentoSelecionada, setFormaPagamentoSelecionada] = useState(null);
  const [bandeira, setBandeira] = useState('');
  const [nsuCartao, setNsuCartao] = useState(''); // NSU para conciliação bancária
  const [numeroParcelas, setNumeroParcelas] = useState(1);
  const [valorRecebido, setValorRecebido] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingPagamentos, setLoadingPagamentos] = useState(false);
  const [erro, setErro] = useState('');
  const [totalPagoExistente, setTotalPagoExistente] = useState(0);
  const [mostrarPerguntaNFe, setMostrarPerguntaNFe] = useState(false);
  const [vendaFinalizadaId, setVendaFinalizadaId] = useState(null);
  
  // 🆕 Estados para status de margem operacional
  const [statusMargem, setStatusMargem] = useState(null);
  const [loadingStatusMargem, setLoadingStatusMargem] = useState(false);

  // 💡 Sugestão PIX — desconto que pode ser oferecido ao cliente se pagar no PIX
  const [sugestaoPix, setSugestaoPix] = useState(null);
  
  // 🆕 Estados para justificativa inline (ÚNICO campo)
  const [justificativaTexto, setJustificativaTexto] = useState('');
  const [erroJustificativa, setErroJustificativa] = useState('');
  
  // 🆕 PASSO 2️⃣ - Estados para simulação de parcelamentos
  const [simulacoesParcelamento, setSimulacoesParcelamento] = useState({});
  const [loadingSimulacao, setLoadingSimulacao] = useState(false);
  const [faixasParcelamento, setFaixasParcelamento] = useState(null);
  
  // 🆕 Estados para excedente (troco vs crédito) em métodos não-dinheiro
  const [opcaoExcedente, setOpcaoExcedente] = useState(null); // 'troco' | 'credito'
  const [mostrarModalCreditoExcedente, setMostrarModalCreditoExcedente] = useState(false);
  const [valorExcedente, setValorExcedente] = useState(0);

  // 💰 Cashback de campanhas
  const [saldoCashback, setSaldoCashback] = useState(0);
  const [campanhasCompra, setCampanhasCompra] = useState([]);
  const [rankCliente, setRankCliente] = useState('bronze');
  const [loadingBeneficiosCampanha, setLoadingBeneficiosCampanha] = useState(false);

  const modalPagamentoContentRef = useRef(null);

  // Ref para o container das opções de parcelamento
  const opcoesParcelamentoRef = useRef(null);
  const statusMargemRef = useRef(null);
  const justificativaRef = useRef(null);
  const justificativaTextareaRef = useRef(null);

  // Carregar formas de pagamento do backend
  useEffect(() => {
    const carregarFormas = async () => {
      try {
        const response = await api.get(`/financeiro/formas-pagamento`);
        setFormasPagamento(response.data);
      } catch (error) {
        console.error('Erro ao carregar formas:', error);
      }
    };
    carregarFormas();
  }, []);

  // 💰 Carregar saldo de cashback do cliente
  useEffect(() => {
    if (!moduloCampanhasAtivo) {
      setSaldoCashback(0);
      return;
    }
    if (!venda.cliente?.id) return;
    const clienteId = venda.cliente.id;
    api.get(`/campanhas/clientes/${clienteId}/saldo`)
      .then(res => setSaldoCashback(parseFloat(res.data.saldo_cashback || 0)))
      .catch(() => {}); // campanhas são opcionais
  }, [moduloCampanhasAtivo, venda.cliente?.id]);

  useEffect(() => {
    if (!moduloCampanhasAtivo || !venda.cliente?.id) {
      setCampanhasCompra([]);
      setRankCliente('bronze');
      setLoadingBeneficiosCampanha(false);
      return;
    }

    const carregarBeneficiosCampanha = async () => {
      try {
        setLoadingBeneficiosCampanha(true);
        const [campanhasResp, saldoResp] = await Promise.allSettled([
          api.get('/campanhas'),
          api.get(`/campanhas/clientes/${venda.cliente.id}/saldo`),
        ]);

        const campanhasAtivas = campanhasResp.status === 'fulfilled'
          ? (campanhasResp.value.data || []).filter((campanha) => campanha.status === 'active')
          : [];

        const rankAtual = saldoResp.status === 'fulfilled'
          ? String(saldoResp.value?.data?.rank_level || 'bronze').toLowerCase()
          : 'bronze';

        setCampanhasCompra(campanhasAtivas);
        setRankCliente(rankAtual);
      } catch (error) {
        console.error('Erro ao carregar prévia de benefícios no pagamento:', error);
      } finally {
        setLoadingBeneficiosCampanha(false);
      }
    };

    carregarBeneficiosCampanha();
  }, [moduloCampanhasAtivo, venda.cliente?.id]);

  // 🆕 Carregar operadoras de cartão
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const response = await api.get('/operadoras-cartao?apenas_ativas=true');
        setOperadoras(response.data);
        
        // Pré-selecionar operadora padrão
        const padrao = response.data.find(op => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error('Erro ao carregar operadoras:', error);
      }
    };
    carregarOperadoras();
  }, []);

  // Buscar pagamentos existentes da venda
  useEffect(() => {
    const buscarPagamentos = async () => {
      if (!venda.id) return; // Se venda não foi criada ainda, não há pagamentos

      setLoadingPagamentos(true);
      try {
        const response = await api.get(`/vendas/${venda.id}/pagamentos`);
        setPagamentosExistentes(response.data.pagamentos || []);
        setTotalPagoExistente(response.data.total_pago || 0);
      } catch (error) {
        console.error('Erro ao buscar pagamentos:', error);
        // Não mostrar erro se a venda ainda não existe
        if (error.response?.status !== 404) {
          setErro('Erro ao carregar pagamentos existentes');
        }
      } finally {
        setLoadingPagamentos(false);
      }
    };

    buscarPagamentos();
  }, [venda.id, venda.status]); // Recarregar quando status mudar também

  // Scroll automático quando opções de parcelamento aparecem
  useEffect(() => {
    if (formaPagamentoSelecionada?.permite_parcelamento && opcoesParcelamentoRef.current) {
      setTimeout(() => {
        opcoesParcelamentoRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'nearest' 
        });
      }, 100);
    }
  }, [formaPagamentoSelecionada?.permite_parcelamento]);

  const valorTotal = venda.total;
  const {
    valorPago,
    valorRestante,
    vendaQuitadaComPagamentosExistentes,
    podeConfirmarFinalizacao,
    troco,
  } = calcularResumoRecebimento({
    valorTotal,
    pagamentos,
    totalPagoExistente,
    valorRecebido,
  });
  const cupomParaFinalizar = montarCupomParaFinalizar({ cupomAplicado, venda });
  const descricaoCupomMargem = descreverCupomMargem(cupomParaFinalizar, formatMoneyBRL);
  const corParcelamentoAtual = obterCorParcelamentoAtual({
    formaPagamento: formaPagamentoSelecionada,
    simulacoesParcelamento,
    numeroParcelas,
  });
  const corVisualParcelamento = obterCorVisualParcelamento({
    formaPagamento: formaPagamentoSelecionada,
    simulacoesParcelamento,
    numeroParcelas,
    statusMargem,
  });
  const estiloVisualParcelamento =
    obterEstiloVisualParcelamento(corVisualParcelamento);
  const { margemCriticaAtual, mostrarCampoJustificativa } =
    avaliarEstadoJustificativaMargem({
      statusMargem,
      corParcelamentoAtual,
      justificativaTexto,
    });
  const mostrarBotaoAdicionarRodape =
    Boolean(formaPagamentoSelecionada) && valorRestante > 0.01;

  const rolarElementoNoModal = useCallback((elemento, { focusElement } = {}) => {
    if (!elemento) return;

    const rolar = () => {
      const container = modalPagamentoContentRef.current;

      if (container && typeof elemento.getBoundingClientRect === 'function') {
        const containerRect = container.getBoundingClientRect();
        const elementoRect = elemento.getBoundingClientRect();
        const destino =
          container.scrollTop + elementoRect.top - containerRect.top - 24;
        const limite = Math.max(0, container.scrollHeight - container.clientHeight);

        container.scrollTo({
          top: Math.max(0, Math.min(destino, limite)),
          behavior: 'smooth',
        });
      } else if (typeof elemento.scrollIntoView === 'function') {
        elemento.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      if (focusElement && typeof window !== 'undefined') {
        window.setTimeout(() => {
          focusElement.focus?.({ preventScroll: true });
        }, 250);
      }
    };

    if (
      typeof window !== 'undefined' &&
      typeof window.requestAnimationFrame === 'function'
    ) {
      window.requestAnimationFrame(() => window.requestAnimationFrame(rolar));
      return;
    }

    rolar();
  }, []);

  const revelarJustificativaObrigatoria = useCallback(() => {
    rolarElementoNoModal(justificativaRef.current, {
      focusElement: justificativaTextareaRef.current,
    });
  }, [rolarElementoNoModal]);

  useRevealFloatingPanel({
    enabled: Boolean(statusMargem === 'amarelo' || statusMargem === 'vermelho'),
    panelRef: statusMargemRef,
    refreshKey: `${statusMargem || ''}:${formaPagamentoSelecionada?.id || ''}:${numeroParcelas}`,
  });

  useEffect(() => {
    if (erroJustificativa) {
      revelarJustificativaObrigatoria();
    }
  }, [erroJustificativa, revelarJustificativaObrigatoria]);

  const {
    cashbackPrevisto,
    carimbosPrevistos,
    recompraPrevista,
  } = calcularBeneficiosCampanhaPreview({
    campanhasCompra,
    rankCliente,
    canalVenda: venda.canal || venda.origem_canal_venda || 'loja_fisica',
    valorBase: venda.total,
  });

  // 🆕 Função para calcular status de margem operacional (INICIAL - À VISTA)
  const calcularStatusMargemInicial = async () => {
    setLoadingStatusMargem(true);
    try {
      // 🎯 SIMULAR pagamento à vista (dinheiro) para análise inicial
      const pagamentoSimuladoAVista = montarPagamentoAVista(venda.total);

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        montarPayloadAnaliseMargem({
          venda,
          formasPagamento: pagamentoSimuladoAVista,
        })
      );

      // Salvar SOMENTE a cor do indicador
      const corIndicador = extrairCorIndicadorMargem(response.data);
      if (corIndicador) {
        setStatusMargem(corIndicador);
        console.log('✅ Status inicial calculado:', corIndicador);
      }
    } catch (error) {
      console.error('❌ Erro ao calcular status inicial:', error);
      setStatusMargem(null);
    } finally {
      setLoadingStatusMargem(false);
    }
  };

  // 🆕 Função para calcular status de margem operacional (COM PAGAMENTOS REAIS)
  const calcularStatusMargem = async () => {
    if (pagamentos.length === 0 && pagamentosExistentes.length === 0) {
      // Se não há pagamentos, manter o status inicial
      return;
    }

    setLoadingStatusMargem(true);
    try {
      const todosPagamentos = montarPagamentosMargem({
        pagamentosExistentes,
        pagamentos,
      });

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        montarPayloadAnaliseMargem({
          venda,
          formasPagamento: todosPagamentos,
        })
      );

      // Salvar SOMENTE a cor do indicador
      const corIndicador = extrairCorIndicadorMargem(response.data);
      if (corIndicador) {
        setStatusMargem(corIndicador);
      }
    } catch (error) {
      console.error('Erro ao calcular status de margem:', error);
      setStatusMargem(null);
    } finally {
      setLoadingStatusMargem(false);
    }
  };

  // 🆕 REMOVIDO: classificarParcelamento - O BACKEND É A ÚNICA FONTE DA VERDADE
  // A cor_indicador JÁ vem do backend, não precisamos interpretar aqui

  // 🆕 Recalcular status de margem sempre que pagamentos mudarem
  useEffect(() => {
    const timer = setTimeout(() => {
      calcularStatusMargem();
    }, 500); // Debounce de 500ms

    return () => clearTimeout(timer);
  }, [pagamentos, numeroParcelas]);

  // 💡 Calcular sugestão PIX quando a forma de pagamento selecionada NÃO É PIX
  useEffect(() => {
    const ehPix = ehFormaPagamentoPix(formaPagamentoSelecionada);
    if (ehPix || !formaPagamentoSelecionada) {
      setSugestaoPix(null);
      return;
    }
    const custoTotal = calcularCustoTotalItensVenda(venda.itens);
    if (!custoTotal) { setSugestaoPix(null); return; }
    api.post('/pdv/indicadores/sugestao-pix', {
      total_venda: venda.total || 0,
      custo_total: custoTotal,
      desconto_atual: venda.desconto_valor || 0,
      taxa_cartao_pct: formaPagamentoSelecionada?.taxa_percentual || 0,
    }).then(res => setSugestaoPix(res.data?.tem_sugestao ? res.data : null))
      .catch(() => setSugestaoPix(null));
  }, [formaPagamentoSelecionada?.id]);

  // 🆕 PASSO 1️⃣ - Calcular status IMEDIATAMENTE ao abrir o modal
  useEffect(() => {
    console.log('🎬 Modal de pagamento aberto - Calculando status inicial...');
    calcularStatusMargemInicial();
  }, []); // Executa apenas uma vez ao montar

  // 🎯 SIMULAR PARCELAMENTOS assim que formas de pagamento forem carregadas
  useEffect(() => {
    if (formasPagamento && formasPagamento.length > 0) {
      const formasComParcelamento = formasPagamento.filter(f => f.permite_parcelamento);
      if (formasComParcelamento.length > 0 && Object.keys(simulacoesParcelamento).length === 0) {
        console.log('📊 Simulando parcelamentos ao carregar formas...');
        // Simular a primeira forma com parcelamento
        simularParcelamentos(formasComParcelamento[0]);
      }
    }
  }, [formasPagamento]); // Executa quando formas de pagamento são carregadas

  // 🆕 PASSO 2️⃣ - Simular parcelamentos para uma forma de pagamento
  const simularParcelamentos = async (formaPagamento) => {
    if (!formaPagamento || !formaPagamento.permite_parcelamento) {
      console.log('⏭️ Forma de pagamento inválida ou não permite parcelamento');
      return;
    }

    const maxParcelas = formaPagamento?.parcelas_maximas ?? 12;
    const formaPagamentoId = formaPagamento.id;
    
    console.log(`🎲 Simulando parcelamentos para ${formaPagamento.nome} (até ${maxParcelas}x)...`);
    
    setLoadingSimulacao(true);
    
    try {
            const resultados = {};
      
      // Simular todas as parcelas de 1 até max
      for (let parcelas = 1; parcelas <= maxParcelas; parcelas++) {
        const pagamentoSimulado = montarPagamentoSimuladoParcelamento({
          formaPagamentoId,
          valorTotal: venda.total,
          parcelas,
        });

        try {
          const response = await api.post(
            `/formas-pagamento/analisar-venda`,
            montarPayloadAnaliseMargem({
              venda,
              formasPagamento: pagamentoSimulado,
            })
          );

          const resultadoSimulacao =
            normalizarResultadoSimulacaoParcelamento(response.data);
          if (resultadoSimulacao) resultados[parcelas] = resultadoSimulacao;
        } catch (error) {
          console.error(`Erro ao simular ${parcelas}x:`, error);
          resultados[parcelas] = montarFallbackSimulacaoParcelamento();
        }
      }
      
      // Salvar simulações no estado
      setSimulacoesParcelamento(prev => ({
        ...prev,
        [formaPagamentoId]: resultados
      }));
      
      // 🆕 PASSO 3️⃣ - Calcular faixas de parcelamento
      const faixas = calcularFaixasParcelamento(resultados, maxParcelas);
      setFaixasParcelamento(faixas);
      
      console.log('✅ Simulações concluídas:', resultados);
      console.log('📊 Faixas calculadas:', faixas);
      
    } catch (error) {
      console.error('❌ Erro ao simular parcelamentos:', error);
    } finally {
      setLoadingSimulacao(false);
    }
  };

  // 🆕 PASSO 2️⃣ - Disparar simulação quando forma de pagamento é selecionada
  useEffect(() => {
    const decisaoParcelamento = resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada,
      simulacoesParcelamento,
      formasPagamento,
    });

    if (decisaoParcelamento?.acao === 'simular') {
      simularParcelamentos(decisaoParcelamento.formaPagamento);
      return;
    }

    if (decisaoParcelamento?.faixas) {
      setFaixasParcelamento(decisaoParcelamento.faixas);
      if (decisaoParcelamento.formaPagamento === formaPagamentoSelecionada) {
        console.log('Reutilizando simulacao existente');
      }
    }
  }, [formaPagamentoSelecionada?.id]);

  // Adicionar forma de pagamento
  const adicionarPagamento = () => {
    const valor = valorRecebido || 0;
    const erroValidacao = validarPagamentoParaAdicionar({
      formaPagamento: formaPagamentoSelecionada,
      valor,
      saldoCashback,
      bandeira,
      operadora: operadoraSelecionada,
      numeroParcelas,
    });

    if (erroValidacao) {
      setErro(erroValidacao);
      return;
    }

    // Permitir valor maior que o restante (para dinheiro com troco)
    // ou menor (para baixa parcial)

    // DEBUG: Verificar estrutura da forma de pagamento
    console.log('🔍 DEBUG formaPagamentoSelecionada:', formaPagamentoSelecionada);
    
    const novoPagamento = montarPagamentoRecebido({
      formaPagamento: formaPagamentoSelecionada,
      valor,
      valorRestante,
      bandeira,
      nsuCartao,
      operadora: operadoraSelecionada,
      numeroParcelas,
      troco,
    });
    console.log('📤 DEBUG novoPagamento:', novoPagamento);

    // ✅ PASSO 5: Se margem crítica, EXIGIR justificativa (mas NÃO bloquear fluxo)
    console.log(`♻️ Reutilizando simulação do backend: ${numeroParcelas}x = cor ${corParcelamentoAtual}`);
    const margemCritica = margemCriticaAtual;
    
    if (margemCritica) {
      if (!justificativaTexto || justificativaTexto.trim().length < 10) {
        setErroJustificativa('⚠️ Justificativa obrigatória para margem crítica (mínimo 10 caracteres)');
        setErro('Por favor, preencha a justificativa abaixo');
        revelarJustificativaObrigatoria();
        return;
      }
      
      venda.observacoes = montarObservacoesComJustificativaMargem({
        observacoesAtuais: venda.observacoes || "",
        descricaoCupomMargem,
        justificativaTexto,
      });
    }

    // Adicionar pagamento normalmente
    // Capturar troco excedente ANTES de resetar os estados
    const trocoParaCredito =
      opcaoExcedente === 'credito' && troco > 0 && formaPagamentoSelecionada?.tipo !== 'dinheiro'
        ? troco
        : 0;

    setPagamentos([...pagamentos, novoPagamento]);
    setFormaPagamentoSelecionada(null);
    setValorRecebido(0);
    setBandeira('');
    setOperadoraSelecionada(operadoras.find(op => op.padrao) || null); // 🆕 Resetar para padrão
    setNsuCartao(''); // Limpar NSU
    setNumeroParcelas(1);
    setErro('');
    setErroJustificativa('');
    setOpcaoExcedente(null);
    // ✅ NÃO limpar justificativaTexto - deve permanecer até finalizar venda

    // Se escolheu gerar crédito, abrir modal após adicionar pagamento
    if (trocoParaCredito > 0) {
      setValorExcedente(trocoParaCredito);
      setMostrarModalCreditoExcedente(true);
    }
  };

  // Remover forma de pagamento
  const removerPagamento = (index) => {
    setPagamentos(pagamentos.filter((_, i) => i !== index));
  };

  // Excluir pagamento existente
  const excluirPagamentoExistente = async (pagamentoId) => {
    if (!confirm('Deseja realmente excluir este pagamento?')) {
      return;
    }

    setLoading(true);
    setErro('');

    try {
      console.log(`🗑️ Excluindo pagamento ID ${pagamentoId}...`);
      await api.delete(`/vendas/pagamentos/${pagamentoId}`);
      console.log('✅ Pagamento excluído com sucesso!');
      
      // Recarregar pagamentos do servidor para garantir sincronização
      const response = await api.get(`/vendas/${venda.id}/pagamentos`);
      setPagamentosExistentes(response.data.pagamentos || []);
      setTotalPagoExistente(response.data.total_pago || 0);
      
      // Se excluiu todos os pagamentos, recarregar a venda para atualizar o status
      if (response.data.pagamentos.length === 0 && onVendaAtualizada) {
        await onVendaAtualizada();
      }
      
      setErro(''); // Limpar erros anteriores
    } catch (error) {
      console.error('❌ Erro ao excluir pagamento:', error);
      console.error('   Response:', error.response);
      console.error('   Message:', error.message);
      
      if (error.message && error.message.includes('CORS')) {
        setErro('⚠️ Erro de CORS: O backend precisa ser reiniciado. Feche e abra novamente o servidor backend.');
      } else {
        setErro(error.response?.data?.detail || error.message || 'Erro ao excluir pagamento');
      }
    } finally {
      setLoading(false);
    }
  };

  // Finalizar venda
  const handleFinalizar = async () => {
    // Permitir baixa parcial - não exigir pagamento total
    if (!podeConfirmarFinalizacao) {
      setErro('Adicione pelo menos uma forma de pagamento');
      return;
    }

    setLoading(true);
    setErro('');

    try {
      // ⚠️ VERIFICAR ESTOQUE NEGATIVO ANTES DE FINALIZAR
      const itensParaVerificar = montarItensParaVerificarEstoqueNegativo(venda.itens);
      
      if (itensParaVerificar.length > 0) {
        const response = await verificarEstoqueNegativo(itensParaVerificar);
        const produtosNegativos = response.data || [];
        
        if (produtosNegativos.length > 0) {
          const confirmar = window.confirm(montarMensagemEstoqueNegativo(produtosNegativos));
          
          if (!confirmar) {
            setLoading(false);
            return; // Cancelar finalização
          }
        }
      }
      
      const vendaParaPersistir = montarVendaParaPersistirComCupom({
        venda,
        cupomParaFinalizar,
      });
      const payloadVenda = montarPayloadVenda(vendaParaPersistir);

      // Criar a venda primeiro se ainda não foi criada
      let vendaId = venda.id;
      
      if (!vendaId) {
        const vendaCriada = await criarVenda(payloadVenda);
        vendaId = vendaCriada.id;
      } else {
        await atualizarVenda(vendaId, payloadVenda);
      }

      // Finalizar a venda com os pagamentos
      const resultado = await finalizarVenda(vendaId, pagamentos, {
        cupom_code: cupomParaFinalizar?.code || null,
        cupom_discount_applied: cupomParaFinalizar?.discount_applied ?? null,
      });

      // Mostrar pergunta sobre NF-e APENAS se pagamento completo
      setVendaFinalizadaId(vendaId);
      
      // ✅ Só perguntar sobre NFCe se status for 'finalizada' (pagamento completo)
      if (devePerguntarNotaFiscal(resultado)) {
        setMostrarPerguntaNFe(true);
      } else {
        // Se foi pagamento parcial, apenas fechar modal
        onConfirmar();
      }
    } catch (error) {
      console.error('Erro ao finalizar venda:', error);
      setErro(error.response?.data?.detail || 'Erro ao finalizar venda');
    } finally {
      setLoading(false);
    }
  };

  // Analisar venda com formas de pagamento atuais
  const analisarVendaModal = async () => {
    if (!onAnalisarVenda) return;

    console.log('🔍 DEBUG pagamentos atuais:', pagamentos);

    const formasPagamentoAnalise = montarFormasPagamentoAnalise({
      pagamentos,
      formasPagamento,
      valorTotal,
    });

    console.log('✅ Formas finais enviadas para análise:', formasPagamentoAnalise);

    // Chamar a função de análise passando as formas de pagamento
    onAnalisarVenda(formasPagamentoAnalise);
  };

  // Emitir NF-e
  const emitirNFe = async (tipoNota) => {
    setLoading(true);
    setErro('');

    try {
      const resultado = await emitirNotaFiscalAssistida({
        vendaId: vendaFinalizadaId,
        tipoNota,
      });

      if (resultado?.cancelado) return;

      const transmissao = resultado?.data?.transmissao;
      if (transmissao?.success === false) {
        alert(
          `${tipoNota === 'nfe' ? 'NF-e' : 'NFC-e'} criada no Bling, mas a transmissao nao foi concluida automaticamente.\n\n${transmissao.erro || ''}`.trim(),
        );
      } else {
        alert(`${tipoNota === 'nfe' ? 'NF-e' : 'NFC-e'} enviada para emissao/transmissao com sucesso!`);
      }
      onConfirmar();
    } catch (error) {
      console.error('Erro ao emitir nota:', error);
      const mensagem = extrairMensagemNFe(error);
      setErro(mensagem);
      alert(mensagem);
      return;
    } finally {
      setLoading(false);
    }
  };

  // Modal de pergunta NF-e
  if (mostrarPerguntaNFe) {
    return (
      <ModalPerguntaNFe
        cliente={venda.cliente}
        erro={erro}
        loading={loading}
        onConfirmar={onConfirmar}
        onEmitir={emitirNFe}
      />
    );
  }

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Registrar Recebimento</h2>
              <p className="text-sm text-gray-500">
                Selecione as formas de pagamento
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* 🚫 BOTÃO "VER ANÁLISE" OCULTADO - Lógica preservada, apenas não renderiza */}
            {false && onAnalisarVenda && (
              <button
                onClick={analisarVendaModal}
                className="flex items-center space-x-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
                title="Ver análise financeira com as formas de pagamento atuais"
              >
                <BarChart2 className="w-4 h-4" />
                <span>Ver Análise</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div ref={modalPagamentoContentRef} className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Coluna Esquerda - Seleção de Pagamentos */}
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-4">
                  Selecione a forma de pagamento
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  {/* Crédito Cliente (exibir primeiro se disponível) */}
                  {venda.cliente && venda.cliente.credito > 0 && (
                    <button
                      onClick={() => {
                        setFormaPagamentoSelecionada({
                          id: 'credito_cliente',
                          nome: 'Crédito Cliente',
                          tipo: 'credito_cliente',
                          icone: '🎁',
                          credito_disponivel: parseFloat(venda.cliente.credito)
                        });
                        setNumeroParcelas(1);
                        setBandeira('');
                        setNsuCartao(''); // Limpar NSU
                        // Pre-preencher com o menor valor entre crédito e valor restante
                        setValorRecebido(Math.min(parseFloat(venda.cliente.credito), valorRestante));
                      }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        formaPagamentoSelecionada?.id === 'credito_cliente'
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-purple-200 bg-purple-50/50 hover:border-purple-300'
                      }`}
                    >
                      <div className="text-2xl mb-1">🎁</div>
                      <div className={`text-sm font-medium ${
                        formaPagamentoSelecionada?.id === 'credito_cliente' ? 'text-purple-900' : 'text-purple-700'
                      }`}>
                        Crédito Cliente
                      </div>
                      <div className="text-xs text-purple-600 mt-1 font-semibold">
                        R$ {parseFloat(venda.cliente.credito).toFixed(2).replace('.', ',')}
                      </div>
                    </button>
                  )}

                  {/* Cashback de campanhas (exibir se disponível) */}
                  {venda.cliente && saldoCashback > 0 && (
                    <button
                      onClick={() => {
                        setFormaPagamentoSelecionada({
                          id: 'cashback',
                          nome: 'Cashback',
                          tipo: 'cashback',
                          icone: '💰',
                        });
                        setNumeroParcelas(1);
                        setBandeira('');
                        setNsuCartao('');
                        setValorRecebido(Math.min(saldoCashback, valorRestante));
                      }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        formaPagamentoSelecionada?.id === 'cashback'
                          ? 'border-green-500 bg-green-50'
                          : 'border-green-200 bg-green-50/50 hover:border-green-300'
                      }`}
                    >
                      <div className="text-2xl mb-1">💰</div>
                      <div className={`text-sm font-medium ${
                        formaPagamentoSelecionada?.id === 'cashback' ? 'text-green-900' : 'text-green-700'
                      }`}>
                        Cashback
                      </div>
                      <div className="text-xs text-green-600 mt-1 font-semibold">
                        R$ {saldoCashback.toFixed(2).replace('.', ',')}
                      </div>
                    </button>
                  )}

                  {/* Formas de pagamento cadastradas */}
                  {formasPagamento.map((forma) => {
                    const selecionada = formaPagamentoSelecionada?.id === forma.id;

                    return (
                      <button
                        key={forma.id}
                        onClick={() => {
                          setFormaPagamentoSelecionada(forma);
                          setNumeroParcelas(1);
                          setBandeira('');
                          setNsuCartao(''); // Limpar NSU
                          setValorRecebido(valorRestante); // Pré-preencher valor restante
                        }}
                        className={`p-4 rounded-lg border-2 transition-all ${
                          selecionada
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex justify-center mb-1 text-gray-500">
                          <PaymentMethodIcon icone={forma.icone} nome={forma.nome} />
                        </div>
                        <div className={`text-sm font-medium ${selecionada ? 'text-blue-900' : 'text-gray-700'}`}>
                          {forma.nome}
                        </div>
                        {forma.taxa_percentual > 0 && (
                          <div className="text-xs text-gray-500 mt-1">
                            Taxa: {forma.taxa_percentual}%
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Formulário de pagamento */}
              {formaPagamentoSelecionada && (
                <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                  {/* Informações de Crédito Cliente */}
                  {formaPagamentoSelecionada.id === 'credito_cliente' && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3">
                      <div className="flex items-center gap-2 text-purple-800 mb-2">
                        <Wallet className="w-4 h-4" />
                        <span className="text-sm font-semibold">Crédito Disponível</span>
                      </div>
                      <div className="text-lg font-bold text-purple-600">
                        R$ {formaPagamentoSelecionada.credito_disponivel.toFixed(2).replace('.', ',')}
                      </div>
                      <p className="text-xs text-purple-700 mt-1">
                        💡 Não gera movimentação de caixa
                      </p>
                    </div>
                  )}

                  {/* Informações de Cashback */}
                  {formaPagamentoSelecionada.id === 'cashback' && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
                      <div className="flex items-center gap-2 text-green-800 mb-2">
                        <span className="text-base">💰</span>
                        <span className="text-sm font-semibold">Cashback Disponível</span>
                      </div>
                      <div className="text-lg font-bold text-green-600">
                        R$ {saldoCashback.toFixed(2).replace('.', ',')}
                      </div>
                      <p className="text-xs text-green-700 mt-1">
                        💡 Saldo acumulado em campanhas — não gera movimentação de caixa
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {formaPagamentoSelecionada.id === 'credito_cliente' ? 'Valor a Utilizar' : formaPagamentoSelecionada.id === 'cashback' ? 'Valor a Resgatar' : 'Valor Recebido'}
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                        R$
                      </span>
                      <CurrencyInput
                        value={valorRecebido}
                        onChange={(v) => {
                          if (formaPagamentoSelecionada.id === 'credito_cliente') {
                            const maxCredito = Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante);
                            setValorRecebido(Math.min(v, maxCredito));
                          } else if (formaPagamentoSelecionada.id === 'cashback') {
                            const maxCashback = Math.min(saldoCashback, valorRestante);
                            setValorRecebido(Math.min(v, maxCashback));
                          } else {
                            setValorRecebido(v);
                          }
                        }}
                        placeholder={valorRestante.toFixed(2).replace('.', ',')}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        autoFocus
                      />
                    </div>
                    {formaPagamentoSelecionada.id === 'credito_cliente' && (
                      <p className="text-xs text-gray-600 mt-1">
                        Máximo: R$ {Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante).toFixed(2)}
                      </p>
                    )}
                    {formaPagamentoSelecionada.id === 'cashback' && (
                      <p className="text-xs text-gray-600 mt-1">
                        Máximo: R$ {Math.min(saldoCashback, valorRestante).toFixed(2).replace('.', ',')}
                      </p>
                    )}
                  </div>

                  {/* Aviso de excedente para métodos NÃO-dinheiro */}
                  {formaPagamentoSelecionada?.tipo !== 'dinheiro' &&
                    formaPagamentoSelecionada?.tipo !== 'credito_cliente' &&
                    formaPagamentoSelecionada?.tipo !== 'cashback' &&
                    troco > 0.005 && (
                    <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 space-y-2">
                      <div className="flex items-center gap-2 text-amber-800 text-sm font-semibold">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        Valor R$ {valorRecebido.toFixed(2).replace('.', ',')} supera o total em{' '}
                        <span className="font-bold">R$ {troco.toFixed(2).replace('.', ',')}</span>
                      </div>
                      {venda.cliente ? (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setOpcaoExcedente(opcaoExcedente === 'troco' ? null : 'troco')}
                            className={`flex-1 py-2 text-xs font-semibold rounded-xl border-2 transition-colors ${
                              opcaoExcedente === 'troco'
                                ? 'bg-yellow-500 border-yellow-500 text-white'
                                : 'bg-white border-yellow-300 text-yellow-800 hover:bg-yellow-50'
                            }`}
                          >
                            💵 Troco em dinheiro
                          </button>
                          <button
                            type="button"
                            onClick={() => setOpcaoExcedente(opcaoExcedente === 'credito' ? null : 'credito')}
                            className={`flex-1 py-2 text-xs font-semibold rounded-xl border-2 transition-colors ${
                              opcaoExcedente === 'credito'
                                ? 'bg-green-500 border-green-500 text-white'
                                : 'bg-white border-green-300 text-green-800 hover:bg-green-50'
                            }`}
                          >
                            💳 Gerar crédito
                          </button>
                        </div>
                      ) : (
                        <p className="text-xs text-amber-700">
                          Sem cliente associado — o excedente será desconsiderado.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Troco (somente para dinheiro) */}
                  {formaPagamentoSelecionada.tipo === 'dinheiro' && valorRecebido > 0 && (
                    <div className={`rounded-lg p-3 ${troco > 0 ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-100'}`}>
                      <div className="text-sm font-medium">
                        <span className={troco > 0 ? 'text-yellow-800' : 'text-gray-600'}>
                          Troco: R$ {troco.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Bandeira do cartão */}
                  {formaPagamentoSelecionada?.tipo && ['cartao_credito', 'cartao_debito'].includes(formaPagamentoSelecionada.tipo) && (
                    <>
                      {/* 🆕 OPERADORA DE CARTÃO */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Operadora *
                        </label>
                        <select
                          value={operadoraSelecionada?.id || ''}
                          onChange={(e) => {
                            const op = operadoras.find(o => o.id === parseInt(e.target.value));
                            setOperadoraSelecionada(op);
                            // Ajustar parcelas se exceder o máximo da nova operadora
                            if (op && numeroParcelas > op.max_parcelas) {
                              setNumeroParcelas(op.max_parcelas);
                            }
                          }}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">Selecione a operadora...</option>
                          {operadoras.map((op) => (
                            <option key={op.id} value={op.id}>
                              {op.nome} ({op.max_parcelas}x máx)
                            </option>
                          ))}
                        </select>
                        {operadoraSelecionada && (
                          <p className="text-xs text-gray-500 mt-1">
                            Máximo de {operadoraSelecionada.max_parcelas} parcelas
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Bandeira
                        </label>
                        <select
                          value={bandeira}
                          onChange={(e) => setBandeira(e.target.value)}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">Selecione...</option>
                          {BANDEIRAS_CARTAO.map((b) => (
                            <option key={b} value={b}>
                              {b}
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      {/* NSU do Cartão (para conciliação bancária) */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          NSU (Número Sequencial Único)
                          <span className="text-gray-500 text-xs ml-1">(Opcional - para conciliação)</span>
                        </label>
                        <input
                          type="text"
                          value={nsuCartao}
                          onChange={(e) => setNsuCartao(e.target.value)}
                          placeholder="Ex: 123456789"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </>
                  )}

                  {/* Número de parcelas (apenas para cartão de crédito parcelado) */}
                  {formaPagamentoSelecionada?.permite_parcelamento && (
                    <div ref={opcoesParcelamentoRef}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Número de Parcelas
                      </label>
                      <select
                        value={numeroParcelas}
                        onChange={(e) => setNumeroParcelas(parseInt(e.target.value))}
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${estiloVisualParcelamento.selectClass}`}
                      >
                        {/* 🆕 Usar max_parcelas da operadora se cartão, senão da forma de pagamento */}
                        {Array.from({ 
                          length: operadoraSelecionada?.max_parcelas || formaPagamentoSelecionada.parcelas_maximas || 12 
                        }, (_, i) => i + 1).map(
                          (n) => {
                            const valorParaParcelar = valorRecebido || valorRestante;
                            const valorParcela = valorParaParcelar / n;
                            const cor = obterCorVisualParcelamento({
                              formaPagamento: formaPagamentoSelecionada,
                              simulacoesParcelamento,
                              numeroParcelas: n,
                              statusMargem: 'verde',
                            });
                            const estilo = obterEstiloVisualParcelamento(cor);
                            
                            return (
                              <option 
                                key={n} 
                                value={n}
                                className={estilo.optionClass}
                              >
                                {estilo.prefixo}
                                {n}x de R$ {valorParcela.toFixed(2)} {valorRecebido > 0 ? `(Total: R$ ${valorParaParcelar.toFixed(2)})` : ''}
                              </option>
                            );
                          }
                        )}
                      </select>
                      {valorRecebido > 0 && numeroParcelas > 1 && (
                        <div className={`mt-2 p-3 border rounded-lg ${estiloVisualParcelamento.painelClass}`}>
                          <p className={`text-sm font-medium ${estiloVisualParcelamento.tituloClass}`}>
                            {estiloVisualParcelamento.prefixo}
                            💳 {numeroParcelas}x de R$ {(valorRecebido / numeroParcelas).toFixed(2)}
                          </p>
                          <p className={`text-xs mt-1 ${estiloVisualParcelamento.descricaoClass}`}>
                            Valor total parcelado: R$ {valorRecebido.toFixed(2)}
                            {estiloVisualParcelamento.aviso}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  <button
                    onClick={adicionarPagamento}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                  >
                    Adicionar Pagamento
                  </button>
                </div>
              )}
            </div>

            {/* Coluna Direita - Resumo */}
            <div className="space-y-6">
              <ModalPagamentoResumoLateral
                valorTotal={valorTotal}
                valorPago={valorPago}
                valorRestante={valorRestante}
                moduloCampanhasAtivo={moduloCampanhasAtivo}
                clienteId={venda.cliente?.id}
                loadingBeneficiosCampanha={loadingBeneficiosCampanha}
                carimbosPrevistos={carimbosPrevistos}
                cashbackPrevisto={cashbackPrevisto}
                recompraPrevista={recompraPrevista}
                pagamentosExistentes={pagamentosExistentes}
                pagamentos={pagamentos}
                loading={loading}
                excluirPagamentoExistente={excluirPagamentoExistente}
                removerPagamento={removerPagamento}
              />

              {/* ✅ Indicador de Status de Margem Operacional (movido para cá) */}
              {statusMargem && (
                <div ref={statusMargemRef}>
                  <StatusMargemIndicador
                    status={statusMargem}
                    loading={loadingStatusMargem}
                  />
                </div>
              )}

              {/* 💡 Sugestão PIX — aparece quando forma atual NÃO é PIX e há margem para oferecer desconto */}
              {sugestaoPix && (
                <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border-2 border-emerald-300 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💡</span>
                    <div className="flex-1">
                      <div className="font-bold text-emerald-900 text-sm mb-1">Ofereça desconto no PIX</div>
                      <div className="text-sm text-emerald-800">
                        Você pode oferecer{' '}
                        <span className="font-bold text-emerald-700 text-base">
                          {sugestaoPix.percentual_sugerido}% de desconto
                        </span>{' '}
                        se o cliente pagar no PIX.
                      </div>
                      {sugestaoPix.modo === 'comparativo_cartao' ? (
                        <div className="text-xs text-emerald-700 mt-1">
                          Cliente pagaria{' '}
                          <strong>R$ {sugestaoPix.total_com_desconto?.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                          {sugestaoPix.economia_cliente > 0 && (
                            <> · cliente economiza <strong>R$ {sugestaoPix.economia_cliente?.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></>
                          )}
                          {' '}· você recebe mais do que pelo cartão (
                          <strong>R$ {sugestaoPix.liquido_cartao?.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>)
                        </div>
                      ) : (
                        <div className="text-xs text-emerald-700 mt-1">
                          Cliente pagaria{' '}
                          <strong>R$ {sugestaoPix.total_com_desconto?.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                          {' '}· sua margem ficaria em <strong>~{sugestaoPix.margem_final_estimada}%</strong>
                          {' '}(mínimo: {sugestaoPix.margem_minima}%)
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* 🆕 PASSO 3️⃣ - Exibir faixas de parcelamento recomendadas */}
              {/* Mostrar SEMPRE que houver faixas calculadas (não depende de seleção) */}
              {faixasParcelamento && Object.keys(simulacoesParcelamento).length > 0 && (
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-4">
                  <h4 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
                    <span className="text-xl">📊</span>
                    <span>Parcelamento Recomendado</span>
                  </h4>
                  
                  {loadingSimulacao ? (
                    <div className="text-center py-4">
                      <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                      <p className="text-sm text-blue-700 mt-2">Analisando opções...</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {faixasParcelamento.saudavel.max > 0 && (
                        <div className="flex items-start space-x-3 p-3 bg-green-100 border border-green-300 rounded-lg">
                          <div className="text-2xl">🟢</div>
                          <div className="flex-1">
                            <div className="font-medium text-green-900">
                              {faixasParcelamento.saudavel.min === faixasParcelamento.saudavel.max 
                                ? `${faixasParcelamento.saudavel.max}x` 
                                : `${faixasParcelamento.saudavel.min}x a ${faixasParcelamento.saudavel.max}x`
                              }
                              <span className="ml-2 text-sm font-normal">- Saudável</span>
                            </div>
                            <div className="text-xs text-green-700 mt-1">
                              Margem adequada, sem restrições
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {faixasParcelamento.alerta.max >= faixasParcelamento.alerta.min && faixasParcelamento.alerta.min > 0 && (
                        <div className="flex items-start space-x-3 p-3 bg-yellow-100 border border-yellow-300 rounded-lg">
                          <div className="text-2xl">🟡</div>
                          <div className="flex-1">
                            <div className="font-medium text-yellow-900">
                              {faixasParcelamento.alerta.min === faixasParcelamento.alerta.max 
                                ? `${faixasParcelamento.alerta.max}x` 
                                : `${faixasParcelamento.alerta.min}x a ${faixasParcelamento.alerta.max}x`
                              }
                              <span className="ml-2 text-sm font-normal">- Atenção</span>
                            </div>
                            <div className="text-xs text-yellow-700 mt-1">
                              Margem próxima ao mínimo, evite se possível
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {faixasParcelamento.proibido.min <= (formaPagamentoSelecionada?.parcelas_maximas ?? 12) && (
                        <div className="flex items-start space-x-3 p-3 bg-red-100 border border-red-300 rounded-lg">
                          <div className="text-2xl">🔴</div>
                          <div className="flex-1">
                            <div className="font-medium text-red-900">
                              {faixasParcelamento.proibido.min}x ou mais
                              <span className="ml-2 text-sm font-normal">- Exige justificativa</span>
                            </div>
                            <div className="text-xs text-red-700 mt-1">
                              Margem crítica, justificativa obrigatória
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* 🆕 PASSO 5: Campo de Justificativa Inline (aparece AUTOMATICAMENTE quando margem vermelha) */}
              {mostrarCampoJustificativa && (
                <div
                  ref={justificativaRef}
                  data-testid="justificativa-margem-obrigatoria"
                  className="bg-red-50 border-2 border-red-300 rounded-lg p-4 scroll-mt-6"
                >
                  <div className="flex items-start space-x-3 mb-3">
                    <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-red-900">⚠️ Justificativa Obrigatória</h4>
                      <p className="text-sm text-red-700 mt-1">
                        {descricaoCupomMargem || "Esta venda tem margem crítica. Informe o motivo para prosseguir."}
                      </p>
                    </div>
                  </div>

                  <textarea
                    ref={justificativaTextareaRef}
                    value={justificativaTexto}
                    onChange={(e) => {
                      setJustificativaTexto(e.target.value);
                      if (e.target.value.trim().length >= 10) {
                        setErroJustificativa('');
                        setErro('');
                      }
                    }}
                    placeholder={
                      descricaoCupomMargem
                        ? "Ex: cupom autorizado pela campanha de fidelidade."
                        : "Ex: Cliente especial, promoção de lançamento, acordo comercial..."
                    }
                    className={`w-full px-3 py-2 border-2 rounded-lg focus:ring-2 focus:ring-red-500 resize-none ${
                      erroJustificativa ? 'border-red-500' : 'border-red-300'
                    }`}
                    rows={3}
                  />

                  {erroJustificativa && (
                    <p className="text-xs text-red-700 font-medium mt-2">
                      {erroJustificativa}
                    </p>
                  )}

                  <p className="text-xs text-red-600 mt-2">
                    💡 Mínimo 10 caracteres. Depois use o botão "Adicionar Pagamento" no rodapé.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50">
          {erro && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm">{erro}</span>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>

            <div className="flex items-center gap-3">
              {mostrarBotaoAdicionarRodape && (
                <button
                  type="button"
                  data-testid="modal-pagamento-footer-adicionar"
                  onClick={adicionarPagamento}
                  disabled={loading}
                  className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle className="w-5 h-5" />
                  <span>Adicionar Pagamento</span>
                </button>
              )}

              <button
                onClick={handleFinalizar}
                disabled={loading || !podeConfirmarFinalizacao}
                className="flex items-center space-x-2 px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processando...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    <span>{pagamentos.length === 0 ? 'Confirmar Ajustes' : 'Registrar Recebimento'}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* Modal de Crédito para excedente */}
    {mostrarModalCreditoExcedente && venda.cliente && (
      <ModalAdicionarCredito
        cliente={venda.cliente}
        valorInicial={valorExcedente}
        motivoPadrao="Crédito de excedente no pagamento"
        onConfirmar={() => setMostrarModalCreditoExcedente(false)}
        onClose={() => setMostrarModalCreditoExcedente(false)}
      />
    )}
    </>
  );
}
