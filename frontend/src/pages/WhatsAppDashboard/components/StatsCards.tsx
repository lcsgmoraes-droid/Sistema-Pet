import React, { memo } from 'react';
import type { DashboardStats } from '../../../stores/whatsappStore';

interface StatsCardsProps {
  stats: DashboardStats | null;
  fallbackStats: DashboardStats;
  isLoading: boolean;
}

export const StatsCards: React.FC<StatsCardsProps> = memo(({ stats, fallbackStats, isLoading }) => {
  const sourceStats = stats || fallbackStats;
  const skeletonKeys = ['s1', 's2', 's3', 's4', 's5', 's6'];

  if (isLoading && !stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {skeletonKeys.map((key) => (
          <div key={key} className="bg-gray-100 rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: 'Total',
      value: sourceStats.total_handoffs,
      icon: '💬',
      color: 'bg-blue-50 text-blue-700'
    },
    {
      label: 'Aguardando',
      value: sourceStats.pending_count,
      icon: '⏳',
      color: 'bg-yellow-50 text-yellow-700'
    },
    {
      label: 'Ativas',
      value: sourceStats.active_count,
      icon: '💭',
      color: 'bg-green-50 text-green-700'
    },
    {
      label: 'Resolvidas',
      value: sourceStats.resolved_count,
      icon: '✅',
      color: 'bg-gray-50 text-gray-700'
    },
    {
      label: 'Agentes Online',
      value: sourceStats.available_agents || 0,
      icon: '👤',
      color: 'bg-purple-50 text-purple-700'
    },
    {
      label: 'Tempo Médio',
      value: sourceStats.avg_response_time_seconds 
        ? Math.round(sourceStats.avg_response_time_seconds / 60) + 'min'
        : '0min',
      icon: '⚡',
      color: 'bg-orange-50 text-orange-700'
    }
  ];
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
      {cards.map((card) => (
        <div key={card.label} className={`rounded-lg p-4 ${card.color}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{card.icon}</span>
            <p className="text-xs font-medium opacity-75">{card.label}</p>
          </div>
          <p className="text-2xl font-bold">{card.value}</p>
        </div>
      ))}
    </div>
  );
});
