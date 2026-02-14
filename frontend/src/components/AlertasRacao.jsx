import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, RefreshCw, Archive, BarChart3, Lightbulb, Edit } from 'lucide-react';
import api from '../api';
import toast from 'react-hot-toast';
import DashboardAnaliseRacoes from './DashboardAnaliseRacoes';
import SugestoesInteligentesRacoes from './SugestoesInteligentesRacoes';

function AlertasRacao() {
  const navigate = useNavigate();
  const [abaAtiva, setAbaAtiva] = useState('dashboard'); // dashboard, alertas, sugestoes
  const [racoesSemClassificacao, setRacoesSemClassificacao] = useState([]);
  const [loading, setLoading] = useState(false);
  const [classificandoIds, setClassificandoIds] = useState(new Set());
  const [stats, setStats] = useState({ total: 0, limite: 50, offset: 0 });
  const [especieFiltro, setEspecieFiltro] = useState(''); // Filtro de espécie

  const especiesDisponiveis = [
    { value: '', label: 'Todas as espécies' },
    { value: 'dog', label: 'Cães' },
    { value: 'cat', label: 'Gatos' },
    { value: 'bird', label: 'Pássaros' },
    { value: 'rodent', label: 'Roedores' },
    { value: 'fish', label: 'Peixes' }
  ];

  // Carregar contagem de alertas ao montar (para badge)
  useEffect(() => {
    carregarContagemAlertas();
  }, []);

  useEffect(() => {
    if (abaAtiva === 'alertas') {
      carregarAlertasRacao();
    }
  }, [especieFiltro, abaAtiva]); // Recarregar quando filtro ou aba mudar

  const carregarContagemAlertas = async () => {
    try {
      const response = await api.get('/produtos/racao/alertas', { 
        params: { limite: 1, offset: 0 }
      });
      setStats(prev => ({ ...prev, total: response.data.total }));
    } catch (error) {
      console.error('Erro ao carregar contagem de alertas:', error);
    }
  };

  const carregarAlertasRacao = async () => {
    setLoading(true);
    try {
      const params = { limite: 50, offset: 0 };
      if (especieFiltro) {
        params.especie = especieFiltro;
      }
      
      const response = await api.get('/produtos/racao/alertas', { params });
      setRacoesSemClassificacao(response.data.items || []);
      setStats({
        total: response.data.total,
        limite: response.data.limite,
        offset: response.data.offset
      });
    } catch (error) {
      console.error('Erro ao carregar alertas:', error);
      toast.error('Erro ao carregar alertas de rações');
    } finally {
      setLoading(false);
    }
  };

  const classificarProduto = async (produtoId) => {
    setClassificandoIds(prev => new Set(prev).add(produtoId));
    try {
      const response = await api.post(`/produtos/${produtoId}/classificar-ia`, null, {
        params: { forcar: true }
      });
      
      toast.success(
        `${response.data.campos_atualizados.length} campos classificados! Score: ${response.data.confianca.score}%`,
        { duration: 4000 }
      );
      
      // Remover da lista local
      setRacoesSemClassificacao(prev => prev.filter(r => r.id !== produtoId));
      setStats(prev => ({ ...prev, total: prev.total - 1 }));
      
    } catch (error) {
      console.error('Erro ao classificar produto:', error);
      toast.error('Erro ao classificar produto');
    } finally {
      setClassificandoIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(produtoId);
        return newSet;
      });
    }
  };

  const classificarTodos = async () => {
    setLoading(true);
    try {
      const response = await api.post('/produtos/classificar-lote', null, {
        params: { apenas_sem_classificacao: true }
      });
      
      toast.success(
        `${response.data.sucessos} produtos classificados com sucesso!`,
        { duration: 5000 }
      );
      
      if (response.data.erros > 0) {
        toast.error(`${response.data.erros} produtos com erro na classificação`);
      }
      
      // Recarregar lista
      await carregarAlertasRacao();
      
    } catch (error) {
      console.error('Erro ao classificar lote:', error);
      toast.error('Erro ao classificar produtos em lote');
    } finally {
      setLoading(false);
    }
  };

  const getChamadaAtencao = (completude) => {
    if (completude >= 75) return { cor: 'text-yellow-600 bg-yellow-50', texto: 'Quase completo' };
    if (completude >= 50) return { cor: 'text-orange-600 bg-orange-50', texto: 'Incompleto' };
    return { cor: 'text-red-600 bg-red-50', texto: 'Muito incompleto' };
  };

  const traduzirCampo = (campo) => {
    const traducoes = {
      porte_animal: 'Porte',
      fase_publico: 'Fase',
      sabor_proteina: 'Sabor/Proteína',
      peso_embalagem: 'Peso'
    };
    return traducoes[campo] || campo;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header com Título e Tabs */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-8 h-8 text-amber-600" />
          <h1 className="text-2xl font-bold text-gray-800">
            Sistema Inteligente de Rações
          </h1>
        </div>
        
        {/* Tabs Navigation */}
        <div className="flex gap-2 border-b border-gray-200">
          <button
            onClick={() => setAbaAtiva('dashboard')}
            className={`px-6 py-3 font-medium text-sm transition-colors relative ${
              abaAtiva === 'dashboard'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Dashboard de Análise
            </div>
          </button>
          
          <button
            onClick={() => setAbaAtiva('alertas')}
            className={`px-6 py-3 font-medium text-sm transition-colors relative ${
              abaAtiva === 'alertas'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Alertas de Classificação
              {stats.total > 0 && (
                <span className="px-2 py-0.5 text-xs bg-red-500 text-white rounded-full">
                  {stats.total}
                </span>
              )}
            </div>
          </button>
          
          <button
            onClick={() => setAbaAtiva('sugestoes')}
            className={`px-6 py-3 font-medium text-sm transition-colors relative ${
              abaAtiva === 'sugestoes'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Sugestões Inteligentes
            </div>
          </button>
        </div>
      </div>

      {/* Conteúdo das Abas */}
      {abaAtiva === 'dashboard' && (
        <DashboardAnaliseRacoes />
      )}

      {abaAtiva === 'sugestoes' && (
        <SugestoesInteligentesRacoes />
      )}

      {abaAtiva === 'alertas' && (
        <div>
          {/* Header da Aba Alertas */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-gray-600">
                Produtos classificados como ração mas sem informações completas
              </p>
              <button
                onClick={classificarTodos}
                disabled={loading || racoesSemClassificacao.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Classificar Todos
              </button>
            </div>
            
            {/* Filtro de Espécie */}
            <div className="flex items-center gap-2 mt-4">
              <label className="text-sm font-medium text-gray-700">Filtrar por:</label>
              <select
                value={especieFiltro}
                onChange={(e) => setEspecieFiltro(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {especiesDisponiveis.map(especie => (
                  <option key={especie.value} value={especie.value}>
                    {especie.label}
                  </option>
                ))}
              </select>
              {especieFiltro && (
                <button
                  onClick={() => setEspecieFiltro('')}
                  className="text-sm text-indigo-600 hover:text-indigo-800"
                >
                  Limpar filtro
                </button>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total de Alertas</p>
                  <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                </div>
                <AlertTriangle className="w-10 h-10 text-red-500 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-amber-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Nesta Página</p>
                  <p className="text-2xl font-bold text-gray-800">{racoesSemClassificacao.length}</p>
                </div>
                <Archive className="w-10 h-10 text-amber-500 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Completude Média</p>
                  <p className="text-2xl font-bold text-gray-800">
                    {racoesSemClassificacao.length > 0
                      ? Math.round(
                          racoesSemClassificacao.reduce((acc, r) => acc + r.completude, 0) /
                            racoesSemClassificacao.length
                        )
                      : 0}
                    %
                  </p>
                </div>
                <CheckCircle className="w-10 h-10 text-green-500 opacity-20" />
              </div>
            </div>
          </div>

          {/* Loading */}
          {loading && racoesSemClassificacao.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
              <span className="ml-3 text-gray-600">Carregando alertas...</span>
            </div>
          )}

          {/* Lista de Rações */}
          {!loading && racoesSemClassificacao.length === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
              <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-green-800 mb-2">
                Nenhum alerta encontrado!
              </h3>
              <p className="text-green-700">
                Todas as rações cadastradas possuem informações completas.
              </p>
            </div>
          )}

          {racoesSemClassificacao.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Código
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Produto
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Categoria / Marca
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Campos Faltantes
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Completude
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {racoesSemClassificacao.map((racao) => {
                      const chamada = getChamadaAtencao(racao.completude);
                      const classificando = classificandoIds.has(racao.id);

                      return (
                        <tr key={racao.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-mono">
                            {racao.codigo}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            <div className="max-w-md">
                              <p className="font-medium">{racao.nome}</p>
                              <div className="flex gap-2 mt-1">
                                {racao.classificacao_racao && (
                                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                    {racao.classificacao_racao}
                                  </span>
                                )}
                                {racao.especies_indicadas && (
                                  <span className="text-xs text-white bg-indigo-600 px-2 py-1 rounded">
                                    {especiesDisponiveis.find(e => e.value === racao.especies_indicadas)?.label || racao.especies_indicadas}
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            <div>
                              <div className="text-gray-700">{racao.categoria || '-'}</div>
                              <div className="text-xs text-gray-500">{racao.marca || '-'}</div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <div className="flex flex-wrap gap-1">
                              {racao.campos_faltantes.map((campo) => (
                                <span
                                  key={campo}
                                  className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-800 text-xs rounded"
                                >
                                  <XCircle className="w-3 h-3" />
                                  {traduzirCampo(campo)}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${chamada.cor}`}>
                              {racao.completude}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex gap-2 justify-center">
                              <button
                                onClick={() => classificarProduto(racao.id)}
                                disabled={classificando || !racao.auto_classificar_ativo}
                                className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
                              >
                                {classificando ? (
                                  <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Classificando...
                                  </>
                                ) : (
                                  <>
                                    <RefreshCw className="w-4 h-4" />
                                    Classificar IA
                                  </>
                                )}
                              </button>
                              <button
                                onClick={() => navigate(`/produtos/${racao.id}/editar?aba=7`)}
                                className="inline-flex items-center gap-2 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition"
                                title="Editar produto manualmente"
                              >
                                <Edit className="w-4 h-4" />
                                Editar
                              </button>
                            </div>
                            {!racao.auto_classificar_ativo && (
                              <p className="text-xs text-gray-500 mt-1">
                                Auto-class. desativada
                              </p>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AlertasRacao;
