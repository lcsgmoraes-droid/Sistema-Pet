/**
 * Página de Movimentações de Estoque por Produto
 * Modelo inspirado no Bling
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import toast from 'react-hot-toast';
import { formatBRL, formatMoneyBRL } from '../utils/formatters';
import EstoqueLancamentoModal from './estoque/EstoqueLancamentoModal';
import GranelLancamentoModal from './estoque/GranelLancamentoModal';
import MovimentacoesLancamentosTable from './estoque/MovimentacoesLancamentosTable';
import MovimentacoesProdutoHeader from './estoque/MovimentacoesProdutoHeader';
import ReservasAtivasModal from './estoque/ReservasAtivasModal';
import VendasPorCanalPanel from './estoque/VendasPorCanalPanel';
import { useModulos } from '../contexts/ModulosContext';

const CANAIS_DESTAQUE = ['loja_fisica', 'mercado_livre', 'shopee', 'amazon'];

const LABELS_CANAIS = {
  loja_fisica: 'Loja Física',
  mercado_livre: 'Mercado Livre',
  shopee: 'Shopee',
  amazon: 'Amazon',
  site: 'Site',
  instagram: 'Instagram',
  whatsapp: 'WhatsApp',
};

const ESTILOS_CANAIS = {
  loja_fisica: {
    card: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    bar: 'bg-emerald-400',
  },
  mercado_livre: {
    card: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    bar: 'bg-yellow-400',
  },
  shopee: {
    card: 'bg-orange-50 border-orange-200 text-orange-700',
    bar: 'bg-orange-400',
  },
  amazon: {
    card: 'bg-sky-50 border-sky-200 text-sky-700',
    bar: 'bg-sky-400',
  },
  site: {
    card: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    bar: 'bg-indigo-400',
  },
  instagram: {
    card: 'bg-pink-50 border-pink-200 text-pink-700',
    bar: 'bg-pink-400',
  },
  whatsapp: {
    card: 'bg-green-50 border-green-200 text-green-700',
    bar: 'bg-green-400',
  },
};

function formatarQuantidade(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function parseNumeroInput(valor) {
  if (valor === null || valor === undefined || valor === '') return 0;
  if (typeof valor === 'number') return Number.isFinite(valor) ? valor : 0;

  const texto = String(valor).trim();
  const normalizado = texto.includes(',')
    ? texto.replace(/\./g, '').replace(',', '.')
    : texto;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : 0;
}

function extrairMensagemErroApi(error, fallback) {
  const detalhe = error?.response?.data?.detail ?? error?.response?.data?.message;
  if (typeof detalhe === 'string') return detalhe;
  if (detalhe && typeof detalhe === 'object') {
    return detalhe.message || detalhe.mensagem || fallback;
  }
  return error?.message || fallback;
}

function getSaldoAposLancamento(movimentacao) {
  const saldo = movimentacao?.saldo_apos_lancamento ?? movimentacao?.quantidade_nova;
  const saldoNumerico = Number(saldo);
  return Number.isFinite(saldoNumerico) ? saldoNumerico : null;
}

export default function MovimentacoesProduto() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { moduloAtivo } = useModulos();
  const moduloBlingAtivo = moduloAtivo('bling');
  
  const [produto, setProduto] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingMovimentacao, setEditingMovimentacao] = useState(null);
  const [syncProduto, setSyncProduto] = useState(null);
  const [forcandoSync, setForcandoSync] = useState(false);
  const [showReservasModal, setShowReservasModal] = useState(false);
  const [loadingReservas, setLoadingReservas] = useState(false);
  const [reservasAtivas, setReservasAtivas] = useState([]);
  const [showGranelModal, setShowGranelModal] = useState(false);
  const [granelVinculos, setGranelVinculos] = useState([]);
  const [granelProdutos, setGranelProdutos] = useState([]);
  const [granelSelecionadoId, setGranelSelecionadoId] = useState('');
  const [buscaGranel, setBuscaGranel] = useState('');
  const [quantidadeGranel, setQuantidadeGranel] = useState('');
  const [observacaoGranel, setObservacaoGranel] = useState('');
  const [loadingGranel, setLoadingGranel] = useState(false);
  const [modoPrecoGranel, setModoPrecoGranel] = useState('margem');
  const [margemBaseGranel, setMargemBaseGranel] = useState('preco_venda_kg');
  const [margemGranel, setMargemGranel] = useState('20');
  const [precoVendaGranel, setPrecoVendaGranel] = useState('');
  const [atualizarPrecoGranel, setAtualizarPrecoGranel] = useState(true);
  
  // Modal de lançamento
  const [tipoLancamento, setTipoLancamento] = useState('entrada'); // entrada, saida, balanco
  const [formData, setFormData] = useState({
    quantidade: '',
    custo_unitario: '',
    observacao: '',
    lote: '',
    data_validade: '',
    data_fabricacao: ''
  });
  const produtoEhGranel = Boolean(produto?.e_granel) || (produto?.nome || '').toLowerCase().includes('granel');
  const pesoPacoteOrigem = parseNumeroInput(produto?.peso_embalagem);
  const produtoBloqueiaGranel =
    produto?.tipo_produto === 'PAI' ||
    (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL');
  const podeLancarGranel = Boolean(produto) && !produtoEhGranel && !produtoBloqueiaGranel;
  const quantidadeGranelNumero = Number(quantidadeGranel || 0);
  const kgGranelPrevisto = quantidadeGranelNumero > 0 ? quantidadeGranelNumero * pesoPacoteOrigem : 0;
  const custoKgGranel = pesoPacoteOrigem > 0 ? Number(produto?.preco_custo || 0) / pesoPacoteOrigem : 0;
  const precoVendaKgOrigem = pesoPacoteOrigem > 0 ? Number(produto?.preco_venda || 0) / pesoPacoteOrigem : 0;
  const vinculoGranelSelecionado = granelVinculos.find(
    (vinculo) => String(vinculo.produto_granel_id) === String(granelSelecionadoId),
  );
  const produtoGranelSelecionado = granelProdutos.find(
    (item) => String(item.id) === String(granelSelecionadoId),
  );
  const nomeGranelSelecionado =
    vinculoGranelSelecionado?.produto_granel_nome || produtoGranelSelecionado?.nome || '';
  const precoVendaAtualGranel = Number(
    vinculoGranelSelecionado?.produto_granel_preco_venda
      ?? produtoGranelSelecionado?.preco_venda
      ?? 0,
  );
  const baseMargemGranel = margemBaseGranel === 'preco_venda_kg' ? precoVendaKgOrigem : custoKgGranel;
  const margemGranelNumero = parseNumeroInput(margemGranel);
  const precoVendaInformadoGranel = parseNumeroInput(precoVendaGranel);
  const precoVendaSugeridoGranel = modoPrecoGranel === 'margem'
    ? baseMargemGranel * (1 + margemGranelNumero / 100)
    : precoVendaInformadoGranel;
  const margemCalculadaGranel = baseMargemGranel > 0 && precoVendaSugeridoGranel > 0
    ? ((precoVendaSugeridoGranel / baseMargemGranel) - 1) * 100
    : 0;
  const precoMinimoEsperadoGranel = precoVendaKgOrigem > 0 ? precoVendaKgOrigem * 1.2 : 0;
  const granelDentroMargemEsperada = precoMinimoEsperadoGranel > 0
    ? precoVendaSugeridoGranel >= precoMinimoEsperadoGranel
    : true;
  const diferencaPrecoGranel = precoVendaSugeridoGranel - precoVendaAtualGranel;
  const baseMargemTexto = margemBaseGranel === 'preco_venda_kg'
    ? 'venda/kg do pacote pai'
    : 'custo/kg do pacote pai';

  useEffect(() => {
    carregarDados();
  }, [id, moduloBlingAtivo]);

  useEffect(() => {
    if (!showGranelModal) return undefined;

    const timer = setTimeout(async () => {
      try {
        await buscarProdutosGranel(buscaGranel.trim());
      } catch (error) {
        console.error('Erro ao buscar produtos granel:', error);
      }
    }, buscaGranel.trim() ? 250 : 0);

    return () => clearTimeout(timer);
  }, [showGranelModal, buscaGranel]);

  const carregarDados = async () => {
    try {
      setLoading(true);

      const [produtoRes, movRes] = await Promise.all([
        api.get(`/produtos/${id}`),
        api.get(`/estoque/movimentacoes/produto/${id}`),
      ]);

      const produtoData = produtoRes.data;
      setProduto(produtoData);
      setMovimentacoes(movRes.data);

      const termoBuscaSync = produtoData?.codigo || produtoData?.sku;
      if (!moduloBlingAtivo) {
        setSyncProduto(null);
        return;
      }

      if (termoBuscaSync) {
        try {
          const syncRes = await api.get('/estoque/sync/status', {
            params: { busca: termoBuscaSync },
          });
          const itemSync = (syncRes.data || []).find((item) => item.produto_id === Number(id));
          setSyncProduto(itemSync || null);
        } catch (syncError) {
          if (syncError?.response?.status !== 403) {
            console.warn('Nao foi possivel carregar status de sincronizacao:', syncError);
          }
          setSyncProduto(null);
        }
      } else {
        setSyncProduto(null);
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      console.error('Detalhes do erro:', error.response?.data);
      toast.error(extrairMensagemErroApi(error, 'Erro ao carregar dados do produto'));
    } finally {
      setLoading(false);
    }
  };

  const carregarVinculosGranel = async () => {
    if (!id) return [];

    const response = await api.get(`/estoque/granel/vinculos/origem/${id}`);
    const vinculos = response.data || [];
    setGranelVinculos(vinculos);
    if (vinculos.length === 1) {
      setGranelSelecionadoId(String(vinculos[0].produto_granel_id));
    }
    return vinculos;
  };

  const buscarProdutosGranel = async (termo = '') => {
    const response = await api.get('/estoque/granel/produtos', {
      params: {
        busca: termo || undefined,
        limite: 30,
      },
    });
    setGranelProdutos(response.data || []);
  };

  const abrirModalGranel = async () => {
    if (!podeLancarGranel) {
      toast.error('Este produto nao permite lancamento de granel.');
      return;
    }

    if (pesoPacoteOrigem <= 0) {
      toast.error('Preencha o peso da embalagem na aba Racao antes de lancar granel.');
      return;
    }

    setQuantidadeGranel('');
    setObservacaoGranel('');
    setBuscaGranel('');
    setModoPrecoGranel('margem');
    setMargemBaseGranel('preco_venda_kg');
    setMargemGranel('20');
    setPrecoVendaGranel('');
    setAtualizarPrecoGranel(true);
    setShowGranelModal(true);
    setLoadingGranel(true);
    try {
      await Promise.all([
        carregarVinculosGranel(),
        buscarProdutosGranel(''),
      ]);
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, 'Erro ao carregar vinculos de granel'));
    } finally {
      setLoadingGranel(false);
    }
  };

  const handleSubmitGranel = async (e) => {
    e.preventDefault();

    if (!granelSelecionadoId) {
      toast.error('Selecione o produto granel que vai receber os kg.');
      return;
    }

    if (!quantidadeGranelNumero || quantidadeGranelNumero <= 0) {
      toast.error('Informe a quantidade de pacotes abertos.');
      return;
    }

    try {
      setLoadingGranel(true);
      const response = await api.post('/estoque/granel/converter', {
        produto_origem_id: Number(id),
        produto_granel_id: Number(granelSelecionadoId),
        quantidade_pacotes: quantidadeGranelNumero,
        atualizar_preco_venda_granel: Boolean(atualizarPrecoGranel && precoVendaSugeridoGranel > 0),
        preco_venda_granel: atualizarPrecoGranel && precoVendaSugeridoGranel > 0
          ? Number(precoVendaSugeridoGranel.toFixed(2))
          : null,
        observacao: observacaoGranel || null,
      });

      const precoAtualizadoMsg = response.data.preco_venda_granel_atualizado
        ? ` Preco do granel: ${formatMoneyBRL(response.data.preco_venda_granel_novo)}.`
        : '';
      toast.success(
        `Granel lancado: ${formatarQuantidade(response.data.quantidade_granel_kg)} kg a partir de ${formatarQuantidade(response.data.quantidade_pacotes)} pacote(s).${precoAtualizadoMsg}`,
        { duration: 5000 },
      );
      setShowGranelModal(false);
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, 'Erro ao lancar granel'));
    } finally {
      setLoadingGranel(false);
    }
  };

  const handleAlterarModoPrecoGranel = (modo) => {
    setModoPrecoGranel(modo);
    if (modo === 'preco' && !precoVendaGranel) {
      const precoBase = precoVendaAtualGranel > 0 ? precoVendaAtualGranel : precoVendaSugeridoGranel;
      setPrecoVendaGranel(precoBase > 0 ? precoBase.toFixed(2) : '');
    }
    if (modo === 'margem' && !margemGranel) {
      setMargemGranel('20');
    }
  };

  const handleSelecionarGranel = (produtoGranelId, precoAtual = 0) => {
    setGranelSelecionadoId(String(produtoGranelId));
    if (modoPrecoGranel === 'preco' && Number(precoAtual || 0) > 0) {
      setPrecoVendaGranel(Number(precoAtual).toFixed(2));
    }
  };

  const handleDesvincularGranel = async (vinculoId) => {
    if (!confirm('Desvincular este produto granel da origem?')) {
      return;
    }

    try {
      await api.delete(`/estoque/granel/vinculos/${vinculoId}`);
      toast.success('Vinculo removido.');
      await carregarVinculosGranel();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, 'Erro ao desvincular granel'));
    }
  };

  const handleForcarSyncProduto = async () => {
    if (!moduloBlingAtivo) {
      toast.error('Integração Bling não está disponível neste plano.');
      return;
    }

    if (!syncProduto?.bling_produto_id) {
      toast.error('Este produto ainda não está vinculado ao Bling para sincronização manual.');
      return;
    }

    try {
      setForcandoSync(true);
      const response = await api.post(`/estoque/sync/forcar/${id}`);
      const data = response?.data || {};
      if (data.rate_limited) {
        toast(data.message || 'O Bling pediu uma pausa. O item ficou reagendado automaticamente.');
      } else {
        toast.success(data.message || 'Sincronização manual enviada para este produto.');
      }
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, 'Erro ao forçar sincronização do produto.'));
    } finally {
      setForcandoSync(false);
    }
  };

  const abrirModalReservas = async () => {
    if (!produto || Number(produto.estoque_reservado || 0) <= 0) {
      return;
    }

    try {
      setLoadingReservas(true);
      const res = await api.get(`/estoque/produto/${id}/reservas-ativas`);
      setReservasAtivas(res.data?.pedidos || []);
      setShowReservasModal(true);
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, 'Erro ao carregar pedidos reservados'));
    } finally {
      setLoadingReservas(false);
    }
  };

  const abrirPedidoReservado = (pedido) => {
    const numeroPedido = pedido?.pedido_bling_numero || pedido?.pedido_bling_id;
    const destino = numeroPedido
      ? `/vendas/bling-pedidos?pedido=${encodeURIComponent(numeroPedido)}`
      : '/vendas/bling-pedidos';
    window.open(destino, '_blank', 'noopener,noreferrer');
  };

  const abrirModal = (tipo, movimentacao = null) => {
    // ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL' && !movimentacao) {
      toast.error(
        `❌ KIT VIRTUAL não permite movimentação manual de estoque.\n\n` +
        `O estoque deste kit é calculado automaticamente com base nos componentes.\n\n` +
        `Para alterar o estoque, movimente os produtos componentes individualmente.`,
        { duration: 6000 }
      );
      return;
    }
    
    setTipoLancamento(tipo);
    setEditingMovimentacao(movimentacao);
    
    if (movimentacao) {
      // Modo edição
      setFormData({
        quantidade: movimentacao.quantidade?.toString() || '',
        custo_unitario: movimentacao.custo_unitario?.toString() || '',
        observacao: movimentacao.observacao || '',
        lote: movimentacao.lote_id || '',
        data_validade: '',
        data_fabricacao: ''
      });
    } else {
      // Modo novo
      setFormData({
        quantidade: '',
        custo_unitario: tipo === 'entrada' ? (produto?.preco_custo || '') : '',
        observacao: '',
        lote: '',
        data_validade: '',
        data_fabricacao: '',
        retornar_componentes: false  // Padrão: não retornar componentes
      });
    }
    setShowModal(true);
  };

  const handleSelectAll = () => {
    if (selectedIds.length === movimentacoes.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(movimentacoes.map(m => m.id));
    }
  };

  const handleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(sid => sid !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleDelete = async () => {
    if (selectedIds.length === 0) {
      toast.error('Selecione pelo menos um lançamento');
      return;
    }

    if (!confirm(`Deseja realmente excluir ${selectedIds.length} lançamento(s)?`)) {
      return;
    }

    try {
            const responses = await Promise.all(
        selectedIds.map(id => 
          api.delete(`/estoque/movimentacoes/${id}`)
        )
      );

      // Verificar se algum teve componentes estornados
      const componentesEstornados = responses.flatMap(r => r.data.componentes_estornados || []);
      
      if (componentesEstornados.length > 0) {
        toast.success(
          `${selectedIds.length} lançamento(s) excluído(s)!\n✅ ${componentesEstornados.length} componente(s) estornado(s)`,
          { duration: 5000 }
        );
      } else {
        toast.success(`${selectedIds.length} lançamento(s) excluído(s)`);
      }
      
      setSelectedIds([]);
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      toast.error(extrairMensagemErroApi(error, 'Erro ao excluir lançamentos'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
            // Se está editando, usar endpoint PATCH
      if (editingMovimentacao) {
        const payload = {
          quantidade: parseFloat(formData.quantidade),
          custo_unitario: formData.custo_unitario ? parseFloat(formData.custo_unitario) : null,
          observacao: formData.observacao || null,
        };

        await api.patch(
          `/estoque/movimentacoes/${editingMovimentacao.id}`,
          payload
        );

        toast.success('Lançamento atualizado com sucesso!');
        setShowModal(false);
        setEditingMovimentacao(null);
        carregarDados();
        return;
      }
      
      // Criando novo lançamento
      if (tipoLancamento === 'entrada' && produtoEhGranel) {
        toast.error('Entrada de granel deve partir do produto fechado em "Lancar granel".');
        return;
      }

      let endpoint = '/estoque/';
      let payload = {
        produto_id: parseInt(id),
        quantidade: parseFloat(formData.quantidade),
        custo_unitario: formData.custo_unitario ? parseFloat(formData.custo_unitario) : null,
        observacao: formData.observacao || null,
      };

      // Configurar endpoint e payload conforme tipo
      if (tipoLancamento === 'entrada') {
        endpoint += 'entrada';
        payload.tipo = 'entrada';
        payload.motivo = 'compra';
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        payload.data_fabricacao = formData.data_fabricacao || null;
      } else if (tipoLancamento === 'saida') {
        endpoint += 'saida';
        payload.tipo = 'saida';
        payload.motivo = 'saida_manual';
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        // Adicionar campo retornar_componentes para KIT FÍSICO
        if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'FISICO') {
          payload.retornar_componentes = formData.retornar_componentes === true;
        }
      } else if (tipoLancamento === 'balanco') {
        // Balanço: definir estoque para o valor exato
        const novaQuantidade = parseFloat(formData.quantidade);
        const estoqueAtual = produto?.estoque_atual || 0;
        const diferenca = novaQuantidade - estoqueAtual;
        
        endpoint += diferenca >= 0 ? 'entrada' : 'saida';
        payload.tipo = diferenca >= 0 ? 'entrada' : 'saida';
        payload.quantidade = Math.abs(diferenca);
        payload.motivo = 'balanco';
      }

      const response = await api.post(endpoint, payload);


      // Mostrar indicador de variação de preço se for entrada
      if (tipoLancamento === 'entrada' && response.data) {
        const { custo_anterior, custo_unitario, variacao_preco } = response.data;
        
        if (variacao_preco && custo_anterior !== null && custo_anterior !== undefined) {
          let mensagem = 'Lançamento registrado!';
          
          if (variacao_preco === 'aumento') {
            mensagem += ` ⬆️ Custo aumentou de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.error(mensagem, { duration: 5000 });
          } else if (variacao_preco === 'reducao') {
            mensagem += ` ⬇️ Custo reduziu de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.success(mensagem, { duration: 5000 });
          } else if (variacao_preco === 'estavel') {
            mensagem += ` Custo mantido em R$ ${custo_unitario?.toFixed(2)}`;
            toast(mensagem, { icon: '➖', duration: 3000 });
          }
        } else if (custo_unitario) {
          // Primeira entrada
          toast.success(`Lançamento registrado! Custo: R$ ${custo_unitario?.toFixed(2)}`, { duration: 3000 });
        } else {
          toast.success('Lançamento registrado com sucesso!');
        }
      } else {
        // Mostrar mensagem sobre componentes sensibilizados se houver
        if (response.data?.componentes_sensibilizados && response.data.componentes_sensibilizados.length > 0) {
          const qtdComponentes = response.data.componentes_sensibilizados.length;
          toast.success(
            `Lançamento registrado com sucesso!\n✅ ${qtdComponentes} componente(s) sensibilizado(s)`,
            { duration: 4000 }
          );
        } else {
          toast.success('Lançamento registrado com sucesso!');
        }
      }

      setShowModal(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao registrar lançamento:', error);
      toast.error(extrairMensagemErroApi(error, 'Erro ao registrar lançamento'));
    }
  };

  const formatarData = (data) => {
    if (!data) return '-';
    // Converter para horário de Brasília (UTC-3)
    const dataUTC = new Date(data);
    const dataBrasilia = new Date(dataUTC.getTime() - (3 * 60 * 60 * 1000));
    return dataBrasilia.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/Sao_Paulo'
    });
  };

  const getTipoLabel = (tipo) => {
    const labels = {
      entrada: 'Entrada',
      saida: 'Saída',
      ajuste: 'Ajuste',
      transferencia: 'Transferência'
    };
    return labels[tipo] || tipo;
  };

  const getMotivoLabel = (motivo) => {
    const labels = {
      compra: 'Compra',
      venda: 'Venda',
      venda_online: 'Venda Online',
      ajuste: 'Ajuste',
      saida_manual: 'Saída Manual',
      devolucao: 'Devolução',
      perda: 'Perda',
      transferencia: 'Transferência',
      balanco: 'Balanço'
    };
    return labels[motivo] || motivo;
  };

  const getOrigem = (mov) => {
    // Se for venda cancelada/excluída
    if (mov.referencia_tipo === 'venda_excluida') {
      return { texto: `Venda Cancelada #${mov.referencia_id}`, icone: 'cancelado', cor: 'text-gray-400', link: null };
    }
    // Se for venda
    if (mov.referencia_tipo === 'venda') {
      // Verificar se tem NF (documento com padrão de chave NFe ou número NF)
      if (mov.documento && (mov.documento.length === 44 || mov.documento.startsWith('NF'))) {
        return { texto: `NF ${mov.documento}`, icone: 'nf-venda', cor: 'text-red-600', link: null };
      }
      // Senão, é apenas pedido
      return { texto: `Pedido #${mov.referencia_id}`, icone: 'pedido', cor: 'text-orange-600', link: `/pdv?venda=${mov.referencia_id}` };
    }
    // Se for balanço
    if (mov.referencia_tipo === 'pedido_integrado') {
      if (mov.nf_numero) {
        return { texto: `NF ${mov.nf_numero}`, icone: 'nf-venda', cor: 'text-red-600', link: null };
      }
      if (mov.documento) {
        return { texto: `Pedido Bling #${mov.documento}`, icone: 'pedido', cor: 'text-orange-600', link: null };
      }
      return { texto: `Pedido Bling #${mov.referencia_id}`, icone: 'pedido', cor: 'text-orange-600', link: null };
    }
    if (mov.motivo === 'balanco') {
      return { texto: 'Balanço', icone: 'balanco', cor: 'text-blue-600', link: null };
    }
    // Se for SAÍDA Manual - vermelho
    if (mov.tipo === 'saida') {
      return { texto: 'Saída Manual', icone: 'manual', cor: 'text-red-600', link: null };
    }
    // Se for entrada por XML (chave NFe com 44 dígitos)
    if (mov.tipo === 'entrada' && mov.documento && mov.documento.length === 44) {
      return { texto: `NF ${mov.documento.substring(25, 34)}`, icone: 'nf-entrada', cor: 'text-green-600', link: null };
    }
    // Se for entrada manual com documento
    if (mov.tipo === 'entrada' && mov.documento) {
      return { texto: mov.documento, icone: 'documento', cor: 'text-blue-600', link: `/pdv?venda=${mov.documento}` };
    }
    // Entrada manual sem documento - verde
    if (mov.tipo === 'entrada') {
      return { texto: 'Entrada Manual', icone: 'manual', cor: 'text-green-600', link: null };
    }
    return { texto: 'Manual', icone: 'manual', cor: 'text-gray-500', link: null };
  };

  // Calcular totalizadores
  const totalEntradas = movimentacoes
    .filter(m => m.tipo === 'entrada' && m.status !== 'cancelado')
    .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0);
  
  const totalSaidas = movimentacoes
    .filter(m => m.tipo === 'saida' && m.status !== 'cancelado')
    .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0);

  // Resumo de vendas por canal
  const vendasPorCanal = useMemo(() => {
    const isSaidaVendaVinculada = (mov) => {
      if (mov?.tipo !== 'saida' || mov?.status === 'cancelado' || !mov?.canal) {
        return false;
      }

      if (mov.referencia_tipo === 'venda') {
        return true;
      }

      if (mov.referencia_tipo === 'pedido_integrado') {
        return Boolean(
          mov.nf_numero ||
          (typeof mov.documento === 'string' && mov.documento.startsWith('NF '))
        );
      }

      return false;
    };

    const grupos = {};
    movimentacoes
      .filter(isSaidaVendaVinculada)
      .forEach(m => {
        const canal = m.canal;
        if (!grupos[canal]) grupos[canal] = { qtd: 0, valor: 0, count: 0 };
        grupos[canal].qtd += parseFloat(m.quantidade || 0);
        grupos[canal].valor += m.preco_venda_unitario
          ? parseFloat(m.quantidade || 0) * parseFloat(m.preco_venda_unitario)
          : 0;
        grupos[canal].count += 1;
      });

    const temVendasPorCanal = Object.values(grupos).some((g) => g.count > 0);
    if (!temVendasPorCanal) {
      return [];
    }

    CANAIS_DESTAQUE.forEach((canal) => {
      if (!grupos[canal]) {
        grupos[canal] = { qtd: 0, valor: 0, count: 0 };
      }
    });

    const totalQtd = Object.values(grupos).reduce((s, g) => s + g.qtd, 0);
    return Object.entries(grupos)
      .filter(([canal, g]) => g.count > 0 || CANAIS_DESTAQUE.includes(canal))
      .map(([canal, g]) => ({
        canal,
        qtd: g.qtd,
        valor: g.valor,
        count: g.count,
        pct: totalQtd > 0 ? (g.qtd / totalQtd) * 100 : 0,
      }))
      .sort((a, b) => {
        if (b.qtd !== a.qtd) return b.qtd - a.qtd;

        const aIndex = CANAIS_DESTAQUE.indexOf(a.canal);
        const bIndex = CANAIS_DESTAQUE.indexOf(b.canal);
        if (aIndex !== -1 || bIndex !== -1) {
          return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
        }

        return a.canal.localeCompare(b.canal);
      });
  }, [movimentacoes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  if (!produto) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Produto não encontrado</div>
      </div>
    );
  }

  const estoqueAtual = produto.estoque_atual || 0;
  const estoqueMinimo = produto.estoque_minimo || 0;
  const estoqueReservado = produto.estoque_reservado || 0;
  const saldoAposReserva = estoqueAtual - estoqueReservado;
  const unidade = produto.unidade || 'UN';

  const syncDisponivel = Boolean(syncProduto?.bling_produto_id);
  let syncStatusLabel = 'Sem vínculo com Bling';
  if (syncDisponivel) {
    syncStatusLabel = syncProduto?.status || 'ativo';
    if (syncProduto?.queue_status) {
      syncStatusLabel = `${syncStatusLabel} / fila ${syncProduto.queue_status}`;
    }
  }

  const handleIncluirLancamento = () => {
    if (produto?.tipo_produto === 'KIT' && produto?.tipo_kit === 'VIRTUAL') {
      toast.error(
        'KIT VIRTUAL nao permite movimentacao manual.\n\nMovimente os componentes individualmente.',
        { duration: 4000 }
      );
      return;
    }

    setTipoLancamento(produtoEhGranel ? 'balanco' : 'entrada');
    setShowModal(true);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <MovimentacoesProdutoHeader
        abrirModalReservas={abrirModalReservas}
        estoqueAtual={estoqueAtual}
        estoqueMinimo={estoqueMinimo}
        estoqueReservado={estoqueReservado}
        forcandoSync={forcandoSync}
        formatarQuantidade={formatarQuantidade}
        loadingReservas={loadingReservas}
        onAbrirPainelBling={() => navigate('/produtos/sinc-bling')}
        onForcarSyncProduto={handleForcarSyncProduto}
        onIncluirLancamento={handleIncluirLancamento}
        onLancarGranel={abrirModalGranel}
        onVoltarProdutos={() => navigate('/produtos')}
        podeLancarGranel={podeLancarGranel}
        produto={produto}
        saldoAposReserva={saldoAposReserva}
        mostrarControlesBling={moduloBlingAtivo}
        syncDisponivel={syncDisponivel}
        syncProduto={syncProduto}
        syncStatusLabel={syncStatusLabel}
        totalEntradas={totalEntradas}
        totalSaidas={totalSaidas}
        unidade={unidade}
      />


      <VendasPorCanalPanel
        estilosCanais={ESTILOS_CANAIS}
        formatMoney={formatMoneyBRL}
        formatQuantidade={formatBRL}
        labelsCanais={LABELS_CANAIS}
        vendasPorCanal={vendasPorCanal}
      />

      <MovimentacoesLancamentosTable
        abrirModal={abrirModal}
        formatarData={formatarData}
        formatarQuantidade={formatarQuantidade}
        getMotivoLabel={getMotivoLabel}
        getOrigem={getOrigem}
        getSaldoAposLancamento={getSaldoAposLancamento}
        handleDelete={handleDelete}
        handleSelectAll={handleSelectAll}
        handleSelectOne={handleSelectOne}
        labelsCanais={LABELS_CANAIS}
        movimentacoes={movimentacoes}
        navigate={navigate}
        produto={produto}
        selectedIds={selectedIds}
      />


      {showReservasModal && (
        <ReservasAtivasModal
          abrirPedidoReservado={abrirPedidoReservado}
          formatarQuantidade={formatarQuantidade}
          onClose={() => setShowReservasModal(false)}
          reservasAtivas={reservasAtivas}
        />
      )}


      {showModal && (
        <EstoqueLancamentoModal
          editingMovimentacao={editingMovimentacao}
          estoqueAtual={estoqueAtual}
          formData={formData}
          onClose={() => setShowModal(false)}
          onSubmit={handleSubmit}
          produto={produto}
          produtoEhGranel={produtoEhGranel}
          setFormData={setFormData}
          setTipoLancamento={setTipoLancamento}
          tipoLancamento={tipoLancamento}
        />
      )}


      {showGranelModal && (
        <GranelLancamentoModal
          atualizarPrecoGranel={atualizarPrecoGranel}
          baseMargemGranel={baseMargemGranel}
          baseMargemTexto={baseMargemTexto}
          buscaGranel={buscaGranel}
          custoKgGranel={custoKgGranel}
          diferencaPrecoGranel={diferencaPrecoGranel}
          formatMoney={formatMoneyBRL}
          formatPercentual={formatBRL}
          formatarQuantidade={formatarQuantidade}
          granelDentroMargemEsperada={granelDentroMargemEsperada}
          granelProdutos={granelProdutos}
          granelSelecionadoId={granelSelecionadoId}
          granelVinculos={granelVinculos}
          handleAlterarModoPrecoGranel={handleAlterarModoPrecoGranel}
          handleDesvincularGranel={handleDesvincularGranel}
          handleSelecionarGranel={handleSelecionarGranel}
          kgGranelPrevisto={kgGranelPrevisto}
          loadingGranel={loadingGranel}
          margemBaseGranel={margemBaseGranel}
          margemCalculadaGranel={margemCalculadaGranel}
          margemGranel={margemGranel}
          modoPrecoGranel={modoPrecoGranel}
          nomeGranelSelecionado={nomeGranelSelecionado}
          observacaoGranel={observacaoGranel}
          onClose={() => setShowGranelModal(false)}
          onSubmit={handleSubmitGranel}
          precoMinimoEsperadoGranel={precoMinimoEsperadoGranel}
          precoVendaAtualGranel={precoVendaAtualGranel}
          precoVendaGranel={precoVendaGranel}
          precoVendaKgOrigem={precoVendaKgOrigem}
          precoVendaSugeridoGranel={precoVendaSugeridoGranel}
          produto={produto}
          quantidadeGranel={quantidadeGranel}
          quantidadeGranelNumero={quantidadeGranelNumero}
          setAtualizarPrecoGranel={setAtualizarPrecoGranel}
          setBuscaGranel={setBuscaGranel}
          setMargemBaseGranel={setMargemBaseGranel}
          setMargemGranel={setMargemGranel}
          setObservacaoGranel={setObservacaoGranel}
          setPrecoVendaGranel={setPrecoVendaGranel}
          setQuantidadeGranel={setQuantidadeGranel}
          pesoPacoteOrigem={pesoPacoteOrigem}
        />
      )}
    </div>
  );
}
