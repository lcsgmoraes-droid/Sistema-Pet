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
  const Icon = config.icone;
  
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
        {dados.quantidade}
      </h3>
      
      <p className="text-sm font-semibold text-gray-700 mb-2">
        {config.titulo}
      </p>
      
      <p className="text-xs text-gray-600 mb-3">
        {config.descricao}
      </p>
      
      {dados.impacto && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Impacto estimado:</span>
            <span className={`font-bold ${config.textColor}`}>
              {dados.impacto}
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
      
      // 1. Buscar todos os clientes com segmentação
      const [clientesRes, segmentosRes] = await Promise.all([
        api.get('/clientes/'),
        api.get('/segmentacao/estatisticas')
      ]);
      
      const clientes = clientesRes.data;
      const estatisticas = segmentosRes.data;
      
      // 2. Calcular métricas agregadas no frontend (MVP)
      const metricas = calcularMetricas(clientes, estatisticas);
      
      setMetricas(metricas);
      setUltimaAtualizacao(new Date());
      
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);
      alert('Erro ao carregar dashboard gerencial');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Calcula métricas agregadas baseado em regras
   */
  const calcularMetricas = (clientes, estatisticas) => {
    const hoje = new Date();
    
    // Filtros por tipo de cliente
    const clientesAtivos = clientes.filter(c => c.tipo_cadastro === 'cliente');
    
    // 1. VIPs inativos (>20 dias sem compra)
    const vipsInativos = clientesAtivos.filter(cliente => {
      // Buscar segmento nas estatísticas ou assumir que está no cliente
      const segmento = cliente.segmento || 'Regular';
      const diasSemCompra = cliente.dias_desde_ultima_compra || 999;
      return segmento === 'VIP' && diasSemCompra > 20;
    });
    
    const impactoVips = vipsInativos.reduce((acc, c) => acc + (c.total_90d || 0), 0);
    
    // 2. Clientes inativos (>90 dias)
    const clientesInativos = clientesAtivos.filter(cliente => {
      const diasSemCompra = cliente.dias_desde_ultima_compra || 0;
      return diasSemCompra > 90;
    });
    
    const impactoInativos = clientesInativos.reduce((acc, c) => acc + (c.total_historico || 0), 0);
    
    // 3. Clientes endividados
    const clientesEndividados = clientesAtivos.filter(cliente => {
      return (cliente.saldo_devedor || 0) > 0;
    });
    
    const totalDividas = clientesEndividados.reduce((acc, c) => acc + (c.saldo_devedor || 0), 0);
    
    // 4. Novos promissores (Segmento Novo + ticket alto)
    const novosPromissores = clientesAtivos.filter(cliente => {
      const segmento = cliente.segmento || 'Regular';
      const ticketMedio = cliente.ticket_medio || 0;
      return segmento === 'Novo' && ticketMedio > 200;
    });
    
    const potencialNovos = novosPromissores.reduce((acc, c) => acc + (c.ticket_medio || 0), 0);
    
    // 5. Pets sem eventos (calculado aproximadamente - requer mais dados)
    const clientesComPets = clientesAtivos.filter(c => c.pets && c.pets.length > 0);
    let petsInativos = 0;
    let clientesComPetsInativos = [];
    
    clientesComPets.forEach(cliente => {
      if (cliente.pets) {
        const petsSemEvento = cliente.pets.filter(pet => {
          if (!pet.ultima_consulta) return true;
          const ultimaConsulta = new Date(pet.ultima_consulta);
          const diasSem = Math.floor((hoje - ultimaConsulta) / (1000 * 60 * 60 * 24));
          return diasSem > 60;
        });
        
        if (petsSemEvento.length > 0) {
          petsInativos += petsSemEvento.length;
          clientesComPetsInativos.push(cliente);
        }
      }
    });
    
    // 6. WhatsApp faltando
    const semWhatsApp = clientesAtivos.filter(c => !c.celular || c.celular.trim() === '');
    
    return {
      vips_inativos: {
        quantidade: vipsInativos.length,
        impacto: `R$ ${impactoVips.toFixed(2)}`,
        clientes: vipsInativos
      },
      clientes_inativos: {
        quantidade: clientesInativos.length,
        impacto: `R$ ${(impactoInativos / 12).toFixed(2)}/mês`,
        clientes: clientesInativos
      },
      clientes_endividados: {
        quantidade: clientesEndividados.length,
        impacto: `R$ ${totalDividas.toFixed(2)}`,
        clientes: clientesEndividados
      },
      oportunidades_novos: {
        quantidade: novosPromissores.length,
        impacto: `~R$ ${potencialNovos.toFixed(0)}/mês`,
        clientes: novosPromissores
      },
      pets_sem_eventos: {
        quantidade: petsInativos,
        impacto: `${clientesComPetsInativos.length} donos`,
        clientes: clientesComPetsInativos
      },
      whatsapp_inativo: {
        quantidade: semWhatsApp.length,
        impacto: 'Canal perdido',
        clientes: semWhatsApp
      },
      
      // Dados gerais
      total_clientes: clientesAtivos.length,
      estatisticas: estatisticas
    };
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
            dados={metricas.vips_inativos}
            onClick={() => handleCardClick('vips_inativos')}
          />
          
          <MetricCard
            tipo="clientes_inativos"
            dados={metricas.clientes_inativos}
            onClick={() => handleCardClick('clientes_inativos')}
          />
          
          <MetricCard
            tipo="clientes_endividados"
            dados={metricas.clientes_endividados}
            onClick={() => handleCardClick('clientes_endividados')}
          />
          
          <MetricCard
            tipo="oportunidades_novos"
            dados={metricas.oportunidades_novos}
            onClick={() => handleCardClick('oportunidades_novos')}
          />
          
          <MetricCard
            tipo="pets_sem_eventos"
            dados={metricas.pets_sem_eventos}
            onClick={() => handleCardClick('pets_sem_eventos')}
          />
          
          <MetricCard
            tipo="whatsapp_inativo"
            dados={metricas.whatsapp_inativo}
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
                <strong>{metricas.vips_inativos.quantidade}</strong> clientes VIP em risco de churn
              </p>
              <p className="text-xs text-gray-600">
                Contate imediatamente para evitar perda de {metricas.vips_inativos.impacto} em receita
              </p>
            </div>
            
            {/* Prioridade 2: Recuperação */}
            <div className="border-l-4 border-yellow-500 pl-4">
              <h3 className="font-semibold text-yellow-700 mb-2">⚠️ Atenção</h3>
              <p className="text-sm text-gray-700 mb-2">
                <strong>{metricas.clientes_endividados.quantidade}</strong> clientes endividados
              </p>
              <p className="text-xs text-gray-600">
                Total de {metricas.clientes_endividados.impacto} em aberto • Avaliar condições
              </p>
            </div>
            
            {/* Prioridade 3: Oportunidades */}
            <div className="border-l-4 border-green-500 pl-4">
              <h3 className="font-semibold text-green-700 mb-2">💡 Oportunidade</h3>
              <p className="text-sm text-gray-700 mb-2">
                <strong>{metricas.oportunidades_novos.quantidade}</strong> novos clientes promissores
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
