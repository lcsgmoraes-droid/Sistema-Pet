import { useState, useEffect } from 'react';
import { X, ShoppingBag, TrendingUp, Calendar, Loader, DollarSign, ChevronDown, ChevronUp, Package, CreditCard, Copy, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../api';

// Formata numero como R$ 4.029,80
const formatBRL = (value) => {
  const num = Number(value) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

export default function HistoricoCliente({ clienteId, clienteNome, onClose }) {
  const [historico, setHistorico] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState('todos');
  const [expandidos, setExpandidos] = useState({});
  const [detalhesVenda, setDetalhesVenda] = useState({});
  const [loadingDetalhes, setLoadingDetalhes] = useState({});
  const [copiadoSku, setCopiadoSku] = useState('');

  useEffect(() => {
    carregarHistorico();
  }, [clienteId]);

  const carregarHistorico = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/clientes/${clienteId}/historico-compras`);
      setHistorico(response.data);
    } catch (error) {
      console.error('Erro ao carregar historico:', error);
      toast.error('Erro ao carregar historico do cliente');
    } finally {
      setLoading(false);
    }
  };

  const carregarDetalhesVenda = async (vendaId) => {
    if (detalhesVenda[vendaId] || loadingDetalhes[vendaId]) return;

    setLoadingDetalhes((prev) => ({ ...prev, [vendaId]: true }));

    try {
      const [respVenda, respPagamentos] = await Promise.allSettled([
        api.get(`/vendas/${vendaId}`),
        api.get(`/vendas/${vendaId}/pagamentos`),
      ]);

      const dadosVenda = respVenda.status === 'fulfilled' ? respVenda.value.data : null;
      const itens = Array.isArray(dadosVenda?.itens) ? dadosVenda.itens : [];

      let pagamentos = [];
      if (respPagamentos.status === 'fulfilled') {
        const payload = respPagamentos.value.data;
        if (Array.isArray(payload?.pagamentos)) {
          pagamentos = payload.pagamentos;
        } else if (Array.isArray(payload)) {
          pagamentos = payload;
        } else {
          pagamentos = [];
        }
      } else {
        pagamentos = Array.isArray(dadosVenda?.pagamentos) ? dadosVenda.pagamentos : [];
      }

      setDetalhesVenda((prev) => ({
        ...prev,
        [vendaId]: {
          itens,
          pagamentos,
        },
      }));
    } catch (error) {
      console.error('Erro ao carregar detalhes da venda:', error);
      toast.error('Nao foi possivel carregar os detalhes da venda');
    } finally {
      setLoadingDetalhes((prev) => ({ ...prev, [vendaId]: false }));
    }
  };

  const toggleExpandir = (venda) => {
    const abrindo = !expandidos[venda.id];
    setExpandidos((prev) => ({ ...prev, [venda.id]: abrindo }));

    if (abrindo) {
      carregarDetalhesVenda(venda.id);
    }
  };

  const obterItensVenda = (venda) => {
    const itensDetalhados = detalhesVenda[venda.id]?.itens;
    let origem = [];
    if (Array.isArray(itensDetalhados) && itensDetalhados.length > 0) {
      origem = itensDetalhados;
    } else if (Array.isArray(venda.itens)) {
      origem = venda.itens;
    }

    return origem.map((item) => ({
      ...item,
      nome: item?.nome || item?.produto_nome || item?.produto?.nome || item?.servico_descricao || 'Item',
      sku:
        item?.sku ||
        item?.produto_codigo ||
        item?.codigo ||
        item?.produto?.codigo ||
        item?.produto?.sku ||
        '',
    }));
  };

  const copiarSkuItem = async (sku, chave) => {
    if (!sku) return;

    try {
      await navigator.clipboard.writeText(String(sku));
      setCopiadoSku(chave);
      window.setTimeout(() => {
        setCopiadoSku((atual) => (atual === chave ? '' : atual));
      }, 1800);
    } catch (error) {
      console.error('Erro ao copiar SKU:', error);
      toast.error('Nao foi possivel copiar o codigo do item');
    }
  };

  const obterPagamentosVenda = (venda) => {
    const pagamentosDetalhados = detalhesVenda[venda.id]?.pagamentos;
    let origem = [];
    if (Array.isArray(pagamentosDetalhados) && pagamentosDetalhados.length > 0) {
      origem = pagamentosDetalhados;
    } else if (Array.isArray(venda.pagamentos)) {
      origem = venda.pagamentos;
    }

    return origem.map((pag) => ({
      ...pag,
      forma: pag?.forma || pag?.forma_pagamento_nome || pag?.forma_pagamento || pag?.forma_pagamento?.nome || 'Nao informado',
      valor: Number(pag?.valor || pag?.valor_pago || 0),
    }));
  };

  const getStatusBadge = (status) => {
    const badges = {
      aberta: 'bg-blue-100 text-blue-800',
      finalizada: 'bg-green-100 text-green-800',
      baixa_parcial: 'bg-yellow-100 text-yellow-800',
      pendente: 'bg-orange-100 text-orange-800',
      cancelada: 'bg-red-100 text-red-800',
      finalizada_devolucao_parcial: 'bg-orange-100 text-orange-800',
      finalizada_devolucao_total: 'bg-gray-100 text-gray-800'
    };
    const labels = {
      aberta: 'Aberta',
      finalizada: 'Finalizada',
      baixa_parcial: 'Baixa Parcial',
      pendente: 'Pendente',
      cancelada: 'Cancelada',
      finalizada_devolucao_parcial: 'Dev. Parcial',
      finalizada_devolucao_total: 'Dev. Total'
    };
    return (
      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${badges[status] || 'bg-gray-100 text-gray-800'}`}>
        {labels[status] || status}
      </span>
    );
  };

  const vendasFiltradas = historico?.vendas?.filter(venda => {
    if (filtroStatus === 'todos') return true;
    return venda.status === filtroStatus;
  }) || [];

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4">
          <div className="flex items-center justify-center">
            <Loader className="w-8 h-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">Carregando...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!historico) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Histórico de Compras</h2>
              <p className="text-gray-600 mt-1">{clienteNome}</p>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white rounded-lg transition-colors">
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Estatisticas */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <ShoppingBag className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <div className="text-sm text-gray-600">Total de Compras</div>
                  <div className="text-2xl font-bold text-gray-900">{historico.total_compras}</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <DollarSign className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <div className="text-sm text-gray-600">Total Gasto</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {formatBRL(historico.valor_total_gasto)}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <div className="text-sm text-gray-600">Ticket Médio</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {formatBRL(historico.ticket_medio)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {historico.ultima_compra && (
            <div className="mt-4 bg-white rounded-lg p-3 shadow-sm flex items-center space-x-2 text-sm">
              <Calendar className="w-4 h-4 text-gray-500" />
              <span className="text-gray-600">
                Última compra: {new Date(historico.ultima_compra).toLocaleDateString('pt-BR', {
                  day: '2-digit', month: 'long', year: 'numeric'
                })}
              </span>
            </div>
          )}
        </div>

        {/* Filtros */}
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Filtrar por status:</span>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="todos">Todos ({historico.vendas?.length || 0})</option>
              <option value="aberta">Abertas</option>
              <option value="finalizada">Finalizadas</option>
              <option value="baixa_parcial">Baixa Parcial</option>
              <option value="pendente">Pendentes</option>
              <option value="cancelada">Canceladas</option>
            </select>
          </div>
        </div>

        {/* Lista de Vendas */}
        <div className="flex-1 overflow-y-auto p-6">
          {vendasFiltradas.length === 0 ? (
            <div className="text-center py-12">
              <ShoppingBag className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-lg font-medium text-gray-900">Nenhuma venda encontrada</p>
              <p className="text-gray-600 mt-2">
                {filtroStatus === 'todos'
                  ? 'Este cliente ainda não realizou compras.'
                  : 'Não há vendas com este status.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {vendasFiltradas.map((venda) => (
                <div key={venda.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
                  {(() => {
                    const itensDaVenda = obterItensVenda(venda);
                    const pagamentosDaVenda = obterPagamentosVenda(venda);
                    const temDetalhes = venda.total_itens > 0 || pagamentosDaVenda.length > 0;
                    const carregandoVenda = !!loadingDetalhes[venda.id];

                    return (
                      <>
                  {/* Linha principal da venda */}
                  <div className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-3">
                          <h3 className="text-lg font-semibold text-gray-900">
                            Venda #{venda.numero_venda}
                          </h3>
                          {getStatusBadge(venda.status)}
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500">Data:</span>
                            <div className="font-medium text-gray-900">
                              {new Date(venda.data_venda).toLocaleDateString('pt-BR')}
                            </div>
                          </div>

                          <div>
                            <span className="text-gray-500">Subtotal:</span>
                            <div className="font-medium text-gray-900">{formatBRL(venda.subtotal)}</div>
                          </div>

                          {venda.desconto_valor > 0 && (
                            <div>
                              <span className="text-gray-500">Desconto:</span>
                              <div className="font-medium text-red-600">- {formatBRL(venda.desconto_valor)}</div>
                            </div>
                          )}

                          {venda.taxa_entrega > 0 && (
                            <div>
                              <span className="text-gray-500">Taxa Entrega:</span>
                              <div className="font-medium text-gray-900">{formatBRL(venda.taxa_entrega)}</div>
                            </div>
                          )}

                          <div>
                            <span className="text-gray-500">Total:</span>
                            <div className="font-bold text-gray-900 text-lg">{formatBRL(venda.total)}</div>
                          </div>

                          {venda.saldo_devedor > 0 && (
                            <div>
                              <span className="text-gray-500">Saldo Devedor:</span>
                              <div className="font-bold text-red-600">{formatBRL(venda.saldo_devedor)}</div>
                            </div>
                          )}

                          <div>
                            <span className="text-gray-500">Itens:</span>
                            <div className="font-medium text-gray-900">{venda.total_itens}</div>
                          </div>

                          {venda.vendedor_nome && (
                            <div>
                              <span className="text-gray-500">Vendedor:</span>
                              <div className="font-medium text-gray-900">{venda.vendedor_nome}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Botao Ver Detalhes */}
                    {temDetalhes && (
                      <button
                        onClick={() => toggleExpandir(venda)}
                        className="mt-3 flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
                      >
                        {expandidos[venda.id] ? (
                          <><ChevronUp className="w-4 h-4" /><span>Ocultar detalhes</span></>
                        ) : (
                          <><ChevronDown className="w-4 h-4" /><span>Ver detalhes da compra</span></>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Painel expansivel: itens + pagamentos */}
                  {expandidos[venda.id] && (
                    <div className="border-t border-gray-100 bg-gray-50 p-4 space-y-4">
                      {carregandoVenda && (
                        <div className="text-sm text-gray-500">Carregando detalhes...</div>
                      )}

                      {/* Itens */}
                      {itensDaVenda.length > 0 && (
                        <div>
                          <div className="flex items-center space-x-2 mb-2">
                            <Package className="w-4 h-4 text-gray-500" />
                            <span className="text-sm font-semibold text-gray-700">Itens vendidos</span>
                          </div>
                          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                            <table className="w-full text-sm">
                              <thead className="bg-gray-100 text-gray-600">
                                <tr>
                                  <th className="text-left px-3 py-2 font-medium">Produto / Serviço</th>
                                  <th className="text-right px-3 py-2 font-medium">Qtd</th>
                                  <th className="text-right px-3 py-2 font-medium">Unit.</th>
                                  <th className="text-right px-3 py-2 font-medium">Subtotal</th>
                                </tr>
                              </thead>
                              <tbody>
                                {itensDaVenda.map((item, index) => {
                                  const itemSku = String(item.sku || '').trim();
                                  const chaveSku = `${venda.id}-${itemSku || item.nome}-${index}`;

                                  return (
                                  <tr key={`${item.nome}-${item.quantidade}-${item.preco_unitario}-${item.subtotal}-${index}`} className="border-t border-gray-100">
                                    <td className="px-3 py-2 text-gray-900">
                                      <div className="space-y-1">
                                        <div>{item.nome}</div>
                                        {itemSku && (
                                          <div className="inline-flex items-center gap-1.5 text-xs text-gray-500">
                                            <span className="font-mono">SKU: {itemSku}</span>
                                            <button
                                              type="button"
                                              onClick={() => copiarSkuItem(itemSku, chaveSku)}
                                              className="text-gray-400 hover:text-gray-700 transition-colors"
                                              title="Copiar SKU"
                                            >
                                              {copiadoSku === chaveSku ? (
                                                <Check className="w-3.5 h-3.5 text-green-600" />
                                              ) : (
                                                <Copy className="w-3.5 h-3.5" />
                                              )}
                                            </button>
                                          </div>
                                        )}
                                      </div>
                                    </td>
                                    <td className="px-3 py-2 text-right text-gray-700">
                                      {Number(item.quantidade) % 1 === 0
                                        ? Number(item.quantidade).toFixed(0)
                                        : Number(item.quantidade).toFixed(3).replace('.', ',')}
                                    </td>
                                    <td className="px-3 py-2 text-right text-gray-700">{formatBRL(item.preco_unitario)}</td>
                                    <td className="px-3 py-2 text-right font-medium text-gray-900">{formatBRL(item.subtotal)}</td>
                                  </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Formas de pagamento */}
                      {pagamentosDaVenda.length > 0 && (
                        <div>
                          <div className="flex items-center space-x-2 mb-2">
                            <CreditCard className="w-4 h-4 text-gray-500" />
                            <span className="text-sm font-semibold text-gray-700">Formas de pagamento</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {pagamentosDaVenda.map((pag) => (
                              <div key={`${pag.forma}-${pag.valor}`} className="flex items-center space-x-2 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm">
                                <span className="text-gray-700">{pag.forma}</span>
                                <span className="font-semibold text-gray-900">{formatBRL(pag.valor)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {!carregandoVenda && itensDaVenda.length === 0 && pagamentosDaVenda.length === 0 && (
                        <div className="text-sm text-gray-500">Nao ha detalhes para esta venda.</div>
                      )}
                    </div>
                  )}
                      </>
                    );
                  })()}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex justify-between items-center text-sm text-gray-600">
            <span>Mostrando {vendasFiltradas.length} de {historico.vendas?.length || 0} vendas</span>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
