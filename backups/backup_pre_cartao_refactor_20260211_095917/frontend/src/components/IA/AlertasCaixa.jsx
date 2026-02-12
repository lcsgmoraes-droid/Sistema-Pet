/**
 * Lista de alertas automáticos do caixa
 * Exibe alertas críticos, avisos e informações
 */

import React from 'react';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

const getAlertaConfig = (tipo) => {
  const configs = {
    critico: {
      icon: AlertTriangle,
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-800',
      iconColor: 'text-red-600'
    },
    alerta: {
      icon: AlertCircle,
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-800',
      iconColor: 'text-yellow-600'
    },
    aviso: {
      icon: Info,
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-800',
      iconColor: 'text-blue-600'
    },
    info: {
      icon: CheckCircle,
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-800',
      iconColor: 'text-green-600'
    }
  };
  return configs[tipo] || configs.info;
};

export default function AlertasCaixa({ alertas }) {
  if (!alertas || alertas.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Alertas do Caixa
        </h3>
        <div className="text-center py-8">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <p className="text-gray-600">Nenhum alerta no momento</p>
          <p className="text-sm text-gray-500 mt-1">Seu caixa está saudável! 🎉</p>
        </div>
      </div>
    );
  }

  // Ordenar por prioridade: crítico > alerta > aviso > info
  const prioridade = { critico: 0, alerta: 1, aviso: 2, info: 3 };
  const alertasOrdenados = [...alertas].sort((a, b) => 
    (prioridade[a.tipo] || 3) - (prioridade[b.tipo] || 3)
  );

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Alertas do Caixa
        </h3>
        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded-full">
          {alertasOrdenados.length}
        </span>
      </div>

      <div className="space-y-3">
        {alertasOrdenados.map((alerta, index) => {
          const config = getAlertaConfig(alerta.tipo);
          const Icon = config.icon;

          return (
            <div
              key={index}
              className={`p-4 rounded-lg border ${config.bgColor} ${config.borderColor}`}
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${config.iconColor}`} />
                <div className="flex-1">
                  <h4 className={`font-medium ${config.textColor} mb-1`}>
                    {alerta.titulo}
                  </h4>
                  <p className={`text-sm ${config.textColor} opacity-90`}>
                    {alerta.mensagem}
                  </p>
                  {alerta.data && (
                    <p className={`text-xs ${config.textColor} opacity-70 mt-2`}>
                      {new Date(alerta.data).toLocaleString('pt-BR')}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Estatísticas */}
      <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-4 gap-4 text-center">
        <div>
          <p className="text-2xl font-bold text-red-600">
            {alertasOrdenados.filter(a => a.tipo === 'critico').length}
          </p>
          <p className="text-xs text-gray-600">Críticos</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-yellow-600">
            {alertasOrdenados.filter(a => a.tipo === 'alerta').length}
          </p>
          <p className="text-xs text-gray-600">Alertas</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-blue-600">
            {alertasOrdenados.filter(a => a.tipo === 'aviso').length}
          </p>
          <p className="text-xs text-gray-600">Avisos</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-green-600">
            {alertasOrdenados.filter(a => a.tipo === 'info').length}
          </p>
          <p className="text-xs text-gray-600">Infos</p>
        </div>
      </div>
    </div>
  );
}
