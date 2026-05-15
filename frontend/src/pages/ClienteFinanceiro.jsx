import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { 
  FiArrowLeft, FiCalendar, FiDollarSign, FiCreditCard,
  FiChevronLeft, FiChevronRight, FiChevronDown,
  FiChevronUp, FiShoppingCart, FiPackage
} from 'react-icons/fi';
import ActionButton from '../components/ui/ActionButton';
import EmptyState from '../components/ui/EmptyState';
import ErrorState from '../components/ui/ErrorState';
import IconActionButton from '../components/ui/IconActionButton';
import LoadingState from '../components/ui/LoadingState';
import MetricCard from '../components/ui/MetricCard';
import MetricGrid from '../components/ui/MetricGrid';
import PageHeader from '../components/ui/PageHeader';
import Panel from '../components/ui/Panel';
import ProductIdentity from '../components/ui/ProductIdentity';
import SaleReference from '../components/ui/SaleReference';

const formatCurrency = (value) => `R$ ${(Number(value) || 0).toFixed(2).replace('.', ',')}`;

const ClienteFinanceiro = () => {
  const { clienteId } = useParams();
  const navigate = useNavigate();
  
  // Estados principais
  const [cliente, setCliente] = useState(null);
  const [resumo, setResumo] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [paginacao, setPaginacao] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Estados de expansão
  const [expandedRows, setExpandedRows] = useState({});
  const [detalhesVendas, setDetalhesVendas] = useState({});
  const [loadingDetalhes, setLoadingDetalhes] = useState({});

  // Estados de filtros
  const [filtros, setFiltros] = useState({
    page: 1,
    per_page: 20,
    data_inicio: '',
    data_fim: '',
    tipo: '',
    status: ''
  });

  // Carregar dados ao montar componente
  useEffect(() => {
    if (clienteId) {
      carregarDados();
    }
  }, [clienteId, filtros]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError('');

      // Montar query params
      const params = new URLSearchParams();
      params.append('page', filtros.page);
      params.append('per_page', filtros.per_page);
      
      if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
      if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
      if (filtros.tipo) params.append('tipo', filtros.tipo);
      if (filtros.status) params.append('status', filtros.status);

      // Fazer requisição para a nova rota otimizada
      const response = await api.get(`/financeiro/cliente/${clienteId}?${params.toString()}`);

      setCliente(response.data.cliente);
      setResumo(response.data.resumo);
      setHistorico(response.data.historico);
      setPaginacao(response.data.paginacao);
    } catch (err) {
      console.error('Erro ao carregar histórico financeiro:', err);
      setError(err.response?.data?.detail || 'Erro ao carregar histórico financeiro');
    } finally {
      setLoading(false);
    }
  };

  const mudarPagina = (novaPagina) => {
    setFiltros({ ...filtros, page: novaPagina });
  };

  const aplicarFiltros = (novosFiltros) => {
    setFiltros({ ...filtros, ...novosFiltros, page: 1 });
  };

  const limparFiltros = () => {
    setFiltros({
      page: 1,
      per_page: 20,
      data_inicio: '',
      data_fim: '',
      tipo: '',
      status: ''
    });
  };

  const toggleExpansao = async (transacao, index) => {
    const key = `${transacao.tipo}-${index}`;
    
    // Se já está expandido, colapsar
    if (expandedRows[key]) {
      setExpandedRows({ ...expandedRows, [key]: false });
      return;
    }

    // Expandir
    setExpandedRows({ ...expandedRows, [key]: true });

    // Se for venda e não tem detalhes carregados, buscar
    if (transacao.tipo === 'venda' && !detalhesVendas[transacao.detalhes?.venda_id]) {
      await carregarDetalhesVenda(transacao.detalhes?.venda_id);
    }
  };

  const carregarDetalhesVenda = async (vendaId) => {
    if (!vendaId) return;

    try {
      setLoadingDetalhes({ ...loadingDetalhes, [vendaId]: true });
      const response = await api.get(`/vendas/${vendaId}`);
      setDetalhesVendas({ ...detalhesVendas, [vendaId]: response.data });
    } catch (err) {
      console.error('Erro ao carregar detalhes da venda:', err);
    } finally {
      setLoadingDetalhes({ ...loadingDetalhes, [vendaId]: false });
    }
  };

  const navegarParaVenda = (vendaId) => {
    if (vendaId) {
      navigate(`/pdv?venda=${vendaId}`);
    }
  };

  const getTipoIcon = (tipo) => {
    switch (tipo) {
      case 'venda': return '🛒';
      case 'devolucao': return '↩️';
      case 'conta_receber': return '📄';
      case 'recebimento': return '💰';
      case 'credito': return '💳';
      default: return '📊';
    }
  };

  const getTipoLabel = (tipo) => {
    switch (tipo) {
      case 'venda': return 'Venda';
      case 'devolucao': return 'Devolução';
      case 'conta_receber': return 'Conta a Receber';
      case 'recebimento': return 'Recebimento';
      case 'credito': return 'Crédito';
      default: return tipo;
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      'finalizada': 'bg-green-100 text-green-700',
      'concluida': 'bg-green-100 text-green-700',
      'pendente': 'bg-yellow-100 text-yellow-700',
      'paga': 'bg-blue-100 text-blue-700',
      'cancelada': 'bg-red-100 text-red-700',
      'devolvida': 'bg-red-100 text-red-700',
      'efetivado': 'bg-green-100 text-green-700'
    };
    return badges[status] || 'bg-gray-100 text-gray-700';
  };

  if (loading && !historico.length) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <Panel>
            <LoadingState label="Carregando historico financeiro..." />
          </Panel>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-2xl">
          <ErrorState
            title="Erro ao carregar dados"
            description={error}
            action={
              <ActionButton
                onClick={() => navigate('/clientes')}
                intent="neutral"
                icon={FiArrowLeft}
                size="md"
              >
                Voltar para Clientes
              </ActionButton>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="space-y-4">
          <ActionButton
            onClick={() => navigate('/clientes')}
            intent="neutral"
            tone="ghost"
            icon={FiArrowLeft}
          >
            Voltar para Clientes
          </ActionButton>

          <PageHeader
            icon={FiCreditCard}
            title="Historico Financeiro"
            subtitle={
              cliente
                ? `${cliente.nome}${cliente.codigo ? ` (${cliente.codigo})` : ''}`
                : 'Historico de vendas e movimentacoes do cliente'
            }
          />
        </div>

        {/* Resumo Rápido (Cards) */}
        {resumo && (
          <MetricGrid className="xl:grid-cols-5">
            <MetricCard
              intent="violet"
              label="Credito disponivel"
              value={formatCurrency(cliente?.credito_atual)}
            />
            <MetricCard
              intent="blue"
              label="Total vendas (90d)"
              value={formatCurrency(resumo.total_vendas_90d)}
            />
            <MetricCard
              intent="amber"
              label="Total em aberto"
              value={formatCurrency(resumo.total_em_aberto)}
            />
            <MetricCard
              intent="emerald"
              label="Ultima compra"
              value={resumo.ultima_compra ? formatCurrency(resumo.ultima_compra.valor) : "-"}
              subtitle={
                resumo.ultima_compra?.data
                  ? new Date(resumo.ultima_compra.data).toLocaleDateString('pt-BR')
                  : "Nenhuma compra"
              }
            />
            <MetricCard
              intent="slate"
              label="Total transacoes"
              value={resumo.total_transacoes_historico || 0}
            />
          </MetricGrid>
        )}

        <Panel
          title="Filtros"
          subtitle="Refine o historico por periodo, tipo, status e quantidade por pagina."
          actions={
            <ActionButton
              onClick={limparFiltros}
              intent="neutral"
              tone="ghost"
              size="sm"
            >
              Limpar filtros
            </ActionButton>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Data Início */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                <FiCalendar className="inline mr-1" />
                Data Início
              </label>
              <input
                type="date"
                value={filtros.data_inicio}
                onChange={(e) => aplicarFiltros({ data_inicio: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            {/* Data Fim */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                <FiCalendar className="inline mr-1" />
                Data Fim
              </label>
              <input
                type="date"
                value={filtros.data_fim}
                onChange={(e) => aplicarFiltros({ data_fim: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            {/* Tipo */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Tipo</label>
              <select
                value={filtros.tipo}
                onChange={(e) => aplicarFiltros({ tipo: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Todas as transações</option>
                <option value="venda">🛒 Vendas</option>
                <option value="devolucao">↩️ Devoluções</option>
              </select>
            </div>

            {/* Status */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filtros.status}
                onChange={(e) => aplicarFiltros({ status: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Todos os status</option>
                <option value="aberta">📋 Em Aberto</option>
                <option value="finalizada">✅ Finalizada (Paga)</option>
                <option value="cancelada">❌ Cancelada</option>
              </select>
            </div>

            {/* Itens por página */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Por página</label>
              <select
                value={filtros.per_page}
                onChange={(e) => aplicarFiltros({ per_page: parseInt(e.target.value) })}
                className="h-9 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </Panel>

        {/* Tabela de Histórico */}
        <Panel padding="none" className="overflow-hidden">
          {loading ? (
            <LoadingState label="Atualizando historico..." />
          ) : historico.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">
                        
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tipo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Descrição
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Valor
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ações
                      </th>
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
                            <td className="px-4 py-4 text-center">
                              <IconActionButton
                                icon={isExpanded ? FiChevronUp : FiChevronDown}
                                intent="neutral"
                                tone="ghost"
                                onClick={() => toggleExpansao(transacao, index)}
                                title={isExpanded ? "Recolher detalhes" : "Ver detalhes"}
                              />
                            </td>

                            {/* Data */}
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {transacao.data ? new Date(transacao.data).toLocaleDateString('pt-BR') : '-'}
                            </td>

                            {/* Tipo */}
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 text-sm font-medium">
                                <span className="text-xl">{getTipoIcon(transacao.tipo)}</span>
                                {getTipoLabel(transacao.tipo)}
                              </span>
                            </td>

                            {/* Descrição */}
                            <td className="px-6 py-4 text-sm text-gray-900 max-w-md">
                              <div className="truncate">{transacao.descricao}</div>
                              {transacao.detalhes?.numero_venda && (
                                <div className="text-xs text-blue-600 mt-1">
                                  <SaleReference
                                    showPrefix={false}
                                    value={transacao.detalhes.numero_venda}
                                  />
                                </div>
                              )}
                            </td>

                            {/* Valor */}
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                              <span className={`font-bold ${
                                transacao.valor < 0 ? 'text-red-600' : 'text-green-600'
                              }`}>
                                {transacao.valor < 0 ? '- ' : '+ '}
                                R$ {Math.abs(transacao.valor).toFixed(2).replace('.', ',')}
                              </span>
                            </td>

                            {/* Status */}
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                getStatusBadge(transacao.status)
                              }`}>
                                {transacao.status}
                              </span>
                            </td>

                            {/* Ações */}
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              {transacao.tipo === 'venda' && vendaId && (
                                <ActionButton
                                  onClick={() => navegarParaVenda(vendaId)}
                                  intent="edit"
                                  icon={FiShoppingCart}
                                  size="xs"
                                >
                                  Ver no PDV
                                </ActionButton>
                              )}
                            </td>
                          </tr>

                          {/* Linha Expandida com Detalhes */}
                          {isExpanded && (
                            <tr>
                              <td colSpan="7" className="px-6 py-4 bg-gray-50">
                                {transacao.tipo === 'venda' && vendaId ? (
                                  loadingDetalhes[vendaId] ? (
                                    <LoadingState compact label="Carregando detalhes..." />
                                  ) : detalhes ? (
                                    <div className="space-y-4">
                                      {/* Header dos Detalhes */}
                                      <div className="flex items-center justify-between border-b border-gray-200 pb-3">
                                        <h4 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                                          <FiShoppingCart className="text-blue-600" />
                                          Detalhes da Venda
                                          <SaleReference
                                            showPrefix={false}
                                            value={detalhes.numero_venda}
                                            valueClassName="font-semibold"
                                          />
                                        </h4>
                                        <div className="text-sm text-gray-600">
                                          {new Date(detalhes.data_venda).toLocaleString('pt-BR')}
                                        </div>
                                      </div>

                                      {/* Grid de Informações Gerais */}
                                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white rounded-lg p-4 border border-gray-200">
                                        <div>
                                          <p className="text-xs text-gray-500 mb-1">💰 Total da Venda</p>
                                          <p className="text-xl font-bold text-green-600">
                                            R$ {detalhes.total?.toFixed(2).replace('.', ',')}
                                          </p>
                                        </div>
                                        <div>
                                          <p className="text-xs text-gray-500 mb-1">📦 Total de Itens</p>
                                          <p className="text-xl font-bold text-blue-600">
                                            {detalhes.itens?.length || 0}
                                          </p>
                                        </div>
                                        <div>
                                          <p className="text-xs text-gray-500 mb-1">🎯 Desconto Total</p>
                                          <p className="text-xl font-bold text-orange-600">
                                            R$ {(detalhes.desconto || 0).toFixed(2).replace('.', ',')}
                                          </p>
                                        </div>
                                      </div>

                                      {/* Tabela de Produtos */}
                                      {detalhes.itens && detalhes.itens.length > 0 && (
                                        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                          <div className="bg-blue-50 px-4 py-2 border-b border-gray-200">
                                            <h5 className="font-semibold text-gray-800 flex items-center gap-2">
                                              <FiPackage className="text-blue-600" />
                                              Produtos Vendidos
                                            </h5>
                                          </div>
                                          <div className="overflow-x-auto">
                                            <table className="min-w-full divide-y divide-gray-200">
                                              <thead className="bg-gray-50">
                                                <tr>
                                                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Produto</th>
                                                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Qtd</th>
                                                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Preço Unit.</th>
                                                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Desc. %</th>
                                                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Desc. R$</th>
                                                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Subtotal</th>
                                                </tr>
                                              </thead>
                                              <tbody className="divide-y divide-gray-200">
                                                {detalhes.itens.map((item, idx) => (
                                                  <tr key={idx} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3 text-sm text-gray-900">
                                                      <ProductIdentity product={item} />
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-center font-semibold text-gray-700">
                                                      {item.quantidade}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-right text-gray-700">
                                                      R$ {item.preco_unitario?.toFixed(2).replace('.', ',')}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                                                      {item.desconto_percentual || 0}%
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-right text-orange-600">
                                                      R$ {(item.desconto || 0).toFixed(2).replace('.', ',')}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-right font-bold text-green-600">
                                                      R$ {item.subtotal?.toFixed(2).replace('.', ',')}
                                                    </td>
                                                  </tr>
                                                ))}
                                              </tbody>
                                              <tfoot className="bg-gray-50">
                                                <tr>
                                                  <td colSpan="5" className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                                                    Total Geral:
                                                  </td>
                                                  <td className="px-4 py-3 text-right text-lg font-bold text-green-600">
                                                    R$ {detalhes.total?.toFixed(2).replace('.', ',')}
                                                  </td>
                                                </tr>
                                              </tfoot>
                                            </table>
                                          </div>
                                        </div>
                                      )}

                                      {/* Observações */}
                                      {detalhes.observacoes && (
                                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                          <p className="text-xs font-semibold text-yellow-800 mb-1">📝 Observações:</p>
                                          <p className="text-sm text-gray-700">{detalhes.observacoes}</p>
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <div className="text-center py-4 text-gray-500">
                                      <p>Não foi possível carregar os detalhes da venda</p>
                                    </div>
                                  )
                                ) : (
                                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                                    <h5 className="font-semibold text-gray-800 mb-3">Detalhes da Transação</h5>
                                    <div className="grid grid-cols-2 gap-3 text-sm">
                                      {Object.entries(transacao.detalhes || {}).map(([key, value]) => (
                                        <div key={key} className="flex justify-between border-b border-gray-100 pb-2">
                                          <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                                          <span className="font-semibold text-gray-900">
                                            {typeof value === 'number' ? 
                                              `R$ ${value.toFixed(2).replace('.', ',')}` : 
                                              value?.toString() || 'N/A'
                                            }
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

              {/* Paginação */}
              {paginacao && paginacao.total_paginas > 1 && (
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Mostrando {((paginacao.pagina_atual - 1) * paginacao.itens_por_pagina) + 1} a{' '}
                      {Math.min(paginacao.pagina_atual * paginacao.itens_por_pagina, paginacao.total_itens)} de{' '}
                      {paginacao.total_itens} transações
                    </div>

                    <div className="flex items-center gap-2">
                      <ActionButton
                        onClick={() => mudarPagina(paginacao.pagina_atual - 1)}
                        disabled={!paginacao.tem_anterior}
                        intent="neutral"
                        icon={FiChevronLeft}
                        size="sm"
                      >
                        Anterior
                      </ActionButton>

                      <span className="px-4 py-2 text-sm text-gray-700">
                        Página {paginacao.pagina_atual} de {paginacao.total_paginas}
                      </span>

                      <ActionButton
                        onClick={() => mudarPagina(paginacao.pagina_atual + 1)}
                        disabled={!paginacao.tem_proxima}
                        intent="neutral"
                        icon={FiChevronRight}
                        iconPosition="right"
                        size="sm"
                      >
                        Proxima
                      </ActionButton>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              icon={FiDollarSign}
              title="Nenhuma transacao encontrada"
              description={
                filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim
                  ? 'Tente ajustar os filtros para ver mais resultados.'
                  : 'Ainda nao ha transacoes financeiras para este cliente.'
              }
              action={
                filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim ? (
                  <ActionButton onClick={limparFiltros} intent="neutral" size="md">
                    Limpar filtros
                  </ActionButton>
                ) : null
              }
            />
          )}
        </Panel>
      </div>
    </div>
  );
};

export default ClienteFinanceiro;
