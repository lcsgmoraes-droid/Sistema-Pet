import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  TrendingUp, TrendingDown, DollarSign, AlertCircle, 
  ShoppingCart, FileText, Package, Store, Sparkles
} from 'lucide-react';

const DashboardFinanceiro = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [periodoDias, setPeriodoDias] = useState(30);
  const [resumo, setResumo] = useState({
    saldo_atual: 0,
    contas_receber: { total: 0, vencidas: 0 },
    contas_pagar: { total: 0, vencidas: 0 },
    vendas_periodo: { quantidade: 0, valor_total: 0, finalizadas: 0, ticket_medio: 0 },
    fluxo_periodo: { entradas: 0, saidas: 0, lucro: 0 }
  });
  const [entradasSaidas, setEntradasSaidas] = useState([]);
  const [contasVencidas, setContasVencidas] = useState({ contas_receber: [], contas_pagar: [] });

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  };

  const carregarDados = async () => {
    setLoading(true);

    // Carregar resumo
    try {
      const resumoRes = await api.get(`/dashboard/resumo?periodo_dias=${periodoDias}`);
      setResumo(resumoRes.data);
    } catch (err) {
      console.error('Erro ao carregar resumo:', err);
    }

    // Carregar entradas/saídas
    try {
      const entradasSaidasRes = await api.get(`/dashboard/entradas-saidas?periodo_dias=${periodoDias}`);
      setEntradasSaidas(entradasSaidasRes.data);
    } catch (err) {
      console.error('Erro ao carregar entradas/saídas:', err);
    }

    // Carregar contas vencidas
    try {
      const contasVencidasRes = await api.get(`/dashboard/contas-vencidas?limite=5`);
      setContasVencidas(contasVencidasRes.data);
    } catch (err) {
      console.error('Erro ao carregar contas vencidas:', err);
    }

    setLoading(false);
  };

  useEffect(() => {
    carregarDados();
  }, [periodoDias]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Dados mockados para canais de venda
  const canaisVenda = [
    {
      nome: 'Loja Física',
      valor: resumo.vendas_periodo.valor_total || 0,
      margem: 35.5,
      lucro: (resumo.vendas_periodo.valor_total || 0) * 0.355,
      icon: Store,
      color: 'blue',
      isMock: false,
      onClick: () => navigate('/financeiro/relatorio-vendas')
    },
    {
      nome: 'Mercado Livre',
      valor: 8450.00,
      margem: 18.2,
      lucro: 1537.90,
      icon: Package,
      color: 'yellow',
      isMock: true,
      onClick: () => toast('Integração com Mercado Livre em breve', { icon: '📦' })
    },
    {
      nome: 'Shopee',
      valor: 5230.00,
      margem: 22.5,
      lucro: 1176.75,
      icon: ShoppingCart,
      color: 'orange',
      isMock: true,
      onClick: () => toast('Integração com Shopee em breve', { icon: '🛒' })
    },
    {
      nome: 'Amazon',
      valor: 12890.00,
      margem: 15.8,
      lucro: 2036.62,
      icon: Package,
      color: 'purple',
      isMock: true,
      onClick: () => toast('Integração com Amazon em breve', { icon: '📦' })
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: 'from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700',
      green: 'from-green-500 to-green-600 hover:from-green-600 hover:to-green-700',
      red: 'from-red-500 to-red-600 hover:from-red-600 hover:to-red-700',
      purple: 'from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700',
      yellow: 'from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700',
      orange: 'from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700'
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Cabeçalho */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Dashboard Gerencial</h1>
          <p className="text-gray-600 mt-1">Visão consolidada do seu negócio</p>
        </div>
        
        {/* Seletor de período */}
        <div className="flex gap-2">
          {[7, 15, 30, 60, 90].map(dias => (
            <button
              key={dias}
              onClick={() => setPeriodoDias(dias)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                periodoDias === dias
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {dias} dias
            </button>
          ))}
        </div>
      </div>

      {/* BLOCO 1: STATUS FINANCEIRO (4 cards clicáveis) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* Saldo Atual */}
        <div
          onClick={() => navigate('/financeiro/fluxo-caixa')}
          className={`bg-gradient-to-br ${getColorClasses('blue')} rounded-xl p-6 text-white shadow-lg cursor-pointer transition-all transform hover:scale-105`}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="bg-white/20 p-3 rounded-lg">
              <DollarSign className="w-6 h-6" />
            </div>
            <span className="text-xs font-medium bg-white/20 px-2 py-1 rounded">
              Atual
            </span>
          </div>
          <p className="text-sm opacity-90 mb-1">Saldo Atual</p>
          <p className="text-2xl font-bold">{formatarMoeda(resumo.saldo_atual)}</p>
          <p className="text-xs mt-2 opacity-75">Clique para ver fluxo de caixa</p>
        </div>

        {/* Contas a Receber */}
        <div
          onClick={() => navigate('/financeiro/contas-receber')}
          className={`bg-gradient-to-br ${getColorClasses('green')} rounded-xl p-6 text-white shadow-lg cursor-pointer transition-all transform hover:scale-105`}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="bg-white/20 p-3 rounded-lg">
              <TrendingUp className="w-6 h-6" />
            </div>
            {resumo.contas_receber.vencidas > 0 && (
              <AlertCircle className="w-5 h-5 text-yellow-300" />
            )}
          </div>
          <p className="text-sm opacity-90 mb-1">A Receber</p>
          <p className="text-2xl font-bold">{formatarMoeda(resumo.contas_receber.total)}</p>
          {resumo.contas_receber.vencidas > 0 ? (
            <p className="text-xs mt-2 opacity-90">
              ⚠️ Vencidas: {formatarMoeda(resumo.contas_receber.vencidas)}
            </p>
          ) : (
            <p className="text-xs mt-2 opacity-75">Clique para gerenciar</p>
          )}
        </div>

        {/* Contas a Pagar */}
        <div
          onClick={() => navigate('/financeiro/contas-pagar')}
          className={`bg-gradient-to-br ${getColorClasses('red')} rounded-xl p-6 text-white shadow-lg cursor-pointer transition-all transform hover:scale-105`}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="bg-white/20 p-3 rounded-lg">
              <TrendingDown className="w-6 h-6" />
            </div>
            {resumo.contas_pagar.vencidas > 0 && (
              <AlertCircle className="w-5 h-5 text-yellow-300" />
            )}
          </div>
          <p className="text-sm opacity-90 mb-1">A Pagar</p>
          <p className="text-2xl font-bold">{formatarMoeda(resumo.contas_pagar.total)}</p>
          {resumo.contas_pagar.vencidas > 0 ? (
            <p className="text-xs mt-2 opacity-90">
              ⚠️ Vencidas: {formatarMoeda(resumo.contas_pagar.vencidas)}
            </p>
          ) : (
            <p className="text-xs mt-2 opacity-75">Clique para gerenciar</p>
          )}
        </div>

        {/* Resultado do Período */}
        <div
          onClick={() => navigate('/financeiro/dre')}
          className={`bg-gradient-to-br ${
            resumo.fluxo_periodo.lucro >= 0 
              ? getColorClasses('purple')
              : getColorClasses('orange')
          } rounded-xl p-6 text-white shadow-lg cursor-pointer transition-all transform hover:scale-105`}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="bg-white/20 p-3 rounded-lg">
              <FileText className="w-6 h-6" />
            </div>
            <span className="text-xs font-medium bg-white/20 px-2 py-1 rounded">
              {periodoDias} dias
            </span>
          </div>
          <p className="text-sm opacity-90 mb-1">
            {resumo.fluxo_periodo.lucro >= 0 ? 'Lucro' : 'Prejuízo'}
          </p>
          <p className="text-2xl font-bold">{formatarMoeda(Math.abs(resumo.fluxo_periodo.lucro))}</p>
          <p className="text-xs mt-2 opacity-75">Clique para ver DRE completo</p>
        </div>
      </div>

      {/* BLOCO 2: VENDAS POR CANAL */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-800">Vendas por Canal</h2>
            <p className="text-sm text-gray-600 mt-1">Performance de cada canal de vendas</p>
          </div>
          <span className="text-xs bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full font-medium">
            Marketplaces em preparação
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {canaisVenda.map((canal, index) => (
            <div
              key={index}
              onClick={canal.onClick}
              className="bg-gray-50 rounded-lg p-5 border border-gray-200 hover:shadow-md transition-all cursor-pointer transform hover:scale-105 relative"
            >
              {canal.isMock && (
                <div className="absolute top-2 right-2">
                  <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                    Mock
                  </span>
                </div>
              )}
              
              <div className="flex items-center gap-3 mb-4">
                <div className={`bg-gradient-to-br ${getColorClasses(canal.color)} p-3 rounded-lg`}>
                  <canal.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-800">{canal.nome}</h3>
              </div>

              <div className="space-y-2">
                <div>
                  <p className="text-xs text-gray-600">Valor Vendido</p>
                  <p className="text-lg font-bold text-gray-900">{formatarMoeda(canal.valor)}</p>
                </div>
                
                <div className="flex justify-between items-center pt-2 border-t border-gray-200">
                  <div>
                    <p className="text-xs text-gray-600">Margem</p>
                    <p className="text-sm font-semibold text-gray-800">{canal.margem}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-600">Lucro Est.</p>
                    <p className="text-sm font-semibold text-green-600">{formatarMoeda(canal.lucro)}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Total consolidado:</strong> {formatarMoeda(canaisVenda.reduce((acc, c) => acc + c.valor, 0))}
            {' '} | <strong>Lucro total:</strong> {formatarMoeda(canaisVenda.reduce((acc, c) => acc + c.lucro, 0))}
          </p>
        </div>
      </div>

      {/* BLOCO 3: ALERTAS & AÇÕES IA (Placeholder) */}
      <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg p-6 mb-6 text-white">
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-white/20 p-3 rounded-lg">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold">Insights Inteligentes</h2>
            <p className="text-sm opacity-90">Alertas e sugestões automáticas</p>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-75" />
          <p className="text-lg font-medium mb-2">Em breve a IA mostrará aqui:</p>
          <div className="mt-3 space-y-2 text-sm opacity-90">
            <p>• Problemas urgentes detectados</p>
            <p>• Oportunidades de lucro identificadas</p>
            <p>• Ações recomendadas para hoje</p>
          </div>
          <p className="text-xs mt-4 opacity-75">
            Sem mágica. Apenas análise inteligente dos seus dados reais.
          </p>
        </div>
      </div>

      {/* BLOCO 4: AÇÕES RÁPIDAS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <button
          onClick={() => navigate('/pdv')}
          className="bg-gradient-to-br from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white font-semibold py-4 px-6 rounded-xl shadow-lg transition-all transform hover:scale-105 flex items-center justify-center gap-3"
        >
          <ShoppingCart className="w-5 h-5" />
          Nova Venda
        </button>

        <button
          onClick={() => navigate('/financeiro/contas-receber')}
          className="bg-gradient-to-br from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-semibold py-4 px-6 rounded-xl shadow-lg transition-all transform hover:scale-105 flex items-center justify-center gap-3"
        >
          <TrendingUp className="w-5 h-5" />
          Registrar Recebimento
        </button>

        <button
          onClick={() => navigate('/financeiro/contas-pagar')}
          className="bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold py-4 px-6 rounded-xl shadow-lg transition-all transform hover:scale-105 flex items-center justify-center gap-3"
        >
          <TrendingDown className="w-5 h-5" />
          Registrar Despesa
        </button>

        <button
          onClick={() => navigate('/ia/fluxo-caixa')}
          className="bg-gradient-to-br from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl shadow-lg transition-all transform hover:scale-105 flex items-center justify-center gap-3"
        >
          <Sparkles className="w-5 h-5" />
          Revisões IA
        </button>
      </div>

      {/* Gráfico de Fluxo (mantido por ora - candidato futuro a substituição por "Previsão 7 dias" ou "Dia crítico de caixa") */}
      <div className="bg-white rounded-xl p-6 shadow-lg mb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">
          Fluxo Financeiro ({periodoDias} dias)
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={entradasSaidas}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="data" 
              tickFormatter={formatarData}
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
              style={{ fontSize: '12px' }}
            />
            <Tooltip 
              formatter={(value) => formatarMoeda(value)}
              labelFormatter={formatarData}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="entradas" 
              stroke="#10B981" 
              strokeWidth={2}
              name="Entradas"
            />
            <Line 
              type="monotone" 
              dataKey="saidas" 
              stroke="#EF4444" 
              strokeWidth={2}
              name="Saídas"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Contas Vencidas (mantido, compactado) */}
      {(contasVencidas.contas_receber.length > 0 || contasVencidas.contas_pagar.length > 0) && (
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            Atenção: Contas Vencidas
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Contas a Receber Vencidas */}
            {contasVencidas.contas_receber.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  A Receber ({contasVencidas.contas_receber.length})
                </h3>
                <div className="space-y-2">
                  {contasVencidas.contas_receber.slice(0, 3).map(conta => (
                    <div 
                      key={conta.id}
                      className="p-3 bg-red-50 border border-red-200 rounded-lg"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <p className="font-medium text-gray-800 text-sm">
                          {conta.cliente || 'Sem cliente'}
                        </p>
                        <p className="font-bold text-red-600 text-sm">
                          {formatarMoeda(conta.saldo)}
                        </p>
                      </div>
                      <p className="text-xs text-red-600">
                        Venceu há {conta.dias_vencido} dias
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Contas a Pagar Vencidas */}
            {contasVencidas.contas_pagar.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  A Pagar ({contasVencidas.contas_pagar.length})
                </h3>
                <div className="space-y-2">
                  {contasVencidas.contas_pagar.slice(0, 3).map(conta => (
                    <div 
                      key={conta.id}
                      className="p-3 bg-orange-50 border border-orange-200 rounded-lg"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <p className="font-medium text-gray-800 text-sm">
                          {conta.fornecedor || 'Sem fornecedor'}
                        </p>
                        <p className="font-bold text-orange-600 text-sm">
                          {formatarMoeda(conta.saldo)}
                        </p>
                      </div>
                      <p className="text-xs text-orange-600">
                        Venceu há {conta.dias_vencido} dias
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardFinanceiro;
