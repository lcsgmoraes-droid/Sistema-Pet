/**
 * Dashboard Gerencial Inteligente
 * Visão executiva do negócio em 1 tela para tomada de decisão
 * 
 * MVP: Baseado em regras simples, sem IA
 * Futuro: Migrar para backend e adicionar IA
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiAlertTriangle, FiTrendingDown, FiDollarSign, FiHeart,
  FiMessageCircle, FiTrendingUp, FiUsers, FiAward, FiClock,
  FiRefreshCw, FiArrowRight, FiInfo
} from 'react-icons/fi';
import api from '../api';

/**
 * Configuração de cards do dashboard
 */
const CARD_CONFIG = {
  vips_inativos: {
    titulo: 'VIPs em Risco',
    descricao: 'Clientes VIP sem compra há mais de 20 dias',
    icone: FiAward,
    cor: 'red',
    bgGradient: 'from-red-500 to-red-600',
    bgLight: 'bg-red-50',
    borderLight: 'border-red-200',
    textColor: 'text-red-700'
  },
  clientes_inativos: {
    titulo: 'Clientes Inativos',
    descricao: 'Sem compra há mais de 90 dias',
    icone: FiClock,
    cor: 'orange',
    bgGradient: 'from-orange-500 to-orange-600',
    bgLight: 'bg-orange-50',
    borderLight: 'border-orange-200',
    textColor: 'text-orange-700'
  },
  clientes_endividados: {
    titulo: 'Alto Endividamento',
    descricao: 'Clientes com saldo devedor significativo',
    icone: FiDollarSign,
    cor: 'yellow',
    bgGradient: 'from-yellow-500 to-yellow-600',
    bgLight: 'bg-yellow-50',
    borderLight: 'border-yellow-200',
    textColor: 'text-yellow-700'
  },
  oportunidades_novos: {
    titulo: 'Novos Promissores',
    descricao: 'Clientes novos com ticket alto',
    icone: FiTrendingUp,
    cor: 'green',
    bgGradient: 'from-green-500 to-green-600',
    bgLight: 'bg-green-50',
    borderLight: 'border-green-200',
    textColor: 'text-green-700'
  },
  pets_sem_eventos: {
    titulo: 'Pets Inativos',
    descricao: 'Sem consulta há mais de 60 dias',
    icone: FiHeart,
    cor: 'purple',
    bgGradient: 'from-purple-500 to-purple-600',
    bgLight: 'bg-purple-50',
    borderLight: 'border-purple-200',
    textColor: 'text-purple-700'
  },
  whatsapp_inativo: {
    titulo: 'WhatsApp Faltando',
    descricao: 'Clientes sem número cadastrado',
    icone: FiMessageCircle,
    cor: 'blue',
    bgGradient: 'from-blue-500 to-blue-600',
    bgLight: 'bg-blue-50',
    borderLight: 'border-blue-200',
    textColor: 'text-blue-700'
  }
};

/**
 * Card individual de métrica
 */
function MetricCard({ tipo, dados, onClick }) {
  const config = CARD_CONFIG[tipo];
  const Icon = config?.icone || FiInfo;
  
  // ✅ VALIDAÇÃO: Garantir que dados sempre existe
  const dadosSafe = dados || { quantidade: 0, impacto: null };
  
  return (
    <div className={`${config.bgLight} border-2 ${config.borderLight} rounded-xl p-6 hover:shadow-lg transition-all cursor-pointer`}
         onClick={onClick}>
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 bg-gradient-to-br ${config.bgGradient} rounded-lg`}>
          <Icon className="text-white" size={24} />
        </div>
        <FiArrowRight className={config.textColor} size={20} />
      </div>
      
      <h3 className={`text-2xl font-bold ${config.textColor} mb-1`}>
        {dadosSafe?.quantidade ?? 0}
      </h3>
      
      <p className="text-sm font-semibold text-gray-700 mb-2">
        {config.titulo}
      </p>
      
      <p className="text-xs text-gray-600 mb-3">
        {config.descricao}
      </p>
      
      {dadosSafe?.impacto && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Impacto estimado:</span>
            <span className={`font-bold ${config.textColor}`}>
              {dadosSafe.impacto}
            </span>
          </div>
        </div>
      )}
      
      <button className={`mt-3 w-full py-2 text-sm font-medium ${config.textColor} hover:bg-white rounded-lg transition-colors flex items-center justify-center gap-2`}>
        Ver detalhes
        <FiArrowRight size={14} />
      </button>
    </div>
  );
}

/**
 * Componente principal do Dashboard
 */
export default function DashboardGerencial() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [metricas, setMetricas] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);

  useEffect(() => {
    carregarDashboard();
  }, []);

  const carregarDashboard = async () => {
    try {
      setLoading(true);

      const res = await api.get('/dashboard/gerencial');
      const data = res?.data;

      if (!data) throw new Error('Resposta vazia do servidor');

      setMetricas(data);
      setUltimaAtualizacao(new Date());

    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);

      setMetricas({
        vips_inativos: { quantidade: 0, impacto: 'R$ 0,00' },
        clientes_inativos: { quantidade: 0, impacto: 'Reativação pendente' },
        clientes_endividados: { quantidade: 0, impacto: 'R$ 0,00' },
        oportunidades_novos: { quantidade: 0, impacto: '~R$ 0/mês' },
        pets_sem_eventos: { quantidade: 0, impacto: 'Em breve' },
        whatsapp_inativo: { quantidade: 0, impacto: 'Canal perdido' },
        total_clientes: 0
      });

      if (err.response?.status === 403) {
        alert('Você não tem permissão para acessar o dashboard gerencial');
      } else {
        alert('Erro ao carregar dashboard gerencial');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCardClick = (tipo) => {
    // Navegar para lista filtrada de clientes
    // TODO: Implementar filtros na lista de clientes
    navigate('/pessoas', { state: { filtro: tipo } });
  };

  const handleRefresh = () => {
    carregarDashboard();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Carregando dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              📊 Dashboard Gerencial
            </h1>
            <p className="text-gray-600 mt-2">
              Visão executiva do negócio • {metricas?.total_clientes || 0} clientes ativos
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            {ultimaAtualizacao && (
              <div className="text-sm text-gray-500">
                Atualizado às {ultimaAtualizacao.toLocaleTimeString('pt-BR')}
              </div>
            )}
            
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              <FiRefreshCw size={18} />
              Atualizar
            </button>
          </div>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <MetricCard
            tipo="vips_inativos"
            dados={metricas?.vips_inativos || { quantidade: 0, impacto: 'R$ 0', clientes: [] }}
            onClick={() => handleCardClick('vips_inativos')}
          />
          
          <MetricCard
            tipo="clientes_inativos"
            dados={metricas?.clientes_inativos || { quantidade: 0, impacto: 'R$ 0', clientes: [] }}
            onClick={() => handleCardClick('clientes_inativos')}
          />
          
          <MetricCard
            tipo="clientes_endividados"
            dados={metricas?.clientes_endividados || { quantidade: 0, impacto: 'R$ 0', clientes: [] }}
            onClick={() => handleCardClick('clientes_endividados')}
          />
          
          <MetricCard
            tipo="oportunidades_novos"
            dados={metricas?.oportunidades_novos || { quantidade: 0, impacto: 'R$ 0', clientes: [] }}
            onClick={() => handleCardClick('oportunidades_novos')}
          />
          
          <MetricCard
            tipo="pets_sem_eventos"
            dados={metricas?.pets_sem_eventos || { quantidade: 0, impacto: '0 donos', clientes: [] }}
            onClick={() => handleCardClick('pets_sem_eventos')}
          />
          
          <MetricCard
            tipo="whatsapp_inativo"
            dados={metricas?.whatsapp_inativo || { quantidade: 0, impacto: 'Canal perdido', clientes: [] }}
            onClick={() => handleCardClick('whatsapp_inativo')}
          />
        </div>

        {/* Resumo Executivo */}
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <FiInfo className="text-blue-600" size={24} />
            <h2 className="text-xl font-bold text-gray-900">Resumo Executivo</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Prioridade 1: Riscos */}
            <div className="border-l-4 border-red-500 pl-4">
              <h3 className="font-semibold text-red-700 mb-2">🚨 Ação Urgente</h3>
              <p className="text-sm text-gray-700 mb-2">
                <strong>{metricas?.vips_inativos?.quantidade ?? 0}</strong> clientes VIP em risco de churn
              </p>
              <p className="text-xs text-gray-600">
                Contate imediatamente para evitar perda de {metricas?.vips_inativos?.impacto ?? 'R$ 0'} em receita
              </p>
            </div>
            
            {/* Prioridade 2: Recuperação */}
            <div className="border-l-4 border-yellow-500 pl-4">
              <h3 className="font-semibold text-yellow-700 mb-2">⚠️ Atenção</h3>
              <p className="text-sm text-gray-700 mb-2">
                <strong>{metricas?.clientes_endividados?.quantidade ?? 0}</strong> clientes endividados
              </p>
              <p className="text-xs text-gray-600">
                Total de {metricas?.clientes_endividados?.impacto ?? 'R$ 0'} em aberto • Avaliar condições
              </p>
            </div>
            
            {/* Prioridade 3: Oportunidades */}
            <div className="border-l-4 border-green-500 pl-4">
              <h3 className="font-semibold text-green-700 mb-2">💡 Oportunidade</h3>
              <p className="text-sm text-gray-700 mb-2">
                <strong>{metricas?.oportunidades_novos?.quantidade ?? 0}</strong> novos clientes promissores
              </p>
              <p className="text-xs text-gray-600">
                Potencial de fidelização • Ticket médio alto
              </p>
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <FiInfo size={12} />
              Dados calculados em tempo real com base em regras de negócio pré-definidas
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
