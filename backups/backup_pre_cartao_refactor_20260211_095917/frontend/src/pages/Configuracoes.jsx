import { Link } from 'react-router-dom';
import { FiUsers, FiShield, FiSettings, FiTruck } from 'react-icons/fi';

export default function Configuracoes() {
  const cards = [
    {
      title: 'Usuários',
      description: 'Gerenciar usuários do sistema',
      icon: FiUsers,
      link: '/admin/usuarios',
      color: 'blue'
    },
    {
      title: 'Permissões',
      description: 'Gerenciar roles e permissões',
      icon: FiShield,
      link: '/admin/roles',
      color: 'purple'
    },
    {
      title: 'Configurações Fiscais',
      description: 'Configurar tributação padrão da empresa',
      icon: FiSettings,
      link: '/configuracoes/fiscal',
      color: 'green'
    },
    {
      title: 'Entregas',
      description: 'Configurar entregadores e ponto inicial de rotas',
      icon: FiTruck,
      link: '/configuracoes/entregas',
      color: 'blue'
    },
    {
      title: 'Custos da Moto',
      description: 'Configurar custos operacionais da moto de entregas',
      icon: FiSettings,
      link: '/configuracoes/custos-moto',
      color: 'orange'
    },
    {
      title: 'Sistema',
      description: 'Configurações gerais do sistema',
      icon: FiSettings,
      link: '#',
      color: 'gray',
      disabled: true
    }
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Configurações</h1>
        <p className="text-gray-600 mt-2">Gerencie usuários, permissões e configurações do sistema</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map((card) => {
          const Icon = card.icon;
          const colorClasses = {
            blue: 'bg-blue-50 text-blue-600 hover:bg-blue-100',
            purple: 'bg-purple-50 text-purple-600 hover:bg-purple-100',
            green: 'bg-green-50 text-green-600 hover:bg-green-100',
            orange: 'bg-orange-50 text-orange-600 hover:bg-orange-100',
            gray: 'bg-gray-50 text-gray-400'
          };

          if (card.disabled) {
            return (
              <div
                key={card.title}
                className={`p-6 rounded-lg border-2 border-gray-200 ${colorClasses[card.color]} cursor-not-allowed opacity-60`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <Icon className="text-2xl" />
                  <h3 className="text-lg font-semibold">{card.title}</h3>
                </div>
                <p className="text-sm text-gray-500">{card.description}</p>
                <span className="text-xs text-gray-400 mt-2 block">Em breve</span>
              </div>
            );
          }

          return (
            <Link
              key={card.title}
              to={card.link}
              className={`p-6 rounded-lg border-2 border-gray-200 ${colorClasses[card.color]} transition-all hover:shadow-lg`}
            >
              <div className="flex items-center gap-3 mb-3">
                <Icon className="text-2xl" />
                <h3 className="text-lg font-semibold">{card.title}</h3>
              </div>
              <p className="text-sm opacity-80">{card.description}</p>
              <div className="mt-4 flex items-center text-sm font-medium">
                Acessar
                <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
