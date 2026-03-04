import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import { buscarClientes as buscarClientesAPI } from '../../api/clientes';
import {
  FiSearch, FiUser, FiX, FiFilter, FiCalendar, FiDollarSign, FiCreditCard,
  FiChevronLeft, FiChevronRight, FiChevronDown, FiChevronUp,
  FiShoppingCart, FiPackage, FiAlertCircle
} from 'react-icons/fi';

/* -----------------------------------------------------------------------
   Componente interno: histórico do cliente selecionado (sem wrapper de página)
   ----------------------------------------------------------------------- */
const HistoricoInline = ({ clienteId, clienteInfo }) => {
  const navigate = useNavigate();

  const [resumo, setResumo] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [paginacao, setPaginacao] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [expandedRows, setExpandedRows] = useState({});
  const [detalhesVendas, setDetalhesVendas] = useState({});
  const [loadingDetalhes, setLoadingDetalhes] = useState({});

  const [filtros, setFiltros] = useState({
    page: 1,
    per_page: 20,
    data_inicio: '',
    data_fim: '',
    tipo: '',
    status: ''
  });

  useEffect(() => {
    if (clienteId) {
      setExpandedRows({});
      setDetalhesVendas({});
      setFiltros({ page: 1, per_page: 20, data_inicio: '', data_fim: '', tipo: '', status: '' });
    }
  }, [clienteId]);

  useEffect(() => {
    if (clienteId) carregarDados();
  }, [clienteId, filtros]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      params.append('page', filtros.page);
      params.append('per_page', filtros.per_page);
      if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
      if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
      if (filtros.tipo) params.append('tipo', filtros.tipo);
      if (filtros.status) params.append('status', filtros.status);
      const response = await api.get(`/financeiro/cliente/${clienteId}?${params.toString()}`);
      setResumo(response.data.resumo);
      setHistorico(response.data.historico);
      setPaginacao(response.data.paginacao);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar histórico financeiro');
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = (novos) => setFiltros(f => ({ ...f, ...novos, page: 1 }));
  const limparFiltros = () => setFiltros({ page: 1, per_page: 20, data_inicio: '', data_fim: '', tipo: '', status: '' });
  const mudarPagina = (p) => setFiltros(f => ({ ...f, page: p }));

  const toggleExpansao = async (transacao, index) => {
    const key = `${transacao.tipo}-${index}`;
    if (expandedRows[key]) { setExpandedRows(r => ({ ...r, [key]: false })); return; }
    setExpandedRows(r => ({ ...r, [key]: true }));
    if (transacao.tipo === 'venda' && transacao.detalhes?.venda_id && !detalhesVendas[transacao.detalhes.venda_id]) {
      try {
        setLoadingDetalhes(l => ({ ...l, [transacao.detalhes.venda_id]: true }));
        const res = await api.get(`/vendas/${transacao.detalhes.venda_id}`);
        setDetalhesVendas(d => ({ ...d, [transacao.detalhes.venda_id]: res.data }));
      } catch { /* ignore */ } finally {
        setLoadingDetalhes(l => ({ ...l, [transacao.detalhes.venda_id]: false }));
      }
    }
  };

  const getTipoIcon = (tipo) => ({ venda: '🛒', devolucao: '↩️', conta_receber: '📄', recebimento: '💰', credito: '💳' }[tipo] || '📊');
  const getTipoLabel = (tipo) => ({ venda: 'Venda', devolucao: 'Devolução', conta_receber: 'Conta a Receber', recebimento: 'Recebimento', credito: 'Crédito' }[tipo] || tipo);
  const getStatusBadge = (status) => ({
    finalizada: 'bg-green-100 text-green-700', concluida: 'bg-green-100 text-green-700',
    pendente: 'bg-yellow-100 text-yellow-700', paga: 'bg-blue-100 text-blue-700',
    cancelada: 'bg-red-100 text-red-700', devolvida: 'bg-red-100 text-red-700',
    efetivado: 'bg-green-100 text-green-700'
  }[status] || 'bg-gray-100 text-gray-700');

  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center mt-4">
      <FiAlertCircle className="text-red-500 text-3xl mx-auto mb-2" />
      <p className="text-red-700 font-medium">{error}</p>
    </div>
  );

  return (
    <div className="mt-4 space-y-4">
      {/* Info do cliente + crédito */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-lg">
            {clienteInfo?.nome?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{clienteInfo?.nome}</p>
            <p className="text-xs text-gray-500">
              Código: {clienteInfo?.codigo || '-'}
              {clienteInfo?.telefone && ` · ${clienteInfo.telefone}`}
            </p>
          </div>
        </div>
        {clienteInfo?.credito_atual != null && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 text-right">
            <p className="text-xs text-gray-500">Crédito disponível</p>
            <p className="text-xl font-bold text-purple-600">
              R$ {clienteInfo.credito_atual.toFixed(2).replace('.', ',')}
            </p>
          </div>
        )}
      </div>

      {/* Cards resumo */}
      {resumo && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Vendas (90d)', value: `R$ ${resumo.total_vendas_90d?.toFixed(2).replace('.', ',') || '0,00'}`, color: 'text-blue-600' },
            { label: 'Total em Aberto', value: `R$ ${resumo.total_em_aberto?.toFixed(2).replace('.', ',') || '0,00'}`, color: 'text-orange-600' },
            { label: 'Última Compra', value: resumo.ultima_compra ? `R$ ${resumo.ultima_compra.valor?.toFixed(2).replace('.', ',')}` : '—', color: 'text-green-600' },
            { label: 'Total Transações', value: resumo.total_transacoes_historico || 0, color: 'text-purple-600' },
          ].map(c => (
            <div key={c.label} className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">{c.label}</p>
              <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-gray-700 flex items-center gap-2"><FiFilter /> Filtros</span>
          <button onClick={limparFiltros} className="text-xs text-gray-500 hover:text-gray-800 underline">Limpar</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1"><FiCalendar className="inline mr-1" />Data início</label>
            <input type="date" value={filtros.data_inicio} onChange={e => aplicarFiltros({ data_inicio: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1"><FiCalendar className="inline mr-1" />Data fim</label>
            <input type="date" value={filtros.data_fim} onChange={e => aplicarFiltros({ data_fim: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Tipo</label>
            <select value={filtros.tipo} onChange={e => aplicarFiltros({ tipo: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent">
              <option value="">Todas</option>
              <option value="venda">🛒 Vendas</option>
              <option value="devolucao">↩️ Devoluções</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Status</label>
            <select value={filtros.status} onChange={e => aplicarFiltros({ status: e.target.value })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent">
              <option value="">Todos</option>
              <option value="aberta">📋 Em Aberto</option>
              <option value="finalizada">✅ Finalizada</option>
              <option value="cancelada">❌ Cancelada</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Por página</label>
            <select value={filtros.per_page} onChange={e => aplicarFiltros({ per_page: parseInt(e.target.value) })}
              className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent">
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-10">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-3"></div>
            <p className="text-sm text-gray-500">Carregando histórico...</p>
          </div>
        ) : historico.length === 0 ? (
          <div className="text-center py-14">
            <FiDollarSign className="text-gray-300 text-5xl mx-auto mb-3" />
            <p className="text-gray-600 font-medium">Nenhuma transação encontrada</p>
            {(filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim) && (
              <button onClick={limparFiltros} className="mt-4 px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700">Limpar filtros</button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3 w-10"></th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {historico.map((transacao, index) => {
                    const key = `${transacao.tipo}-${index}`;
                    const isExpanded = expandedRows[key];
                    const vendaId = transacao.detalhes?.venda_id;
                    const detalhes = vendaId ? detalhesVendas[vendaId] : null;
                    return (
                      <React.Fragment key={key}>
                        <tr className="hover:bg-gray-50 transition-colors">
                          <td className="px-3 py-4 text-center">
                            <button onClick={() => toggleExpansao(transacao, index)} className="text-gray-400 hover:text-purple-600">
                              {isExpanded ? <FiChevronUp size={16} /> : <FiChevronDown size={16} />}
                            </button>
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">
                            {transacao.data ? new Date(transacao.data).toLocaleDateString('pt-BR') : '-'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 text-sm font-medium">
                              <span className="text-lg">{getTipoIcon(transacao.tipo)}</span>
                              {getTipoLabel(transacao.tipo)}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs">
                            <div className="truncate">{transacao.descricao}</div>
                            {transacao.detalhes?.numero_venda && (
                              <div className="text-xs text-blue-600 mt-0.5">#{transacao.detalhes.numero_venda}</div>
                            )}
                          </td>
                          <td className="px-4 py-4 text-sm text-right whitespace-nowrap">
                            <span className={`font-bold ${transacao.valor < 0 ? 'text-red-600' : 'text-green-600'}`}>
                              {transacao.valor < 0 ? '- ' : '+ '}R$ {Math.abs(transacao.valor).toFixed(2).replace('.', ',')}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-center whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(transacao.status)}`}>
                              {transacao.status}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-center whitespace-nowrap">
                            {transacao.tipo === 'venda' && vendaId && (
                              <button onClick={() => navigate(`/pdv?venda=${vendaId}`)}
                                className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg flex items-center gap-1 mx-auto">
                                <FiShoppingCart size={12} /> Ver no PDV
                              </button>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan="7" className="px-4 py-4 bg-gray-50">
                              {transacao.tipo === 'venda' && vendaId ? (
                                loadingDetalhes[vendaId] ? (
                                  <div className="text-center py-3 text-sm text-gray-500">Carregando detalhes...</div>
                                ) : detalhes ? (
                                  <div className="space-y-3">
                                    <div className="grid grid-cols-3 gap-3 bg-white rounded-lg p-4 border border-gray-200">
                                      <div><p className="text-xs text-gray-500">💰 Total</p><p className="text-lg font-bold text-green-600">R$ {detalhes.total?.toFixed(2).replace('.', ',')}</p></div>
                                      <div><p className="text-xs text-gray-500">📦 Itens</p><p className="text-lg font-bold text-blue-600">{detalhes.itens?.length || 0}</p></div>
                                      <div><p className="text-xs text-gray-500">🎯 Desconto</p><p className="text-lg font-bold text-orange-600">R$ {(detalhes.desconto || 0).toFixed(2).replace('.', ',')}</p></div>
                                    </div>
                                    {detalhes.itens?.length > 0 && (
                                      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                        <div className="bg-blue-50 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
                                          <FiPackage className="text-blue-600" /><span className="font-semibold text-sm text-gray-800">Produtos</span>
                                        </div>
                                        <table className="min-w-full divide-y divide-gray-200">
                                          <thead className="bg-gray-50">
                                            <tr>
                                              {['Produto','Qtd','Preço Unit.','Desc.','Subtotal'].map(h => (
                                                <th key={h} className="px-4 py-2 text-xs font-medium text-gray-500 text-left">{h}</th>
                                              ))}
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-gray-200">
                                            {detalhes.itens.map((item, i) => (
                                              <tr key={i} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 text-sm text-gray-900">{item.produto_nome}</td>
                                                <td className="px-4 py-2 text-sm text-center font-semibold">{item.quantidade}</td>
                                                <td className="px-4 py-2 text-sm text-right">R$ {item.preco_unitario?.toFixed(2).replace('.', ',')}</td>
                                                <td className="px-4 py-2 text-sm text-right text-orange-600">R$ {(item.desconto || 0).toFixed(2).replace('.', ',')}</td>
                                                <td className="px-4 py-2 text-sm text-right font-bold text-green-600">R$ {item.subtotal?.toFixed(2).replace('.', ',')}</td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>
                                ) : <p className="text-sm text-gray-500 text-center py-2">Não foi possível carregar os detalhes.</p>
                              ) : (
                                <div className="bg-white rounded-lg p-3 border border-gray-200">
                                  <div className="grid grid-cols-2 gap-2 text-sm">
                                    {Object.entries(transacao.detalhes || {}).map(([k, v]) => (
                                      <div key={k} className="flex justify-between border-b border-gray-100 pb-1">
                                        <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                                        <span className="font-medium text-gray-900">
                                          {typeof v === 'number' ? `R$ ${v.toFixed(2).replace('.', ',')}` : v?.toString() || 'N/A'}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {paginacao && paginacao.total_paginas > 1 && (
              <div className="bg-gray-50 px-5 py-3 border-t border-gray-200 flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {((paginacao.pagina_atual - 1) * paginacao.itens_por_pagina) + 1}–
                  {Math.min(paginacao.pagina_atual * paginacao.itens_por_pagina, paginacao.total_itens)} de {paginacao.total_itens}
                </span>
                <div className="flex items-center gap-2">
                  <button onClick={() => mudarPagina(paginacao.pagina_atual - 1)} disabled={!paginacao.tem_anterior}
                    className={`px-3 py-1.5 rounded-lg flex items-center gap-1 text-sm ${paginacao.tem_anterior ? 'bg-purple-600 text-white hover:bg-purple-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>
                    <FiChevronLeft size={14} /> Anterior
                  </button>
                  <span className="text-sm text-gray-600">Pág. {paginacao.pagina_atual}/{paginacao.total_paginas}</span>
                  <button onClick={() => mudarPagina(paginacao.pagina_atual + 1)} disabled={!paginacao.tem_proxima}
                    className={`px-3 py-1.5 rounded-lg flex items-center gap-1 text-sm ${paginacao.tem_proxima ? 'bg-purple-600 text-white hover:bg-purple-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>
                    Próxima <FiChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/* -----------------------------------------------------------------------
   Componente principal: busca de cliente + histórico inline
   ----------------------------------------------------------------------- */
const HistoricoVendasClienteTab = () => {
  const [busca, setBusca] = useState('');
  const [resultados, setResultados] = useState([]);
  const [loadingBusca, setLoadingBusca] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [mostrarDropdown, setMostrarDropdown] = useState(false);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    const handler = (e) => { if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setMostrarDropdown(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const buscarClientes = (termo) => {
    clearTimeout(debounceRef.current);
    setBusca(termo);
    if (!termo || termo.trim().length < 2) { setResultados([]); setMostrarDropdown(false); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        setLoadingBusca(true);
        const lista = await buscarClientesAPI({ search: termo, limit: 10 });
        setResultados(Array.isArray(lista) ? lista : []);
        setMostrarDropdown(true);
      } catch { setResultados([]); } finally { setLoadingBusca(false); }
    }, 350);
  };

  const selecionarCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setBusca(cliente.nome);
    setMostrarDropdown(false);
    setResultados([]);
  };

  const limparCliente = () => {
    setClienteSelecionado(null);
    setBusca('');
    setResultados([]);
    setMostrarDropdown(false);
  };

  return (
    <div className="p-6">
      {/* Cabeçalho */}
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <FiUser className="text-purple-600" />
          Histórico de Vendas por Cliente
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Pesquise um cliente pelo nome, código ou telefone para visualizar seu histórico financeiro completo.
        </p>
      </div>

      {/* Campo de busca */}
      <div ref={wrapperRef} className="relative max-w-xl">
        <div className="flex items-center gap-2 border border-gray-300 rounded-xl px-4 py-2.5 bg-white shadow-sm focus-within:ring-2 focus-within:ring-purple-500 focus-within:border-transparent">
          <FiSearch className="text-gray-400 flex-shrink-0" />
          <input
            type="text"
            value={busca}
            onChange={e => buscarClientes(e.target.value)}
            placeholder="Buscar por nome, código ou telefone..."
            className="flex-1 outline-none text-sm text-gray-800 bg-transparent"
            onFocus={() => resultados.length > 0 && setMostrarDropdown(true)}
          />
          {loadingBusca && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-500 flex-shrink-0" />
          )}
          {busca && !loadingBusca && (
            <button onClick={limparCliente} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
              <FiX size={16} />
            </button>
          )}
        </div>

        {/* Dropdown de resultados */}
        {mostrarDropdown && resultados.length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden max-h-60 overflow-y-auto">
            {resultados.map(c => (
              <button
                key={c.id}
                onMouseDown={() => selecionarCliente(c)}
                className="w-full text-left px-4 py-3 hover:bg-purple-50 flex items-center gap-3 border-b border-gray-100 last:border-0"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-400 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                  {c.nome?.[0]?.toUpperCase() || '?'}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{c.nome}</p>
                  <p className="text-xs text-gray-500">
                    Cód: {c.codigo || '-'}
                    {c.telefone && ` · ${c.telefone}`}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}

        {mostrarDropdown && !loadingBusca && resultados.length === 0 && busca.trim().length >= 2 && (
          <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-50 px-4 py-3 text-sm text-gray-500">
            Nenhum cliente encontrado para "{busca}"
          </div>
        )}
      </div>

      {/* Estado inicial sem cliente */}
      {!clienteSelecionado && (
        <div className="mt-12 text-center text-gray-400">
          <FiUser className="text-6xl mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">Selecione um cliente acima</p>
          <p className="text-sm mt-1">O histórico financeiro completo será exibido aqui</p>
        </div>
      )}

      {/* Histórico do cliente selecionado */}
      {clienteSelecionado && (
        <HistoricoInline
          key={clienteSelecionado.id}
          clienteId={clienteSelecionado.id}
          clienteInfo={clienteSelecionado}
        />
      )}
    </div>
  );
};

export default HistoricoVendasClienteTab;
