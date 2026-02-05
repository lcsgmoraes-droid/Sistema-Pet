import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { 
  TrendingUp, TrendingDown, DollarSign, Calendar, 
  Filter, RefreshCw, Plus, Settings, ChevronRight,
  Brain, AlertTriangle, Sparkles
} from 'lucide-react';
import ChatIAModal from './ChatIAModal';
import ProjecoesIA from './ProjecoesIA';
import AlertasIA from './AlertasIA';

const FluxoCaixa = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);
  
  // Tabs
  const [tabAtiva, setTabAtiva] = useState('movimentacoes'); // movimentacoes, projecoes, alertas
  
  // Modal Chat IA
  const [chatIAAberto, setChatIAAberto] = useState(false);
  
  // Filtros
  const obterDataLocal = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    const dia = String(hoje.getDate()).padStart(2, '0');
    return `${ano}-${mes}-${dia}`;
  };
  
  const obterPrimeiroDiaMes = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    return `${ano}-${mes}-01`;
  };
  
  const [filtros, setFiltros] = useState({
    data_inicio: obterPrimeiroDiaMes(),  // Primeiro dia do mês
    data_fim: obterDataLocal(),          // Dia atual
    conta_bancaria_id: null,
    agrupamento: 'dia'  // dia, semana, mes
  });
  
  // Novos filtros de tipo
  const [filtroTipo, setFiltroTipo] = useState('todos'); // todos, entradas, saidas
  const [filtroStatus, setFiltroStatus] = useState('todos'); // todos, realizado, previsto
  
  const [contasBancarias, setContasBancarias] = useState([]);
  const [periodoExpandido, setPeriodoExpandido] = useState(null);
  const [apenasComLancamentos, setApenasComLancamentos] = useState(false);
  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState('');

  useEffect(() => {
    carregarContasBancarias();
    carregarFluxoCaixa();
  }, []);

  const carregarContasBancarias = async () => {
    try {
      const response = await api.get(`/api/contas-bancarias`);
      setContasBancarias(response.data);
    } catch (error) {
      console.error('Erro ao carregar contas bancárias:', error);
    }
  };

  const carregarFluxoCaixa = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
        agrupamento: filtros.agrupamento
      });
      
      if (filtros.conta_bancaria_id) {
        params.append('conta_bancaria_id', filtros.conta_bancaria_id);
      }
      
      // Adicionar filtro de número de venda se preenchido
      if (buscaNumeroVenda) {
        params.append('numero_venda', buscaNumeroVenda);
      }
      
      const response = await api.get(`/financeiro/fluxo-caixa?${params}`);
      
      setDados(response.data);
    } catch (error) {
      console.error('Erro ao carregar fluxo de caixa:', error);
      alert('Erro ao carregar fluxo de caixa: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodoPreset = (preset) => {
    const hoje = new Date();
    let inicio, fim;

    switch (preset) {
      case '7dias':
        inicio = new Date(hoje.setDate(hoje.getDate() - 7));
        fim = new Date();
        break;
      case '30dias':
        inicio = new Date(hoje.setDate(hoje.getDate() - 30));
        fim = new Date();
        break;
      case 'mes_atual':
        inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
        break;
      case 'proximo_mes':
        inicio = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
        fim = new Date(hoje.getFullYear(), hoje.getMonth() + 2, 0);
        break;
      default:
        return;
    }

    const novosFiltros = {
      ...filtros,
      data_inicio: inicio.toISOString().split('T')[0],
      data_fim: fim.toISOString().split('T')[0]
    };
    
    setFiltros(novosFiltros);
    
    // Recarregar dados com novos filtros
    setTimeout(() => carregarFluxoCaixa(), 100);
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const getMovimentacoesDoPeriodo = (periodo) => {
    if (!dados) return [];
    
    return dados.movimentacoes.filter(mov => {
      const dataMovFormatada = new Date(mov.data);
      const dataInicio = new Date(periodo.data_inicio);
      const dataFim = new Date(periodo.data_fim);
      const dentroDataPeriodo = dataMovFormatada >= dataInicio && dataMovFormatada <= dataFim;
      
      if (!dentroDataPeriodo) return false;
      
      // Filtro por tipo (entrada/saída)
      if (filtroTipo === 'entradas' && mov.tipo !== 'credito') return false;
      if (filtroTipo === 'saidas' && mov.tipo !== 'debito') return false;
      
      // Filtro por status (realizado/previsto)
      if (filtroStatus === 'realizado' && mov.status !== 'realizado') return false;
      if (filtroStatus === 'previsto' && mov.status !== 'previsto') return false;
      
      // Filtro por busca de número de venda
      if (buscaNumeroVenda) {
        const descricao = mov.descricao || '';
        const numeroVenda = mov.numero_venda || '';
        const busca = buscaNumeroVenda.toLowerCase();
        
        return numeroVenda.toLowerCase().includes(busca) || 
               descricao.toLowerCase().includes(busca);
      }
      
      return true;
    });
  };

  if (loading && !dados) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4" size={48} />
          <p className="text-gray-600">Carregando fluxo de caixa...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">💹 Fluxo de Caixa</h1>
          <p className="text-gray-600 mt-1">Visão completa: Previsto vs Realizado</p>
          <p className="text-sm text-blue-600 mt-1">✨ Os lançamentos são criados automaticamente a partir de Contas a Pagar e Contas a Receber</p>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        {/* Campo de busca por número de venda */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            🔢 Buscar por Número da Venda
          </label>
          <input
            type="text"
            placeholder="Digite o número da venda (ex: 202601100007) e pressione Enter"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            value={buscaNumeroVenda}
            onChange={(e) => setBuscaNumeroVenda(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                carregarFluxoCaixa();
              }
            }}
          />
        </div>
        
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Visualização
            </label>
            <select
              value={filtros.agrupamento}
              onChange={(e) => setFiltros({...filtros, agrupamento: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="dia">📅 Diário</option>
              <option value="semana">📊 Semanal</option>
              <option value="mes">📈 Mensal</option>
            </select>
          </div>
          
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Movimentação
            </label>
            <select
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="todos">📊 Todas</option>
              <option value="entradas">💰 Apenas Entradas</option>
              <option value="saidas">💸 Apenas Saídas</option>
            </select>
          </div>
          
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="todos">📋 Todos</option>
              <option value="realizado">✅ Apenas Realizados</option>
              <option value="previsto">📅 Apenas Previstos</option>
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Início
            </label>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({...filtros, data_inicio: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Fim
            </label>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({...filtros, data_fim: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Conta Bancária
            </label>
            <select
              value={filtros.conta_bancaria_id || ''}
              onChange={(e) => setFiltros({...filtros, conta_bancaria_id: e.target.value || null})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todas as Contas</option>
              {contasBancarias.map(conta => (
                <option key={conta.id} value={conta.id}>{conta.nome}</option>
              ))}
            </select>
          </div>

          <div className="flex items-end gap-2">
            <button
              onClick={carregarFluxoCaixa}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
            >
              <RefreshCw size={18} />
              Atualizar
            </button>
          </div>
        </div>
        
        {/* Banner de Filtros Ativos */}
        {(filtroTipo !== 'todos' || filtroStatus !== 'todos') && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-blue-800 font-medium">🔍 Filtros ativos:</span>
              {filtroTipo !== 'todos' && (
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {filtroTipo === 'entradas' ? '💰 Apenas Entradas' : '💸 Apenas Saídas'}
                </span>
              )}
              {filtroStatus !== 'todos' && (
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {filtroStatus === 'realizado' ? '✅ Apenas Realizados' : '📅 Apenas Previstos'}
                </span>
              )}
            </div>
            <button
              onClick={() => {
                setFiltroTipo('todos');
                setFiltroStatus('todos');
              }}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              Limpar filtros
            </button>
          </div>
        )}

        {/* Presets rápidos */}
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          <button
            onClick={() => handlePeriodoPreset('7dias')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
          >
            Últimos 7 dias
          </button>
          <button
            onClick={() => handlePeriodoPreset('30dias')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
          >
            Últimos 30 dias
          </button>
          <button
            onClick={() => handlePeriodoPreset('mes_atual')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
          >
            Mês Atual
          </button>
          <button
            onClick={() => handlePeriodoPreset('proximo_mes')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
          >
            Próximo Mês
          </button>
          
          <div className="ml-auto flex items-center gap-2 bg-blue-50 px-3 py-2 rounded border border-blue-200">
            <input
              type="checkbox"
              id="apenasComLancamentos"
              checked={apenasComLancamentos}
              onChange={(e) => setApenasComLancamentos(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
            <label htmlFor="apenasComLancamentos" className="text-sm font-medium text-blue-700 cursor-pointer">
              📊 Apenas dias com lançamentos
            </label>
          </div>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setTabAtiva('movimentacoes')}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium transition-colors ${
                tabAtiva === 'movimentacoes'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
              }`}
            >
              <DollarSign className="w-5 h-5" />
              Movimentações
            </button>
            <button
              onClick={() => setTabAtiva('projecoes')}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium transition-colors ${
                tabAtiva === 'projecoes'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
              }`}
            >
              <Brain className="w-5 h-5" />
              Projeções IA
              <Sparkles className="w-4 h-4" />
            </button>
            <button
              onClick={() => setTabAtiva('alertas')}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium transition-colors ${
                tabAtiva === 'alertas'
                  ? 'border-orange-600 text-orange-600'
                  : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
              Alertas IA
              <Sparkles className="w-4 h-4" />
            </button>
          </nav>
        </div>
      </div>

      {/* Conteúdo das Tabs */}
      {tabAtiva === 'projecoes' && <ProjecoesIA />}
      
      {tabAtiva === 'alertas' && <AlertasIA />}
      
      {tabAtiva === 'movimentacoes' && dados && (
        <>
          {/* Cards de Resumo */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-600 font-medium">Saldo Inicial</p>
                  <p className="text-2xl font-bold text-blue-700">{formatarMoeda(dados.saldo_inicial)}</p>
                </div>
                <DollarSign className="text-blue-500" size={32} />
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-600 font-medium">Total Realizado (Entradas)</p>
                  <p className="text-2xl font-bold text-green-700">{formatarMoeda(dados.total_realizado_entradas)}</p>
                  <p className="text-xs text-green-600 mt-1">Previsto: {formatarMoeda(dados.total_previsto_entradas)}</p>
                </div>
                <TrendingUp className="text-green-500" size={32} />
              </div>
            </div>

            <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-red-600 font-medium">Total Realizado (Saídas)</p>
                  <p className="text-2xl font-bold text-red-700">{formatarMoeda(dados.total_realizado_saidas)}</p>
                  <p className="text-xs text-red-600 mt-1">Previsto: {formatarMoeda(dados.total_previsto_saidas)}</p>
                </div>
                <TrendingDown className="text-red-500" size={32} />
              </div>
            </div>

            <div className={`rounded-lg p-4 border-l-4 ${dados.saldo_final >= 0 ? 'bg-blue-50 border-blue-500' : 'bg-red-50 border-red-500'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: dados.saldo_final >= 0 ? '#2563eb' : '#dc2626' }}>
                    Saldo Final Realizado
                  </p>
                  <p className="text-2xl font-bold" style={{ color: dados.saldo_final >= 0 ? '#1d4ed8' : '#b91c1c' }}>
                    {formatarMoeda(dados.saldo_final)}
                  </p>
                  <p className="text-xs mt-1" style={{ color: dados.saldo_final >= 0 ? '#2563eb' : '#dc2626' }}>
                    Previsto: {formatarMoeda(dados.saldo_previsto_final)}
                  </p>
                </div>
                <DollarSign className={dados.saldo_final >= 0 ? 'text-blue-500' : 'text-red-500'} size={32} />
              </div>
            </div>
          </div>

          {/* Tabela Estilo Flua: Previsto vs Realizado */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Período
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-green-50" colSpan="2">
                      💰 Entradas
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-red-50" colSpan="2">
                      💸 Saídas
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-blue-50">
                      💵 Saldo Final
                    </th>
                    <th className="px-6 py-3"></th>
                  </tr>
                  <tr className="bg-gray-100">
                    <th className="px-6 py-2"></th>
                    <th className="px-4 py-2 text-xs text-gray-600 bg-green-50">Previsto</th>
                    <th className="px-4 py-2 text-xs text-gray-600 bg-green-100">Realizado</th>
                    <th className="px-4 py-2 text-xs text-gray-600 bg-red-50">Previsto</th>
                    <th className="px-4 py-2 text-xs text-gray-600 bg-red-100">Realizado</th>
                    <th className="px-4 py-2 text-xs text-gray-600 bg-blue-50">Real / Previsto</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dados.periodos && dados.periodos.length > 0 ? (
                    dados.periodos
                      .filter(periodo => {
                        // Se o filtro estiver ativo, mostra apenas períodos com movimentações
                        if (!apenasComLancamentos) return true;
                        return periodo.realizado_entradas > 0 || 
                               periodo.realizado_saidas > 0 || 
                               periodo.previsto_entradas > 0 || 
                               periodo.previsto_saidas > 0;
                      })
                      .map((periodo, idx) => {
                      const movimentacoes = getMovimentacoesDoPeriodo(periodo);
                      const periodoId = periodo.data; // Usa data como ID único
                      const isExpandido = periodoExpandido === periodoId;
                      
                      return (
                        <React.Fragment key={periodoId}>
                          <tr className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {periodo.data}
                            </td>
                            <td className="px-4 py-4 text-sm text-gray-600 text-right bg-green-50">
                              {formatarMoeda(periodo.previsto_entradas)}
                            </td>
                            <td className="px-4 py-4 text-sm font-bold text-green-700 text-right bg-green-100">
                              {formatarMoeda(periodo.realizado_entradas)}
                            </td>
                            <td className="px-4 py-4 text-sm text-gray-600 text-right bg-red-50">
                              {formatarMoeda(periodo.previsto_saidas)}
                            </td>
                            <td className="px-4 py-4 text-sm font-bold text-red-700 text-right bg-red-100">
                              {formatarMoeda(periodo.realizado_saidas)}
                            </td>
                            <td className="px-4 py-4 text-sm text-center bg-blue-50">
                              <div className={`font-bold ${periodo.realizado_saldo >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                                {formatarMoeda(periodo.realizado_saldo)}
                              </div>
                              <div className={`text-xs ${periodo.previsto_saldo >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                Prev: {formatarMoeda(periodo.previsto_saldo)}
                              </div>
                            </td>
                            <td className="px-4 py-4 text-center">
                              <button
                                onClick={() => setPeriodoExpandido(isExpandido ? null : periodoId)}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                <ChevronRight 
                                  size={20} 
                                  className={`transform transition-transform ${isExpandido ? 'rotate-90' : ''}`}
                                />
                              </button>
                            </td>
                          </tr>
                          
                          {/* Detalhes expandidos */}
                          {isExpandido && movimentacoes.length > 0 && (
                            <tr className="bg-gray-50">
                              <td colSpan="7" className="px-6 py-4">
                                <div className="space-y-2">
                                  <h4 className="font-bold text-gray-700 mb-3">📋 Movimentações Detalhadas</h4>
                                  {movimentacoes.map((mov, movIdx) => (
                                    <div
                                      key={movIdx}
                                      className={`flex justify-between items-center p-2 rounded ${
                                        mov.status === 'previsto' ? 'bg-yellow-50 border-l-2 border-yellow-400' : 'bg-white border-l-2 border-blue-400'
                                      }`}
                                    >
                                      <div className="flex-1">
                                        <span className="font-medium">{mov.descricao}</span>
                                        <span className="text-xs text-gray-500 ml-2">({mov.categoria})</span>
                                      </div>
                                      <div className="flex items-center gap-3">
                                        <span className={`text-xs px-2 py-1 rounded ${
                                          mov.status === 'previsto' ? 'bg-yellow-200 text-yellow-800' : 'bg-blue-200 text-blue-800'
                                        }`}>
                                          {mov.status === 'previsto' ? '📅 Previsto' : '✅ Realizado'}
                                        </span>
                                        <span className={`font-bold ${mov.tipo === 'entrada' ? 'text-green-600' : 'text-red-600'}`}>
                                          {mov.tipo === 'entrada' ? '+' : '-'} {formatarMoeda(mov.valor)}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                        Nenhuma movimentação encontrada para o período selecionado
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Fluxo de Caixa é apenas visualização - lançamentos vêm de Contas a Pagar/Receber */}
    </div>
  );
};

export default FluxoCaixa;
