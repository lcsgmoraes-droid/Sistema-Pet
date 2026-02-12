/**
 * Componente de Segmentação de Clientes
 * Exibe visualmente o segmento calculado, métricas e tags
 */

import { useState, useEffect } from 'react';
import { 
  FiTrendingUp, FiTrendingDown, FiDollarSign, FiShoppingCart, 
  FiAlertCircle, FiAward, FiClock, FiUser, FiRefreshCw
} from 'react-icons/fi';
import api from '../api';

// Configuração de cores por segmento
const SEGMENTO_CONFIG = {
  VIP: {
    color: 'purple',
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-800',
    borderClass: 'border-purple-300',
    icon: FiAward,
    descricao: 'Cliente de alto valor',
    emoji: '👑'
  },
  Recorrente: {
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-800',
    borderClass: 'border-blue-300',
    icon: FiTrendingUp,
    descricao: 'Compra com frequência',
    emoji: '🔄'
  },
  Novo: {
    color: 'green',
    bgClass: 'bg-green-100',
    textClass: 'text-green-800',
    borderClass: 'border-green-300',
    icon: FiUser,
    descricao: 'Cliente recente',
    emoji: '🌟'
  },
  Inativo: {
    color: 'gray',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-800',
    borderClass: 'border-gray-300',
    icon: FiClock,
    descricao: 'Sem compras recentes',
    emoji: '⏰'
  },
  Endividado: {
    color: 'red',
    bgClass: 'bg-red-100',
    textClass: 'text-red-800',
    borderClass: 'border-red-300',
    icon: FiAlertCircle,
    descricao: 'Alto saldo devedor',
    emoji: '⚠️'
  },
  Risco: {
    color: 'orange',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-800',
    borderClass: 'border-orange-300',
    icon: FiTrendingDown,
    descricao: 'Diminuição de frequência',
    emoji: '📉'
  },
  Regular: {
    color: 'gray',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-600',
    borderClass: 'border-gray-200',
    icon: FiUser,
    descricao: 'Cliente regular',
    emoji: '👤'
  }
};

/**
 * Badge de segmento simples (para lista)
 */
export function SegmentoBadge({ segmento, size = 'sm', showIcon = false }) {
  if (!segmento) return null;

  const config = SEGMENTO_CONFIG[segmento] || SEGMENTO_CONFIG.Regular;
  const Icon = config.icon;

  const sizeClasses = {
    xs: 'text-xs px-2 py-0.5',
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2'
  };

  return (
    <span 
      className={`inline-flex items-center gap-1 font-medium rounded-full ${config.bgClass} ${config.textClass} ${sizeClasses[size]}`}
      title={config.descricao}
    >
      {showIcon && <Icon size={size === 'xs' ? 10 : size === 'sm' ? 12 : 14} />}
      {config.emoji} {segmento}
    </span>
  );
}

/**
 * Tag individual (para múltiplas tags)
 */
function TagBadge({ tag }) {
  const config = SEGMENTO_CONFIG[tag] || SEGMENTO_CONFIG.Regular;

  return (
    <span 
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md ${config.bgClass} ${config.textClass}`}
      title={config.descricao}
    >
      {config.emoji} {tag}
    </span>
  );
}

/**
 * Formatador de valores monetários
 */
function formatMoney(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
}

/**
 * Card completo de segmentação (para detalhe do cliente)
 */
export function ClienteSegmentos({ clienteId, compact = false }) {
  const [segmento, setSegmento] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recalculando, setRecalculando] = useState(false);

  useEffect(() => {
    if (clienteId) {
      carregarSegmento();
    }
  }, [clienteId]);

  const carregarSegmento = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get(`/segmentacao/clientes/${clienteId}`);
      setSegmento(response.data);
    } catch (err) {
      if (err.response?.status === 404) {
        // Cliente ainda não foi segmentado - isso é normal, não é erro
        setError('not_calculated');
        // Silenciar completamente - não é um problema
      } else {
        setError('Erro ao carregar segmentação');
        console.error('Erro ao carregar segmentação:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const recalcularSegmento = async () => {
    try {
      setRecalculando(true);
      
      const response = await api.post(`/segmentacao/clientes/${clienteId}/recalcular`);
      setSegmento(response.data);
      setError(null);
    } catch (err) {
      console.error('Erro ao recalcular segmento:', err);
      alert('Erro ao recalcular segmento. Tente novamente.');
    } finally {
      setRecalculando(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="animate-pulse bg-gray-100 rounded-lg p-6">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    );
  }

  // Error: ainda não calculado
  if (error === 'not_calculated') {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <FiAlertCircle className="text-yellow-600 mt-1" size={20} />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-yellow-900 mb-2">
              Segmentação não calculada
            </h4>
            <p className="text-sm text-yellow-800 mb-4">
              Este cliente ainda não foi segmentado. Clique abaixo para calcular.
            </p>
            <button
              onClick={recalcularSegmento}
              disabled={recalculando}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-400 text-white rounded-lg transition-colors text-sm font-medium"
            >
              <FiRefreshCw className={recalculando ? 'animate-spin' : ''} />
              {recalculando ? 'Calculando...' : 'Calcular segmento'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Error: outro erro
  if (error && error !== 'not_calculated') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  // Sem dados
  if (!segmento) {
    return null;
  }

  const config = SEGMENTO_CONFIG[segmento.segmento] || SEGMENTO_CONFIG.Regular;
  const Icon = config.icon;
  const metricas = segmento.metricas || {};

  // Classes de gradiente (não podem ser construídas dinamicamente no Tailwind)
  const gradientClasses = {
    purple: 'bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-300',
    blue: 'bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300',
    green: 'bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-300',
    gray: 'bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-300',
    red: 'bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-300',
    orange: 'bg-gradient-to-br from-orange-50 to-orange-100 border-2 border-orange-300'
  };

  const gradientClass = gradientClasses[config.color] || gradientClasses.gray;

  // Versão compacta (para lista)
  if (compact) {
    return <SegmentoBadge segmento={segmento.segmento} size="sm" />;
  }

  // Versão completa (para detalhe)
  return (
    <div className={`${gradientClass} rounded-xl p-6 shadow-sm`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-3 ${config.bgClass} rounded-lg`}>
            <Icon className={config.textClass} size={24} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              {config.emoji} Segmentação: <span className={config.textClass}>{segmento.segmento}</span>
            </h3>
            <p className="text-sm text-gray-600">{config.descricao}</p>
          </div>
        </div>
        <button
          onClick={recalcularSegmento}
          disabled={recalculando}
          className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-gray-50 disabled:bg-gray-100 border border-gray-300 text-gray-700 rounded-lg transition-colors text-sm"
          title="Recalcular segmento"
        >
          <FiRefreshCw size={14} className={recalculando ? 'animate-spin' : ''} />
          {recalculando ? 'Calculando...' : 'Atualizar'}
        </button>
      </div>

      {/* Tags múltiplas */}
      {segmento.tags && segmento.tags.length > 1 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">Também se enquadra em:</p>
          <div className="flex flex-wrap gap-2">
            {segmento.tags.filter(tag => tag !== segmento.segmento).map(tag => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        </div>
      )}

      {/* Métricas principais */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <FiDollarSign className="text-gray-500" size={16} />
            <p className="text-xs text-gray-600 font-medium">Total 90 dias</p>
          </div>
          <p className="text-lg font-bold text-gray-900">
            {formatMoney(metricas.total_compras_90d || 0)}
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <FiShoppingCart className="text-gray-500" size={16} />
            <p className="text-xs text-gray-600 font-medium">Compras 90d</p>
          </div>
          <p className="text-lg font-bold text-gray-900">
            {metricas.compras_90d || 0}
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <FiTrendingUp className="text-gray-500" size={16} />
            <p className="text-xs text-gray-600 font-medium">Ticket médio</p>
          </div>
          <p className="text-lg font-bold text-gray-900">
            {formatMoney(metricas.ticket_medio || 0)}
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <FiClock className="text-gray-500" size={16} />
            <p className="text-xs text-gray-600 font-medium">Última compra</p>
          </div>
          <p className="text-lg font-bold text-gray-900">
            {metricas.ultima_compra_dias === 9999 
              ? 'Nunca' 
              : `${metricas.ultima_compra_dias} dias`
            }
          </p>
        </div>
      </div>

      {/* Métricas secundárias */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="flex justify-between items-center bg-white/60 rounded-lg p-2">
          <span className="text-gray-600">Total em aberto:</span>
          <span className={`font-semibold ${metricas.total_em_aberto > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatMoney(metricas.total_em_aberto || 0)}
          </span>
        </div>

        <div className="flex justify-between items-center bg-white/60 rounded-lg p-2">
          <span className="text-gray-600">Cliente há:</span>
          <span className="font-semibold text-gray-900">
            {metricas.primeira_compra_dias > 0 ? `${metricas.primeira_compra_dias} dias` : 'Sem compras'}
          </span>
        </div>

        <div className="flex justify-between items-center bg-white/60 rounded-lg p-2">
          <span className="text-gray-600">Total histórico:</span>
          <span className="font-semibold text-gray-900">
            {formatMoney(metricas.total_historico || 0)}
          </span>
        </div>

        <div className="flex justify-between items-center bg-white/60 rounded-lg p-2">
          <span className="text-gray-600">Total de compras:</span>
          <span className="font-semibold text-gray-900">
            {metricas.total_compras_historico || 0}
          </span>
        </div>
      </div>

      {/* Informação de atualização */}
      {segmento.updated_at && (
        <div className="mt-4 pt-4 border-t border-gray-300/50">
          <p className="text-xs text-gray-600">
            Atualizado em: {new Date(segmento.updated_at).toLocaleString('pt-BR')}
          </p>
        </div>
      )}
    </div>
  );
}

export default ClienteSegmentos;
