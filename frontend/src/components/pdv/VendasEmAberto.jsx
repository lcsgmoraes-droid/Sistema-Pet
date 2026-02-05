import { useState, useEffect } from 'react';
import { X, DollarSign, Calendar, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../api';

export default function VendasEmAberto({ clienteId, clienteNome, onClose, onSucesso }) {
  const [vendas, setVendas] = useState([]);
  const [vendasSelecionadas, setVendasSelecionadas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [valorPagamento, setValorPagamento] = useState('');
  const [formaPagamento, setFormaPagamento] = useState('dinheiro');
  const [numeroTransacao, setNumeroTransacao] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [resumo, setResumo] = useState({ total_vendas: 0, total_em_aberto: 0 });
  const [ordenacao, setOrdenacao] = useState('antiga'); // 'antiga' ou 'recente'

  useEffect(() => {
    carregarVendasEmAberto();
  }, [clienteId]);

  const carregarVendasEmAberto = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/clientes/${clienteId}/vendas-em-aberto`);
      setVendas(response.data.vendas || []);
      setResumo(response.data.resumo || { total_vendas: 0, total_em_aberto: 0 });
    } catch (error) {
      console.error('Erro ao carregar vendas em aberto:', error);
      toast.error('Erro ao carregar vendas em aberto');
    } finally {
      setLoading(false);
    }
  };

  const toggleVenda = (vendaId) => {
    setVendasSelecionadas(prev => {
      if (prev.includes(vendaId)) {
        return prev.filter(id => id !== vendaId);
      } else {
        return [...prev, vendaId];
      }
    });
  };

  const selecionarTodas = () => {
    if (vendasSelecionadas.length === vendas.length) {
      setVendasSelecionadas([]);
    } else {
      setVendasSelecionadas(vendas.map(v => v.id));
    }
  };

  const calcularDiasEmAberto = (dataVenda) => {
    const hoje = new Date();
    const data = new Date(dataVenda);
    const diffTime = Math.abs(hoje - data);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Ordenar vendas
  const vendasOrdenadas = [...vendas].sort((a, b) => {
    if (ordenacao === 'antiga') {
      return new Date(a.data_venda) - new Date(b.data_venda);
    } else {
      return new Date(b.data_venda) - new Date(a.data_venda);
    }
  });

  const totalSelecionado = vendas
    .filter(v => vendasSelecionadas.includes(v.id))
    .reduce((sum, v) => sum + parseFloat(v.saldo_devedor), 0);

  const handleBaixarVendas = async () => {
    if (vendasSelecionadas.length === 0) {
      toast.error('Selecione ao menos uma venda');
      return;
    }

    if (!valorPagamento || parseFloat(valorPagamento) <= 0) {
      toast.error('Informe um valor válido');
      return;
    }

    if (parseFloat(valorPagamento) > totalSelecionado) {
      toast.error('Valor do pagamento não pode ser maior que o total selecionado');
      return;
    }

    try {
      setProcessando(true);
      console.log('Enviando requisição:', {
        vendas_ids: vendasSelecionadas,
        valor_total: parseFloat(valorPagamento),
        forma_pagamento: formaPagamento,
        numero_transacao: numeroTransacao || null,
        observacoes: observacoes || null
      });
      
      const response = await api.post(`/clientes/${clienteId}/baixar-vendas-lote`, {
        vendas_ids: vendasSelecionadas,
        valor_total: parseFloat(valorPagamento),
        forma_pagamento: formaPagamento,
        numero_transacao: numeroTransacao || null,
        observacoes: observacoes || null
      });

      console.log('Resposta completa:', response);
      console.log('Response.data:', response.data);

      if (!response.data) {
        throw new Error('Resposta vazia do servidor');
      }

      const { vendas_quitadas, vendas_parciais, total_vendas_afetadas, valor_total_baixado } = response.data;

      // Mensagem de sucesso detalhada
      let mensagem = `💰 Total baixado: R$ ${valor_total_baixado.toFixed(2)}\n`;
      
      if (vendas_quitadas.length > 0) {
        mensagem += `\n✅ ${vendas_quitadas.length} venda(s) quitada(s):`;
        vendas_quitadas.forEach(v => {
          mensagem += `\n  • ${v.numero_venda}: R$ ${v.valor_baixado.toFixed(2)}`;
        });
      }
      
      if (vendas_parciais.length > 0) {
        mensagem += `\n\n⚠️ ${vendas_parciais.length} venda(s) parcial:`;
        vendas_parciais.forEach(v => {
          mensagem += `\n  • ${v.numero_venda}:`;
          mensagem += `\n    Baixado: R$ ${v.valor_baixado.toFixed(2)}`;
          mensagem += `\n    Falta: R$ ${v.saldo_restante.toFixed(2)}`;
        });
      }

      toast.success(mensagem, { duration: 6000 });
      
      if (onSucesso) {
        onSucesso();
      }
      
      onClose();
    } catch (error) {
      console.error('Erro completo:', error);
      console.error('Erro response:', error.response);
      console.error('Erro response data:', error.response?.data);
      console.error('Erro response status:', error.response?.status);
      
      const mensagemErro = error.response?.data?.detail || error.message || 'Erro ao baixar vendas';
      toast.error(mensagemErro);
    } finally {
      setProcessando(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4">
          <div className="flex items-center justify-center">
            <Loader className="w-8 h-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">Carregando vendas...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-red-50 to-orange-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Vendas em Aberto</h2>
              <p className="text-gray-600 mt-1">{clienteNome}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Resumo */}
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-sm text-gray-600">Total de Vendas</div>
              <div className="text-2xl font-bold text-gray-900">{resumo.total_vendas}</div>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-sm text-gray-600">Total em Aberto</div>
              <div className="text-2xl font-bold text-red-600">
                R$ {resumo.total_em_aberto.toFixed(2)}
              </div>
            </div>
          </div>
        </div>

        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto p-6">
          {vendas.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <p className="text-xl font-medium text-gray-900">Nenhuma venda em aberto!</p>
              <p className="text-gray-600 mt-2">Este cliente não possui débitos pendentes.</p>
            </div>
          ) : (
            <>
              {/* Controles */}
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <button
                    onClick={selecionarTodas}
                    className="text-blue-600 hover:text-blue-700 font-medium text-sm"
                  >
                    {vendasSelecionadas.length === vendas.length ? 'Desmarcar todas' : 'Selecionar todas'}
                  </button>
                  <button
                    onClick={() => setOrdenacao(ordenacao === 'antiga' ? 'recente' : 'antiga')}
                    className="text-sm text-gray-600 hover:text-gray-700 flex items-center gap-1 font-medium"
                  >
                    📅 {ordenacao === 'antiga' ? '↑ Mais Antigas' : '↓ Mais Recentes'}
                  </button>
                </div>
                <div className="text-sm text-gray-600">
                  {vendasSelecionadas.length} de {vendas.length} selecionada(s)
                </div>
              </div>

              {/* Tabela de Vendas */}
              <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        <input
                          type="checkbox"
                          checked={vendasSelecionadas.length === vendas.length}
                          onChange={selecionarTodas}
                          className="rounded border-gray-300"
                        />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Venda</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pago</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Saldo Devedor</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Dias</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {vendasOrdenadas.map((venda) => {
                      const dias = calcularDiasEmAberto(venda.data_venda);
                      const isVencido = dias > 30;
                      
                      return (
                        <tr
                          key={venda.id}
                          className={`hover:bg-gray-50 ${vendasSelecionadas.includes(venda.id) ? 'bg-blue-50' : ''}`}
                        >
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={vendasSelecionadas.includes(venda.id)}
                              onChange={() => toggleVenda(venda.id)}
                              className="rounded border-gray-300"
                            />
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-900">
                            #{venda.numero_venda}
                          </td>
                          <td className="px-4 py-3 text-gray-600 text-sm">
                            {new Date(venda.data_venda).toLocaleDateString('pt-BR')}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-900">
                            R$ {parseFloat(venda.total).toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right text-green-600">
                            R$ {parseFloat(venda.total_pago).toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-red-600">
                            R$ {parseFloat(venda.saldo_devedor).toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                isVencido
                                  ? 'bg-red-100 text-red-800'
                                  : dias > 15
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-green-100 text-green-800'
                              }`}
                            >
                              {dias} {dias === 1 ? 'dia' : 'dias'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Formulário de Pagamento */}
              {vendasSelecionadas.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Registrar Pagamento</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Valor Total Selecionado
                      </label>
                      <div className="text-2xl font-bold text-blue-600">
                        R$ {totalSelecionado.toFixed(2)}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Valor do Pagamento *
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={valorPagamento}
                        onChange={(e) => setValorPagamento(e.target.value)}
                        placeholder="0.00"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Forma de Pagamento *
                      </label>
                      <select
                        value={formaPagamento}
                        onChange={(e) => setFormaPagamento(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="dinheiro">Dinheiro</option>
                        <option value="pix">PIX</option>
                        <option value="debito">Cartão de Débito</option>
                        <option value="credito">Cartão de Crédito</option>
                        <option value="transferencia">Transferência</option>
                      </select>
                    </div>

                    {(formaPagamento === 'pix' || formaPagamento === 'transferencia') && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Número da Transação
                        </label>
                        <input
                          type="text"
                          value={numeroTransacao}
                          onChange={(e) => setNumeroTransacao(e.target.value)}
                          placeholder="Código/ID da transação"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    )}
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Observações
                    </label>
                    <textarea
                      value={observacoes}
                      onChange={(e) => setObservacoes(e.target.value)}
                      rows="2"
                      placeholder="Informações adicionais sobre o pagamento..."
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-start space-x-2 mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-yellow-800">
                      <strong>Atenção:</strong> O valor será aplicado automaticamente da venda mais antiga para a mais recente. 
                      Se o valor for insuficiente para quitar todas as vendas selecionadas, a última venda ficará parcialmente paga.
                    </div>
                  </div>

                  <button
                    onClick={handleBaixarVendas}
                    disabled={processando || !valorPagamento || parseFloat(valorPagamento) <= 0}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {processando ? (
                      <>
                        <Loader className="w-5 h-5 animate-spin" />
                        <span>Processando...</span>
                      </>
                    ) : (
                      <>
                        <DollarSign className="w-5 h-5" />
                        <span>Baixar Vendas Selecionadas</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
