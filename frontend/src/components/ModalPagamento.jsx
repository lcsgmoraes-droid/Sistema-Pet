import { useState, useEffect, useRef } from 'react';
import {
  X,
  CreditCard,
  DollarSign,
  Wallet,
  Building,
  CheckCircle,
  AlertCircle,
  Trash2,
  FileText,
  BarChart2
} from 'lucide-react';
import { finalizarVenda, criarVenda } from '../api/vendas';
import { verificarEstoqueNegativo } from '../api/alertasEstoque';
import StatusMargemIndicador from './StatusMargemIndicador';
import api from '../api';

const BANDEIRAS = [
  'Visa',
  'Mastercard',
  'Elo',
  'American Express',
  'Hipercard',
  'Outros'
];

export default function ModalPagamento({ venda, onClose, onConfirmar, onVendaAtualizada, onAnalisarVenda }) {
  const [pagamentos, setPagamentos] = useState([]);
  const [pagamentosExistentes, setPagamentosExistentes] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [operadoras, setOperadoras] = useState([]); // 🆕 Operadoras de cartão
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null); // 🆕 Operadora selecionada
  const [formaPagamentoSelecionada, setFormaPagamentoSelecionada] = useState(null);
  const [bandeira, setBandeira] = useState('');
  const [nsuCartao, setNsuCartao] = useState(''); // NSU para conciliação bancária
  const [numeroParcelas, setNumeroParcelas] = useState(1);
  const [valorRecebido, setValorRecebido] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingPagamentos, setLoadingPagamentos] = useState(false);
  const [erro, setErro] = useState('');
  const [totalPagoExistente, setTotalPagoExistente] = useState(0);
  const [mostrarPerguntaNFe, setMostrarPerguntaNFe] = useState(false);
  const [vendaFinalizadaId, setVendaFinalizadaId] = useState(null);
  
  // 🆕 Estados para status de margem operacional
  const [statusMargem, setStatusMargem] = useState(null);
  const [loadingStatusMargem, setLoadingStatusMargem] = useState(false);
  
  // 🆕 Estados para justificativa inline (ÚNICO campo)
  const [justificativaTexto, setJustificativaTexto] = useState('');
  const [erroJustificativa, setErroJustificativa] = useState('');
  
  // 🆕 PASSO 2️⃣ - Estados para simulação de parcelamentos
  const [simulacoesParcelamento, setSimulacoesParcelamento] = useState({});
  const [loadingSimulacao, setLoadingSimulacao] = useState(false);
  const [faixasParcelamento, setFaixasParcelamento] = useState(null);
  
  // Ref para o container das opções de parcelamento
  const opcoesParcelamentoRef = useRef(null);

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
  const valorPago = pagamentos.reduce((sum, p) => sum + p.valor, 0) + totalPagoExistente;
  const valorRestante = valorTotal - valorPago;
  const troco = valorRecebido ? parseFloat(valorRecebido) - valorRestante : 0;

  // 🆕 Função para calcular status de margem operacional (INICIAL - À VISTA)
  const calcularStatusMargemInicial = async () => {
    setLoadingStatusMargem(true);
    try {
            // 🎯 SIMULAR pagamento à vista (dinheiro) para análise inicial
      const pagamentoSimuladoAVista = [{
        forma_pagamento_id: 1, // ID do dinheiro (geralmente 1)
        valor: venda.total,
        parcelas: 1
      }];

      // 🔧 Mapear itens para o formato correto do backend
      const itemsFormatados = (venda.itens || []).map(item => ({
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        preco_venda: item.preco_unitario || item.preco_venda || 0,
        custo: item.custo || null
      }));

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        {
          items: itemsFormatados,
          formas_pagamento: pagamentoSimuladoAVista,
          desconto: venda.desconto_valor || 0,
          taxa_entrega: venda.entrega?.taxa_entrega_total || 0
        }
      );

      // Salvar SOMENTE a cor do indicador
      if (response.data?.resultado?.cor_indicador) {
        setStatusMargem(response.data.resultado.cor_indicador);
        console.log('✅ Status inicial calculado:', response.data.resultado.cor_indicador);
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
            const todosPagamentos = [
        ...pagamentosExistentes,
        ...pagamentos
      ];

      // 🔧 Mapear itens para o formato correto do backend
      const itemsFormatados = (venda.itens || []).map(item => ({
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        preco_venda: item.preco_unitario || item.preco_venda || 0,
        custo: item.custo || null
      }));

      const response = await api.post(
        `/formas-pagamento/analisar-venda`,
        {
          items: itemsFormatados,
          formas_pagamento: todosPagamentos,
          desconto: venda.desconto_valor || 0,
          taxa_entrega: venda.entrega?.taxa_entrega_total || 0
        }
      );

      // Salvar SOMENTE a cor do indicador
      if (response.data?.resultado?.cor_indicador) {
        setStatusMargem(response.data.resultado.cor_indicador);
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
      
      // 🔧 Mapear itens para o formato correto do backend
      const itemsFormatados = (venda.itens || []).map(item => ({
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        preco_venda: item.preco_unitario || item.preco_venda || 0,
        custo: item.custo || null
      }));
      
      // Simular todas as parcelas de 1 até max
      for (let parcelas = 1; parcelas <= maxParcelas; parcelas++) {
        const pagamentoSimulado = [{
          forma_pagamento_id: formaPagamentoId,
          valor: venda.total,
          parcelas: parcelas
        }];

        try {
          const response = await api.post(
            `/formas-pagamento/analisar-venda`,
            {
              items: itemsFormatados,
              formas_pagamento: pagamentoSimulado,
              desconto: venda.desconto_valor || 0,
              taxa_entrega: venda.entrega?.taxa_entrega_total || 0
            }
          );

          if (response.data?.resultado?.cor_indicador) {
            resultados[parcelas] = {
              cor: response.data.resultado.cor_indicador,
              // ✅ O BACKEND já define a classificação através da cor
              classificacao: response.data.resultado.cor_indicador
            };
          }
        } catch (error) {
          console.error(`Erro ao simular ${parcelas}x:`, error);
          resultados[parcelas] = { cor: null, classificacao: 'verde' }; // Default seguro
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

  // 🆕 PASSO 3️⃣ - Calcular faixas de parcelamento baseado nas CORES DO BACKEND
  const calcularFaixasParcelamento = (simulacoes, maxParcelas) => {
    const faixas = {
      saudavel: { min: 1, max: 0 },
      alerta: { min: 0, max: 0 },
      proibido: { min: 0, max: maxParcelas }
    };
    
    let ultimaVerde = 0;
    let primeiraVermelha = maxParcelas + 1;
    
    for (let i = 1; i <= maxParcelas; i++) {
      const sim = simulacoes[i];
      if (!sim) continue;
      
      // ✅ Usar a COR que veio do BACKEND, não interpretar
      if (sim.cor === 'verde') {
        ultimaVerde = i;
      } else if (sim.cor === 'vermelho') {
        if (i < primeiraVermelha) {
          primeiraVermelha = i;
        }
      }
    }
    
    faixas.saudavel.max = ultimaVerde;
    faixas.alerta.min = ultimaVerde + 1;
    faixas.alerta.max = primeiraVermelha - 1;
    faixas.proibido.min = primeiraVermelha;
    
    return faixas;
  };

  // 🆕 PASSO 2️⃣ - Disparar simulação quando forma de pagamento é selecionada
  useEffect(() => {
    if (formaPagamentoSelecionada?.permite_parcelamento) {
      // Verificar se já temos simulação para esta forma
      if (!simulacoesParcelamento[formaPagamentoSelecionada.id]) {
        simularParcelamentos(formaPagamentoSelecionada);
      } else {
        // Reutilizar simulação existente
        const simulacoesExistentes = simulacoesParcelamento[formaPagamentoSelecionada.id];
        const faixas = calcularFaixasParcelamento(
          simulacoesExistentes, 
          formaPagamentoSelecionada?.parcelas_maximas ?? 12
        );
        setFaixasParcelamento(faixas);
        console.log('♻️ Reutilizando simulação existente');
      }
    } else if (!formaPagamentoSelecionada) {
      // Se não há forma selecionada mas já temos simulações, usar a primeira disponível
      const primeiraFormaComParcelamento = Object.keys(simulacoesParcelamento)[0];
      if (primeiraFormaComParcelamento && formasPagamento.length > 0) {
        const formaInfo = formasPagamento.find(f => f.id === parseInt(primeiraFormaComParcelamento));
        if (formaInfo) {
          const faixas = calcularFaixasParcelamento(
            simulacoesParcelamento[primeiraFormaComParcelamento],
            formaInfo?.parcelas_maximas ?? 12
          );
          setFaixasParcelamento(faixas);
        }
      }
    }
  }, [formaPagamentoSelecionada?.id]);

  // Adicionar forma de pagamento
  const adicionarPagamento = () => {
    if (!formaPagamentoSelecionada) {
      setErro('Selecione uma forma de pagamento');
      return;
    }

    const valor = parseFloat(valorRecebido) || 0;

    if (valor <= 0) {
      setErro('Informe o valor recebido');
      return;
    }

    // Validar crédito disponível para Crédito Cliente
    if (formaPagamentoSelecionada.id === 'credito_cliente') {
      if (valor > formaPagamentoSelecionada.credito_disponivel) {
        setErro(`Valor excede o crédito disponível (R$ ${formaPagamentoSelecionada.credito_disponivel.toFixed(2)})`);
        return;
      }
    }

    // Validar bandeira para cartões
    if (['cartao_credito', 'cartao_debito'].includes(formaPagamentoSelecionada.tipo) && !bandeira) {
      setErro('Selecione a bandeira do cartão');
      return;
    }

    // 🆕 ALERTA 1: Validar operadora para cartões
    if (['cartao_credito', 'cartao_debito'].includes(formaPagamentoSelecionada.tipo) && !operadoraSelecionada) {
      setErro('Selecione a operadora do cartão');
      return;
    }

    // 🆕 ALERTA 1: Validar parcelas contra operadora
    if (operadoraSelecionada && numeroParcelas > operadoraSelecionada.max_parcelas) {
      setErro(`A operadora ${operadoraSelecionada.nome} permite no máximo ${operadoraSelecionada.max_parcelas}x`);
      return;
    }

    // Permitir valor maior que o restante (para dinheiro com troco)
    // ou menor (para baixa parcial)

    // DEBUG: Verificar estrutura da forma de pagamento
    console.log('🔍 DEBUG formaPagamentoSelecionada:', formaPagamentoSelecionada);
    
    const novoPagamento = {
      forma_pagamento: formaPagamentoSelecionada.nome, // Enviar o nome ao invés do ID
      forma_id: formaPagamentoSelecionada.id, // ID da forma de pagamento
      forma_pagamento_id: formaPagamentoSelecionada.id, // ID da forma de pagamento (compatibilidade)
      nome: formaPagamentoSelecionada.nome,
      valor: Math.min(valor, valorRestante), // Valor efetivo do pagamento
      bandeira: ['cartao_credito', 'cartao_debito'].includes(formaPagamentoSelecionada.tipo)
        ? bandeira
        : null,
      nsu_cartao: ['cartao_credito', 'cartao_debito'].includes(formaPagamentoSelecionada.tipo) && nsuCartao
        ? nsuCartao
        : null,
      operadora_id: operadoraSelecionada?.id || null, // 🆕 ID da operadora
      numero_parcelas: formaPagamentoSelecionada.permite_parcelamento ? numeroParcelas : 1,
      parcelas: formaPagamentoSelecionada.permite_parcelamento ? numeroParcelas : 1, // Compatibilidade
      valor_recebido: valor, // Valor recebido do cliente
      troco:
        formaPagamentoSelecionada.tipo === 'dinheiro' && troco > 0 ? troco : null,
      // Marcar se é crédito cliente
      is_credito_cliente: formaPagamentoSelecionada.nome === 'Crédito Cliente' || formaPagamentoSelecionada.tipo === 'credito_cliente'
    };
    
    console.log('📤 DEBUG novoPagamento:', novoPagamento);

    // 🆕 PASSO 4️⃣ - Verificar justificativa usando APENAS dados do BACKEND
    let corParcelamento = 'verde'; // Default
    
    if (formaPagamentoSelecionada?.permite_parcelamento && simulacoesParcelamento[formaPagamentoSelecionada.id]) {
      // ✅ Reutilizar COR que veio do BACKEND
      const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
      corParcelamento = simulacao?.cor ?? 'verde';
      console.log(`♻️ Reutilizando simulação do backend: ${numeroParcelas}x = cor ${corParcelamento}`);
    }
    
    // ✅ PASSO 5: Se margem crítica, EXIGIR justificativa (mas NÃO bloquear fluxo)
    const margemCritica = statusMargem === 'vermelho' || corParcelamento === 'vermelho';
    
    if (margemCritica) {
      if (!justificativaTexto || justificativaTexto.trim().length < 10) {
        setErroJustificativa('⚠️ Justificativa obrigatória para margem crítica (mínimo 10 caracteres)');
        setErro('Por favor, preencha a justificativa abaixo');
        return;
      }
      
      // Se já tem justificativa válida, adicionar às observações
      const observacoesAtualizadas = venda.observacoes 
        ? `${venda.observacoes}\n\n⚠️ JUSTIFICATIVA (Margem Crítica): ${justificativaTexto}`
        : `⚠️ JUSTIFICATIVA (Margem Crítica): ${justificativaTexto}`;
      
      venda.observacoes = observacoesAtualizadas;
    }

    // Adicionar pagamento normalmente
    setPagamentos([...pagamentos, novoPagamento]);
    setFormaPagamentoSelecionada(null);
    setValorRecebido('');
    setBandeira('');
    setOperadoraSelecionada(operadoras.find(op => op.padrao) || null); // 🆕 Resetar para padrão
    setNsuCartao(''); // Limpar NSU
    setNumeroParcelas(1);
    setErro('');
    setErroJustificativa('');
    // ✅ NÃO limpar justificativaTexto - deve permanecer até finalizar venda
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
    if (pagamentos.length === 0) {
      setErro('Adicione pelo menos uma forma de pagamento');
      return;
    }

    setLoading(true);
    setErro('');

    try {
      // ⚠️ VERIFICAR ESTOQUE NEGATIVO ANTES DE FINALIZAR
      const itensParaVerificar = venda.itens
        .filter(item => item.tipo === 'produto' && item.produto_id)
        .map(item => ({
          produto_id: item.produto_id,
          quantidade: item.quantidade
        }));
      
      if (itensParaVerificar.length > 0) {
        const response = await verificarEstoqueNegativo(itensParaVerificar);
        const produtosNegativos = response.data || [];
        
        if (produtosNegativos.length > 0) {
          // Montar mensagem de alerta
          const mensagens = produtosNegativos.map(p => 
            `• ${p.produto_nome}: estoque atual ${p.estoque_atual}, após venda ficará ${p.estoque_resultante}`
          ).join('\n');
          
          const confirmar = window.confirm(
            `⚠️ ATENÇÃO: Os seguintes produtos ficarão com ESTOQUE NEGATIVO:\n\n${mensagens}\n\nDeseja continuar mesmo assim?`
          );
          
          if (!confirmar) {
            setLoading(false);
            return; // Cancelar finalização
          }
        }
      }
      
      // Criar a venda primeiro se ainda não foi criada
      let vendaId = venda.id;
      
      if (!vendaId) {
        // Calcular percentuais baseado nos valores inseridos
        const taxaTotal = venda.entrega?.taxa_entrega_total || 0;
        const taxaLoja = venda.entrega?.taxa_loja || 0;
        const taxaEntregador = venda.entrega?.taxa_entregador || 0;
        
        const percentualLoja = taxaTotal > 0 ? ((taxaLoja / taxaTotal) * 100).toFixed(2) : 100;
        const percentualEntregador = taxaTotal > 0 ? ((taxaEntregador / taxaTotal) * 100).toFixed(2) : 0;
        
        const vendaCriada = await criarVenda({
          cliente_id: venda.cliente?.id,
          funcionario_id: venda.funcionario_id,  // ✅ Funcionário para comissão
          itens: venda.itens,
          desconto_valor: venda.desconto_valor,
          desconto_percentual: venda.desconto_percentual,
          observacoes: venda.observacoes,
          // Campos de entrega
          tem_entrega: venda.tem_entrega,
          taxa_entrega: taxaTotal,
          percentual_taxa_loja: parseFloat(percentualLoja),
          percentual_taxa_entregador: parseFloat(percentualEntregador),
          entregador_id: venda.entregador_id,  // ✅ Entregador (direto em venda, não em venda.entrega)
          endereco_entrega: venda.entrega?.endereco_completo,
          observacoes_entrega: venda.entrega?.observacoes_entrega
        });
        vendaId = vendaCriada.id;
      }

      // Finalizar a venda com os pagamentos
      const resultado = await finalizarVenda(vendaId, pagamentos);

      // Mostrar pergunta sobre NF-e APENAS se pagamento completo
      setVendaFinalizadaId(vendaId);
      
      // ✅ Só perguntar sobre NFCe se status for 'finalizada' (pagamento completo)
      if (resultado?.status === 'finalizada' || resultado?.status === 'pago_nf') {
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

    // Calcular o total já alocado em formas de pagamento
    const totalAlocado = pagamentos.reduce((sum, p) => sum + p.valor, 0);
    const restante = valorTotal - totalAlocado;

    console.log('💰 Total alocado:', totalAlocado);
    console.log('💵 Restante:', restante);

    // Preparar dados para análise
    // Se houver pagamentos, usar proporcionalmente
    // Se não houver, assumir tudo em dinheiro
    let formasPagamentoAnalise = [];

    if (pagamentos.length > 0) {
      // Adicionar pagamentos já selecionados
      formasPagamentoAnalise = pagamentos.map(pag => {
        console.log('📋 Processando pagamento:', pag);
        const formaId = pag.forma_pagamento_id || pag.forma_id;
        const parcelas = pag.parcelas || pag.numero_parcelas || 1;
        
        console.log(`  ➡️ forma_id: ${formaId}, valor: ${pag.valor}, parcelas: ${parcelas}`);
        
        return {
          forma_pagamento_id: formaId,
          valor: pag.valor,
          parcelas: parcelas
        };
      });

      console.log('📊 Formas de pagamento para análise (após adicionar):', formasPagamentoAnalise);

      // Se ainda sobrou valor, assumir o restante em dinheiro
      if (restante > 0) {
        // Buscar ID do dinheiro
        const dinheiro = formasPagamento.find(f => f.tipo === 'dinheiro' || f.nome.toLowerCase().includes('dinheiro'));
        formasPagamentoAnalise.push({
          forma_pagamento_id: dinheiro?.id || null,
          valor: restante,
          parcelas: 1
        });
        console.log('💵 Adicionado restante em dinheiro');
      }
    } else {
      // Sem pagamentos = assumir tudo em dinheiro
      const dinheiro = formasPagamento.find(f => f.tipo === 'dinheiro' || f.nome.toLowerCase().includes('dinheiro'));
      formasPagamentoAnalise = [{
        forma_pagamento_id: dinheiro?.id || null,
        valor: valorTotal,
        parcelas: 1
      }];
      console.log('💵 Sem pagamentos, assumindo tudo em dinheiro');
    }

    console.log('✅ Formas finais enviadas para análise:', formasPagamentoAnalise);

    // Chamar a função de análise passando as formas de pagamento
    onAnalisarVenda(formasPagamentoAnalise);
  };

  // Emitir NF-e
  const emitirNFe = async (tipoNota) => {
    setLoading(true);
    setErro('');

    try {
      await api.post('/nfe/emitir', {
        venda_id: vendaFinalizadaId,
        tipo_nota: tipoNota // 'nfe' ou 'nfce'
      });

      alert(`${tipoNota === 'nfe' ? 'NF-e' : 'NFC-e'} emitida com sucesso!`);
      onConfirmar();
    } catch (error) {
      console.error('Erro ao emitir nota:', error);
      alert(error.response?.data?.detail || 'Erro ao emitir nota fiscal. Você pode emiti-la depois na tela de vendas.');
      onConfirmar(); // Continuar mesmo com erro na NF-e
    } finally {
      setLoading(false);
    }
  };

  // Modal de pergunta NF-e
  if (mostrarPerguntaNFe) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
          <div className="p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Venda Finalizada!</h3>
                <p className="text-sm text-gray-500">Deseja emitir nota fiscal?</p>
              </div>
            </div>

            <div className="space-y-3">
              {/* Cliente tem CNPJ? Oferecer NF-e, senão só NFC-e */}
              {venda.cliente?.cnpj ? (
                <>
                  <button
                    onClick={() => emitirNFe('nfe')}
                    disabled={loading}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    <FileText className="w-5 h-5" />
                    <span>Emitir NF-e (Empresa)</span>
                  </button>
                  <button
                    onClick={() => emitirNFe('nfce')}
                    disabled={loading}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    <FileText className="w-5 h-5" />
                    <span>Emitir NFC-e (Cupom)</span>
                  </button>
                </>
              ) : (
                <button
                  onClick={() => emitirNFe('nfce')}
                  disabled={loading}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  <FileText className="w-5 h-5" />
                  <span>Emitir NFC-e</span>
                </button>
              )}

              <button
                onClick={onConfirmar}
                disabled={loading}
                className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                Não emitir agora
              </button>
            </div>

            <p className="text-xs text-gray-500 text-center mt-4">
              Você pode emitir a nota fiscal depois na tela de vendas
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
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
        <div className="flex-1 overflow-y-auto p-6">
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
                        setValorRecebido(Math.min(parseFloat(venda.cliente.credito), valorRestante).toFixed(2));
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
                        }}
                        className={`p-4 rounded-lg border-2 transition-all ${
                          selecionada
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-2xl mb-1">{forma.icone || '💳'}</div>
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

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {formaPagamentoSelecionada.id === 'credito_cliente' ? 'Valor a Utilizar' : 'Valor Recebido'}
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                        R$
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        value={valorRecebido}
                        onChange={(e) => {
                          // Permitir digitação livre, apenas limitar ao confirmar
                          setValorRecebido(e.target.value);
                        }}
                        onBlur={(e) => {
                          // Validar e limitar quando sair do campo
                          const valor = parseFloat(e.target.value) || 0;
                          if (formaPagamentoSelecionada.id === 'credito_cliente') {
                            const maxCredito = Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante);
                            if (valor > maxCredito) {
                              setValorRecebido(maxCredito.toFixed(2));
                              setErro(`Valor ajustado para o crédito disponível: R$ ${maxCredito.toFixed(2)}`);
                              setTimeout(() => setErro(''), 3000);
                            }
                          }
                        }}
                        placeholder={valorRestante.toFixed(2)}
                        max={formaPagamentoSelecionada.id === 'credito_cliente' 
                          ? Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante) 
                          : undefined}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        autoFocus
                      />
                    </div>
                    {formaPagamentoSelecionada.id === 'credito_cliente' && (
                      <p className="text-xs text-gray-600 mt-1">
                        Máximo: R$ {Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante).toFixed(2)}
                      </p>
                    )}
                  </div>

                  {/* Troco (somente para dinheiro) */}
                  {formaPagamentoSelecionada.tipo === 'dinheiro' && valorRecebido && (
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
                          {BANDEIRAS.map((b) => (
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
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                          (() => {
                            // ✅ Usar COR do BACKEND (única fonte da verdade)
                            const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                            const cor = simulacao?.cor || statusMargem || 'verde';
                            
                            return cor === 'verde' 
                              ? 'border-gray-300 bg-white' 
                              : cor === 'amarelo'
                              ? 'border-yellow-400 bg-yellow-50 text-yellow-900'
                              : 'border-red-400 bg-red-50 text-red-900';
                          })()
                        }`}
                      >
                        {/* 🆕 Usar max_parcelas da operadora se cartão, senão da forma de pagamento */}
                        {Array.from({ 
                          length: operadoraSelecionada?.max_parcelas || formaPagamentoSelecionada.parcelas_maximas || 12 
                        }, (_, i) => i + 1).map(
                          (n) => {
                            const valorParaParcelar = parseFloat(valorRecebido) || valorRestante;
                            const valorParcela = valorParaParcelar / n;
                            
                            // ✅ Usar COR do BACKEND (única fonte da verdade)
                            const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[n];
                            const cor = simulacao?.cor || 'verde';
                            
                            return (
                              <option 
                                key={n} 
                                value={n}
                                className={
                                  cor === 'verde' ? '' 
                                  : cor === 'amarelo' ? 'bg-yellow-100 text-yellow-900'
                                  : 'bg-red-100 text-red-900'
                                }
                              >
                                {cor === 'vermelho' ? '🚫 ' : cor === 'amarelo' ? '⚠️ ' : ''}
                                {n}x de R$ {valorParcela.toFixed(2)} {valorRecebido ? `(Total: R$ ${valorParaParcelar.toFixed(2)})` : ''}
                              </option>
                            );
                          }
                        )}
                      </select>
                      {valorRecebido && numeroParcelas > 1 && (
                        <div className={`mt-2 p-3 border rounded-lg ${
                          (() => {
                            // ✅ Usar COR do BACKEND (única fonte da verdade)
                            const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                            const cor = simulacao?.cor || statusMargem || 'verde';
                            
                            return cor === 'verde'
                              ? 'bg-blue-50 border-blue-200'
                              : cor === 'amarelo'
                              ? 'bg-yellow-50 border-yellow-300'
                              : 'bg-red-50 border-red-300';
                          })()
                        }`}>
                          <p className={`text-sm font-medium ${
                            (() => {
                              const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                              const cor = simulacao?.cor || statusMargem || 'verde';
                              
                              return cor === 'verde'
                                ? 'text-blue-800'
                                : cor === 'amarelo'
                                ? 'text-yellow-800'
                                : 'text-red-800';
                            })()
                          }`}>
                            {(() => {
                              const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                              const cor = simulacao?.cor || statusMargem || 'verde';
                              return (
                                <>
                                  {cor === 'vermelho' && '🚫 '}
                                  {cor === 'amarelo' && '⚠️ '}
                                  💳 {numeroParcelas}x de R$ {(parseFloat(valorRecebido) / numeroParcelas).toFixed(2)}
                                </>
                              );
                            })()}
                          </p>
                          <p className={`text-xs mt-1 ${
                            (() => {
                              const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                              const cor = simulacao?.cor || statusMargem || 'verde';
                              
                              return cor === 'verde'
                                ? 'text-blue-600'
                                : cor === 'amarelo'
                                ? 'text-yellow-700'
                                : 'text-red-700';
                            })()
                          }`}>
                            Valor total parcelado: R$ {parseFloat(valorRecebido).toFixed(2)}
                            {(() => {
                              const simulacao = simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas];
                              const cor = simulacao?.cor || statusMargem || 'verde';
                              return cor === 'amarelo' ? ' - Requer atenção' : cor === 'vermelho' ? ' - Requer justificativa' : '';
                            })()}
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
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-4">Resumo da Venda</h3>

                <div className="space-y-3">
                  <div className="flex justify-between text-gray-600">
                    <span>Total da Venda:</span>
                    <span className="font-medium">R$ {valorTotal.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between text-green-600">
                    <span>Valor Pago:</span>
                    <span className="font-medium">R$ {valorPago.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between text-blue-600 text-lg font-semibold border-t pt-3">
                    <span>Restante:</span>
                    <span>R$ {valorRestante.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Pagamentos adicionados */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-4">
                  Formas de Pagamento
                </h3>

                {/* Pagamentos Existentes (já registrados) */}
                {pagamentosExistentes.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-600 mb-2">
                      💰 Pagamentos Registrados ({pagamentosExistentes.length})
                    </h4>
                    <div className="space-y-2">
                      {pagamentosExistentes.map((pag, idx) => (
                        <div
                          key={pag.id}
                          className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <div className="font-medium text-gray-900">
                                {pag.forma_pagamento === 'dinheiro' ? '💵 Dinheiro' :
                                 pag.forma_pagamento === 'pix' ? '📱 PIX' :
                                 pag.forma_pagamento === 'credito' ? '💳 Cartão de Crédito' :
                                 pag.forma_pagamento === 'debito' ? '💳 Cartão de Débito' :
                                 pag.forma_pagamento === 'boleto' ? '📄 Boleto' :
                                 pag.forma_pagamento}
                              </div>
                              <span className="px-2 py-0.5 bg-green-200 text-green-800 text-xs rounded-full font-medium">
                                Pagamento {idx + 1}
                              </span>
                            </div>
                            {pag.bandeira && (
                              <div className="text-sm text-gray-500 mt-1">Bandeira: {pag.bandeira}</div>
                            )}
                            {pag.nsu_cartao && (
                              <div className="text-sm text-gray-600 mt-1 font-mono">🔢 NSU: {pag.nsu_cartao}</div>
                            )}
                            {pag.numero_parcelas && pag.numero_parcelas > 1 && (
                              <div className="text-sm text-blue-600 mt-1 font-medium">
                                🔢 Parcelado em {pag.numero_parcelas}x de R$ {(parseFloat(pag.valor) / pag.numero_parcelas).toFixed(2)}
                              </div>
                            )}
                            <div className="text-xs text-gray-400 mt-1">
                              📅 {new Date(pag.data_pagamento).toLocaleString('pt-BR')}
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <div className="text-right">
                              <div className="font-semibold text-green-700 text-lg">
                                R$ {parseFloat(pag.valor).toFixed(2)}
                              </div>
                              {pag.troco && parseFloat(pag.troco) > 0 && (
                                <div className="text-xs text-yellow-600">
                                  Troco: R$ {parseFloat(pag.troco).toFixed(2)}
                                </div>
                              )}
                            </div>
                            <button
                              onClick={() => excluirPagamentoExistente(pag.id)}
                              disabled={loading}
                              className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors disabled:opacity-50"
                              title="Excluir pagamento"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Novos Pagamentos (a serem adicionados) */}
                {pagamentos.length === 0 && pagamentosExistentes.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 bg-gray-50 rounded-lg border-2 border-dashed">
                    <Wallet className="w-12 h-12 mx-auto mb-2 opacity-40" />
                    <p className="text-sm font-medium">Nenhuma forma de pagamento adicionada</p>
                    <p className="text-xs mt-1">Selecione uma forma acima para começar</p>
                  </div>
                ) : pagamentos.length > 0 ? (
                  <div>
                    <h4 className="text-sm font-medium text-gray-600 mb-2">
                      ⏳ Novos Pagamentos (a confirmar)
                    </h4>
                    <div className="space-y-3">
                      {pagamentos.map((pag, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <div className="font-medium text-gray-900">{pag.nome}</div>
                              <span className="px-2 py-0.5 bg-blue-200 text-blue-800 text-xs rounded-full font-medium">
                                Novo
                              </span>
                            </div>
                            {pag.bandeira && (
                              <div className="text-sm text-gray-500 mt-1">Bandeira: {pag.bandeira}</div>
                            )}
                            {pag.nsu_cartao && (
                              <div className="text-sm text-gray-600 mt-1 font-mono">🔢 NSU: {pag.nsu_cartao}</div>
                            )}
                            {pag.numero_parcelas > 1 && (
                              <div className="text-sm text-blue-600 mt-1 font-medium">
                                🔢 {pag.numero_parcelas}x de R$ {(pag.valor / pag.numero_parcelas).toFixed(2)}
                              </div>
                            )}
                            {pag.troco && pag.troco > 0 && (
                              <div className="text-sm text-yellow-600 mt-1">
                                💵 Troco: R$ {pag.troco.toFixed(2)}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="font-semibold text-blue-700 text-lg">
                              R$ {pag.valor.toFixed(2)}
                            </span>
                            <button
                              onClick={() => removerPagamento(index)}
                              className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                              title="Remover"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              {/* ✅ Indicador de Status de Margem Operacional (movido para cá) */}
              {statusMargem && (
                <StatusMargemIndicador 
                  status={statusMargem} 
                  loading={loadingStatusMargem}
                />
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
              {(() => {
                // Detectar se precisa justificativa
                let corParcelamento = 'verde';
                if (formaPagamentoSelecionada?.permite_parcelamento && 
                    simulacoesParcelamento[formaPagamentoSelecionada.id]?.[numeroParcelas]) {
                  corParcelamento = simulacoesParcelamento[formaPagamentoSelecionada.id][numeroParcelas]?.cor ?? 'verde';
                }
                
                const margemCritica = statusMargem === 'vermelho' || corParcelamento === 'vermelho';
                
                // ✅ Mostrar também se já tem texto de justificativa (para preservar após adicionar pagamento)
                const mostrarCampo = margemCritica || (justificativaTexto && justificativaTexto.trim().length > 0);
                
                if (!mostrarCampo) return null;
                
                return (
                  <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
                    <div className="flex items-start space-x-3 mb-3">
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="font-semibold text-red-900">⚠️ Justificativa Obrigatória</h4>
                        <p className="text-sm text-red-700 mt-1">
                          Esta venda tem margem crítica. Informe o motivo para prosseguir.
                        </p>
                      </div>
                    </div>
                    
                    <textarea
                      value={justificativaTexto}
                      onChange={(e) => {
                        setJustificativaTexto(e.target.value);
                        if (e.target.value.trim().length >= 10) {
                          setErroJustificativa('');
                        }
                      }}
                      placeholder="Ex: Cliente especial, promoção de lançamento, acordo comercial..."
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
                      💡 Mínimo 10 caracteres
                    </p>
                  </div>
                );
              })()}
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

          <div className="flex items-center justify-between">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>

            <button
              onClick={handleFinalizar}
              disabled={loading || pagamentos.length === 0}
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
                  <span>Registrar Recebimento</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
