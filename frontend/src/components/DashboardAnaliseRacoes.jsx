import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  BarChart3,
  Package,
  DollarSign,
  Filter,
  Download,
  RefreshCw,
  AlertCircle,
  Award,
  Target,
  Percent,
  ShoppingCart
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../api';

/**
 * Dashboard de Análise Dinâmica de Rações - Fase 4
 * 
 * Features:
 * - Filtros dinâmicos (porte, fase, sabor, marca)
 * - Gráficos de margem por segmento
 * - Comparação de preços entre marcas
 * - Ranking de produtos mais vendidos
 * 
 * @version 1.0.0 (2026-02-14)
 */
const DashboardAnaliseRacoes = () => {
  // ============================================================================
  // STATES
  // ============================================================================
  
  const [loading, setLoading] = useState(true);
  const [loadingAnalise, setLoadingAnalise] = useState(false);
  
  // Resumo geral
  const [resumo, setResumo] = useState(null);
  
  // Análises
  const [analiseSegmento, setAnaliseSegmento] = useState([]);
  const [comparacaoMarcas, setComparacaoMarcas] = useState([]);
  const [rankingVendas, setRankingVendas] = useState([]);
  const [produtosComparacao, setProdutosComparacao] = useState([]);
  const [ordenacao, setOrdenacao] = useState({ campo: null, direcao: 'asc' });
  
  // Filtros
  const [filtros, setFiltros] = useState({
    especies: [],
    linhas: [],
    portes: [],
    fases: [],
    tratamentos: [],
    sabores: [],
    pesos: [],
    marca_ids: [],
    categoria_ids: [],
    margem_min: null,
    margem_max: null,
    data_inicio: null,
    data_fim: null
  });
  
  // Opções de filtros (carregadas do backend)
  const [opcoesFiltros, setOpcoesFiltros] = useState({
    marcas: [],
    categorias: [],
    especies: [],
    linhas: [],
    portes: [],
    fases: [],
    tratamentos: [],
    sabores: [],
    pesos: []
  });
  
  // Tipo de segmento para análise
  const [tipoSegmento, setTipoSegmento] = useState('porte');
  
  // Controle de exibição de filtros
  const [mostrarFiltros, setMostrarFiltros] = useState(true);
  
  // Abas ativas
  const [abaAtiva, setAbaAtiva] = useState('comparacao');
  
  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  useEffect(() => {
    carregarDados();
  }, []);
  
  // ============================================================================
  // FUNÇÕES DE CARREGAMENTO
  // ============================================================================
  
  const carregarDados = async () => {
    try {
      setLoading(true);
      
      // 🔍 DEBUG: Verificar token antes da requisição
      const token = localStorage.getItem('access_token');
      console.log('🔐 [DashboardAnaliseRacoes] Iniciando carregamento de dados', {
        hasToken: !!token,
        tokenPreview: token ? `${token.substring(0, 20)}...` : 'NO TOKEN'
      });
      
      // Carregar opções de filtros
      console.log('📡 [DashboardAnaliseRacoes] Chamando: /racoes/analises/opcoes-filtros');
      const resOpcoes = await api.get('/racoes/analises/opcoes-filtros');
      console.log('✅ [DashboardAnaliseRacoes] Opções carregadas:', resOpcoes.data);
      setOpcoesFiltros(resOpcoes.data);
      
      // Carregar resumo (sem filtros de data para overview geral)
      await carregarResumo();
      
      setLoading(false);
    } catch (error) {
      console.error('❌ [DashboardAnaliseRacoes] Erro ao carregar dados:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        config: error.config
      });
      
      if (error.response?.status === 403) {
        toast.error('Acesso negado. Verifique suas permissões ou faça login novamente.');
      } else {
        toast.error('Erro ao carregar dados do dashboard');
      }
      
      setLoading(false);
    }
  };
  
  const carregarResumo = async (dataInicio = null, dataFim = null) => {
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      
      const res = await api.get('/racoes/analises/resumo', { params });
      setResumo(res.data);
    } catch (error) {
      console.error('Erro ao carregar resumo:', error);
      toast.error('Erro ao carregar resumo');
    }
  };
  
  const carregarAnaliseSegmento = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post(
        `/racoes/analises/margem-por-segmento?tipo_segmento=${tipoSegmento}`,
        filtros
      );
      setAnaliseSegmento(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error('Erro ao carregar análise:', error);
      toast.error('Erro ao carregar análise de segmento');
      setLoadingAnalise(false);
    }
  };
  
  const carregarComparacaoMarcas = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post('/racoes/analises/comparacao-marcas', filtros);
      setComparacaoMarcas(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error('Erro ao carregar comparação:', error);
      toast.error('Erro ao carregar comparação de marcas');
      setLoadingAnalise(false);
    }
  };
  
  const carregarRankingVendas = async () => {
    try {
      if (!filtros.data_inicio || !filtros.data_fim) {
        toast.error('Selecione um período para ver o ranking de vendas');
        return;
      }
      
      setLoadingAnalise(true);
      const res = await api.get('/racoes/analises/ranking-vendas', {
        params: {
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
          limite: 20
        }
      });
      setRankingVendas(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error('Erro ao carregar ranking:', error);
      toast.error('Erro ao carregar ranking de vendas');
      setLoadingAnalise(false);
    }
  };
  
  const carregarProdutosComparacao = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post('/racoes/analises/produtos-comparacao', filtros);
      setProdutosComparacao(res.data);
      setOrdenacao({ campo: null, direcao: 'asc' }); // Reset ordenação
      setLoadingAnalise(false);
    } catch (error) {
      console.error('Erro ao carregar produtos para comparação:', error);
      toast.error('Erro ao carregar produtos');
      setLoadingAnalise(false);
    }
  };
  
  const ordenarProdutos = (campo) => {
    const novaDirecao = ordenacao.campo === campo && ordenacao.direcao === 'asc' ? 'desc' : 'asc';
    setOrdenacao({ campo, direcao: novaDirecao });
    
    const produtosOrdenados = [...produtosComparacao].sort((a, b) => {
      let valorA, valorB;
      
      switch(campo) {
        case 'nome':
          valorA = a.nome;
          valorB = b.nome;
          break;
        case 'custo':
          valorA = a.preco_custo || 0;
          valorB = b.preco_custo || 0;
          break;
        case 'venda':
          valorA = a.preco_venda || 0;
          valorB = b.preco_venda || 0;
          break;
        case 'lucro':
          valorA = (a.preco_venda || 0) - (a.preco_custo || 0);
          valorB = (b.preco_venda || 0) - (b.preco_custo || 0);
          break;
        case 'margem':
          valorA = calcularMargem(a.preco_custo, a.preco_venda);
          valorB = calcularMargem(b.preco_custo, b.preco_venda);
          break;
        case 'roi':
          valorA = calcularROI(a.preco_custo, a.preco_venda);
          valorB = calcularROI(b.preco_custo, b.preco_venda);
          break;
        case 'custokg':
          valorA = (a.preco_custo || 0) / (a.peso_embalagem || 1);
          valorB = (b.preco_custo || 0) / (b.peso_embalagem || 1);
          break;
        case 'vendakg':
          valorA = (a.preco_venda || 0) / (a.peso_embalagem || 1);
          valorB = (b.preco_venda || 0) / (b.peso_embalagem || 1);
          break;
        default:
          return 0;
      }
      
      if (typeof valorA === 'string') {
        return novaDirecao === 'asc' 
          ? valorA.localeCompare(valorB)
          : valorB.localeCompare(valorA);
      }
      
      return novaDirecao === 'asc' ? valorA - valorB : valorB - valorA;
    });
    
    setProdutosComparacao(produtosOrdenados);
  };
  
  // ============================================================================
  // HANDLERS
  // ============================================================================
  
  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({
      ...prev,
      [campo]: valor
    }));
  };
  
  const toggleFiltroMultiplo = (campo, valor) => {
    setFiltros(prev => {
      const atual = prev[campo] || [];
      const existe = atual.includes(valor);
      
      return {
        ...prev,
        [campo]: existe 
          ? atual.filter(v => v !== valor)  // Remove
          : [...atual, valor]               // Adiciona
      };
    });
  };
  
  const handleAplicarFiltros = () => {
    if (abaAtiva === 'segmento') {
      carregarAnaliseSegmento();
    } else if (abaAtiva === 'marcas') {
      carregarComparacaoMarcas();
    } else if (abaAtiva === 'ranking') {
      carregarRankingVendas();
    } else if (abaAtiva === 'comparacao') {
      carregarProdutosComparacao();
    }
    
    // Atualizar resumo com período se houver
    if (filtros.data_inicio && filtros.data_fim) {
      carregarResumo(filtros.data_inicio, filtros.data_fim);
    }
  };
  
  const handleLimparFiltros = () => {
    setFiltros({
      especies: [],
      linhas: [],
      portes: [],
      fases: [],
      tratamentos: [],
      sabores: [],
      pesos: [],
      marca_ids: [],
      categoria_ids: [],
      margem_min: null,
      margem_max: null,
      data_inicio: null,
      data_fim: null
    });
  };
  
  const handleMudarAba = (aba) => {
    setAbaAtiva(aba);
    
    // Carregar dados da aba automaticamente
    if (aba === 'segmento' && analiseSegmento.length === 0) {
      carregarAnaliseSegmento();
    } else if (aba === 'marcas' && comparacaoMarcas.length === 0) {
      carregarComparacaoMarcas();
    } else if (aba === 'ranking' && rankingVendas.length === 0) {
      if (filtros.data_inicio && filtros.data_fim) {
        carregarRankingVendas();
      }
    } else if (aba === 'comparacao' && produtosComparacao.length === 0) {
      carregarProdutosComparacao();
    }
  };
  
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  const renderResumo = () => {
    if (!resumo) return null;
    
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Rações */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Package className="h-5 w-5 text-blue-500" />
            <span className="text-xs text-gray-500">Rações Cadastradas</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{resumo.total_racoes}</div>
          <div className="text-sm text-gray-600 mt-1">
            {resumo.total_classificadas} classificadas ({resumo.percentual_classificadas}%)
          </div>
        </div>
        
        {/* Margem Média */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Percent className="h-5 w-5 text-green-500" />
            <span className="text-xs text-gray-500">Margem Média</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{resumo.margem_media_geral}%</div>
          <div className="text-sm text-gray-600 mt-1">
            em {resumo.total_racoes} produtos
          </div>
        </div>
        
        {/* Faturamento */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <DollarSign className="h-5 w-5 text-yellow-500" />
            <span className="text-xs text-gray-500">Faturamento Período</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            R$ {resumo.faturamento_periodo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-sm text-gray-600 mt-1">
            {resumo.marcas_cadastradas} marcas ativas
          </div>
        </div>
        
        {/* Produto Mais Vendido */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Award className="h-5 w-5 text-purple-500" />
            <span className="text-xs text-gray-500">Mais Vendido</span>
          </div>
          {resumo.produto_mais_vendido ? (
            <>
              <div className="text-sm font-semibold text-gray-900 truncate">
                {resumo.produto_mais_vendido.nome}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                {resumo.produto_mais_vendido.quantidade} unidades
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-500">Sem dados de vendas</div>
          )}
        </div>
      </div>
    );
  };
  
  const renderFiltros = () => {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Filtros</h3>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
              Clique para selecionar/desmarcar
            </span>
          </div>
          <button
            onClick={() => setMostrarFiltros(!mostrarFiltros)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            {mostrarFiltros ? 'Ocultar ▲' : 'Mostrar ▼'}
          </button>
        </div>
        
        {mostrarFiltros && (
          <>
            <div className="space-y-4 mb-4">
              {/* Marcas */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Marcas
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.marcas.map(marca => (
                    <button
                      key={marca.id}
                      onClick={() => toggleFiltroMultiplo('marca_ids', marca.id)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.marca_ids.includes(marca.id)
                          ? 'bg-blue-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {marca.nome}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Linha de Ração */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Linha de Ração
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.linhas.map(linha => (
                    <button
                      key={linha.id}
                      onClick={() => toggleFiltroMultiplo('linhas', linha.id)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.linhas.includes(linha.id)
                          ? 'bg-purple-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {linha.nome}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Portes */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Porte do Animal
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.portes.map(porte => (
                    <button
                      key={porte.id}
                      onClick={() => toggleFiltroMultiplo('portes', porte.id)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.portes.includes(porte.id)
                          ? 'bg-green-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {porte.nome}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Fases */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Fase/Público
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.fases.map(fase => (
                    <button
                      key={fase.id}
                      onClick={() => toggleFiltroMultiplo('fases', fase.id)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.fases.includes(fase.id)
                          ? 'bg-amber-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {fase.nome}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Sabores */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Sabor/Proteína
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.sabores.map(sabor => (
                    <button
                      key={sabor}
                      onClick={() => toggleFiltroMultiplo('sabores', sabor)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.sabores.includes(sabor)
                          ? 'bg-pink-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {sabor}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Pesos */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Peso da Embalagem
                </label>
                <div className="flex flex-wrap gap-2">
                  {opcoesFiltros.pesos.map(peso => (
                    <button
                      key={peso}
                      onClick={() => toggleFiltroMultiplo('pesos', peso)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filtros.pesos.includes(peso)
                          ? 'bg-indigo-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {peso} kg
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Filtros de Margem */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Margem Mínima (%)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={filtros.margem_min || ''}
                    onChange={(e) => handleFiltroChange('margem_min', parseFloat(e.target.value) || null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    placeholder="Ex: 25"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Margem Máxima (%)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={filtros.margem_max || ''}
                    onChange={(e) => handleFiltroChange('margem_max', parseFloat(e.target.value) || null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    placeholder="Ex: 50"
                  />
                </div>
              </div>
              
              {/* Período */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Início
                  </label>
                  <input
                    type="date"
                    value={filtros.data_inicio || ''}
                    onChange={(e) => handleFiltroChange('data_inicio', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Fim
                  </label>
                  <input
                    type="date"
                    value={filtros.data_fim || ''}
                    onChange={(e) => handleFiltroChange('data_fim', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex gap-3 pt-4 border-t">
              <button
                onClick={handleAplicarFiltros}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2 font-medium"
              >
                <Filter className="h-4 w-4" />
                Aplicar Filtros
              </button>
              
              <button
                onClick={handleLimparFiltros}
                className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 font-medium"
              >
                Limpar Tudo
              </button>
              
              {/* Contador de filtros ativos */}
              {(filtros.marca_ids.length + filtros.linhas.length + filtros.portes.length + 
                filtros.fases.length + filtros.sabores.length + filtros.pesos.length) > 0 && (
                <div className="flex items-center gap-2 ml-auto text-sm text-gray-600">
                  <span className="font-semibold">
                    {filtros.marca_ids.length + filtros.linhas.length + filtros.portes.length + 
                     filtros.fases.length + filtros.sabores.length + filtros.pesos.length}
                  </span>
                  filtros ativos
                </div>
              )}
            </div>
          </>
        )}
      </div>
    );
  };
  
  const renderAnaliseSegmento = () => {
    if (loadingAnalise) {
      return <div className="text-center py-8 text-gray-500">Carregando análise...</div>;
    }
    
    if (analiseSegmento.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          Nenhum dado encontrado. Aplique filtros e clique em "Aplicar Filtros"
        </div>
      );
    }
    
    return (
      <div className="space-y-4">
        {/* Seletor de tipo de segmento */}
        <div className="flex items-center gap-2 mb-4">
          <label className="text-sm font-medium text-gray-700">Analisar por:</label>
          <select
            value={tipoSegmento}
            onChange={(e) => {
              setTipoSegmento(e.target.value);
              // Recarregar análise com novo tipo
              setTimeout(() => carregarAnaliseSegmento(), 0);
            }}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
          >
            <option value="porte">Porte</option>
            <option value="fase">Fase</option>
            <option value="sabor">Sabor</option>
            <option value="linha">Linha</option>
            <option value="especie">Espécie</option>
          </select>
        </div>
        
        {/* Tabela de análise */}
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Segmento</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Produtos</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Margem Média</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Margem Min/Max</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Preço/Kg Médio</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Faturamento</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {analiseSegmento.map((seg, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-semibold text-gray-900">{seg.segmento}</td>
                  <td className="px-4 py-3 text-sm text-center text-gray-600">{seg.total_produtos}</td>
                  <td className="px-4 py-3 text-sm text-center">
                    <span className={`font-semibold ${seg.margem_media >= 30 ? 'text-green-600' : seg.margem_media >= 20 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {seg.margem_media}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-600">
                    {seg.margem_minima}% - {seg.margem_maxima}%
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-600">
                    R$ {seg.preco_medio_kg.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">
                    R$ {seg.faturamento.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };
  
  const renderComparacaoMarcas = () => {
    if (loadingAnalise) {
      return <div className="text-center py-8 text-gray-500">Carregando comparação...</div>;
    }
    
    if (comparacaoMarcas.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          Nenhum dado encontrado. Aplique filtros e clique em "Aplicar Filtros"
        </div>
      );
    }
    
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Marca</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Produtos</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Preço/Kg Médio</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Margem Média</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Mais Barato</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Mais Caro</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {comparacaoMarcas.map((marca) => (
              <tr key={marca.marca_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-semibold text-gray-900">{marca.marca_nome}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-600">{marca.total_produtos}</td>
                <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">
                  R$ {marca.preco_medio_kg.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span className={`font-semibold ${marca.margem_media >= 30 ? 'text-green-600' : marca.margem_media >= 20 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {marca.margem_media}%
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-700">
                  {marca.produto_mais_barato?.nome?.substring(0, 30) || '-'}
                  {marca.produto_mais_barato?.preco_kg && (
                    <div className="text-green-600 font-semibold">
                      R$ {marca.produto_mais_barato.preco_kg}/kg
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-gray-700">
                  {marca.produto_mais_caro?.nome?.substring(0, 30) || '-'}
                  {marca.produto_mais_caro?.preco_kg && (
                    <div className="text-red-600 font-semibold">
                      R$ {marca.produto_mais_caro.preco_kg}/kg
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  
  const renderRankingVendas = () => {
    if (loadingAnalise) {
      return <div className="text-center py-8 text-gray-500">Carregando ranking...</div>;
    }
    
    if (rankingVendas.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          Selecione um período nos filtros e clique em "Aplicar Filtros"
        </div>
      );
    }
    
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">#</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Produto</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Marca</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Qtd Vendida</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Faturamento</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Margem Média</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Preço Médio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {rankingVendas.map((prod, idx) => (
              <tr key={prod.produto_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-600">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                    idx === 1 ? 'bg-gray-200 text-gray-700' :
                    idx === 2 ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-50 text-gray-600'
                  }`}>
                    {idx + 1}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-900">{prod.nome}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{prod.marca}</td>
                <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">{prod.quantidade_vendida}</td>
                <td className="px-4 py-3 text-sm text-center font-semibold text-green-600">
                  R$ {prod.faturamento.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span className={`font-semibold ${prod.margem_media >= 30 ? 'text-green-600' : prod.margem_media >= 20 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {prod.margem_media}%
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-900">
                  R$ {prod.preco_medio_venda.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  
  const renderComparacaoDetalhada = () => {
    if (loadingAnalise) {
      return (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mr-3" />
          <span className="text-gray-600">Carregando produtos...</span>
        </div>
      );
    }
    
    if (produtosComparacao.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <AlertCircle className="h-16 w-16 mx-auto mb-3 text-gray-400" />
          <p className="text-lg font-medium mb-2">Nenhum produto encontrado</p>
          <p className="text-sm">Selecione filtros acima e clique em "Aplicar Filtros"</p>
        </div>
      );
    }
    
    // Funções de cálculo
    const calcularMargem = (custo, venda) => {
      if (!venda || venda === 0) return 0;
      return parseFloat(((venda - custo) / venda * 100).toFixed(2));
    };
    
    const calcularMarkup = (custo, venda) => {
      if (!custo || custo === 0) return 0;
      return parseFloat(((venda - custo) / custo * 100).toFixed(2));
    };
    
    const calcularLucro = (custo, venda) => {
      return parseFloat((venda - custo).toFixed(2));
    };
    
    const calcularROI = (custo, venda) => {
      if (!custo || custo === 0) return 0;
      return parseFloat((((venda - custo) / custo) * 100).toFixed(2));
    };

    const formatarPesoCompacto = (peso) => {
      if (!peso && peso !== 0) return '-';
      return `${String(peso).replace(/\.0+$/, '')}kg`;
    };

    const formatarMoedaCompacta = (valor) => `R$ ${Number(valor || 0).toFixed(2)}`;
    
    // Identificar melhores valores
    const custos = produtosComparacao.map(p => p.preco_custo || 0);
    const margens = produtosComparacao.map(p => calcularMargem(p.preco_custo, p.preco_venda));
    const lucros = produtosComparacao.map(p => calcularLucro(p.preco_custo || 0, p.preco_venda || 0));
    const rois = produtosComparacao.map(p => calcularROI(p.preco_custo, p.preco_venda));
    
    const menorCusto = Math.min(...custos.filter(c => c > 0));
    const melhorMargem = Math.max(...margens);
    const maiorLucro = Math.max(...lucros);
    const melhorROI = Math.max(...rois);
    
    // Função para cor baseada em valor relativo
    const getCorValor = (valor, min, max, inverter = false) => {
      if (max === min) return 'text-slate-700';
      const percentual = ((valor - min) / (max - min)) * 100;
      
      if (inverter) {
        // Para custos: menor é melhor (verde)
        if (percentual <= 20) return 'text-emerald-700 font-semibold';
        if (percentual <= 60) return 'text-slate-700';
        return 'text-rose-600';
      } else {
        // Para margem/lucro: maior é melhor (verde)
        if (percentual >= 80) return 'text-emerald-700 font-semibold';
        if (percentual >= 40) return 'text-slate-700';
        return 'text-rose-600';
      }
    };
    
    const getCorMargem = (margem) => {
      if (margem >= 40) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      if (margem >= 30) return 'text-blue-700 bg-blue-50 border-blue-200';
      if (margem >= 20) return 'text-amber-700 bg-amber-50 border-amber-200';
      if (margem >= 10) return 'text-orange-700 bg-orange-50 border-orange-200';
      return 'text-rose-700 bg-rose-50 border-rose-200';
    };
    
    // Componente de header ordenável
    const HeaderOrdenavel = ({ campo, children, className = "" }) => (
      <th 
        onClick={() => ordenarProdutos(campo)}
        className={`px-3 py-3 text-xs font-bold text-slate-600 uppercase cursor-pointer hover:bg-slate-100 transition-colors ${className}`}
      >
        <div className="flex items-center justify-center gap-1">
          {children}
          {ordenacao.campo === campo && (
            <span className="text-blue-600">
              {ordenacao.direcao === 'asc' ? '▲' : '▼'}
            </span>
          )}
        </div>
      </th>
    );
    
    return (
      <div className="space-y-4">
        {/* Cards de Melhores Valores */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">💰</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Menor custo</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">R$ {menorCusto.toFixed(2)}</p>
            <p className="text-xs text-green-600 mt-1">Melhor preço de compra</p>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">⭐</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Melhor margem</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">{melhorMargem.toFixed(2)}%</p>
            <p className="text-xs text-blue-600 mt-1">Maior percentual de lucro</p>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">🎯</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Melhor ROI</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">{melhorROI.toFixed(2)}%</p>
            <p className="text-xs text-purple-600 mt-1">Retorno sobre investimento</p>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">💵</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Maior lucro</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">R$ {maiorLucro.toFixed(2)}</p>
            <p className="text-xs text-amber-600 mt-1">Lucro absoluto por unidade</p>
          </div>
        </div>
        
        {/* Resumo Rápido */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total de Produtos Encontrados</p>
              <p className="text-3xl font-bold text-gray-900">{produtosComparacao.length}</p>
            </div>
            
            {produtosComparacao.length > 0 && (
              <>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Margem Média</p>
                  <p className="text-2xl font-bold text-blue-700">
                    {(margens.reduce((a, b) => a + b, 0) / margens.length).toFixed(2)}%
                  </p>
                </div>
                
                <div>
                  <p className="text-sm text-gray-600 mb-1">Custo Médio/kg</p>
                  <p className="text-2xl font-bold text-slate-900">
                    R$ {(produtosComparacao.reduce((acc, p) => 
                      acc + ((p.preco_custo || 0) / (p.peso_embalagem || 1)), 0
                    ) / produtosComparacao.length).toFixed(2)}
                  </p>
                </div>
                
                <div>
                  <p className="text-sm text-gray-600 mb-1">Preço Venda Médio/kg</p>
                  <p className="text-2xl font-bold text-emerald-700">
                    R$ {(produtosComparacao.reduce((acc, p) => 
                      acc + ((p.preco_venda || 0) / (p.peso_embalagem || 1)), 0
                    ) / produtosComparacao.length).toFixed(2)}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
        
        {/* Dica de Uso */}
        <div className="flex items-start gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" />
          <div className="text-sm text-slate-700">
            <strong>💡 Dica:</strong> Clique nos cabeçalhos das colunas para ordenar. 
            As cores indicam valores melhores (verde) e piores (vermelho).
            Produtos destacados com badges são os melhores em cada categoria.
          </div>
        </div>
        
        {/* Tabela de Comparação */}
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full bg-white">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="sticky left-0 border-r border-slate-200 bg-slate-50 px-4 py-3 text-left text-xs font-bold uppercase text-slate-600">
                  Produto / Marca
                </th>
                <th className="border-r border-slate-200 px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                  Linha
                </th>
                <th className="border-r border-slate-200 px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                  Peso
                </th>
                <HeaderOrdenavel campo="custo" className="border-r border-slate-200">
                  💰 Custo
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="venda" className="border-r border-slate-200">
                  💵 Venda
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="lucro" className="border-r border-slate-200">
                  Lucro R$
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="margem" className="border-r border-slate-200">
                  📊 Margem %
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="roi" className="border-r border-slate-200">
                  🎯 ROI %
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="custokg" className="border-r border-slate-200">
                  Custo/kg
                </HeaderOrdenavel>
                <HeaderOrdenavel campo="vendakg" className="border-r border-slate-200">
                  Venda/kg
                </HeaderOrdenavel>
                <th className="px-3 py-3 text-center text-xs font-bold uppercase text-slate-600">
                  Estoque
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {produtosComparacao.map((produto) => {
                const margem = calcularMargem(produto.preco_custo, produto.preco_venda);
                const markup = calcularMarkup(produto.preco_custo, produto.preco_venda);
                const lucro = calcularLucro(produto.preco_custo || 0, produto.preco_venda || 0);
                const roi = calcularROI(produto.preco_custo, produto.preco_venda);
                const custoKg = ((produto.preco_custo || 0) / (produto.peso_embalagem || 1));
                const vendaKg = ((produto.preco_venda || 0) / (produto.peso_embalagem || 1));
                
                // Identificar se é o melhor em cada categoria
                const isMenorCusto = (produto.preco_custo || 0) === menorCusto && menorCusto > 0;
                const isMelhorMargem = margem === melhorMargem && melhorMargem > 0;
                const isMaiorLucro = lucro === maiorLucro && maiorLucro > 0;
                const isMelhorROI = roi === melhorROI && melhorROI > 0;
                
                const destaque = isMenorCusto || isMelhorMargem || isMaiorLucro || isMelhorROI;
                
                return (
                  <tr 
                    key={produto.id} 
                    className={`transition-colors hover:bg-slate-50 ${
                      destaque ? 'bg-blue-50/40 border-l-4 border-blue-300' : ''
                    }`}
                  >
                    <td className="sticky left-0 border-r border-slate-200 bg-white px-4 py-3">
                      <div className="max-w-xs">
                        <p className="font-semibold text-gray-900 text-sm">{produto.nome}</p>
                        <p className="text-xs text-gray-600 mt-0.5">
                          {produto.marca?.nome || 'Sem marca'} • Cód: {produto.codigo}
                        </p>
                        <div className="flex gap-1 mt-1.5 flex-wrap">
                          {/* Badges de características */}
                          {produto.porte_animal && Array.isArray(produto.porte_animal) && produto.porte_animal.map(p => (
                            <span key={p} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                              {p}
                            </span>
                          ))}
                          {produto.fase_publico && Array.isArray(produto.fase_publico) && produto.fase_publico.map(f => (
                            <span key={f} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                              {f}
                            </span>
                          ))}
                          {produto.sabor_proteina && (
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                              {produto.sabor_proteina}
                            </span>
                          )}
                        </div>
                        {/* Badges de destaque */}
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {isMenorCusto && (
                            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                              💰 MENOR CUSTO
                            </span>
                          )}
                          {isMelhorMargem && (
                            <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
                              ⭐ MELHOR MARGEM
                            </span>
                          )}
                          {isMelhorROI && (
                            <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                              🎯 MELHOR ROI
                            </span>
                          )}
                          {isMaiorLucro && (
                            <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                              💵 MAIOR LUCRO
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    
                    <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                        {produto.classificacao_racao || '-'}
                      </span>
                    </td>
                    
                    <td className="border-r border-slate-200 px-3 py-3 text-center text-sm font-medium text-gray-900">
                      {produto.peso_embalagem ? (
                        <span className="inline-flex whitespace-nowrap rounded-full bg-slate-100 px-2.5 py-1 font-bold text-slate-700">
                          {formatarPesoCompacto(produto.peso_embalagem)}
                        </span>
                      ) : '-'}
                    </td>
                    
                    <td className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${
                      getCorValor(produto.preco_custo || 0, menorCusto, Math.max(...custos), true)
                    }`}>
                      {formatarMoedaCompacta(produto.preco_custo)}
                    </td>
                    
                    <td className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${
                      getCorValor(produto.preco_venda || 0, 
                        Math.min(...produtosComparacao.map(p => p.preco_venda || 0)), 
                        Math.max(...produtosComparacao.map(p => p.preco_venda || 0)))
                    }`}>
                      {formatarMoedaCompacta(produto.preco_venda)}
                    </td>
                    
                    <td className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold whitespace-nowrap ${
                      getCorValor(lucro, Math.min(...lucros), Math.max(...lucros))
                    }`}>
                      {formatarMoedaCompacta(lucro)}
                    </td>
                    
                    <td className="border-r border-slate-200 px-3 py-3 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className={`rounded-full border px-3 py-1.5 text-sm font-bold ${getCorMargem(margem)}`}>
                          {margem.toFixed(2)}%
                        </span>
                        {/* Barra de progresso */}
                        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                          <div 
                            className={`h-full transition-all ${
                              margem >= 40 ? 'bg-green-500' :
                              margem >= 30 ? 'bg-green-400' :
                              margem >= 20 ? 'bg-yellow-400' :
                              margem >= 10 ? 'bg-orange-400' :
                              'bg-red-400'
                            }`}
                            style={{ width: `${Math.min(margem, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    
                    <td className={`border-r border-slate-200 px-3 py-3 text-center text-sm font-bold ${
                      getCorValor(roi, Math.min(...rois), Math.max(...rois))
                    }`}>
                      {roi.toFixed(2)}%
                    </td>
                    
                    <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                      <span className={`inline-flex whitespace-nowrap rounded-full bg-slate-50 px-2.5 py-1 font-semibold ${
                        getCorValor(custoKg, 
                          Math.min(...produtosComparacao.map(p => (p.preco_custo || 0) / (p.peso_embalagem || 1))),
                          Math.max(...produtosComparacao.map(p => (p.preco_custo || 0) / (p.peso_embalagem || 1))),
                          true)
                      }`}>
                        {formatarMoedaCompacta(custoKg)}
                      </span>
                    </td>
                    
                    <td className="border-r border-slate-200 px-3 py-3 text-center text-sm text-gray-700">
                      <span className={`inline-flex whitespace-nowrap rounded-full bg-slate-50 px-2.5 py-1 font-semibold ${
                        getCorValor(vendaKg,
                          Math.min(...produtosComparacao.map(p => (p.preco_venda || 0) / (p.peso_embalagem || 1))),
                          Math.max(...produtosComparacao.map(p => (p.preco_venda || 0) / (p.peso_embalagem || 1))))
                      }`}>
                        {formatarMoedaCompacta(vendaKg)}
                      </span>
                    </td>
                    
                    <td className="px-3 py-3 text-sm text-center">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        (produto.estoque_atual || 0) > 10 
                          ? 'bg-green-100 text-green-700 border border-green-300' 
                          : (produto.estoque_atual || 0) > 0 
                            ? 'bg-yellow-100 text-yellow-700 border border-yellow-300'
                            : 'bg-red-100 text-red-700 border border-red-300'
                      }`}>
                        {produto.estoque_atual || 0}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {/* Legenda */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-sm font-bold text-slate-800">
            Legenda de leitura
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <div className="flex items-start gap-2 text-xs">
                <span className="font-bold text-emerald-700">Verde:</span>
                <span className="text-gray-700">melhor indicador do grupo naquela coluna.</span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <span className="font-bold text-rose-700">Vermelho:</span>
                <span className="text-gray-700">pior indicador relativo naquela comparação.</span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <span className="font-bold text-blue-700">Selos:</span>
                <span className="text-gray-700">mostram apenas os destaques reais de custo, margem, ROI e lucro.</span>
              </div>
            </div>
            <div className="space-y-1.5 text-xs text-gray-700">
              <p><strong>Margem %:</strong> (Venda - Custo) / Venda × 100</p>
              <p><strong>ROI %:</strong> (Lucro / Custo) × 100</p>
              <p><strong>Lucro R$:</strong> Venda - Custo (valor absoluto)</p>
              <p><strong>Custo/Venda por kg:</strong> Preço dividido pelo peso</p>
            </div>
          </div>
        </div>
      </div>
    );
  };
  
  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="h-7 w-7 text-blue-600" />
            Comparador de Rações
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Compare itens da mesma linha com foco em custo, margem, venda por kg e estoque.
          </p>
        </div>
        
        <button
          onClick={() => carregarDados()}
          className="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Atualizar
        </button>
      </div>
      
      {/* Resumo */}
      {renderResumo()}
      
      {/* Filtros */}
      {renderFiltros()}
      
      {/* Abas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex space-x-1 p-2 overflow-x-auto">
            <button
              onClick={() => handleMudarAba('comparacao')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === 'comparacao'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Target className="h-4 w-4 inline mr-2" />
              Comparação detalhada
            </button>
            
            <button
              onClick={() => handleMudarAba('segmento')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === 'segmento'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <TrendingUp className="h-4 w-4 inline mr-2" />
              Margem por Segmento
            </button>
            
            <button
              onClick={() => handleMudarAba('marcas')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === 'marcas'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Package className="h-4 w-4 inline mr-2" />
              Comparação de Marcas
            </button>
            
            <button
              onClick={() => handleMudarAba('ranking')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === 'ranking'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <ShoppingCart className="h-4 w-4 inline mr-2" />
              Ranking de Vendas
            </button>
          </div>
        </div>
        
        <div className="p-4">
          {abaAtiva === 'comparacao' && renderComparacaoDetalhada()}
          {abaAtiva === 'resumo' && renderResumo()}
          {abaAtiva === 'segmento' && renderAnaliseSegmento()}
          {abaAtiva === 'marcas' && renderComparacaoMarcas()}
          {abaAtiva === 'ranking' && renderRankingVendas()}
        </div>
      </div>
    </div>
  );
};

export default DashboardAnaliseRacoes;
