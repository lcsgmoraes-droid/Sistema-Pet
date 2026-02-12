import { useState, useEffect } from 'react';
import { X, ShoppingBag, TrendingUp, Calendar, Loader, DollarSign } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../api';

export default function HistoricoCliente({ clienteId, clienteNome, onClose }) {
  const [historico, setHistorico] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState('todos');

  useEffect(() => {
    carregarHistorico();
  }, [clienteId]);

  const carregarHistorico = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/clientes/${clienteId}/historico-compras`);
      setHistorico(response.data);
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
      toast.error('Erro ao carregar histórico do cliente');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      finalizada: 'bg-green-100 text-green-800',
      baixa_parcial: 'bg-yellow-100 text-yellow-800',
      pendente: 'bg-blue-100 text-blue-800',
      cancelada: 'bg-red-100 text-red-800',
      finalizada_devolucao_parcial: 'bg-orange-100 text-orange-800',
      finalizada_devolucao_total: 'bg-gray-100 text-gray-800'
    };
    
    const labels = {
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
            <span className="ml-3 text-gray-600">Carregando histórico...</span>
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
            <button
              onClick={onClose}
              className="p-2 hover:bg-white rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Estatísticas */}
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
                    R$ {historico.valor_total_gasto.toFixed(2)}
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
                    R$ {historico.ticket_medio.toFixed(2)}
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
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric'
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
                <div
                  key={venda.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
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
                          <div className="font-medium text-gray-900">
                            R$ {venda.subtotal.toFixed(2)}
                          </div>
                        </div>

                        {venda.desconto_valor > 0 && (
                          <div>
                            <span className="text-gray-500">Desconto:</span>
                            <div className="font-medium text-red-600">
                              - R$ {venda.desconto_valor.toFixed(2)}
                            </div>
                          </div>
                        )}

                        {venda.taxa_entrega > 0 && (
                          <div>
                            <span className="text-gray-500">Taxa Entrega:</span>
                            <div className="font-medium text-gray-900">
                              R$ {venda.taxa_entrega.toFixed(2)}
                            </div>
                          </div>
                        )}

                        <div>
                          <span className="text-gray-500">Total:</span>
                          <div className="font-bold text-gray-900 text-lg">
                            R$ {venda.total.toFixed(2)}
                          </div>
                        </div>

                        {venda.saldo_devedor > 0 && (
                          <div>
                            <span className="text-gray-500">Saldo Devedor:</span>
                            <div className="font-bold text-red-600">
                              R$ {venda.saldo_devedor.toFixed(2)}
                            </div>
                          </div>
                        )}

                        <div>
                          <span className="text-gray-500">Itens:</span>
                          <div className="font-medium text-gray-900">
                            {venda.total_itens}
                          </div>
                        </div>

                        {venda.vendedor_nome && (
                          <div>
                            <span className="text-gray-500">Vendedor:</span>
                            <div className="font-medium text-gray-900">
                              {venda.vendedor_nome}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
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
