/**
 * 📊 Página de Alertas de Estoque Negativo
 * Sistema de monitoramento e gerenciamento de estoque crítico
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, TrendingDown, Package, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getAlertasPendentes,
  getTodosAlertas,
  getDashboardAlertas,
  resolverAlerta
} from '../api/alertasEstoque';
import { getProdutos } from '../api/produtos';

export default function AlertasEstoque() {
  const navigate = useNavigate();
  const [alertasPendentes, setAlertasPendentes] = useState([]);
  const [todosAlertas, setTodosAlertas] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState('pendentes'); // 'pendentes' | 'historico' | 'dashboard'
  const [produtosBrutos, setProdutosBrutos] = useState([]);

  useEffect(() => {
    carregarDados();
  }, [abaAtiva]);

  useEffect(() => {
    getProdutos({ limit: 5000, ativo: true })
      .then(res => {
        const lista = Array.isArray(res.data) ? res.data
          : Array.isArray(res.data?.itens) ? res.data.itens
          : Array.isArray(res.data?.produtos) ? res.data.produtos
          : [];
        setProdutosBrutos(lista);
      })
      .catch(() => {});
  }, []);

  const insights = useMemo(() => {
    const ativos = (produtosBrutos || []).filter(
      p => p?.ativo !== false && p?.tipo_produto !== 'PAI'
    );
    const est = p => Number(p?.estoque_atual ?? p?.estoque ?? 0);
    const min = p => Number(p?.estoque_minimo ?? 0);

    const rupturas = ativos.filter(p => est(p) <= 0);
    const riscoRuptura = ativos.filter(p => {
      const a = est(p); const m = Math.max(1, min(p));
      return a > 0 && a <= m;
    });
    const excessoEstoque = ativos.filter(p => {
      const m = min(p); return m > 0 && est(p) >= m * 4;
    });
    const margemBaixa = ativos
      .map(p => {
        const pv = Number(p?.preco_venda ?? 0);
        const pc = Number(p?.preco_custo ?? 0);
        const margem = pv ? Number((((pv - pc) / pv) * 100).toFixed(2)) : 0;
        return { ...p, margem };
      })
      .filter(p => p.margem > 0 && p.margem < 15)
      .sort((a, b) => a.margem - b.margem)
      .slice(0, 5);
    const sugestoesReposicao = riscoRuptura.slice(0, 5).map(p => ({
      ...p,
      sugestao: Math.max(Math.max(1, min(p)) * 2 - est(p), 1),
    }));
    return { totalAtivos: ativos.length, rupturas, riscoRuptura, excessoEstoque, margemBaixa, sugestoesReposicao };
  }, [produtosBrutos]);

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

  const handleResolverAlerta = async (alertaId, acao, produtoId = null) => {
    if (acao === 'resolvido' && produtoId) {
      // Redirecionar para página de produtos para fazer ajuste de estoque
      navigate(`/produtos?produto_id=${produtoId}`);
      toast.info('Redirecionando para ajustar o estoque do produto...');
      return;
    }
    
    // Apenas ignorar o alerta
    try {
      await resolverAlerta(alertaId, acao);
      toast.success('Alerta ignorado com sucesso');
      carregarDados();
    } catch (error) {
      console.error('Erro ao ignorar alerta:', error);
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

      {/* Análises Inteligentes */}
      {produtosBrutos.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-5 mb-6 border border-indigo-100">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Análises Inteligentes</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <div className="p-3 rounded-lg bg-red-50 border border-red-200">
              <div className="text-xs text-red-700">Ruptura</div>
              <div className="text-2xl font-bold text-red-700">{insights.rupturas.length}</div>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
              <div className="text-xs text-amber-700">Risco de ruptura</div>
              <div className="text-2xl font-bold text-amber-700">{insights.riscoRuptura.length}</div>
            </div>
            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
              <div className="text-xs text-blue-700">Excesso de estoque</div>
              <div className="text-2xl font-bold text-blue-700">{insights.excessoEstoque.length}</div>
            </div>
            <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
              <div className="text-xs text-purple-700">Ativos monitorados</div>
              <div className="text-2xl font-bold text-purple-700">{insights.totalAtivos}</div>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Sugestão de reposição imediata</h3>
              {insights.sugestoesReposicao.length === 0 ? (
                <p className="text-sm text-gray-500">Nenhuma reposição urgente agora.</p>
              ) : (
                <div className="space-y-2">
                  {insights.sugestoesReposicao.map(p => (
                    <div key={p.id} className="text-sm p-2 rounded bg-gray-50 border border-gray-200 flex items-center justify-between gap-2">
                      <button
                        onClick={() => navigate(`/produtos/${p.id}/movimentacoes`)}
                        className="font-medium text-gray-800 hover:text-indigo-700 hover:underline text-left"
                      >
                        {p.nome}
                      </button>
                      <span className="text-gray-600 whitespace-nowrap">
                        estoque {Number(p.estoque_atual ?? p.estoque ?? 0)} — comprar <strong>{p.sugestao}</strong>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Produtos com margem crítica</h3>
              {insights.margemBaixa.length === 0 ? (
                <p className="text-sm text-gray-500">Nenhum produto com margem abaixo de 15%.</p>
              ) : (
                <div className="space-y-2">
                  {insights.margemBaixa.map(p => (
                    <div key={p.id} className="text-sm p-2 rounded bg-red-50 border border-red-100 flex items-center justify-between gap-2">
                      <button
                        onClick={() => navigate(`/produtos/${p.id}/movimentacoes`)}
                        className="font-medium text-red-800 hover:underline text-left"
                      >
                        {p.nome}
                      </button>
                      <span className="text-red-700 whitespace-nowrap">
                        margem <strong>{p.margem.toFixed(1)}%</strong>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
                          onClick={() => handleResolverAlerta(alerta.id, 'resolvido', alerta.produto_id)}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                          title="Ir para o produto e fazer ajuste de estoque"
                        >
                          <Package size={16} />
                          Ajustar Estoque
                        </button>
                        <button
                          onClick={() => handleResolverAlerta(alerta.id, 'ignorado')}
                          className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm"
                          title="Ignorar este alerta (aceitar estoque negativo)"
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
