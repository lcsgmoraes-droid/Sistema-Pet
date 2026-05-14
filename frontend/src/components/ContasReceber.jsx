import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDownUp, Plus, Receipt, X } from 'lucide-react';
import api from '../api';
import { getAccessToken } from '../auth/tokenStorage';
import { toast } from 'react-hot-toast';
import { safeArray } from '../utils/safeArray';
import ActionButton from './ui/ActionButton';
import CustomerIdentity from './ui/CustomerIdentity';
import DataTable from './ui/DataTable';
import FilterBar from './ui/FilterBar';
import LoadingState from './ui/LoadingState';
import MoneyCell, { formatMoneyCellValue } from './ui/MoneyCell';
import PageHeader from './ui/PageHeader';
import StatusBadge from './ui/StatusBadge';

const ContasReceber = () => {
  const navigate = useNavigate();
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    status: 'todos',
    cliente_id: null,
    data_inicio: '',
    data_fim: '',
    apenas_vencidas: false,
    apenas_vencer: false
  });
  
  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState('');
  const [ordenacao, setOrdenacao] = useState('desc'); // 'asc' = mais antiga primeiro, 'desc' = mais nova primeiro
  
  const [clientes, setClientes] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [detalhesCompletos, setDetalhesCompletos] = useState(null);
  const [mostrarModalRecebimento, setMostrarModalRecebimento] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  
  const [dadosRecebimento, setDadosRecebimento] = useState({
    valor_recebido: 0,
    data_recebimento: new Date().toISOString().split('T')[0],
    forma_pagamento_id: null,
    conta_bancaria_id: null,
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: ''
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarFormasPagamento = async (headers) => {
    const response = await api.get('/comissoes/formas-pagamento', { headers });
    const lista = response.data?.formas || [];
    return safeArray(lista).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.nome?.toLowerCase()?.replace(/\s+/g, '_') || 'outro',
      icone: '💳',
      conta_bancaria_destino_id: null,
    }));
  };

  // Aplicar filtro automaticamente quando buscaNumeroVenda mudar
  useEffect(() => {
    if (buscaNumeroVenda.trim().length > 0) {
      const timer = setTimeout(() => {
        aplicarFiltros();
      }, 500);  // Debounce de 500ms
      return () => clearTimeout(timer);
    } else if (buscaNumeroVenda === '') {
      // Se limpar o campo, recarregar tudo
      carregarDados();
    }
  }, [buscaNumeroVenda]);

  const carregarDados = async () => {
    try {
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };
      
      const [contasRes, clientesRes, formasRes, bancariasRes] = await Promise.allSettled([
        api.get(`/contas-receber/`, { headers }),
        api.get(`/clientes/`, { headers }),
        carregarFormasPagamento(headers),
        api.get(`/contas-bancarias?apenas_ativas=true`, { headers })
      ]);

      if (contasRes.status !== 'fulfilled') throw contasRes.reason;
      if (clientesRes.status !== 'fulfilled') throw clientesRes.reason;
      if (bancariasRes.status !== 'fulfilled') throw bancariasRes.reason;

      // Ordenar por ID (mais recentes primeiro por padrao)
      const contasOrdenadas = [...safeArray(contasRes.value.data)].sort((a, b) => b.id - a.id);
      setContas(contasOrdenadas);
      setClientes(safeArray(clientesRes.value.data));

      if (formasRes.status === 'fulfilled') {
        setFormasPagamento(safeArray(formasRes.value));
      } else {
        setFormasPagamento([]);
        console.warn('Nao foi possivel carregar formas de pagamento. Usando lista vazia.');
      }

      setContasBancarias(safeArray(bancariasRes.value.data));
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar contas a receber');
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = async () => {
    try {
      setLoading(true);
            const params = new URLSearchParams();
      if (filtros.status !== 'todos') params.append('status', filtros.status);
      if (filtros.cliente_id) params.append('cliente_id', filtros.cliente_id);
      if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
      if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
      if (filtros.apenas_vencidas) params.append('apenas_vencidas', 'true');
      if (filtros.apenas_vencer) params.append('apenas_vencer', 'true');
      if (buscaNumeroVenda) params.append('numero_venda', buscaNumeroVenda);  // Filtro pelo backend
      
      const response = await api.get(`/contas-receber/?${params}`);
      
      setContas(response.data);
    } catch (error) {
      console.error('Erro ao filtrar:', error);
      toast.error('Erro ao aplicar filtros');
    } finally {
      setLoading(false);
    }
  };

  const abrirVendaNoPDV = (vendaId) => {
    // Armazena ID da venda para abrir automaticamente no PDV
    sessionStorage.setItem('abrirVenda', vendaId);
    sessionStorage.setItem('abrirModalPagamento', 'true');
    toast.success('Redirecionando para o PDV...');
    navigate('/pdv');
  };

  const abrirFluxoDeCaixa = (conta) => {
    // Redireciona para o fluxo de caixa com filtros da conta
    const params = new URLSearchParams();
    if (conta.cliente_nome) {
      params.append('busca', conta.cliente_nome);
    }
    if (conta.documento) {
      params.append('documento', conta.documento);
    }
    navigate(`/financeiro/fluxo-caixa?${params.toString()}`);
    toast.success('Redirecionando para o Fluxo de Caixa...');
  };

  const alternarOrdenacao = () => {
    const novaOrdenacao = ordenacao === 'desc' ? 'asc' : 'desc';
    setOrdenacao(novaOrdenacao);
    
    const contasOrdenadas = [...contas].sort((a, b) => {
      if (novaOrdenacao === 'desc') {
        return b.id - a.id; // Mais nova primeiro
      } else {
        return a.id - b.id; // Mais antiga primeiro
      }
    });
    
    setContas(contasOrdenadas);
    toast.success(novaOrdenacao === 'desc' ? 'Ordenado: mais recentes primeiro' : 'Ordenado: mais antigas primeiro');
  };

  const abrirModalRecebimento = (conta) => {
    setContaSelecionada(conta);
    setDadosRecebimento({
      valor_recebido: parseFloat((conta.valor_final - conta.valor_recebido).toFixed(2)),
      data_recebimento: new Date().toISOString().split('T')[0],
      forma_pagamento_id: conta.forma_pagamento_id || null,
      conta_bancaria_id: null,
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: ''
    });
    setMostrarModalRecebimento(true);
  };

  const abrirDetalhes = async (conta) => {
    try {
            const response = await api.get(`/contas-receber/${conta.id}`);
      
      setContaSelecionada(conta);
      setDetalhesCompletos(response.data);
      setMostrarDetalhes(true);
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      toast.error('Erro ao carregar detalhes da conta');
    }
  };

  const abrirVenda = (vendaId) => {
    // Navegar para o PDV com a venda
    navigate(`/pdv?venda=${vendaId}`);
  };

  const registrarRecebimento = async () => {
    try {
            await api.post(
        `/contas-receber/${contaSelecionada.id}/receber`,
        dadosRecebimento
      );
      
      toast.success('Recebimento registrado com sucesso!');
      setMostrarModalRecebimento(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao registrar recebimento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao registrar recebimento');
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
    if (conta.status === 'recebido') return <StatusBadge status="recebido" />;
    if (vencimento < hoje) return <StatusBadge status="vencida" />;
    if (conta.status === 'parcial') return <StatusBadge status="parcial" />;
    return <StatusBadge status="pendente" />;
  };

  const contasReceberExibidas = safeArray(contas).filter((conta) => {
    if (!buscaNumeroVenda) return true;

    const numeroVenda = String(conta.numero_venda || '');
    const descricao = String(conta.descricao || '');
    const busca = buscaNumeroVenda.toLowerCase();

    return numeroVenda.toLowerCase().includes(busca)
      || descricao.toLowerCase().includes(busca);
  });

  const contasReceberColumns = [
    {
      key: 'id',
      header: 'ID',
      render: (conta) => conta.id,
    },
    {
      key: 'descricao',
      header: 'Descricao',
      className: 'min-w-[220px]',
      render: (conta) => (
        <div>
          {conta.descricao}
          {conta.eh_parcelado && (
            <span className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
              {conta.numero_parcela}/{conta.total_parcelas}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'cliente',
      header: 'Cliente',
      className: 'min-w-[160px]',
      render: (conta) => (
        <CustomerIdentity
          fallback=""
          nameClassName="font-medium text-slate-800"
          record={conta}
        />
      ),
    },
    {
      key: 'vencimento',
      header: 'Vencimento',
      render: (conta) => formatarData(conta.data_vencimento),
    },
    {
      key: 'valor_original',
      header: 'Valor Original',
      align: 'right',
      render: (conta) => <MoneyCell value={conta.valor_original} />,
    },
    {
      key: 'valor_recebido',
      header: 'Valor Recebido',
      align: 'right',
      render: (conta) => <MoneyCell value={conta.valor_recebido} zeroAsDash />,
    },
    {
      key: 'saldo',
      header: 'Saldo',
      align: 'right',
      className: 'font-bold',
      render: (conta) => <MoneyCell value={conta.valor_final - conta.valor_recebido} zeroAsDash />,
    },
    {
      key: 'status',
      header: 'Status',
      render: getStatusBadge,
    },
    {
      key: 'acoes',
      header: 'Acoes',
      className: 'min-w-[230px]',
      render: (conta) => (
        <div className="flex flex-wrap items-center gap-2">
          {conta.status !== 'recebido' && (
            <>
              {conta.nsu && !conta.conciliado ? (
                <>
                  <ActionButton
                    intent="warning"
                    size="xs"
                    onClick={() => navigate(`/conciliacao-cartao?nsu=${conta.nsu}`)}
                    title={`Conciliar NSU ${conta.nsu} com extrato da operadora`}
                  >
                    Conciliar
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (caso nao consiga conciliar)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : conta.venda_id && !conta.nsu ? (
                <>
                  <ActionButton
                    intent="neutral"
                    size="xs"
                    onClick={() => {
                      if (conta.venda_id) {
                        abrirVendaNoPDV(conta.venda_id);
                      } else {
                        abrirModalRecebimento(conta);
                      }
                    }}
                    title="Receber no PDV (movimenta caixa)"
                  >
                    PDV
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (sem PDV)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : (
                <ActionButton
                  intent="create"
                  size="xs"
                  onClick={() => abrirModalRecebimento(conta)}
                  title="Registrar recebimento manual"
                >
                  Receber Manual
                </ActionButton>
              )}
            </>
          )}
          {conta.conciliado && (
            <span className="text-xs text-green-600 font-semibold" title={`Conciliado em ${conta.data_conciliacao}`}>
              Conciliado
            </span>
          )}
          <ActionButton
            intent="neutral"
            tone="soft"
            size="xs"
            title="Ver Detalhes"
            onClick={() => abrirDetalhes(conta)}
          >
            Ver
          </ActionButton>
        </div>
      ),
    },
  ];

  const handleFiltrosSubmit = (event) => {
    event.preventDefault();
  };

  if (loading) {
    return <LoadingState label="Carregando contas a receber..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              onClick={alternarOrdenacao}
              intent="neutral"
              tone="soft"
              size="md"
              icon={ArrowDownUp}
              title={ordenacao === 'desc' ? 'Clique para ver mais antigas primeiro' : 'Clique para ver mais recentes primeiro'}
            >
              {ordenacao === 'desc' ? 'Mais recentes' : 'Mais antigas'}
            </ActionButton>
            <ActionButton intent="create" size="md" icon={Plus}>
              Nova Conta
            </ActionButton>
          </>
        }
        className="mb-6"
        icon={Receipt}
        subtitle="Acompanhe recebimentos, vencimentos e saldos"
        title="Contas a Receber"
      />

      {/* Filtros */}
      <FilterBar className="mb-6" onSubmit={handleFiltrosSubmit}>
        <h5 className="text-lg font-semibold mb-4">Filtros</h5>
        
        {/* Campo de busca por numero de venda */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Buscar por Numero da Venda</label>
          <input
            type="text"
            placeholder="Digite o numero da venda (ex: 202601100003) e pressione Enter"
            className="w-full border border-gray-300 rounded px-3 py-2"
            value={buscaNumeroVenda}
            onChange={(e) => {
              // Remove # automaticamente
              const valor = e.target.value.replace('#', '');
              setBuscaNumeroVenda(valor);
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                aplicarFiltros();
              }
            }}
          />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.status}
              onChange={(e) => setFiltros({...filtros, status: e.target.value})}
            >
              <option value="todos">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="recebido">Recebido</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Cliente</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.cliente_id || ''}
              onChange={(e) => setFiltros({...filtros, cliente_id: e.target.value || null})}
            >
              <option value="">Todos</option>
              {safeArray(clientes).map(c => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Inicio</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({...filtros, data_inicio: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Fim</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({...filtros, data_fim: e.target.value})}
            />
          </div>

          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencidas}
                onChange={(e) => setFiltros({...filtros, apenas_vencidas: e.target.checked, apenas_vencer: false})}
              />
              <span className="text-sm">So Vencidas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencer}
                onChange={(e) => setFiltros({...filtros, apenas_vencer: e.target.checked, apenas_vencidas: false})}
              />
              <span className="text-sm">A Vencer</span>
            </label>
            <ActionButton
              intent="neutral"
              tone="solid"
              size="sm"
              onClick={aplicarFiltros}
            >
              Filtrar
            </ActionButton>
          </div>
        </div>
      </FilterBar>

      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <DataTable
          columns={contasReceberColumns}
          data={contasReceberExibidas}
          emptyMessage="Nenhuma conta encontrada"
          getRowKey={(conta) => conta.id}
          tableClassName="min-w-[960px]"
          theadClassName="bg-gray-50"
          tbodyClassName="divide-y divide-gray-200"
        />
        
        {contasReceberExibidas.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contasReceberExibidas.length} conta(s) |
            <strong className="ml-3">Saldo a Receber:</strong>{" "}
            <MoneyCell value={contasReceberExibidas.reduce((sum, c) => sum + (c.valor_final - c.valor_recebido), 0)} zeroAsDash />
          </div>
        )}
      </div>

      {/* Modal de Recebimento */}
      {mostrarModalRecebimento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">Registrar Recebimento</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar recebimento"
                onClick={() => setMostrarModalRecebimento(false)}
              />
            </div>
            
            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}<br/>
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}<br/>
                <strong>Ja Recebido:</strong> {formatarMoeda(contaSelecionada.valor_recebido)}<br/>
                <strong>Saldo Restante:</strong> {formatarMoeda(contaSelecionada.valor_final - contaSelecionada.valor_recebido)}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Valor a Receber *</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_recebido}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, valor_recebido: parseFloat(e.target.value)})}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Data do Recebimento *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.data_recebimento}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, data_recebimento: e.target.value})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Forma de Pagamento</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.forma_pagamento_id || ''}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, forma_pagamento_id: parseInt(e.target.value) || null})}
                  >
                    <option value="">Selecione...</option>
                    {safeArray(formasPagamento).map(f => (
                      <option key={f.id} value={f.id}>{f.nome}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Conta Bancaria *</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.conta_bancaria_id || ''}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, conta_bancaria_id: parseInt(e.target.value) || null})}
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
                    value={dadosRecebimento.valor_juros}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, valor_juros: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Multa</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_multa}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, valor_multa: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Desconto</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_desconto}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, valor_desconto: parseFloat(e.target.value) || 0})}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Observacoes</label>
                  <textarea
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    rows="3"
                    value={dadosRecebimento.observacoes}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, observacoes: e.target.value})}
                  />
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded p-3 mt-4">
                <strong>Valor Final do Recebimento:</strong> {formatarMoeda(
                  (dadosRecebimento.valor_recebido || 0) +
                  (dadosRecebimento.valor_juros || 0) +
                  (dadosRecebimento.valor_multa || 0) -
                  (dadosRecebimento.valor_desconto || 0)
                )}
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalRecebimento(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                intent="create"
                size="md"
                onClick={registrarRecebimento}
              >
                Confirmar Recebimento
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* Modal Detalhes */}
      {mostrarDetalhes && contaSelecionada && detalhesCompletos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">Detalhes da Conta</h3>
              <ActionButton
                onClick={() => setMostrarDetalhes(false)}
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                className="text-white hover:bg-blue-700"
                aria-label="Fechar detalhes"
              />
            </div>
            
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Numero da Conta</label>
                  <p className="mt-1 text-lg">{contaSelecionada.numero_documento || 'N/A'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cliente</label>
                  <p className="mt-1 text-lg">
                    <CustomerIdentity
                      code={detalhesCompletos.cliente?.codigo || detalhesCompletos.cliente_id || detalhesCompletos.cliente?.id}
                      customer={detalhesCompletos.cliente}
                      fallback="N/A"
                    />
                  </p>
                </div>
              </div>

              {/* Numero do Pedido - Clicavel */}
              {detalhesCompletos.venda && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Pedido/Venda</label>
                  <div className="flex gap-2">
                    <ActionButton
                      onClick={() => abrirVenda(detalhesCompletos.venda.id)}
                      intent="edit"
                      tone="soft"
                      size="md"
                      className="flex-1"
                    >
                      <span className="text-xl">Venda</span>
                      <span className="font-semibold">{detalhesCompletos.venda.numero_venda}</span>
                    </ActionButton>
                    <ActionButton
                      onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                      intent="create"
                      tone="soft"
                      size="md"
                      title="Ver no Fluxo de Caixa"
                    >
                      <span className="text-xl">Fluxo</span>
                      <span className="text-sm">Fluxo</span>
                    </ActionButton>
                  </div>
                </div>
              )}

              {!detalhesCompletos.venda && (
                <div>
                  <ActionButton
                    onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                    intent="create"
                    tone="soft"
                    size="md"
                    className="w-full"
                  >
                    <span className="text-xl">Fluxo</span>
                    <span className="font-medium">Ver no Fluxo de Caixa</span>
                  </ActionButton>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Emissao</label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.emissao)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Vencimento</label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.vencimento)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Original</label>
                  <p className="mt-1 text-lg font-semibold text-blue-600">{formatarMoeda(detalhesCompletos.valores.final)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Recebido</label>
                  <p className="mt-1 text-lg font-semibold text-green-600">{formatarMoeda(detalhesCompletos.valores.recebido)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Saldo Restante</label>
                  <p className="mt-1 text-lg font-semibold text-red-600">
                    {formatarMoeda(detalhesCompletos.valores.saldo)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <p className="mt-1">
                    <StatusBadge status={detalhesCompletos.status} />
                  </p>
                </div>
              </div>

              {/* Recebimentos com Conta Bancaria */}
              {detalhesCompletos.recebimentos && detalhesCompletos.recebimentos.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Historico de Recebimentos</label>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <DataTable
                      columns={[
                        {
                          key: 'data',
                          header: 'Data',
                          render: (recebimento) => formatarData(recebimento.data),
                        },
                        {
                          key: 'valor',
                          header: 'Valor',
                          align: 'right',
                          className: 'font-semibold text-green-600',
                          render: (recebimento) => <MoneyCell value={recebimento.valor} zeroAsDash />,
                        },
                        {
                          key: 'conta',
                          header: 'Conta Bancaria',
                          render: (recebimento) => (
                            recebimento.conta_bancaria_nome ? (
                              <span className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">
                                {recebimento.conta_bancaria_nome}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">Nao informada</span>
                            )
                          ),
                        },
                      ]}
                      data={safeArray(detalhesCompletos?.recebimentos)}
                      getRowKey={(recebimento, index) => recebimento.id || index}
                      tableClassName="w-full"
                      theadClassName="bg-gray-50"
                      tbodyClassName="divide-y divide-gray-200"
                    />
                  </div>
                </div>
              )}

              {detalhesCompletos.observacoes && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observacoes</label>
                  <p className="mt-1 text-gray-600">{detalhesCompletos.observacoes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContasReceber;

