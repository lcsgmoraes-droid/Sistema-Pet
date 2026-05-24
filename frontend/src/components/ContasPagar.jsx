import React, { useState, useEffect } from 'react';
import { Edit3, Plus, Trash2, Wallet, X } from 'lucide-react';
import api from '../api';
import { toast } from 'react-hot-toast';
import ModalNovaContaPagar from './ModalNovaContaPagar';
import { safeArray } from '../utils/safeArray';
import ActionButton from './ui/ActionButton';
import DataTable from './ui/DataTable';
import FilterBar from './ui/FilterBar';
import LoadingState from './ui/LoadingState';
import MoneyCell, { formatMoneyCellValue } from './ui/MoneyCell';
import PageHeader from './ui/PageHeader';
import StatusBadge from './ui/StatusBadge';
import FornecedorSelector from './fornecedores/FornecedorSelector';
import FornecedorIdentity, { getFornecedorIdentityName } from './ui/FornecedorIdentity';

const PERIODOS_RAPIDOS_CONTAS_PAGAR = [
  { value: 'hoje', label: 'Hoje' },
  { value: 'amanha', label: 'Amanha' },
  { value: 'semana', label: 'Semana' },
  { value: 'mes', label: 'Mes' },
];

function formatarDataISO(data) {
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function calcularIntervaloPeriodoRapido(periodo) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  const inicio = new Date(hoje);
  const fim = new Date(hoje);

  if (periodo === 'amanha') {
    inicio.setDate(inicio.getDate() + 1);
    fim.setDate(fim.getDate() + 1);
  }

  if (periodo === 'semana') {
    const diaSemana = hoje.getDay();
    const diffSegunda = diaSemana === 0 ? -6 : 1 - diaSemana;
    inicio.setDate(hoje.getDate() + diffSegunda);
    fim.setDate(inicio.getDate() + 6);
  }

  if (periodo === 'mes') {
    inicio.setDate(1);
    fim.setMonth(hoje.getMonth() + 1, 0);
  }

  return {
    data_inicio: formatarDataISO(inicio),
    data_fim: formatarDataISO(fim),
  };
}

const ContasPagar = () => {
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    status: 'todos',
    fornecedor_id: null,
    data_inicio: '',
    data_fim: '',
    apenas_vencidas: false,
    apenas_vencer: false,
    numero_nf: '',
    tipo_custo: 'todos',
    origem: 'todos',
    busca: '',
    data_campo: 'vencimento',
    fornecedor_busca: '',
    tipo_despesa_id: '',
    periodo_rapido: ''
  });
  
  const [fornecedores, setFornecedores] = useState([]);
  const [categoriasFinanceiras, setCategoriasFinanceiras] = useState([]);
  const [subcategoriasDre, setSubcategoriasDre] = useState([]);
  const [tiposDespesa, setTiposDespesa] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalNovaConta, setMostrarModalNovaConta] = useState(false);
  const [contaEdicao, setContaEdicao] = useState(null);
  const [mostrarModalClassificacao, setMostrarModalClassificacao] = useState(false);
  const [modalExclusaoRecorrencia, setModalExclusaoRecorrencia] = useState({
    aberto: false,
    conta: null,
    itens: [],
    loading: false,
  });
  const [recorrenciasSelecionadasExclusao, setRecorrenciasSelecionadasExclusao] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [mostrarModalNovaForma, setMostrarModalNovaForma] = useState(false);
  const [novaFormaData, setNovaFormaData] = useState({ nome: '', tipo: 'dinheiro', conta_bancaria_destino_id: null });
  const [dadosClassificacao, setDadosClassificacao] = useState({
    categoria_id: null,
    dre_subcategoria_id: null,
    tipo_despesa_id: null,
    canal: 'loja_fisica'
  });
  
  const [dadosPagamento, setDadosPagamento] = useState({
    valor_pago: 0,
    data_pagamento: new Date().toISOString().split('T')[0],
    forma_pagamento_id: '',
    conta_bancaria_id: '',
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: ''
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarFormasPagamento = async () => {
    const response = await api.get('/comissoes/formas-pagamento');
    const lista = response.data?.formas || [];
    return safeArray(lista).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.nome?.toLowerCase()?.replace(/\s+/g, '_') || 'outro',
      icone: '💳',
      conta_bancaria_destino_id: null,
    }));
  };

  const carregarDados = async () => {
    try {
      const [
        contasRes,
        fornecedoresRes,
        formasRes,
        bancariasRes,
        categoriasRes,
        subcategoriasRes,
        tiposRes,
      ] = await Promise.allSettled([
        api.get(`/contas-pagar/?_t=${Date.now()}`),
        api.get(`/clientes/?tipo_cadastro=fornecedor`),
        carregarFormasPagamento(),
        api.get(`/contas-bancarias?apenas_ativas=true`),
        api.get('/categorias-financeiras'),
        api.get('/dre/subcategorias'),
        api.get('/cadastros/tipo-despesa/')
      ]);

      if (contasRes.status === 'fulfilled') {
        setContas(safeArray(contasRes.value.data));
      } else {
        throw contasRes.reason;
      }

      if (fornecedoresRes.status === 'fulfilled') {
        setFornecedores(safeArray(fornecedoresRes.value.data));
      } else {
        throw fornecedoresRes.reason;
      }

      if (formasRes.status === 'fulfilled') {
        setFormasPagamento(safeArray(formasRes.value));
      } else {
        setFormasPagamento([]);
        console.warn('Nao foi possivel carregar formas de pagamento. Usando lista vazia.');
      }

      if (bancariasRes.status === 'fulfilled') {
        setContasBancarias(safeArray(bancariasRes.value.data));
      } else {
        throw bancariasRes.reason;
      }

      setCategoriasFinanceiras(categoriasRes?.status === 'fulfilled' ? safeArray(categoriasRes.value.data) : []);
      setSubcategoriasDre(subcategoriasRes?.status === 'fulfilled' ? safeArray(subcategoriasRes.value.data) : []);
      setTiposDespesa(tiposRes?.status === 'fulfilled' ? safeArray(tiposRes.value.data) : []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar contas a pagar');
    } finally {
      setLoading(false);
    }
  };

  const filtrosPadrao = {
    status: 'todos',
    fornecedor_id: null,
    data_inicio: '',
    data_fim: '',
    apenas_vencidas: false,
    apenas_vencer: false,
    numero_nf: '',
    tipo_custo: 'todos',
    origem: 'todos',
    busca: '',
    data_campo: 'vencimento',
    fornecedor_busca: '',
    tipo_despesa_id: '',
    periodo_rapido: ''
  };

  const aplicarFiltros = async (filtrosParaAplicar = filtros) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filtrosParaAplicar.status !== 'todos') params.append('status', filtrosParaAplicar.status);
      if (filtrosParaAplicar.fornecedor_id) params.append('fornecedor_id', filtrosParaAplicar.fornecedor_id);
      if (filtrosParaAplicar.data_inicio) params.append('data_inicio', filtrosParaAplicar.data_inicio);
      if (filtrosParaAplicar.data_fim) params.append('data_fim', filtrosParaAplicar.data_fim);
      if (filtrosParaAplicar.apenas_vencidas) params.append('apenas_vencidas', 'true');
      if (filtrosParaAplicar.apenas_vencer) params.append('apenas_vencer', 'true');
      if (filtrosParaAplicar.numero_nf) params.append('numero_nf', filtrosParaAplicar.numero_nf);
      if (filtrosParaAplicar.tipo_custo !== 'todos') params.append('tipo_custo', filtrosParaAplicar.tipo_custo);
      if (filtrosParaAplicar.origem !== 'todos') params.append('origem', filtrosParaAplicar.origem);
      if (filtrosParaAplicar.busca) params.append('busca', filtrosParaAplicar.busca);
      if (filtrosParaAplicar.fornecedor_busca) params.append('fornecedor_nome', filtrosParaAplicar.fornecedor_busca);
      if (filtrosParaAplicar.data_campo) params.append('data_campo', filtrosParaAplicar.data_campo);
      if (filtrosParaAplicar.tipo_despesa_id) params.append('tipo_despesa_id', filtrosParaAplicar.tipo_despesa_id);
      
      const response = await api.get(`/contas-pagar/?${params}`);

      setContas(safeArray(response.data));
    } catch (error) {
      console.error('Erro ao filtrar:', error);
      toast.error('Erro ao aplicar filtros');
      setContas([]);
    } finally {
      setLoading(false);
    }
  };

  const filtrarDespesasCaixa = () => {
    const filtrosCaixa = {
      ...filtrosPadrao,
      status: 'pago',
      origem: 'caixa_pdv',
      data_campo: filtros.data_campo || 'pagamento',
      data_inicio: filtros.data_inicio,
      data_fim: filtros.data_fim
    };
    setFiltros(filtrosCaixa);
    aplicarFiltros(filtrosCaixa);
  };

  const aplicarPeriodoRapido = (periodo) => {
    const intervalo = calcularIntervaloPeriodoRapido(periodo);
    const novosFiltros = {
      ...filtros,
      ...intervalo,
      periodo_rapido: periodo,
      apenas_vencidas: false,
      apenas_vencer: false,
    };

    setFiltros(novosFiltros);
    aplicarFiltros(novosFiltros);
  };

  const limparFiltros = () => {
    setFiltros(filtrosPadrao);
    aplicarFiltros(filtrosPadrao);
  };

  const abrirModalPagamento = (conta) => {
    setContaSelecionada(conta);
    // Buscar conta padrão da forma de pagamento se houver
    const formaDefault = formasPagamento.find(f => f.id === conta.forma_pagamento_id);
    setDadosPagamento({
      valor_pago: conta.valor_final - conta.valor_pago,
      forma_pagamento_id: conta.forma_pagamento_id || '',
      conta_bancaria_id: formaDefault?.conta_bancaria_destino_id || '',
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: ''
    });
    setMostrarModalPagamento(true);
  };

  const abrirModalEdicao = async (conta) => {
    try {
      const response = await api.get(`/contas-pagar/${conta.id}`);
      setContaEdicao({
        ...conta,
        ...response.data,
        fornecedor_id: response.data?.fornecedor?.id ?? conta.fornecedor_id ?? null,
        categoria_id: response.data?.categoria_id ?? response.data?.categoria?.id ?? conta.categoria_id ?? null,
        dre_subcategoria_id: response.data?.dre_subcategoria_id ?? conta.dre_subcategoria_id ?? null,
        tipo_despesa_id: response.data?.tipo_despesa_id ?? conta.tipo_despesa_id ?? null,
        canal: response.data?.canal ?? conta.canal ?? 'loja_fisica',
        valor_original: response.data?.valores?.original ?? conta.valor_original,
        data_emissao: response.data?.datas?.emissao ?? conta.data_emissao,
        data_vencimento: response.data?.datas?.vencimento ?? conta.data_vencimento,
        documento: response.data?.documento ?? conta.documento ?? '',
        observacoes: response.data?.observacoes ?? conta.observacoes ?? '',
      });
      setMostrarModalNovaConta(true);
    } catch (error) {
      console.error('Erro ao abrir edicao:', error);
      toast.error(error.response?.data?.detail || 'Erro ao carregar conta para edicao');
    }
  };

  const carregarRecorrenciaExclusao = async (conta) => {
    setModalExclusaoRecorrencia({
      aberto: true,
      conta,
      itens: [],
      loading: true,
    });
    setRecorrenciasSelecionadasExclusao([]);

    try {
      const response = await api.get(`/contas-pagar/${conta.id}/recorrencia`);
      const itens = safeArray(response.data?.itens);
      setModalExclusaoRecorrencia({
        aberto: true,
        conta,
        itens,
        loading: false,
      });
      setRecorrenciasSelecionadasExclusao(
        itens.filter((item) => item.pode_excluir).map((item) => item.id)
      );
    } catch (error) {
      console.error('Erro ao carregar recorrencia:', error);
      toast.error(error.response?.data?.detail || 'Erro ao carregar lancamentos recorrentes');
      setModalExclusaoRecorrencia({
        aberto: false,
        conta: null,
        itens: [],
        loading: false,
      });
    }
  };

  const alternarRecorrenciaExclusao = (itemId) => {
    setRecorrenciasSelecionadasExclusao((atuais) => (
      atuais.includes(itemId)
        ? atuais.filter((id) => id !== itemId)
        : [...atuais, itemId]
    ));
  };

  const confirmarExclusaoRecorrencia = async () => {
    if (recorrenciasSelecionadasExclusao.length === 0) {
      toast.error('Selecione pelo menos um lancamento para excluir');
      return;
    }

    try {
      await api.post('/contas-pagar/recorrencias/excluir', {
        ids: recorrenciasSelecionadasExclusao,
      });
      toast.success('Lancamentos recorrentes excluidos com sucesso');
      setModalExclusaoRecorrencia({
        aberto: false,
        conta: null,
        itens: [],
        loading: false,
      });
      setRecorrenciasSelecionadasExclusao([]);
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir recorrencia:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir lancamentos recorrentes');
    }
  };

  const excluirContaPagar = async (conta) => {
    if (conta.eh_recorrente || conta.conta_recorrencia_origem_id) {
      await carregarRecorrenciaExclusao(conta);
      return;
    }

    const confirmado = window.confirm(
      `Excluir a conta "${conta.descricao}"? Apenas contas sem pagamento registrado podem ser excluidas.`
    );
    if (!confirmado) return;

    try {
      await api.delete(`/contas-pagar/${conta.id}`);
      toast.success('Conta excluida com sucesso');
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir conta:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir conta a pagar');
    }
  };

  const precisaClassificacao = (conta) => {
    return !conta.categoria_id || !conta.dre_subcategoria_id;
  };

  const abrirModalClassificacao = (conta) => {
    setContaSelecionada(conta);
    setDadosClassificacao({
      categoria_id: conta.categoria_id || null,
      dre_subcategoria_id: conta.dre_subcategoria_id || null,
      tipo_despesa_id: conta.tipo_despesa_id || null,
      canal: conta.canal || 'loja_fisica'
    });
    setMostrarModalClassificacao(true);
  };

  const salvarClassificacao = async () => {
    if (!contaSelecionada) return;
    try {
      const response = await api.patch(
        `/contas-pagar/${contaSelecionada.id}/classificacao?aplicar_fornecedor=true`,
        dadosClassificacao
      );
      setMostrarModalClassificacao(false);
      await carregarDados();

      const outrasAtualizadas = Number(response?.data?.fornecedor_atualizadas || 0);
      if (outrasAtualizadas > 0) {
        toast.success(`Classificação aplicada automaticamente em ${outrasAtualizadas + 1} lançamentos do fornecedor`);
      } else {
        toast.success('Classificação salva com sucesso');
      }
    } catch (error) {
      console.error('Erro ao classificar conta:', error);
      toast.error(error.response?.data?.detail || 'Erro ao classificar conta');
    }
  };

  const handleFormaChange = (formaId) => {
    const forma = formasPagamento.find(f => f.id === parseInt(formaId));
    setDadosPagamento({
      ...dadosPagamento,
      forma_pagamento_id: parseInt(formaId) || '',
      conta_bancaria_id: forma?.conta_bancaria_destino_id || dadosPagamento.conta_bancaria_id || ''
    });
  };
  const salvarNovaForma = async () => {
    try {
            await api.post(`/financeiro/formas-pagamento`, {
        ...novaFormaData,
        taxa_percentual: 0,
        taxa_fixa: 0,
        prazo_dias: 0,
        ativo: true,
        permite_parcelamento: false,
        parcelas_maximas: 1
      });
      toast.success('Forma de pagamento criada!');
      setMostrarModalNovaForma(false);
      setNovaFormaData({ nome: '', tipo: 'dinheiro', conta_bancaria_destino_id: null });
      carregarDados(); // Recarregar formas
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao criar forma de pagamento');
    }
  };

  const registrarPagamento = async () => {
    try {
            await api.post(
        `/contas-pagar/${contaSelecionada.id}/pagar`,
        dadosPagamento
      );
      
      toast.success('Pagamento registrado com sucesso!');
      setMostrarModalPagamento(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao registrar pagamento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao registrar pagamento');
    }
  };

  const formatarData = (data) => {
    if (!data) return '-';
    // Evita problemas de timezone ao criar data diretamente dos componentes
    const partes = data.split('T')[0].split('-');
    const dataLocal = new Date(parseInt(partes[0]), parseInt(partes[1]) - 1, parseInt(partes[2]));
    return dataLocal.toLocaleDateString('pt-BR');
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const getStatusBadge = (conta) => {
    const hoje = new Date();
    const vencimento = new Date(conta.data_vencimento);
    if (conta.status === 'pago') return <StatusBadge status="pago" />;
    if (vencimento < hoje) return <StatusBadge status="vencida" />;
    if (conta.status === 'parcial') return <StatusBadge status="parcial" />;
    return <StatusBadge status="pendente" />;
  };

  const getOrigemLabel = (conta) => {
    const origem = conta.origem_lancamento || 'manual';

    if (origem === 'caixa_pdv') {
      return conta.caixa_referencia ? `Caixa/PDV (${conta.caixa_referencia})` : 'Caixa/PDV';
    }

    if (origem === 'nota_entrada') {
      return 'Nota entrada';
    }

    return 'Manual';
  };

  const getDescricaoPrincipal = (conta) => {
    const descricao = String(conta.descricao || '-').trim();
    const nfMatch = descricao.match(/\bNF-e?\s+\d+/i);
    if (nfMatch) return nfMatch[0].replace(/\s+/g, ' ');
    return descricao;
  };

  const getContaTooltip = (conta) => {
    const linhas = [
      `Descricao: ${conta.descricao || '-'}`,
      conta.documento ? `Documento/NF: ${conta.documento}` : null,
      `Origem: ${getOrigemLabel(conta)}`,
      conta.tipo_despesa_nome ? `Tipo de despesa: ${conta.tipo_despesa_nome}` : null,
      conta.eh_parcelado ? `Parcela: ${conta.numero_parcela}/${conta.total_parcelas}` : null,
      conta.e_custo_fixo === true ? 'Tipo de custo: Fixo' : null,
      conta.e_custo_fixo === false ? 'Tipo de custo: Variavel' : null,
    ].filter(Boolean);

    return linhas.join('\n');
  };

  const tiposDespesaOrdenados = [...safeArray(tiposDespesa)].sort((a, b) =>
    String(a.nome || '').localeCompare(String(b.nome || ''), 'pt-BR', { sensitivity: 'base' })
  );

  const fornecedorFiltroSelecionado = safeArray(fornecedores).find(
    (fornecedor) => String(fornecedor.id) === String(filtros.fornecedor_id)
  );

  const getFornecedorNome = (fornecedor) =>
    fornecedor?.nome || fornecedor?.razao_social || fornecedor?.nome_fantasia || '';

  const contasPagarColumns = [
    {
      key: 'id',
      header: 'ID',
      render: (conta) => conta.id,
    },
    {
      key: 'descricao',
      header: 'Conta',
      className: 'w-[210px] max-w-[210px]',
      cellStyle: { width: 210, maxWidth: 210 },
      render: (conta) => (
        <div className="min-w-0 max-w-[210px]" title={getContaTooltip(conta)}>
          <div className="truncate text-sm font-semibold text-slate-900" title={getContaTooltip(conta)}>
            {getDescricaoPrincipal(conta)}
          </div>
          <div className="mt-1 flex flex-nowrap gap-1 overflow-hidden">
            {conta.eh_parcelado && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-700">
                {conta.numero_parcela}/{conta.total_parcelas}
              </span>
            )}
            {conta.e_custo_fixo === true && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded-full bg-orange-100 text-orange-700 font-semibold">Fixo</span>
            )}
            {conta.e_custo_fixo === false && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 font-semibold">Variavel</span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'fornecedor',
      header: 'Fornecedor',
      className: 'w-[220px] max-w-[220px]',
      cellStyle: { width: 220, maxWidth: 220 },
      render: (conta) => {
        const fornecedorNome = getFornecedorIdentityName(conta);
        return (
          <div className="max-w-[220px] truncate" title={fornecedorNome}>
            <FornecedorIdentity
              className="w-full max-w-[220px] truncate"
              copyable={false}
              fallback=""
              nameClassName="max-w-[220px] truncate font-medium text-slate-700"
              record={conta}
              showDocument={false}
            />
          </div>
        );
      },
    },
    {
      key: 'tipo',
      header: 'Tipo',
      render: (conta) => (
        conta.tipo_despesa_nome ? (
          <span className="inline-flex max-w-[150px] truncate px-2 py-1 text-xs rounded-full bg-slate-100 text-slate-700" title={conta.tipo_despesa_nome}>
            {conta.tipo_despesa_nome}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )
      ),
    },
    {
      key: 'vencimento',
      header: 'Vencimento',
      headerClassName: 'w-[110px] whitespace-nowrap',
      className: 'w-[110px] whitespace-nowrap',
      render: (conta) => formatarData(conta.data_vencimento),
    },
    {
      key: 'valor_original',
      header: 'Original',
      title: 'Valor original',
      align: 'right',
      headerClassName: 'w-[110px] whitespace-nowrap',
      className: 'w-[110px] whitespace-nowrap tabular-nums',
      render: (conta) => <MoneyCell value={conta.valor_original} />,
    },
    {
      key: 'valor_pago',
      header: 'Pago',
      title: 'Valor pago',
      align: 'right',
      headerClassName: 'w-[100px] whitespace-nowrap',
      className: 'w-[100px] whitespace-nowrap tabular-nums',
      render: (conta) => <MoneyCell value={conta.valor_pago} zeroAsDash />,
    },
    {
      key: 'saldo',
      header: 'Saldo',
      align: 'right',
      headerClassName: 'w-[100px] whitespace-nowrap',
      className: 'w-[100px] whitespace-nowrap tabular-nums font-bold',
      render: (conta) => <MoneyCell value={conta.valor_final - conta.valor_pago} zeroAsDash />,
    },
    {
      key: 'status',
      header: 'Status',
      render: getStatusBadge,
    },
    {
      key: 'acoes',
      header: 'Acoes',
      headerClassName: 'contas-pagar-actions-cell sticky right-0 z-20 w-[260px] min-w-[260px] bg-gray-50 text-right',
      className: 'contas-pagar-actions-cell sticky right-0 z-10 w-[260px] min-w-[260px] border-l border-slate-100 bg-white',
      render: (conta) => (
        <div className="flex flex-wrap items-center justify-end gap-2">
          <ActionButton
            intent="edit"
            tone="soft"
            size="xs"
            icon={Edit3}
            onClick={() => abrirModalEdicao(conta)}
            title="Editar conta a pagar"
          >
            Editar
          </ActionButton>
          {conta.status !== 'pago' && (
            <ActionButton
              intent="create"
              size="xs"
              onClick={() => abrirModalPagamento(conta)}
              title="Registrar Pagamento"
            >
              Pagar
            </ActionButton>
          )}
          {precisaClassificacao(conta) && (
            <ActionButton
              intent="warning"
              size="xs"
              onClick={() => abrirModalClassificacao(conta)}
              title="Classificar categoria, DRE e tipo da despesa"
            >
              Classificar
            </ActionButton>
          )}
          <ActionButton
            intent="delete"
            tone="soft"
            size="xs"
            icon={Trash2}
            onClick={() => excluirContaPagar(conta)}
            disabled={Number(conta.valor_pago || 0) > 0 || conta.status === 'pago'}
            title="Excluir conta sem pagamento"
          >
            Excluir
          </ActionButton>
        </div>
      ),
    },
  ];

  const handleFiltrosSubmit = (event) => {
    event.preventDefault();
  };

  if (loading) {
    return <LoadingState label="Carregando contas a pagar..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        actions={
          <ActionButton
            onClick={() => {
              setContaEdicao(null);
              setMostrarModalNovaConta(true);
            }}
            intent="create"
            size="md"
            icon={Plus}
          >
            Nova Conta
          </ActionButton>
        }
        className="mb-6"
        icon={Wallet}
        subtitle="Gerencie vencimentos, despesas e pagamentos"
        title="Contas a Pagar"
      />

      {/* Filtros */}
      <FilterBar className="mb-6" onSubmit={handleFiltrosSubmit}>
        <h5 className="text-lg font-semibold mb-4">🔍 Filtros</h5>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-1">Buscar</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Descrição, documento, NF, fornecedor..."
              value={filtros.busca}
              onChange={(e) => setFiltros({...filtros, busca: e.target.value})}
              onKeyDown={(e) => e.key === 'Enter' && aplicarFiltros()}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.status}
              onChange={(e) => setFiltros({...filtros, status: e.target.value})}
            >
              <option value="todos">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="pago">Pago</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Origem</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.origem}
              onChange={(e) => setFiltros({...filtros, origem: e.target.value})}
            >
              <option value="todos">Todas</option>
              <option value="caixa_pdv">Caixa/PDV</option>
              <option value="nota_entrada">Nota de entrada</option>
              <option value="manual">Manual/financeiro</option>
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-1">Fornecedor</label>
            <FornecedorSelector
              fornecedores={fornecedores}
              fornecedorId={filtros.fornecedor_id}
              fornecedorSelecionado={fornecedorFiltroSelecionado}
              showLabel={false}
              value={filtros.fornecedor_busca || ''}
              placeholder="Digite nome, fantasia, CPF ou CNPJ..."
              onInputChange={(termo) => setFiltros({
                ...filtros,
                fornecedor_busca: termo,
                fornecedor_id: null,
              })}
              onSelect={(fornecedor) => setFiltros({
                ...filtros,
                fornecedor_id: fornecedor?.id || null,
                fornecedor_busca: getFornecedorNome(fornecedor),
              })}
              onClear={() => setFiltros({
                ...filtros,
                fornecedor_id: null,
                fornecedor_busca: '',
              })}
              onFornecedorCriado={(fornecedor) => setFiltros({
                ...filtros,
                fornecedor_id: fornecedor?.id || null,
                fornecedor_busca: getFornecedorNome(fornecedor),
              })}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Tipo despesa</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.tipo_despesa_id || ''}
              onChange={(e) => setFiltros({...filtros, tipo_despesa_id: e.target.value})}
            >
              <option value="">Todos</option>
              {tiposDespesaOrdenados.map(t => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">NF/documento</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Ex: 12345"
              value={filtros.numero_nf}
              onChange={(e) => setFiltros({...filtros, numero_nf: e.target.value})}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Tipo de custo</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.tipo_custo}
              onChange={(e) => setFiltros({...filtros, tipo_custo: e.target.value})}
            >
              <option value="todos">Todos</option>
              <option value="fixo">So fixos</option>
              <option value="variavel">Só variáveis</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data usada</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_campo}
              onChange={(e) => setFiltros({...filtros, data_campo: e.target.value})}
            >
              <option value="vencimento">Vencimento</option>
              <option value="pagamento">Pagamento</option>
              <option value="emissao">Emissão</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data início</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({...filtros, data_inicio: e.target.value, periodo_rapido: ''})}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data fim</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({...filtros, data_fim: e.target.value, periodo_rapido: ''})}
            />
          </div>

          <div className="md:col-span-4">
            <label className="block text-sm font-medium mb-1">Periodo rapido</label>
            <div className="flex flex-wrap gap-2">
              {PERIODOS_RAPIDOS_CONTAS_PAGAR.map((periodo) => {
                const ativo = filtros.periodo_rapido === periodo.value;

                return (
                  <button
                    key={periodo.value}
                    type="button"
                    onClick={() => aplicarPeriodoRapido(periodo.value)}
                    className={`rounded-md border px-3 py-2 text-sm font-semibold transition ${
                      ativo
                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-blue-400 hover:text-blue-700'
                    }`}
                  >
                    {periodo.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="md:col-span-3 flex items-end gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencidas}
                onChange={(e) => setFiltros({...filtros, apenas_vencidas: e.target.checked, apenas_vencer: false})}
              />
              <span className="text-sm">Só vencidas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencer}
                onChange={(e) => setFiltros({...filtros, apenas_vencer: e.target.checked, apenas_vencidas: false})}
              />
              <span className="text-sm">A vencer</span>
            </label>
          </div>

          <div className="md:col-span-5 flex flex-wrap items-end justify-end gap-2">
            <ActionButton
              intent="warning"
              tone="soft"
              size="sm"
              onClick={filtrarDespesasCaixa}
              type="button"
            >
              Despesas do caixa
            </ActionButton>
            <ActionButton
              intent="neutral"
              tone="soft"
              size="sm"
              onClick={limparFiltros}
              type="button"
            >
              Limpar
            </ActionButton>
            <ActionButton
              intent="neutral"
              tone="solid"
              size="sm"
              onClick={() => aplicarFiltros()}
              type="button"
            >
              Filtrar
            </ActionButton>
          </div>
        </div>
      </FilterBar>

      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <DataTable
          columns={contasPagarColumns}
          data={safeArray(contas)}
          emptyMessage="Nenhuma conta encontrada"
          getRowKey={(conta) => conta.id}
          tableClassName="min-w-[1280px]"
          theadClassName="bg-gray-50"
          tbodyClassName="divide-y divide-gray-200"
        />

        {contas.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contas.length} conta(s) | 
            <strong className="ml-3">Saldo a Pagar:</strong>{" "}
            <MoneyCell value={contas.reduce((sum, c) => sum + (c.valor_final - c.valor_pago), 0)} zeroAsDash />
          </div>
        )}
      </div>

      {/* Modal de Pagamento */}
      {mostrarModalPagamento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">💰 Registrar Pagamento</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar modal de pagamento"
                onClick={() => setMostrarModalPagamento(false)}
              />
            </div>
            
            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}<br/>
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}<br/>
                <strong>Já Pago:</strong> {formatarMoeda(contaSelecionada.valor_pago)}<br/>
                <strong>Saldo Restante:</strong> {formatarMoeda(contaSelecionada.valor_final - contaSelecionada.valor_pago)}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Valor a Pagar *</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_pago}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_pago: parseFloat(e.target.value)})}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Data do Pagamento *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.data_pagamento}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, data_pagamento: e.target.value})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Forma de Pagamento</label>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 border border-gray-300 rounded px-3 py-2"
                      value={dadosPagamento.forma_pagamento_id || ''}
                      onChange={(e) => handleFormaChange(e.target.value)}
                    >
                      <option value="">Selecione...</option>
                      {safeArray(formasPagamento).map(f => (
                        <option key={f.id} value={f.id}>{f.icone || '💳'} {f.nome}</option>
                      ))}
                    </select>
                    <ActionButton
                      type="button"
                      onClick={() => setMostrarModalNovaForma(true)}
                      title="Adicionar nova forma de pagamento"
                      intent="create"
                      size="sm"
                      icon={Plus}
                    >
                      Nova
                    </ActionButton>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Conta Bancária * 
                    {dadosPagamento.forma_pagamento_id && formasPagamento.find(f => f.id === dadosPagamento.forma_pagamento_id)?.conta_bancaria_destino_id && (
                      <span className="text-xs text-gray-500 ml-2">(Padrão da forma selecionada)</span>
                    )}
                  </label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosPagamento.conta_bancaria_id || ''}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, conta_bancaria_id: parseInt(e.target.value) || null})}
                  >
                    <option value="">Selecione a conta...</option>
                    {safeArray(contasBancarias).map(c => (
                      <option key={c.id} value={c.id}>
                        {c.nome} - {formatarMoeda(c.saldo_atual || 0)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Juros</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_juros}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_juros: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Multa</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_multa}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_multa: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Desconto</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosPagamento.valor_desconto}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, valor_desconto: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Observações</label>
                  <textarea
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    rows="3"
                    value={dadosPagamento.observacoes}
                    onChange={(e) => setDadosPagamento({...dadosPagamento, observacoes: e.target.value})}
                  />
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded p-3 mt-4">
                <strong>Valor Final do Pagamento:</strong> {formatarMoeda(
                  (dadosPagamento.valor_pago || 0) +
                  (dadosPagamento.valor_juros || 0) +
                  (dadosPagamento.valor_multa || 0) -
                  (dadosPagamento.valor_desconto || 0)
                )}
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalPagamento(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                intent="create"
                size="md"
                onClick={registrarPagamento}
              >
                Confirmar Pagamento
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nova Forma Rápida */}
      {mostrarModalNovaForma && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="bg-green-600 text-white px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-semibold">Nova Forma de Pagamento</h3>
              <ActionButton
                onClick={() => setMostrarModalNovaForma(false)}
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                className="text-white hover:bg-green-700"
                aria-label="Fechar nova forma de pagamento"
              />
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nome *</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.nome}
                  onChange={(e) => setNovaFormaData({...novaFormaData, nome: e.target.value})}
                  placeholder="Ex: PIX Santander, Dinheiro..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Tipo</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.tipo}
                  onChange={(e) => setNovaFormaData({...novaFormaData, tipo: e.target.value})}
                >
                  <option value="dinheiro">💵 Dinheiro</option>
                  <option value="pix">📱 PIX</option>
                  <option value="cartao_debito">💳 Cartão Débito</option>
                  <option value="cartao_credito">💳 Cartão Crédito</option>
                  <option value="transferencia">🏦 Transferência</option>
                  <option value="boleto">📄 Boleto</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Conta Bancária Padrão</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={novaFormaData.conta_bancaria_destino_id || ''}
                  onChange={(e) => setNovaFormaData({...novaFormaData, conta_bancaria_destino_id: parseInt(e.target.value) || null})}
                >
                  <option value="">Nenhuma (selecionar manualmente)</option>
                  {safeArray(contasBancarias).map(c => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Esta conta será pré-selecionada automaticamente ao usar esta forma
                </p>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalNovaForma(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                intent="create"
                size="md"
                onClick={salvarNovaForma}
              >
                Criar
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* Modal Classificacao */}
      {mostrarModalClassificacao && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">🏷 Classificar Conta #{contaSelecionada.id}</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar classificação"
                onClick={() => setMostrarModalClassificacao(false)}
              />
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Categoria Financeira</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.categoria_id || ''}
                  onChange={(e) => setDadosClassificacao({ ...dadosClassificacao, categoria_id: e.target.value ? parseInt(e.target.value, 10) : null, dre_subcategoria_id: null })}
                >
                  <option value="">Selecione...</option>
                  {safeArray(categoriasFinanceiras).map((c) => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Subcategoria DRE</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.dre_subcategoria_id || ''}
                  onChange={(e) => setDadosClassificacao({ ...dadosClassificacao, dre_subcategoria_id: e.target.value ? parseInt(e.target.value, 10) : null })}
                >
                  <option value="">Selecione...</option>
                  {safeArray(subcategoriasDre).filter(s => s.categoria_financeira_id === dadosClassificacao.categoria_id).map((s) => (
                    <option key={s.id} value={s.id}>{s.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Tipo de despesa</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.tipo_despesa_id || ''}
                  onChange={(e) => setDadosClassificacao({ ...dadosClassificacao, tipo_despesa_id: e.target.value ? parseInt(e.target.value, 10) : null })}
                >
                  <option value="">Selecione...</option>
                  {tiposDespesaOrdenados.map((t) => (
                    <option key={t.id} value={t.id}>{t.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Canal</label>
                <select
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  value={dadosClassificacao.canal || 'loja_fisica'}
                  onChange={(e) => setDadosClassificacao({ ...dadosClassificacao, canal: e.target.value })}
                >
                  <option value="loja_fisica">Loja Física</option>
                  <option value="mercado_livre">Mercado Livre</option>
                  <option value="shopee">Shopee</option>
                  <option value="amazon">Amazon</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalClassificacao(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                intent="warning"
                size="md"
                onClick={salvarClassificacao}
              >
                Salvar Classificação
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {modalExclusaoRecorrencia.aberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <div>
                <h5 className="text-xl font-bold">Lançamentos da recorrência</h5>
                <p className="text-sm text-gray-500">
                  Selecione quais lançamentos sem pagamento devem ser excluídos.
                </p>
              </div>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar exclusao de recorrencia"
                onClick={() => {
                  setModalExclusaoRecorrencia({
                    aberto: false,
                    conta: null,
                    itens: [],
                    loading: false,
                  });
                  setRecorrenciasSelecionadasExclusao([]);
                }}
              />
            </div>

            <div className="max-h-[60vh] overflow-y-auto p-4">
              {modalExclusaoRecorrencia.loading ? (
                <p className="py-8 text-center text-gray-500">Carregando lançamentos...</p>
              ) : (
                <div className="space-y-2">
                  {safeArray(modalExclusaoRecorrencia.itens).map((item) => {
                    const selecionado = recorrenciasSelecionadasExclusao.includes(item.id);
                    return (
                      <label
                        key={item.id}
                        className={`flex items-center gap-3 rounded-lg border p-3 ${
                          item.pode_excluir ? 'border-gray-200 bg-white' : 'border-gray-100 bg-gray-50 opacity-70'
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={!item.pode_excluir}
                          checked={selecionado}
                          onChange={() => alternarRecorrenciaExclusao(item.id)}
                          className="h-4 w-4"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-gray-900">#{item.id}</span>
                            {item.eh_origem && (
                              <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">
                                Origem
                              </span>
                            )}
                            <span className="text-sm text-gray-500">{formatarData(item.data_vencimento)}</span>
                            <span className="text-sm font-semibold text-gray-900">
                              {formatarMoeda(item.valor_final)}
                            </span>
                          </div>
                          <p className="mt-1 truncate text-sm text-gray-700" title={item.descricao}>
                            {item.descricao}
                          </p>
                          {item.motivo_bloqueio && (
                            <p className="mt-1 text-xs text-red-600">{item.motivo_bloqueio}</p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t p-4 md:flex-row md:items-center md:justify-between">
              <p className="text-sm text-gray-500">
                {recorrenciasSelecionadasExclusao.length} lançamento(s) selecionado(s)
              </p>
              <div className="flex justify-end gap-3">
                <ActionButton
                  intent="neutral"
                  tone="soft"
                  size="md"
                  onClick={() => {
                    setModalExclusaoRecorrencia({
                      aberto: false,
                      conta: null,
                      itens: [],
                      loading: false,
                    });
                    setRecorrenciasSelecionadasExclusao([]);
                  }}
                >
                  Cancelar
                </ActionButton>
                <ActionButton
                  intent="delete"
                  size="md"
                  icon={Trash2}
                  disabled={recorrenciasSelecionadasExclusao.length === 0}
                  onClick={confirmarExclusaoRecorrencia}
                >
                  Excluir selecionados
                </ActionButton>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nova Conta */}
      <ModalNovaContaPagar
        isOpen={mostrarModalNovaConta}
        contaEdicao={contaEdicao}
        onClose={() => {
          setMostrarModalNovaConta(false);
          setContaEdicao(null);
        }}
        onSave={carregarDados}
      />
    </div>
  );
};

export default ContasPagar;
