import { useState, useEffect } from 'react';
import { X, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import api from '../api';
import toast from 'react-hot-toast';

export default function ModalMovimentacoesCaixa({ caixaId, onClose }) {
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [caixa, setCaixa] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    carregarMovimentacoes();
  }, [caixaId]);

  const carregarMovimentacoes = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/caixas/${caixaId}/movimentacoes`);
      setMovimentacoes(response.data.movimentacoes);
      setCaixa(response.data.caixa);
    } catch (error) {
      console.error('Erro ao carregar movimentações:', error);
      toast.error('Erro ao carregar movimentações do caixa');
    } finally {
      setLoading(false);
    }
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(data);
  };

  const getTipoLabel = (tipo) => {
    const labels = {
      'venda': 'Venda',
      'suprimento': 'Suprimento',
      'sangria': 'Sangria',
      'despesa': 'Despesa',
      'devolucao': 'Devolução',
      'transferencia': 'Transferência'
    };
    return labels[tipo] || tipo;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-blue-50 to-purple-50">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              📋 Extrato do Caixa
            </h2>
            {caixa && (
              <p className="text-sm text-gray-600 mt-1">
                Caixa #{caixa.id} - {caixa.nome} | Status: {caixa.status}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={carregarMovimentacoes}
              className="p-2 hover:bg-white rounded-lg transition-colors"
              title="Atualizar"
            >
              <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : movimentacoes.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-gray-500 text-lg">Nenhuma movimentação registrada</p>
            </div>
          ) : (
            <div className="space-y-3">
              {movimentacoes.map((mov) => (
                <div
                  key={mov.id}
                  className={`p-4 rounded-lg border-2 ${
                    mov.natureza === 'entrada'
                      ? 'bg-green-50 border-green-200'
                      : mov.natureza === 'saida'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    {/* Info principal */}
                    <div className="flex items-start gap-3 flex-1">
                      <div className="text-3xl">{mov.emoji}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            {getTipoLabel(mov.tipo)}
                          </span>
                          {mov.forma_pagamento && (
                            <span className="text-xs bg-white px-2 py-1 rounded border">
                              {mov.forma_pagamento}
                            </span>
                          )}
                        </div>
                        
                        {mov.descricao && (
                          <p className="text-sm text-gray-700 mt-1">{mov.descricao}</p>
                        )}
                        
                        <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-600">
                          <span>🕐 {formatarData(mov.data_movimento)}</span>
                          <span>👤 {mov.usuario_nome}</span>
                          {mov.venda_id && (
                            <span>🧾 Venda #{mov.venda_numero || mov.venda_id}</span>
                          )}
                          {mov.documento && (
                            <span>📄 {mov.documento}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Valor */}
                    <div className="text-right ml-4">
                      <div
                        className={`text-2xl font-bold ${
                          mov.natureza === 'entrada'
                            ? 'text-green-600'
                            : mov.natureza === 'saida'
                            ? 'text-red-600'
                            : 'text-gray-600'
                        }`}
                      >
                        {mov.natureza === 'entrada' && '+'}
                        {mov.natureza === 'saida' && '-'}
                        R$ {mov.valor.toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {mov.natureza === 'entrada' ? (
                          <span className="flex items-center gap-1 justify-end">
                            <TrendingUp className="w-3 h-3" /> Entrada
                          </span>
                        ) : mov.natureza === 'saida' ? (
                          <span className="flex items-center gap-1 justify-end">
                            <TrendingDown className="w-3 h-3" /> Saída
                          </span>
                        ) : (
                          'Neutro'
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
        <div className="border-t p-4 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {movimentacoes.length} movimentação(ões) encontrada(s)
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
