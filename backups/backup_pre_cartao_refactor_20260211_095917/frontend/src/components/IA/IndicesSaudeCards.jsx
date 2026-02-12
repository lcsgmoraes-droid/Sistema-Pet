/**
 * Cards com índices de saúde do caixa
 * Exibe: saldo atual, dias de caixa, status, tendência, score
 */

import React, { useState } from 'react';
import {
  DollarSign,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  AlertTriangle,
  CheckCircle,
  HelpCircle
} from 'lucide-react';

const getStatusColor = (status) => {
  const colors = {
    critico: 'bg-red-100 text-red-800 border-red-200',
    alerta: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    ok: 'bg-green-100 text-green-800 border-green-200'
  };
  return colors[status] || colors.ok;
};

const getStatusIcon = (status) => {
  if (status === 'critico') return <AlertTriangle className="w-5 h-5" />;
  if (status === 'alerta') return <AlertTriangle className="w-5 h-5" />;
  return <CheckCircle className="w-5 h-5" />;
};

const getTendenciaIcon = (tendencia) => {
  if (tendencia === 'melhorando') return <TrendingUp className="w-5 h-5 text-green-600" />;
  if (tendencia === 'piorando') return <TrendingDown className="w-5 h-5 text-red-600" />;
  return <Minus className="w-5 h-5 text-gray-600" />;
};

export default function IndicesSaudeCards({ indices }) {
  const [tooltipAtivo, setTooltipAtivo] = useState(null);

  if (!indices) {
    return (
      <div className="text-center py-8 text-gray-500">
        Nenhum índice disponível
      </div>
    );
  }

  const {
    saldo_atual,
    dias_de_caixa,
    status,
    tendencia,
    score_saude,
    receita_mensal_estimada,
    despesa_mensal_estimada,
    percentual_variacao_7d
  } = indices;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Saldo Atual */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 relative group">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-blue-100 rounded-lg">
            <DollarSign className="w-6 h-6 text-blue-600" />
          </div>
          <div className="relative">
            {getTendenciaIcon(tendencia)}
            <button
              onMouseEnter={() => setTooltipAtivo('saldo')}
              onMouseLeave={() => setTooltipAtivo(null)}
              className="ml-2 text-gray-400 hover:text-gray-600"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
            {tooltipAtivo === 'saldo' && (
              <div className="absolute -right-40 top-8 bg-gray-900 text-white text-xs rounded p-2 w-48 z-10 whitespace-normal">
                <p className="font-semibold mb-1">Saldo Atual</p>
                <p>Seu saldo de caixa real neste momento. O número verde ao lado mostra a variação dos últimos 7 dias.</p>
              </div>
            )}
          </div>
        </div>
        <h3 className="text-gray-600 text-sm font-medium mb-1">Saldo Atual</h3>
        <p className="text-2xl font-bold text-gray-900">
          {new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
          }).format(saldo_atual || 0)}
        </p>
        {percentual_variacao_7d && (
          <p className="text-sm text-gray-500 mt-1">
            {percentual_variacao_7d > 0 ? '+' : ''}{percentual_variacao_7d.toFixed(1)}% em 7 dias
          </p>
        )}
      </div>

      {/* Dias de Caixa */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 relative group">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-purple-100 rounded-lg">
            <Calendar className="w-6 h-6 text-purple-600" />
          </div>
          <button
            onMouseEnter={() => setTooltipAtivo('dias')}
            onMouseLeave={() => setTooltipAtivo(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
          {tooltipAtivo === 'dias' && (
            <div className="absolute -right-40 top-8 bg-gray-900 text-white text-xs rounded p-2 w-48 z-10 whitespace-normal">
              <p className="font-semibold mb-1">Dias de Caixa</p>
              <p>Quantos dias você consegue pagar as despesas com seu saldo atual. Se tem R$ 10.000 e gasta R$ 1.000/dia = 10 dias.</p>
            </div>
          )}
        </div>
        <h3 className="text-gray-600 text-sm font-medium mb-1">Dias de Caixa</h3>
        <p className="text-2xl font-bold text-gray-900">
          {dias_de_caixa?.toFixed(1) || '0.0'} dias
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {dias_de_caixa < 7 ? 'Crítico - menos de 1 semana' :
           dias_de_caixa < 15 ? 'Alerta - menos de 2 semanas' :
           'Saudável'}
        </p>
      </div>

      {/* Status Geral */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 relative group">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-lg ${getStatusColor(status)}`}>
            {getStatusIcon(status)}
          </div>
          <button
            onMouseEnter={() => setTooltipAtivo('status')}
            onMouseLeave={() => setTooltipAtivo(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
          {tooltipAtivo === 'status' && (
            <div className="absolute -right-40 top-8 bg-gray-900 text-white text-xs rounded p-2 w-48 z-10 whitespace-normal">
              <p className="font-semibold mb-1">Status</p>
              <p><strong>CRITICO:</strong> &lt;7 dias (risco iminente). <strong>ALERTA:</strong> 7-15 dias. <strong>OK:</strong> &gt;15 dias.</p>
            </div>
          )}
        </div>
        <h3 className="text-gray-600 text-sm font-medium mb-1">Status</h3>
        <p className="text-2xl font-bold text-gray-900 capitalize">
          {status || 'N/A'}
        </p>
        <p className="text-sm text-gray-500 mt-1 capitalize">
          Tendência: {tendencia || 'estável'}
        </p>
      </div>

      {/* Score de Saúde */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 relative group">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-green-100 rounded-lg">
            <Activity className="w-6 h-6 text-green-600" />
          </div>
          <button
            onMouseEnter={() => setTooltipAtivo('score')}
            onMouseLeave={() => setTooltipAtivo(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
          {tooltipAtivo === 'score' && (
            <div className="absolute -right-40 top-8 bg-gray-900 text-white text-xs rounded p-2 w-48 z-10 whitespace-normal">
              <p className="font-semibold mb-1">Score de Saúde</p>
              <p>Nota de 0-100 que resume a saúde financeira. Considera dias de caixa, tendência e volatilidade.</p>
            </div>
          )}
        </div>
        <h3 className="text-gray-600 text-sm font-medium mb-1">Score de Saúde</h3>
        <p className="text-2xl font-bold text-gray-900">
          {score_saude?.toFixed(0) || '0'}/100
        </p>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${
              score_saude >= 70 ? 'bg-green-600' :
              score_saude >= 40 ? 'bg-yellow-600' :
              'bg-red-600'
            }`}
            style={{ width: `${score_saude || 0}%` }}
          ></div>
        </div>
      </div>

      {/* Receita Mensal Estimada */}
      {receita_mensal_estimada && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <h3 className="text-gray-600 text-sm font-medium mb-1">Receita Mensal</h3>
          <p className="text-xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', {
              style: 'currency',
              currency: 'BRL'
            }).format(receita_mensal_estimada)}
          </p>
          <p className="text-sm text-gray-500 mt-1">Estimativa</p>
        </div>
      )}

      {/* Despesa Mensal Estimada */}
      {despesa_mensal_estimada && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-red-100 rounded-lg">
              <TrendingDown className="w-6 h-6 text-red-600" />
            </div>
          </div>
          <h3 className="text-gray-600 text-sm font-medium mb-1">Despesa Mensal</h3>
          <p className="text-xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', {
              style: 'currency',
              currency: 'BRL'
            }).format(despesa_mensal_estimada)}
          </p>
          <p className="text-sm text-gray-500 mt-1">Estimativa</p>
        </div>
      )}
    </div>
  );
}
