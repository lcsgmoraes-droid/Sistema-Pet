import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

/**
 * RELATÓRIOS ANALÍTICOS DE COMISSÕES
 * =====================================
 * Página de análise de rentabilidade e tomada de decisão.
 * NÃO recalcula comissões, apenas consulta dados existentes.
 */

const RelatoriosComissoes = () => {
  const navigate = useNavigate();
  
  // Estado
  const [abaAtiva, setAbaAtiva] = useState('margem-produto');
  const [carregando, setCarregando] = useState(false);
  
  // Filtros
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  
  // Dados dos relatórios
  const [dadosMargemProduto, setDadosMargemProduto] = useState(null);
  const [dadosProdutosPrejudiciais, setDadosProdutosPrejudiciais] = useState(null);
  const [dadosRankingFuncionarios, setDadosRankingFuncionarios] = useState(null);
  const [dadosRankingProdutos, setDadosRankingProdutos] = useState(null);
  const [dadosRankingCategorias, setDadosRankingCategorias] = useState(null);
  const [dadosDRE, setDadosDRE] = useState(null);

  // ========================================
  // CARREGAMENTO DE DADOS
  // ========================================

  const carregarRelatorio = async (tipo) => {
    setCarregando(true);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;

      let endpoint = '';
      let setDados = null;

      switch (tipo) {
        case 'margem-produto':
          endpoint = '/relatorios-comissoes/margem-produto';
          setDados = setDadosMargemProduto;
          break;
        case 'produtos-prejudiciais':
          endpoint = '/relatorios-comissoes/produtos-prejudiciais';
          setDados = setDadosProdutosPrejudiciais;
          break;
        case 'ranking-funcionarios':
          endpoint = '/relatorios-comissoes/ranking-funcionarios';
          setDados = setDadosRankingFuncionarios;
          break;
        case 'ranking-produtos':
          endpoint = '/relatorios-comissoes/ranking-produtos';
          setDados = setDadosRankingProdutos;
          break;
        case 'ranking-categorias':
          endpoint = '/relatorios-comissoes/ranking-categorias';
          setDados = setDadosRankingCategorias;
          break;
        case 'dre':
          endpoint = '/relatorios-comissoes/visao-dre';
          params.ano = 2026;
          setDados = setDadosDRE;
          break;
        default:
          setCarregando(false);
          return;
      }

      const response = await api.get(endpoint, { 
        params,
        timeout: 10000 // 10 segundos timeout
      });
      setDados(response.data);
    } catch (error) {
      console.error(`Erro ao carregar relatório ${tipo}:`, error);
      
      // Se for erro de rede/timeout, mostrar estrutura vazia
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        alert('⏱️ Tempo de resposta excedido. Verifique se o backend está rodando.');
      } else {
        alert('❌ Erro ao carregar relatório. Verifique o console para detalhes.');
      }
    } finally {
      setCarregando(false);
    }
  };

  // Carregar relatório ao mudar aba
  useEffect(() => {
    carregarRelatorio(abaAtiva);
  }, [abaAtiva]);

  // Aplicar filtros manualmente (não automático)
  const aplicarFiltros = () => {
    carregarRelatorio(abaAtiva);
  };

  // ========================================
  // FORMATAÇÃO
  // ========================================

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const formatarPercentual = (valor) => {
    return `${valor.toFixed(2)}%`;
  };

  // ========================================
  // EXPORTAÇÃO
  // ========================================

  const exportarCSV = async () => {
    try {
      const params = {
        tipo: abaAtiva,
        data_inicio: dataInicio,
        data_fim: dataFim
      };

      const response = await api.get('/relatorios-comissoes/exportar-csv', {
        params,
        responseType: 'blob'
      });

      // Download do arquivo
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `relatorio_${abaAtiva}_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Erro ao exportar CSV:', error);
      alert('Erro ao exportar arquivo');
    }
  };

  // ========================================
  // CORES E TEMAS
  // ========================================

  const CORES = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#a28bd4', '#f48fb1'];

  const obterCorAlerta = (nivel) => {
    if (nivel === 3) return 'text-red-700 bg-red-100 border-red-300';
    if (nivel === 2) return 'text-orange-700 bg-orange-100 border-orange-300';
    return 'text-yellow-700 bg-yellow-100 border-yellow-300';
  };

  // ========================================
  // RENDERIZAÇÃO: ABAS
  // ========================================

  const renderizarAbas = () => {
    const abas = [
      { id: 'margem-produto', label: '📊 Margem por Produto', icone: '💰' },
      { id: 'produtos-prejudiciais', label: '⚠️ Produtos Prejudiciais', icone: '🚨' },
      { id: 'ranking-funcionarios', label: '👥 Ranking Funcionários', icone: '🏆' },
      { id: 'ranking-produtos', label: '📦 Ranking Produtos', icone: '📈' },
      { id: 'ranking-categorias', label: '📂 Ranking Categorias', icone: '🎯' },
      { id: 'dre', label: '📑 Visão DRE', icone: '💼' }
    ];

    return (
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {abas.map(aba => (
          <button
            key={aba.id}
            onClick={() => setAbaAtiva(aba.id)}
            className={`px-4 py-3 rounded-lg font-medium whitespace-nowrap transition-all ${
              abaAtiva === aba.id
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <span className="text-xl mr-2">{aba.icone}</span>
            {aba.label}
          </button>
        ))}
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: FILTROS
  // ========================================

  const renderizarFiltros = () => {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              📅 Data Início
            </label>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              📅 Data Fim
            </label>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={aplicarFiltros}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition mt-6"
            >
              🔍 Buscar
            </button>
            
            <button
              onClick={() => {
                setDataInicio('');
                setDataFim('');
                carregarRelatorio(abaAtiva);
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition mt-6"
            >
              🔄 Limpar
            </button>
            
            {['margem-produto', 'produtos-prejudiciais', 'ranking-funcionarios', 'ranking-produtos'].includes(abaAtiva) && (
              <button
                onClick={exportarCSV}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition mt-6"
              >
                📥 Exportar CSV
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: MARGEM POR PRODUTO
  // ========================================

  const renderizarMargemProduto = () => {
    if (!dadosMargemProduto) return <div className="text-center py-12">Carregando...</div>;

    const top10 = dadosMargemProduto.dados.slice(0, 10);

    return (
      <div className="space-y-6">
        {/* Cards de Resumo */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-sm text-blue-600 font-medium">Total de Produtos</div>
            <div className="text-3xl font-bold text-blue-800">{dadosMargemProduto.total_produtos}</div>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-sm text-red-600 font-medium">Produtos com Margem Negativa</div>
            <div className="text-3xl font-bold text-red-800">{dadosMargemProduto.produtos_com_alerta}</div>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-sm text-green-600 font-medium">Produtos Saudáveis</div>
            <div className="text-3xl font-bold text-green-800">
              {dadosMargemProduto.total_produtos - dadosMargemProduto.produtos_com_alerta}
            </div>
          </div>
        </div>

        {/* Gráfico */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">
            Top 10 Produtos por Margem Líquida
          </h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={top10}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="produto_nome" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => formatarMoeda(value)} />
              <Legend />
              <Bar dataKey="margem_liquida" fill="#82ca9d" name="Margem Líquida" />
              <Bar dataKey="valor_comissao" fill="#ff7c7c" name="Comissão" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Tabela Detalhada */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoria</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Venda</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Comissão</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Margem Líquida</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">% Margem</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dadosMargemProduto.dados.map((produto, idx) => (
                  <tr key={idx} className={produto.alerta_margem_negativa ? 'bg-red-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {produto.produto_nome}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {produto.categoria_nome}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      {formatarMoeda(produto.valor_venda)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                      {formatarMoeda(produto.valor_custo)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600 font-medium">
                      {formatarMoeda(produto.valor_comissao)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold">
                      <span className={produto.margem_liquida < 0 ? 'text-red-600' : 'text-green-600'}>
                        {formatarMoeda(produto.margem_liquida)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {formatarPercentual(produto.percentual_margem)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {produto.alerta_margem_negativa ? (
                        <span className="px-2 py-1 text-xs font-bold text-red-700 bg-red-100 rounded">
                          ⚠️ NEGATIVA
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-bold text-green-700 bg-green-100 rounded">
                          ✅ OK
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: PRODUTOS PREJUDICIAIS
  // ========================================

  const renderizarProdutosPrejudiciais = () => {
    if (!dadosProdutosPrejudiciais) return <div className="text-center py-12">Carregando...</div>;

    return (
      <div className="space-y-6">
        {/* Aviso Informativo */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                <strong className="font-semibold">Relatório informativo</strong> baseado em vendas já realizadas.
                Os dados não alteram comissões, preços ou históricos e não devem ser usados para ajustes retroativos.
              </p>
            </div>
          </div>
        </div>

        {/* Cards de Alerta */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-sm text-blue-600 font-medium">Produtos Analisados</div>
            <div className="text-3xl font-bold text-blue-800">{dadosProdutosPrejudiciais.total_produtos_analisados}</div>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-sm text-red-600 font-medium">Críticos</div>
            <div className="text-3xl font-bold text-red-800">{dadosProdutosPrejudiciais.produtos_criticos}</div>
          </div>

          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="text-sm text-orange-600 font-medium">Total Prejudiciais</div>
            <div className="text-3xl font-bold text-orange-800">{dadosProdutosPrejudiciais.total_produtos_prejudiciais}</div>
          </div>
        </div>

        {/* Lista de Produtos Prejudiciais */}
        <div className="space-y-4">
          {dadosProdutosPrejudiciais.dados.map((produto, idx) => (
            <div
              key={idx}
              className={`border-2 rounded-lg p-6 ${obterCorAlerta(produto.nivel_gravidade)}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold">
                    {produto.nivel_gravidade === 3 && '🚨'} 
                    {produto.nivel_gravidade === 2 && '⚠️'} 
                    {produto.nivel_gravidade === 1 && '⚡'} 
                    {' '}{produto.produto_nome}
                  </h3>
                  <p className="text-sm opacity-75">{produto.categoria_nome}</p>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">Impacto Financeiro</div>
                  <div className="text-2xl font-bold">{formatarMoeda(produto.impacto_financeiro)}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <div className="text-xs font-medium opacity-75">Margem Líquida</div>
                  <div className="text-lg font-bold">{formatarMoeda(produto.margem_liquida)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium opacity-75">% Margem</div>
                  <div className="text-lg font-bold">{formatarPercentual(produto.percentual_margem)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium opacity-75">Comissão</div>
                  <div className="text-lg font-bold">{formatarMoeda(produto.valor_comissao)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium opacity-75">% Comissão</div>
                  <div className="text-lg font-bold">{formatarPercentual(produto.percentual_comissao)}</div>
                </div>
              </div>

              <div>
                <div className="text-sm font-bold mb-2">⚠️ Alertas:</div>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {produto.alertas.map((alerta, aIdx) => (
                    <li key={aIdx}>{alerta}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: RANKINGS
  // ========================================

  const renderizarRankingFuncionarios = () => {
    if (!dadosRankingFuncionarios) return <div className="text-center py-12">Carregando...</div>;

    return (
      <div className="space-y-6">
        {/* Aviso Informativo */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                <strong className="font-semibold">Relatório informativo</strong> baseado em volume histórico.
                Não representa meta, desempenho ou política de incentivo.
              </p>
            </div>
          </div>
        </div>

        {/* Gráfico de Barras */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Funcionários por Volume de Comissões (10 maiores)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={dadosRankingFuncionarios.ranking}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="funcionario_nome" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => formatarMoeda(value)} />
              <Legend />
              <Bar dataKey="total_comissao" fill="#8884d8" name="Total de Comissões" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Tabela de Ranking */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Posição</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Funcionário</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Comissões</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Quantidade</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Média</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dadosRankingFuncionarios.ranking.map((item) => (
                <tr key={item.posicao}>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className="text-lg font-semibold text-gray-700">
                      {item.posicao}º
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.funcionario_nome}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-green-600">
                    {formatarMoeda(item.total_comissao)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {item.quantidade_comissoes}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {formatarMoeda(item.media_comissao)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderizarRankingProdutos = () => {
    if (!dadosRankingProdutos) return <div className="text-center py-12">Carregando...</div>;

    return (
      <div className="space-y-6">
        {/* Aviso Informativo */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                <strong className="font-semibold">Relatório informativo</strong> baseado em volume histórico.
                Não representa meta, desempenho ou política de incentivo.
              </p>
            </div>
          </div>
        </div>

        {/* Gráfico */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Produtos por Volume de Comissões (10 maiores)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={dadosRankingProdutos.ranking}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="produto_nome" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => formatarMoeda(value)} />
              <Legend />
              <Bar dataKey="total_comissao" fill="#82ca9d" name="Total de Comissões" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Tabela */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Posição</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoria</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Comissão</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qtd Vendas</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Venda</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dadosRankingProdutos.ranking.map((item) => (
                <tr key={item.posicao}>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-lg font-bold text-gray-700">
                    {item.posicao}º
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.produto_nome}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {item.categoria_nome}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-green-600">
                    {formatarMoeda(item.total_comissao)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {item.quantidade_vendas}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    {formatarMoeda(item.total_venda)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderizarRankingCategorias = () => {
    if (!dadosRankingCategorias) return <div className="text-center py-12">Carregando...</div>;

    return (
      <div className="space-y-6">
        {/* Aviso Informativo */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                <strong className="font-semibold">Relatório informativo</strong> baseado em volume histórico.
                Não representa meta, desempenho ou política de incentivo.
              </p>
            </div>
          </div>
        </div>

        {/* Gráfico de Pizza */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Distribuição de Comissões por Categoria</h3>
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={dadosRankingCategorias.ranking}
                dataKey="total_comissao"
                nameKey="categoria_nome"
                cx="50%"
                cy="50%"
                outerRadius={120}
                label={(entry) => `${entry.categoria_nome}: ${entry.percentual_total}%`}
              >
                {dadosRankingCategorias.ranking.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CORES[index % CORES.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatarMoeda(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Tabela */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Posição</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoria</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Comissão</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">% do Total</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qtd Comissões</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Vendas</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dadosRankingCategorias.ranking.map((item) => (
                <tr key={item.posicao}>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-lg font-bold text-gray-700">
                    {item.posicao}º
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.categoria_nome}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-green-600">
                    {formatarMoeda(item.total_comissao)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-blue-600 font-medium">
                    {formatarPercentual(item.percentual_total)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {item.quantidade_comissoes}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    {formatarMoeda(item.total_venda)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: VISÃO DRE
  // ========================================

  const renderizarVisaoDRE = () => {
    if (!dadosDRE) return <div className="text-center py-12">Carregando...</div>;

    return (
      <div className="space-y-6">
        {/* Aviso Informativo */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-800">
                <strong className="font-semibold">Regime de competência:</strong> as comissões são reconhecidas
                como despesa na data da venda, independentemente do pagamento.
                Inclui comissões pendentes e pagas.
              </p>
            </div>
          </div>
        </div>

        {/* Resumo Anual */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-sm text-blue-600 font-medium">Receita Bruta (Ano)</div>
            <div className="text-2xl font-bold text-blue-800">
              {formatarMoeda(dadosDRE.total_ano.receita_bruta)}
            </div>
          </div>
          
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="text-sm text-orange-600 font-medium">Despesa Comissão (Ano)</div>
            <div className="text-2xl font-bold text-orange-800">
              {formatarMoeda(dadosDRE.total_ano.despesa_comissao)}
            </div>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-sm text-green-600 font-medium">Margem Líquida (Ano)</div>
            <div className="text-2xl font-bold text-green-800">
              {formatarMoeda(dadosDRE.total_ano.margem_liquida)}
            </div>
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="text-sm text-purple-600 font-medium">% Comissão sobre Receita</div>
            <div className="text-2xl font-bold text-purple-800">
              {formatarPercentual(dadosDRE.total_ano.percentual_comissao)}
            </div>
          </div>
        </div>

        {/* Gráfico de Linha - Evolução Mensal */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Evolução Mensal - DRE</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={dadosDRE.dados_mensais}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="mes_nome" />
              <YAxis />
              <Tooltip formatter={(value) => formatarMoeda(value)} />
              <Legend />
              <Line type="monotone" dataKey="receita_bruta" stroke="#8884d8" name="Receita Bruta" strokeWidth={2} />
              <Line type="monotone" dataKey="despesa_comissao" stroke="#ff7c7c" name="Despesa Comissão" strokeWidth={2} />
              <Line type="monotone" dataKey="margem_liquida" stroke="#82ca9d" name="Margem Líquida" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Tabela Mensal */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mês</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Receita Bruta</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Comissão</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Margem Bruta</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Margem Líquida</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">% Comissão</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dadosDRE.dados_mensais.map((mes) => (
                <tr key={mes.mes}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {mes.mes_nome}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-blue-600 font-medium">
                    {formatarMoeda(mes.receita_bruta)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {formatarMoeda(mes.custo_total)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600 font-medium">
                    {formatarMoeda(mes.despesa_comissao)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-700">
                    {formatarMoeda(mes.margem_bruta)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-green-600">
                    {formatarMoeda(mes.margem_liquida)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-purple-600">
                    {formatarPercentual(mes.percentual_comissao_sobre_receita)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO PRINCIPAL
  // ========================================

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/comissoes-listagem')}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-4"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Voltar para Demonstrativo
        </button>

        <h1 className="text-3xl font-bold text-gray-800">📊 Relatórios Analíticos de Comissões</h1>
        <p className="text-gray-600 mt-2">
          Análise de rentabilidade, margem e tomada de decisão estratégica
        </p>
      </div>

      {/* Abas de Navegação */}
      {renderizarAbas()}

      {/* Filtros */}
      {renderizarFiltros()}

      {/* Conteúdo da Aba Ativa */}
      {carregando ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
        </div>
      ) : (
        <>
          {abaAtiva === 'margem-produto' && renderizarMargemProduto()}
          {abaAtiva === 'produtos-prejudiciais' && renderizarProdutosPrejudiciais()}
          {abaAtiva === 'ranking-funcionarios' && renderizarRankingFuncionarios()}
          {abaAtiva === 'ranking-produtos' && renderizarRankingProdutos()}
          {abaAtiva === 'ranking-categorias' && renderizarRankingCategorias()}
          {abaAtiva === 'dre' && renderizarVisaoDRE()}
        </>
      )}
    </div>
  );
};

export default RelatoriosComissoes;
