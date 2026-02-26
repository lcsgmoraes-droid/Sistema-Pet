import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  DollarSign,
  Calendar,
  Clock,
  TrendingUp,
  TrendingDown,
  Receipt,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Download
} from 'lucide-react';
import { listarCaixas, obterResumoCaixa, reabrirCaixa } from '../api/caixa';

export default function MeusCaixas() {
  const navigate = useNavigate();
  const [caixas, setCaixas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    data_inicio: '',
    data_fim: '',
    status: ''
  });

  useEffect(() => {
    carregarCaixas();
  }, [filtros]);

  const carregarCaixas = async () => {
    try {
      setLoading(true);
      const params = {};
      
      if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
      if (filtros.data_fim) params.data_fim = filtros.data_fim;
      if (filtros.status) params.status_filter = filtros.status;
      
      const response = await listarCaixas(params);
      setCaixas(response);
    } catch (error) {
      console.error('Erro ao carregar caixas:', error);
      alert('Erro ao carregar histÃ³rico de caixas');
    } finally {
      setLoading(false);
    }
  };

  const handleReabrir = async (caixaId) => {
    if (!confirm('Deseja realmente reabrir este caixa?')) return;

    try {
      await reabrirCaixa(caixaId);
      alert('Caixa reaberto com sucesso!');
      navigate('/pdv'); // Redirecionar para o PDV
    } catch (error) {
      console.error('Erro ao reabrir caixa:', error);
      alert(error.response?.data?.detail || 'Erro ao reabrir caixa');
    }
  };

  const handleDownloadPDF = async (caixaId, numeroCaixa) => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_URL || '/api';
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const response = await fetch(`${apiBaseUrl}/caixas/${caixaId}/pdf`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Erro ao gerar PDF');
      }

      // Converter resposta em blob
      const blob = await response.blob();
      
      // Criar URL temporÃ¡ria e fazer download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Caixa_${numeroCaixa}_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      alert('PDF baixado com sucesso!');
    } catch (error) {
      console.error('Erro ao baixar PDF:', error);
      alert('Erro ao gerar PDF do caixa');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      aberto: { cor: 'bg-green-100 text-green-800', icone: CheckCircle, texto: 'Aberto' },
      fechado: { cor: 'bg-gray-100 text-gray-800', icone: XCircle, texto: 'Fechado' }
    };

    const badge = badges[status] || badges.fechado;
    const Icone = badge.icone;

    return (
      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${badge.cor}`}>
        <Icone className="w-4 h-4" />
        {badge.texto}
      </span>
    );
  };

  const calcularDiferenca = (esperado, informado) => {
    const dif = informado - esperado;
    return {
      valor: Math.abs(dif),
      tipo: dif > 0 ? 'sobra' : dif < 0 ? 'falta' : 'ok'
    };
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Meus Caixas</h1>
        <p className="text-gray-600 mt-1">HistÃ³rico e gestÃ£o dos seus caixas</p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data InÃ­cio
            </label>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Fim
            </label>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filtros.status}
              onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="aberto">Aberto</option>
              <option value="fechado">Fechado</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFiltros({ data_inicio: '', data_fim: '', status: '' })}
              className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              Limpar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Lista de Caixas */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando caixas...</p>
        </div>
      ) : caixas.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow-sm">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Nenhum caixa encontrado</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {caixas.map((caixa) => {
            const diferenca = caixa.status === 'fechado' && caixa.valor_esperado 
              ? calcularDiferenca(caixa.valor_esperado, caixa.valor_informado)
              : null;

            return (
              <div key={caixa.id} className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow">
                <div className="p-6">
                  {/* Header do Card */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
                        <DollarSign className="w-8 h-8 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">
                          Caixa #{caixa.numero_caixa}
                        </h3>
                        <p className="text-sm text-gray-600">{caixa.usuario_nome}</p>
                      </div>
                    </div>
                    {getStatusBadge(caixa.status)}
                  </div>

                  {/* Datas */}
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="w-4 h-4" />
                      <span>Abertura: {new Date(caixa.data_abertura).toLocaleString('pt-BR')}</span>
                    </div>
                    {caixa.data_fechamento && (
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Clock className="w-4 h-4" />
                        <span>Fechamento: {new Date(caixa.data_fechamento).toLocaleString('pt-BR')}</span>
                      </div>
                    )}
                  </div>

                  {/* Valores */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-600 mb-1">Abertura</div>
                      <div className="text-lg font-semibold text-gray-900">
                        R$ {caixa.valor_abertura.toFixed(2)}
                      </div>
                    </div>

                    {caixa.status === 'fechado' && caixa.valor_esperado && (
                      <>
                        <div className="bg-blue-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">Esperado</div>
                          <div className="text-lg font-semibold text-blue-900">
                            R$ {caixa.valor_esperado.toFixed(2)}
                          </div>
                        </div>

                        <div className="bg-green-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">Informado</div>
                          <div className="text-lg font-semibold text-green-900">
                            R$ {caixa.valor_informado.toFixed(2)}
                          </div>
                        </div>

                        <div className={`rounded-lg p-3 ${
                          diferenca.tipo === 'ok' ? 'bg-gray-50' :
                          diferenca.tipo === 'sobra' ? 'bg-green-50' : 'bg-red-50'
                        }`}>
                          <div className="text-xs text-gray-600 mb-1">DiferenÃ§a</div>
                          <div className={`text-lg font-semibold ${
                            diferenca.tipo === 'ok' ? 'text-gray-900' :
                            diferenca.tipo === 'sobra' ? 'text-green-900' : 'text-red-900'
                          }`}>
                            {diferenca.tipo === 'sobra' && '+'}
                            {diferenca.tipo === 'falta' && '-'}
                            R$ {diferenca.valor.toFixed(2)}
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* ObservaÃ§Ãµes */}
                  {(caixa.observacoes_abertura || caixa.observacoes_fechamento) && (
                    <div className="border-t pt-4 mb-4">
                      {caixa.observacoes_abertura && (
                        <p className="text-sm text-gray-600 mb-2">
                          <span className="font-medium">Obs. Abertura:</span> {caixa.observacoes_abertura}
                        </p>
                      )}
                      {caixa.observacoes_fechamento && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Obs. Fechamento:</span> {caixa.observacoes_fechamento}
                        </p>
                      )}
                    </div>
                  )}

                  {/* AÃ§Ãµes */}
                  {caixa.status === 'fechado' && (
                    <div className="border-t pt-4 flex gap-3">
                      <button
                        onClick={() => handleReabrir(caixa.id)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Reabrir Caixa
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(caixa.id, caixa.numero_caixa)}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        Baixar PDF
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

