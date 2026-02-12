/**
 * Componente de Status de Margem - Apenas Indicador Visual
 * NÃO mostra valores numéricos, apenas cores e mensagens
 */
import React from 'react';

const StatusMargemIndicador = ({ status, className = '' }) => {
  if (!status) return null;

  const configs = {
    verde: {
      cor: 'bg-green-500',
      borda: 'border-green-500',
      texto: 'text-green-700',
      fundo: 'bg-green-50',
      icone: '✅',
      mensagem: 'Margem Saudável',
      descricao: 'Venda em condições ideais'
    },
    amarelo: {
      cor: 'bg-yellow-500',
      borda: 'border-yellow-500',
      texto: 'text-yellow-700',
      fundo: 'bg-yellow-50',
      icone: '⚠️',
      mensagem: 'Margem em Alerta',
      descricao: 'Atenção com parcelamento e descontos'
    },
    vermelho: {
      cor: 'bg-red-500',
      borda: 'border-red-500',
      texto: 'text-red-700',
      fundo: 'bg-red-50',
      icone: '🔴',
      mensagem: 'Margem Crítica',
      descricao: 'Evite mais descontos ou parcelamentos longos'
    }
  };

  const config = configs[status] || configs.verde;

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${config.borda} ${config.fundo} ${className}`}>
      <div className={`w-3 h-3 rounded-full ${config.cor} animate-pulse`} />
      <div className="flex-1">
        <div className={`text-sm font-semibold ${config.texto}`}>
          {config.icone} {config.mensagem}
        </div>
        <div className="text-xs text-gray-600">
          {config.descricao}
        </div>
      </div>
    </div>
  );
};

export default StatusMargemIndicador;
