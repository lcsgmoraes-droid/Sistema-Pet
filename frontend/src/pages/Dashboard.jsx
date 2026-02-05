import { FiUsers, FiPackage, FiShoppingCart, FiDollarSign, FiTrendingUp } from 'react-icons/fi';

const Dashboard = () => {
  // Dados mock - depois virão da API
  const stats = [
    {
      title: 'Total de Vendas',
      value: 'R$ 15.432,50',
      icon: FiShoppingCart,
      color: 'bg-green-500',
      change: '+12%'
    },
    {
      title: 'Clientes Ativos',
      value: '248',
      icon: FiUsers,
      color: 'bg-blue-500',
      change: '+5%'
    },
    {
      title: 'Produtos',
      value: '1.234',
      icon: FiPackage,
      color: 'bg-purple-500',
      change: '+8'
    },
    {
      title: 'Faturamento',
      value: 'R$ 45.890,00',
      icon: FiDollarSign,
      color: 'bg-yellow-500',
      change: '+18%'
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Visão geral do seu negócio</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div
            key={index}
            className="bg-white rounded-xl shadow-card p-6 hover:shadow-lg transition-shadow animate-fade-in"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                <h3 className="text-2xl font-bold text-gray-900">{stat.value}</h3>
                <p className="text-sm text-green-600 mt-2 font-medium">
                  <FiTrendingUp className="inline mr-1" />
                  {stat.change} este mês
                </p>
              </div>
              <div className={`${stat.color} p-4 rounded-xl`}>
                <stat.icon className="text-3xl text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resumo Financeiro */}
      <div className="bg-white rounded-xl shadow-card p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Resumo Financeiro</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-600 font-medium">BRUTO</p>
            <p className="text-2xl font-bold text-blue-900 mt-2">R$ 52.320,00</p>
            <p className="text-xs text-blue-600 mt-1">Total em vendas</p>
          </div>
          
          <div className="p-4 bg-red-50 rounded-lg">
            <p className="text-sm text-red-600 font-medium">DESPESAS</p>
            <p className="text-2xl font-bold text-red-900 mt-2">R$ 12.450,00</p>
            <p className="text-xs text-red-600 mt-1">Custos e taxas</p>
          </div>
          
          <div className="p-4 bg-green-50 rounded-lg">
            <p className="text-sm text-green-600 font-medium">LÍQUIDO</p>
            <p className="text-2xl font-bold text-green-900 mt-2">R$ 39.870,00</p>
            <p className="text-xs text-green-600 mt-1">Lucro do período</p>
          </div>
        </div>
      </div>

      {/* Barra de composição */}
      <div className="bg-white rounded-xl shadow-card p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Composição do Faturamento</h3>
        <div className="flex h-8 rounded-lg overflow-hidden">
          <div className="bg-green-500 flex items-center justify-center text-white text-xs font-semibold" style={{width: '76%'}}>
            Líquido 76%
          </div>
          <div className="bg-red-500 flex items-center justify-center text-white text-xs font-semibold" style={{width: '15%'}}>
            Despesas 15%
          </div>
          <div className="bg-yellow-500 flex items-center justify-center text-white text-xs font-semibold" style={{width: '9%'}}>
            Impostos 9%
          </div>
        </div>
      </div>

      {/* Estatísticas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gradient-to-br from-purple-500 to-purple-700 rounded-xl shadow-card p-6 text-white">
          <h3 className="text-lg font-semibold mb-4">Estatísticas</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span>Total de Vendas</span>
              <span className="font-bold text-2xl">3.636</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Ticket Médio Bruto</span>
              <span className="font-bold text-xl">R$ 14,39</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Ticket Médio Líquido</span>
              <span className="font-bold text-xl">R$ 10,96</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Margem Média</span>
              <span className="font-bold text-xl">76,2%</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Ações Rápidas</h3>
          <div className="space-y-3">
            <button className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors text-left flex items-center gap-3">
              <FiShoppingCart />
              Nova Venda (PDV)
            </button>
            <button className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors text-left flex items-center gap-3">
              <FiUsers />
              Cadastrar Cliente
            </button>
            <button className="w-full bg-purple-500 hover:bg-purple-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors text-left flex items-center gap-3">
              <FiPackage />
              Adicionar Produto
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
