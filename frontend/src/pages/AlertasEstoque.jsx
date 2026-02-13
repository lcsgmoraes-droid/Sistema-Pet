/**
 * 📊 Página de Alertas de Estoque Negativo
 * Sistema de monitoramento e gerenciamento de estoque crítico
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle, TrendingDown, Package, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getAlertasPendentes,
  getTodosAlertas,
  getDashboardAlertas,
  resolverAlerta
} from '../api/alertasEstoque';

export default function AlertasEstoque() {
  const [alertasPendentes, setAlertasPendentes] = useState([]);
  const [todosAlertas, setTodosAlertas] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState('pendentes'); // 'pendentes' | 'historico' | 'dashboard'

  useEffect(() => {
    carregarDados();
  }, [abaAtiva]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      if (abaAtiva === 'pendentes') {
        const response = await getAlertasPendentes();
        setAlertasPendentes(response.data);
      } else if (abaAtiva === 'historico') {
        const response = await getTodosAlertas();
        setTodosAlertas(response.data);
      } else if (abaAtiva === 'dashboard') {
        const response = await getDashboardAlertas();
        setDashboard(response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar alertas:', error);
      toast.error('Erro ao carregar alertas de estoque');
    } finally {
      setLoading(false);
    }
  };

  const handleResolverAlerta = async (alertaId, acao) => {
    try {
      await resolverAlerta(alertaId, acao);
      toast.success(acao === 'resolvido' ? 'Alerta resolvido com sucesso!' : 'Alerta ignorado');
      carregarDados();
    } catch (error) {
      console.error('Erro ao resolver alerta:', error);
      toast.error('Erro ao processar alerta');
    }
  };

  const getCriticidadeBadge = (criticidade) => {
    const cores = {
      'CRITICO': 'bg-red-100 text-red-800 border-red-300',
      'ALTO': 'bg-orange-100 text-orange-800 border-orange-300',
      'MEDIO': 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'BAIXO': 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return cores[criticidade] || cores['MEDIO'];
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <AlertTriangle className="text-red-500" />
          Alertas de Estoque Negativo
        </h1>
        <p className="text-gray-600 mt-2">
          Monitoramento em tempo real de produtos com estoque crítico
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setAbaAtiva('pendentes')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                abaAtiva === 'pendentes'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} />
                Pendentes
                {alertasPendentes.length > 0 && (
                  <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                    {alertasPendentes.length}
                  </span>
                )}
              </div>
            </button>
            <button
              onClick={() => setAbaAtiva('dashboard')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                abaAtiva === 'dashboard'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <TrendingDown size={18} />
                Dashboard
              </div>
            </button>
            <button
              onClick={() => setAbaAtiva('historico')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                abaAtiva === 'historico'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <Package size={18} />
                Histórico
              </div>
            </button>
          </nav>
        </div>
      </div>

      {/* Botão Atualizar */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={carregarDados}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* Conteúdo das Abas */}
      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <RefreshCw className="animate-spin mx-auto text-gray-400" size={48} />
          <p className="text-gray-600 mt-4">Carregando...</p>
        </div>
      ) : (
        <>
          {/* Aba Pendentes */}
          {abaAtiva === 'pendentes' && (
            <div className="space-y-4">
              {alertasPendentes.length === 0 ? (
                <div className="bg-white rounded-lg shadow-sm p-12 text-center">
                  <CheckCircle className="mx-auto text-green-500" size={64} />
                  <h3 className="text-xl font-semibold text-gray-900 mt-4">
                    Nenhum alerta pendente!
                  </h3>
                  <p className="text-gray-600 mt-2">
                    Todos os produtos estão com estoque adequado.
                  </p>
                </div>
              ) : (
                alertasPendentes.map((alerta) => (
                  <div
                    key={alerta.id}
                    className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {alerta.produto_nome}
                          </h3>
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-medium border ${getCriticidadeBadge(
                              alerta.criticidade
                            )}`}
                          >
                            {alerta.criticidade}
                          </span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                          <div>
                            <p className="text-sm text-gray-500">Estoque Anterior</p>
                            <p className="text-lg font-semibold text-gray-900">
                              {alerta.estoque_anterior}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">Estoque Resultante</p>
                            <p className="text-lg font-semibold text-red-600">
                              {alerta.estoque_resultante}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">Quantidade Vendida</p>
                            <p className="text-lg font-semibold text-gray-900">
                              {alerta.quantidade_vendida}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">Venda</p>
                            <p className="text-lg font-semibold text-blue-600">
                              {alerta.venda_codigo ? `#${alerta.venda_codigo}` : (alerta.venda_id ? `ID: ${alerta.venda_id}` : 'N/A')}
                            </p>
                          </div>
                        </div>

                        <div className="mt-4 text-sm text-gray-600">
                          <p>
                            <strong>Data:</strong> {formatarData(alerta.data_alerta)}
                          </p>
                          {alerta.observacao && (
                            <p className="mt-1">
                              <strong>Observação:</strong> {alerta.observacao}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-col gap-2 ml-4">
                        <button
                          onClick={() => handleResolverAlerta(alerta.id, 'resolvido')}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                        >
                          <CheckCircle size={16} />
                          Resolver
                        </button>
                        <button
                          onClick={() => handleResolverAlerta(alerta.id, 'ignorado')}
                          className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm"
                        >
                          <XCircle size={16} />
                          Ignorar
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Aba Dashboard */}
          {abaAtiva === 'dashboard' && dashboard && (
            <div className="space-y-6">
              {/* Métricas Resumidas */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Total de Alertas</p>
                      <p className="text-3xl font-bold text-gray-900 mt-2">
                        {dashboard.total_alertas}
                      </p>
                    </div>
                    <AlertTriangle className="text-gray-400" size={40} />
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6 border border-red-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Pendentes</p>
                      <p className="text-3xl font-bold text-red-600 mt-2">
                        {dashboard.alertas_pendentes}
                      </p>
                    </div>
                    <AlertTriangle className="text-red-400" size={40} />
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6 border border-orange-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Críticos</p>
                      <p className="text-3xl font-bold text-orange-600 mt-2">
                        {dashboard.alertas_criticos}
                      </p>
                    </div>
                    <TrendingDown className="text-orange-400" size={40} />
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6 border border-green-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Resolvidos</p>
                      <p className="text-3xl font-bold text-green-600 mt-2">
                        {dashboard.alertas_resolvidos}
                      </p>
                    </div>
                    <CheckCircle className="text-green-400" size={40} />
                  </div>
                </div>
              </div>

              {/* Produtos com Estoque Negativo */}
              {dashboard.produtos_estoque_negativo && dashboard.produtos_estoque_negativo.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Package className="text-red-500" />
                    Produtos com Estoque Negativo Atual
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Produto
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Estoque Atual
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Alertas Pendentes
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {dashboard.produtos_estoque_negativo.map((produto, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {produto.nome}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-red-600">
                              {produto.estoque_atual}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                              {produto.alertas_pendentes}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Aba Histórico */}
          {abaAtiva === 'historico' && (
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Produto
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Criticidade
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Estoque Ant.
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Estoque Res.
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Venda
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {todosAlertas.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="px-6 py-12 text-center text-gray-500">
                          Nenhum alerta registrado
                        </td>
                      </tr>
                    ) : (
                      todosAlertas.map((alerta) => (
                        <tr key={alerta.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatarData(alerta.data_alerta)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {alerta.produto_nome}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-center">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${getCriticidadeBadge(
                                alerta.criticidade
                              )}`}
                            >
                              {alerta.criticidade}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                            {alerta.estoque_anterior}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-semibold text-red-600">
                            {alerta.estoque_resultante}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-center">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${
                                alerta.resolvido
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {alerta.resolvido ? 'Resolvido' : 'Pendente'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-blue-600 font-medium">
                            {alerta.venda_codigo ? `#${alerta.venda_codigo}` : (alerta.venda_id ? `ID: ${alerta.venda_id}` : 'N/A')}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
