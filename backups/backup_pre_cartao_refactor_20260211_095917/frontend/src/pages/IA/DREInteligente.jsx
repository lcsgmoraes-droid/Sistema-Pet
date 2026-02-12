/**
 * ABA 7: DRE Inteligente - Página Principal
 * Demonstração de Resultado do Exercício com análises automáticas
 */

import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-hot-toast';
import {
  TrendingUp, TrendingDown, DollarSign, PieChart,
  Calendar, AlertTriangle, CheckCircle, BarChart3,
  Award, Package, Lightbulb, ArrowUpCircle, ArrowDownCircle
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart as RePieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export default function DREInteligente() {
  const [dres, setDres] = useState([]);
  const [dreAtual, setDreAtual] = useState(null);
  const [produtos, setProdutos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [calculando, setCalculando] = useState(false);
  const [periodoCustom, setPeriodoCustom] = useState({
    data_inicio: '',
    data_fim: ''
  });

  useEffect(() => {
    carregarDREs();
  }, []);

  const carregarDREs = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/ia/dre/listar');
      setDres(response.data);
      
      if (response.data.length > 0) {
        carregarDetalhes(response.data[0].id);
      }
    } catch (error) {
      console.error('Erro ao carregar DREs:', error);
      toast.error('Erro ao carregar histórico de DREs');
    } finally {
      setLoading(false);
    }
  };

  const carregarDetalhes = async (dreId) => {
    try {
      // Carregar DRE completo
      const dreResponse = await api.get(`/api/ia/dre/${dreId}`);
      setDreAtual(dreResponse.data);
      
      // Carregar produtos
      const produtosResponse = await api.get(`/api/ia/dre/${dreId}/produtos`);
      setProdutos(produtosResponse.data);
      
      // Carregar categorias
      const categoriasResponse = await api.get(`/api/ia/dre/${dreId}/categorias`);
      setCategorias(categoriasResponse.data);
      
      // Carregar insights
      const insightsResponse = await api.get(`/api/ia/dre/${dreId}/insights`);
      setInsights(insightsResponse.data);
      
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      toast.error('Erro ao carregar detalhes do DRE');
    }
  };

  const calcularMesAtual = async () => {
    setCalculando(true);
    try {
      const response = await api.post('/api/ia/dre/calcular-mes-atual', {});
      
      toast.success('DRE do mês atual calculado!');
      carregarDREs();
      setDreAtual(response.data);
    } catch (error) {
      console.error('Erro ao calcular:', error);
      toast.error('Erro ao calcular DRE');
    } finally {
      setCalculando(false);
    }
  };

  const calcularMesPassado = async () => {
    setCalculando(true);
    try {
      const response = await api.post('/api/ia/dre/calcular-mes-passado', {});
      
      toast.success('DRE do mês passado calculado!');
      carregarDREs();
      setDreAtual(response.data);
    } catch (error) {
      console.error('Erro ao calcular:', error);
      toast.error('Erro ao calcular DRE');
    } finally {
      setCalculando(false);
    }
  };

  const calcularPeriodoCustom = async () => {
    if (!periodoCustom.data_inicio || !periodoCustom.data_fim) {
      toast.error('Selecione o período');
      return;
    }
    
    setCalculando(true);
    try {
      const response = await api.post('/api/ia/dre/calcular', periodoCustom);
      
      toast.success('DRE calculado!');
      carregarDREs();
      setDreAtual(response.data);
      setPeriodoCustom({ data_inicio: '', data_fim: '' });
    } catch (error) {
      console.error('Erro ao calcular:', error);
      toast.error('Erro ao calcular DRE');
    } finally {
      setCalculando(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value || 0);
  };

  const formatPercent = (value) => {
    return `${(value || 0).toFixed(1)}%`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'lucro':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'prejuizo':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'lucro':
        return <TrendingUp className="w-6 h-6" />;
      case 'prejuizo':
        return <TrendingDown className="w-6 h-6" />;
      default:
        return <DollarSign className="w-6 h-6" />;
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <BarChart3 className="w-8 h-8 text-blue-600" />
          DRE Inteligente
        </h1>
        <p className="text-gray-600 mt-1">
          Análise de rentabilidade com insights automáticos
        </p>
      </div>

      {/* Ações Rápidas */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Calcular Novo DRE</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={calcularMesAtual}
            disabled={calculando}
            className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 transition-colors flex items-center justify-center gap-2"
          >
            <Calendar className="w-5 h-5" />
            Mês Atual
          </button>
          
          <button
            onClick={calcularMesPassado}
            disabled={calculando}
            className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 transition-colors flex items-center justify-center gap-2"
          >
            <Calendar className="w-5 h-5" />
            Mês Passado
          </button>
          
          <div className="flex gap-2">
            <input
              type="date"
              value={periodoCustom.data_inicio}
              onChange={(e) => setPeriodoCustom({ ...periodoCustom, data_inicio: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <input
              type="date"
              value={periodoCustom.data_fim}
              onChange={(e) => setPeriodoCustom({ ...periodoCustom, data_fim: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <button
              onClick={calcularPeriodoCustom}
              disabled={calculando}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 transition-colors"
            >
              Calcular
            </button>
          </div>
        </div>
      </div>

      {dreAtual && (
        <>
          {/* Cards de Resumo */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">Receita Líquida</span>
                <DollarSign className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(dreAtual.receita_liquida)}
              </p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">Lucro Bruto</span>
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(dreAtual.lucro_bruto)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Margem: {formatPercent(dreAtual.margem_bruta_percent)}
              </p>
            </div>

            <div className={`rounded-lg border p-4 ${getStatusColor(dreAtual.status)}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Lucro Líquido</span>
                {getStatusIcon(dreAtual.status)}
              </div>
              <p className="text-2xl font-bold">
                {formatCurrency(dreAtual.lucro_liquido)}
              </p>
              <p className="text-xs mt-1">
                Margem: {formatPercent(dreAtual.margem_liquida_percent)}
              </p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">Score de Saúde</span>
                <Award className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {dreAtual.score_saude}/100
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-purple-600 h-2 rounded-full"
                  style={{ width: `${dreAtual.score_saude}%` }}
                />
              </div>
            </div>
          </div>

          {/* Insights */}
          {insights.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Lightbulb className="w-6 h-6 text-yellow-500" />
                Insights Automáticos
              </h2>
              
              <div className="space-y-3">
                {insights.map((insight) => (
                  <div
                    key={insight.id}
                    className={`p-4 rounded-lg border ${
                      insight.tipo === 'alerta'
                        ? 'bg-red-50 border-red-200'
                        : insight.tipo === 'oportunidade'
                        ? 'bg-blue-50 border-blue-200'
                        : 'bg-green-50 border-green-200'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {insight.tipo === 'alerta' && <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
                      {insight.tipo === 'oportunidade' && <ArrowUpCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />}
                      {insight.tipo === 'recomendacao' && <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />}
                      
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">{insight.titulo}</h3>
                        <p className="text-sm text-gray-700 mt-1">{insight.descricao}</p>
                        {insight.acao_sugerida && (
                          <p className="text-sm text-gray-600 mt-2">
                            <strong>Ação:</strong> {insight.acao_sugerida}
                          </p>
                        )}
                        {insight.impacto_estimado > 0 && (
                          <p className="text-sm font-medium mt-2">
                            Impacto estimado: {formatCurrency(insight.impacto_estimado)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gráficos */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Top 10 Produtos */}
            {produtos.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <Package className="w-6 h-6 text-blue-600" />
                  Top 10 Produtos Mais Lucrativos
                </h2>
                
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={produtos.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="produto_nome" angle={-45} textAnchor="end" height={100} />
                    <YAxis />
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                    <Bar dataKey="lucro_total" fill="#0088FE" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Categorias */}
            {categorias.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <PieChart className="w-6 h-6 text-green-600" />
                  Receita por Categoria
                </h2>
                
                <ResponsiveContainer width="100%" height={300}>
                  <RePieChart>
                    <Pie
                      data={categorias}
                      dataKey="receita_total"
                      nameKey="categoria_nome"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={(entry) => `${entry.categoria_nome}: ${formatCurrency(entry.receita_total)}`}
                    >
                      {categorias.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                  </RePieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Tabela de Produtos */}
          {produtos.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-xl font-bold">Todos os Produtos</h2>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">#</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Produto</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Categoria</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Qtd</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Receita</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Custo</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Lucro</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Margem</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {produtos.map((produto) => (
                      <tr key={produto.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{produto.ranking_rentabilidade}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{produto.produto_nome}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{produto.categoria}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{produto.quantidade_vendida}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{formatCurrency(produto.receita_total)}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{formatCurrency(produto.custo_total)}</td>
                        <td className={`px-4 py-3 text-sm font-medium text-right ${produto.lucro_total > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(produto.lucro_total)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{formatPercent(produto.margem_percent)}</td>
                        <td className="px-4 py-3">
                          {produto.eh_lucrativo ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Lucrativo
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              Prejuízo
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {!dreAtual && !loading && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <BarChart3 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Nenhum DRE calculado ainda
          </h3>
          <p className="text-gray-600 mb-6">
            Calcule seu primeiro DRE para começar a análise de rentabilidade
          </p>
          <button
            onClick={calcularMesAtual}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Calcular Mês Atual
          </button>
        </div>
      )}
    </div>
  );
}
