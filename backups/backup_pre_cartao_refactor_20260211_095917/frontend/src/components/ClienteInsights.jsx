/**
 * Componente de Insights Operacionais por Cliente
 * Exibe 1-3 insights acionáveis baseados em regras simples
 * 
 * MVP: Apenas visual, sem automações ou IA
 * Futuro: Migrar regras para backend e adicionar IA
 */

import { useState, useEffect } from 'react';
import { 
  FiAlertTriangle, FiTrendingUp, FiMessageCircle, 
  FiClock, FiDollarSign, FiHeart, FiZap, FiInfo
} from 'react-icons/fi';
import api from '../api';

// Tipos de impacto dos insights
const TIPO_IMPACTO = {
  RISCO: {
    color: 'red',
    bgClass: 'bg-red-50',
    borderClass: 'border-red-200',
    tagClass: 'bg-red-100 text-red-700',
    label: '⚠️ Risco'
  },
  OPORTUNIDADE: {
    color: 'green',
    bgClass: 'bg-green-50',
    borderClass: 'border-green-200',
    tagClass: 'bg-green-100 text-green-700',
    label: '💡 Oportunidade'
  },
  ATENCAO: {
    color: 'yellow',
    bgClass: 'bg-yellow-50',
    borderClass: 'border-yellow-200',
    tagClass: 'bg-yellow-100 text-yellow-700',
    label: '👀 Atenção'
  }
};

/**
 * Função que calcula insights baseados em regras
 */
function calcularInsights(cliente, metricas, pets, temWhatsApp) {
  const insights = [];
  const hoje = new Date();

  // Regra 1: VIP sem compra há >20 dias → Risco de churn
  if (metricas?.segmento === 'VIP' && metricas?.dias_desde_ultima_compra > 20) {
    insights.push({
      tipo: 'RISCO',
      icone: FiAlertTriangle,
      titulo: 'VIP em risco de churn',
      descricao: `Sem compras há ${metricas.dias_desde_ultima_compra} dias. Cliente VIP precisa de atenção especial.`,
      prioridade: 10
    });
  }

  // Regra 2: Inativo >90 dias → Cliente perdido
  if (metricas?.dias_desde_ultima_compra > 90) {
    insights.push({
      tipo: 'RISCO',
      icone: FiClock,
      titulo: 'Cliente inativo há muito tempo',
      descricao: `Última compra foi há ${metricas.dias_desde_ultima_compra} dias. Considere campanha de reativação.`,
      prioridade: 8
    });
  }

  // Regra 3: Endividado com compras recentes → Alerta financeiro
  if (metricas?.saldo_devedor > 0 && metricas?.total_90d > 0 && metricas?.dias_desde_ultima_compra < 30) {
    const percDevedor = (metricas.saldo_devedor / metricas.total_90d) * 100;
    if (percDevedor > 50) {
      insights.push({
        tipo: 'ATENCAO',
        icone: FiDollarSign,
        titulo: 'Alto endividamento com atividade recente',
        descricao: `Saldo devedor de R$ ${metricas.saldo_devedor.toFixed(2)} (${percDevedor.toFixed(0)}% das compras). Avaliar condições.`,
        prioridade: 9
      });
    }
  }

  // Regra 4: Novo com ticket alto → Oportunidade de fidelização
  if (metricas?.segmento === 'Novo' && metricas?.ticket_medio > 200) {
    insights.push({
      tipo: 'OPORTUNIDADE',
      icone: FiTrendingUp,
      titulo: 'Novo cliente de alto valor',
      descricao: `Ticket médio de R$ ${metricas.ticket_medio.toFixed(2)}. Potencial para se tornar VIP.`,
      prioridade: 7
    });
  }

  // Regra 5: Cliente sem WhatsApp registrado → Ativar canal
  if (!temWhatsApp) {
    insights.push({
      tipo: 'ATENCAO',
      icone: FiMessageCircle,
      titulo: 'WhatsApp não registrado',
      descricao: 'Adicione o número para facilitar comunicação e envio de promoções.',
      prioridade: 5
    });
  }

  // Regra 6: Pet sem evento há 60 dias → Lembrete de serviço
  if (pets && pets.length > 0) {
    const petsInativos = pets.filter(pet => {
      if (!pet.ultima_consulta) return true;
      const ultimaConsulta = new Date(pet.ultima_consulta);
      const diasSemConsulta = Math.floor((hoje - ultimaConsulta) / (1000 * 60 * 60 * 24));
      return diasSemConsulta > 60;
    });

    if (petsInativos.length > 0) {
      const nomePet = petsInativos[0].nome;
      insights.push({
        tipo: 'OPORTUNIDADE',
        icone: FiHeart,
        titulo: `Pet ${nomePet} sem consulta há mais de 60 dias`,
        descricao: `${petsInativos.length === 1 ? 'Considere' : `${petsInativos.length} pets precisam de`} check-up ou retorno.`,
        prioridade: 6
      });
    }
  }

  // Regra 7: Recorrente com queda de frequência → Atenção
  if (metricas?.segmento === 'Recorrente' && metricas?.dias_desde_ultima_compra > 30) {
    insights.push({
      tipo: 'ATENCAO',
      icone: FiClock,
      titulo: 'Cliente recorrente com atraso',
      descricao: `Costuma comprar regularmente, mas está há ${metricas.dias_desde_ultima_compra} dias sem aparecer.`,
      prioridade: 7
    });
  }

  // Regra 8: Cliente com crédito disponível → Lembrete
  if (metricas?.saldo_credito > 0) {
    insights.push({
      tipo: 'OPORTUNIDADE',
      icone: FiDollarSign,
      titulo: 'Cliente tem crédito disponível',
      descricao: `R$ ${metricas.saldo_credito.toFixed(2)} de crédito pode ser usado. Incentive o uso.`,
      prioridade: 4
    });
  }

  // Ordenar por prioridade e retornar no máximo 3
  return insights
    .sort((a, b) => b.prioridade - a.prioridade)
    .slice(0, 3);
}

/**
 * Componente principal
 */
export default function ClienteInsights({ clienteId, cliente, metricas }) {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pets, setPets] = useState([]);

  useEffect(() => {
    if (clienteId) {
      carregarDadosInsights();
    }
  }, [clienteId, metricas]);

  const carregarDadosInsights = async () => {
    try {
      setLoading(true);
      
      // Carregar pets do cliente (se não foram passados)
      let petsCliente = cliente?.pets || [];
      if (petsCliente.length === 0 && clienteId) {
        try {
          const response = await api.get(`/clientes/${clienteId}`);
          petsCliente = response.data.pets || [];
        } catch (err) {
          console.error('Erro ao carregar pets:', err);
        }
      }
      setPets(petsCliente);

      // Verificar se tem WhatsApp
      const temWhatsApp = cliente?.celular && cliente.celular.trim() !== '';

      // Calcular insights
      const insightsCalculados = calcularInsights(
        cliente,
        metricas,
        petsCliente,
        temWhatsApp
      );

      setInsights(insightsCalculados);
    } catch (err) {
      console.error('Erro ao calcular insights:', err);
      setInsights([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <FiZap className="text-yellow-500" size={24} />
          <h3 className="text-lg font-semibold text-gray-900">⚡ Insights & Ações</h3>
        </div>
        <div className="text-center py-4 text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm">Analisando cliente...</p>
        </div>
      </div>
    );
  }

  if (!insights || insights.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <FiZap className="text-yellow-500" size={24} />
          <h3 className="text-lg font-semibold text-gray-900">⚡ Insights & Ações</h3>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-2 text-green-700">
            <FiInfo size={20} />
            <p className="font-medium">✅ Cliente em dia!</p>
          </div>
          <p className="text-sm text-green-600 mt-1">
            Nenhuma ação prioritária no momento
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-300 rounded-xl p-6 shadow-md">
      <div className="flex items-center gap-2 mb-5">
        <FiZap className="text-yellow-600" size={24} />
        <h3 className="text-lg font-semibold text-gray-900">⚡ Insights & Ações</h3>
        <span className="ml-auto text-xs text-gray-500 bg-white px-2 py-1 rounded-full">
          {insights.length} {insights.length === 1 ? 'insight' : 'insights'}
        </span>
      </div>

      <div className="space-y-3">
        {insights.map((insight, index) => {
          const config = TIPO_IMPACTO[insight.tipo];
          const Icon = insight.icone;

          return (
            <div
              key={index}
              className={`${config.bgClass} border ${config.borderClass} rounded-lg p-4 transition-all hover:shadow-md`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Icon className={`text-${config.color}-600`} size={20} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-gray-900 text-sm">
                      {insight.titulo}
                    </h4>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${config.tagClass}`}>
                      {config.label}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {insight.descricao}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-yellow-200">
        <p className="text-xs text-gray-600 flex items-center gap-1">
          <FiInfo size={12} />
          Insights calculados automaticamente com base no histórico do cliente
        </p>
      </div>
    </div>
  );
}
