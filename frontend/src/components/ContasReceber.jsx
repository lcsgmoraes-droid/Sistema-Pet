import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';

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
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      
      const [contasRes, clientesRes, formasRes, bancariasRes] = await Promise.all([
        api.get(`/contas-receber/`, { headers }),
        api.get(`/clientes/`, { headers }),
        api.get(`/financeiro/formas-pagamento/`, { headers }),
        api.get(`/api/contas-bancarias?apenas_ativas=true`, { headers })
      ]);
      
      console.log('📊 Contas carregadas:', contasRes.data.length, 'contas');
      console.log('📋 Status das contas:', contasRes.data.map(c => ({ id: c.id, status: c.status, descricao: c.descricao })));
      console.log('� Todas as vendas nos contas:', contasRes.data.map(c => c.numero_venda).filter(n => n));
      console.log('🎯 Procurando venda 202601100007:', contasRes.data.find(c => c.numero_venda === '202601100007' || c.descricao?.includes('202601100007')));
      console.log('�📦 Antes de setContas:', contasRes.data);
      // Ordenar por ID (mais recentes primeiro por padrão)
      const contasOrdenadas = [...contasRes.data].sort((a, b) => b.id - a.id);
      setContas(contasOrdenadas);
      console.log('✅ Contas setadas no estado');
      setClientes(clientesRes.data);
      setClientes(clientesRes.data);
      setFormasPagamento(formasRes.data);
      setContasBancarias(bancariasRes.data);
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
    toast.success(novaOrdenacao === 'desc' ? '📅 Ordenado: Mais recentes primeiro' : '📅 Ordenado: Mais antigas primeiro');
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
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const getStatusBadge = (conta) => {
    const hoje = new Date();
    const vencimento = new Date(conta.data_vencimento);
    
    if (conta.status === 'recebido') {
      return <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">✓ Recebido</span>;
    }
    
    if (vencimento < hoje) {
      return <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">⚠ Vencida</span>;
    }
    
    if (conta.status === 'parcial') {
      return <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">⚡ Parcial</span>;
    }
    
    return <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">⏱ Pendente</span>;
  };

  if (loading) {
    return <div className="text-center p-8">Carregando contas a receber...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">💵 Contas a Receber</h2>
        <div className="flex gap-2">
          <button 
            onClick={alternarOrdenacao}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            title={ordenacao === 'desc' ? 'Clique para ver mais antigas primeiro' : 'Clique para ver mais recentes primeiro'}
          >
            {ordenacao === 'desc' ? '🔽 Mais Recentes' : '🔼 Mais Antigas'}
          </button>
          <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg">
            ➕ Nova Conta
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h5 className="text-lg font-semibold mb-4">🔍 Filtros</h5>
        
        {/* Campo de busca por número de venda */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">🔢 Buscar por Número da Venda</label>
          <input
            type="text"
            placeholder="Digite o número da venda (ex: 202601100003) e pressione Enter"
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
              {clientes.map(c => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Início</label>
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
              <span className="text-sm">Só Vencidas</span>
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
            <button 
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
              onClick={aplicarFiltros}
            >
              Filtrar
            </button>
          </div>
        </div>
      </div>

      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Descrição</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Cliente</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Vencimento</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Valor Original</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Valor Recebido</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Saldo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {contas.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-gray-500">
                    Nenhuma conta encontrada
                  </td>
                </tr>
              ) : (
                contas
                  .filter(conta => {
                    // Filtro local por número de venda
                    if (!buscaNumeroVenda) return true;
                    
                    // Busca no número da venda se existir - converter para string
                    const numeroVenda = String(conta.numero_venda || '');
                    const descricao = String(conta.descricao || '');
                    const busca = buscaNumeroVenda.toLowerCase();
                    
                    return numeroVenda.toLowerCase().includes(busca) || 
                           descricao.toLowerCase().includes(busca);
                  })
                  .map(conta => (
                  <tr key={conta.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{conta.id}</td>
                    <td className="px-4 py-3 text-sm">
                      {conta.descricao}
                      {conta.eh_parcelado && (
                        <span className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
                          {conta.numero_parcela}/{conta.total_parcelas}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{conta.cliente_nome || '-'}</td>
                    <td className="px-4 py-3 text-sm">{formatarData(conta.data_vencimento)}</td>
                    <td className="px-4 py-3 text-sm">{formatarMoeda(conta.valor_original)}</td>
                    <td className="px-4 py-3 text-sm">{formatarMoeda(conta.valor_recebido)}</td>
                    <td className="px-4 py-3 text-sm font-bold">{formatarMoeda(conta.valor_final - conta.valor_recebido)}</td>
                    <td className="px-4 py-3 text-sm">{getStatusBadge(conta)}</td>
                    <td className="px-4 py-3 text-sm">
                      {conta.status !== 'recebido' && (
                        <>
                          {/* NSU informado - É transação de cartão */}
                          {conta.nsu && !conta.conciliado ? (
                            <>
                              {/* Link para conciliação */}
                              <button
                                className="bg-orange-500 hover:bg-orange-600 text-white px-3 py-1 rounded text-xs mr-2"
                                onClick={() => navigate(`/conciliacao-cartao?nsu=${conta.nsu}`)}
                                title={`Conciliar NSU ${conta.nsu} com extrato da operadora`}
                              >
                                🔄 Conciliar
                              </button>
                              {/* Recebimento manual para cartão */}
                              <button
                                className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs mr-2"
                                onClick={() => abrirModalRecebimento(conta)}
                                title="Receber manual (caso não consiga conciliar)"
                              >
                                💳 Manual
                              </button>
                            </>
                          ) : conta.venda_id && !conta.nsu ? (
                            /* Venda sem NSU - pode receber no PDV OU manual */
                            <>
                              <button
                                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs mr-2"
                                onClick={() => {
                                  console.log('Conta:', conta); // DEBUG
                                  if (conta.venda_id) {
                                    abrirVendaNoPDV(conta.venda_id);
                                  } else {
                                    abrirModalRecebimento(conta);
                                  }
                                }}
                                title="Receber no PDV (movimenta caixa)"
                              >
                                💵 PDV
                              </button>
                              <button
                                className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs mr-2"
                                onClick={() => abrirModalRecebimento(conta)}
                                title="Receber manual (sem PDV)"
                              >
                                💰 Manual
                              </button>
                            </>
                          ) : (
                            /* Lançamento manual ou outros - recebimento manual */
                            <button
                              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs mr-2"
                              onClick={() => abrirModalRecebimento(conta)}
                              title="Registrar recebimento manual"
                            >
                              💰 Receber Manual
                            </button>
                          )}
                        </>
                      )}
                      {conta.conciliado && (
                        <span className="text-xs text-green-600 font-semibold mr-2" title={`Conciliado em ${conta.data_conciliacao}`}>
                          ✓ Conciliado
                        </span>
                      )}
                      <button
                        className="bg-blue-50 hover:bg-blue-100 text-blue-600 px-3 py-1 rounded text-xs"
                        title="Ver Detalhes"
                        onClick={() => abrirDetalhes(conta)}
                      >
                        👁️
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {contas.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contas.length} conta(s) | 
            <strong className="ml-3">Saldo a Receber:</strong> {formatarMoeda(
              contas.reduce((sum, c) => sum + (c.valor_final - c.valor_recebido), 0)
            )}
          </div>
        )}
      </div>

      {/* Modal de Recebimento */}
      {mostrarModalRecebimento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">💰 Registrar Recebimento</h5>
              <button
                className="text-gray-500 hover:text-gray-700 text-2xl"
                onClick={() => setMostrarModalRecebimento(false)}
              >
                ×
              </button>
            </div>
            
            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}<br/>
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}<br/>
                <strong>Já Recebido:</strong> {formatarMoeda(contaSelecionada.valor_recebido)}<br/>
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
                    {formasPagamento.map(f => (
                      <option key={f.id} value={f.id}>{f.nome}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Conta Bancária *</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.conta_bancaria_id || ''}
                    onChange={(e) => setDadosRecebimento({...dadosRecebimento, conta_bancaria_id: parseInt(e.target.value) || null})}
                  >
                    <option value="">Selecione a conta...</option>
                    {contasBancarias.map(c => (
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
                  <label className="block text-sm font-medium mb-1">Observações</label>
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
              <button
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setMostrarModalRecebimento(false)}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={registrarRecebimento}
              >
                ✓ Confirmar Recebimento
              </button>
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
              <button
                onClick={() => setMostrarDetalhes(false)}
                className="text-white hover:bg-blue-700 px-3 py-1 rounded"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Número da Conta</label>
                  <p className="mt-1 text-lg">{contaSelecionada.numero_documento || 'N/A'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cliente</label>
                  <p className="mt-1 text-lg">{detalhesCompletos.cliente?.nome || 'N/A'}</p>
                </div>
              </div>

              {/* Número do Pedido - Clicável */}
              {detalhesCompletos.venda && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Pedido/Venda</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirVenda(detalhesCompletos.venda.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg border border-blue-200 transition-colors"
                    >
                      <span className="text-xl">🛒</span>
                      <span className="font-semibold">{detalhesCompletos.venda.numero_venda}</span>
                    </button>
                    <button
                      onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                      className="flex items-center gap-2 px-4 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg border border-green-200 transition-colors"
                      title="Ver no Fluxo de Caixa"
                    >
                      <span className="text-xl">📈</span>
                      <span className="text-sm">Fluxo</span>
                    </button>
                  </div>
                </div>
              )}

              {!detalhesCompletos.venda && (
                <div>
                  <button
                    onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg border border-green-200 transition-colors"
                  >
                    <span className="text-xl">📈</span>
                    <span className="font-medium">Ver no Fluxo de Caixa</span>
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Emissão</label>
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
                    <span className={`px-2 py-1 rounded text-sm ${
                      detalhesCompletos.status === 'recebido' ? 'bg-green-100 text-green-800' :
                      detalhesCompletos.status === 'parcial' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {detalhesCompletos.status === 'recebido' ? '✓ Recebido' :
                       detalhesCompletos.status === 'parcial' ? '⚡ Parcial' : '⏱ Pendente'}
                    </span>
                  </p>
                </div>
              </div>

              {/* Recebimentos com Conta Bancária */}
              {detalhesCompletos.recebimentos && detalhesCompletos.recebimentos.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">💰 Histórico de Recebimentos</label>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Data</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Valor</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Conta Bancária</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {detalhesCompletos.recebimentos.map((recebimento, index) => (
                          <tr key={index}>
                            <td className="px-3 py-2 text-sm">{formatarData(recebimento.data)}</td>
                            <td className="px-3 py-2 text-sm font-semibold text-green-600">{formatarMoeda(recebimento.valor)}</td>
                            <td className="px-3 py-2 text-sm">
                              {recebimento.conta_bancaria_nome ? (
                                <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                                  🏦 {recebimento.conta_bancaria_nome}
                                </span>
                              ) : (
                                <span className="text-gray-400 text-xs">Não informada</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {detalhesCompletos.observacoes && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observações</label>
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
