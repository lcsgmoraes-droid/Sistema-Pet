/**
 * Gráfico de projeções de fluxo de caixa
 * Usa Recharts para visualizar projeções futuras com intervalo de confiança
 */

import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const formatarMoeda = (valor) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0
  }).format(valor);
};

const formatarData = (dataString) => {
  try {
    const data = parseISO(dataString);
    return format(data, 'dd/MMM', { locale: ptBR });
  } catch {
    return dataString;
  }
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
      <p className="font-medium text-gray-900 mb-2">
        {formatarData(data.data_projetada)}
      </p>
      <div className="space-y-1 text-sm">
        <p className="text-blue-600">
          Saldo: <strong>{formatarMoeda(data.saldo_estimado)}</strong>
        </p>
        {data.limite_superior && (
          <p className="text-green-600">
            Otimista: {formatarMoeda(data.limite_superior)}
          </p>
        )}
        {data.limite_inferior && (
          <p className="text-red-600">
            Pessimista: {formatarMoeda(data.limite_inferior)}
          </p>
        )}
        {data.alerta_nivel && (
          <p className={`font-medium ${
            data.alerta_nivel === 'critico' ? 'text-red-600' :
            data.alerta_nivel === 'alerta' ? 'text-yellow-600' :
            'text-green-600'
          }`}>
            Status: {data.alerta_nivel}
          </p>
        )}
      </div>
    </div>
  );
};

export default function GraficoProjecoes({ projecoes, titulo = 'Projeção de Fluxo de Caixa', detalhado = false }) {
  if (!projecoes || projecoes.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{titulo}</h3>
        <div className="text-center py-8 text-gray-500">
          Nenhuma projeção disponível. Clique em "Atualizar Projeção" para gerar.
        </div>
      </div>
    );
  }

  // Preparar dados para o gráfico
  const dados = projecoes.map(p => ({
    ...p,
    data_formatada: formatarData(p.data_projetada),
    saldo: p.saldo_estimado || 0,
    superior: p.limite_superior || null,
    inferior: p.limite_inferior || null
  }));

  // Verificar se tem intervalos de confiança
  const temIntervalos = dados.some(d => d.superior !== null || d.inferior !== null);

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{titulo}</h3>
      
      {/* Estatísticas rápidas */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <p className="text-sm text-gray-600">Saldo Inicial</p>
          <p className="text-lg font-bold text-gray-900">
            {formatarMoeda(dados[0]?.saldo || 0)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600">Saldo Final</p>
          <p className="text-lg font-bold text-gray-900">
            {formatarMoeda(dados[dados.length - 1]?.saldo || 0)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600">Variação</p>
          <p className={`text-lg font-bold ${
            (dados[dados.length - 1]?.saldo - dados[0]?.saldo) >= 0
              ? 'text-green-600'
              : 'text-red-600'
          }`}>
            {formatarMoeda((dados[dados.length - 1]?.saldo || 0) - (dados[0]?.saldo || 0))}
          </p>
        </div>
      </div>

      {/* Gráfico */}
      <ResponsiveContainer width="100%" height={detalhado ? 400 : 300}>
        {temIntervalos ? (
          <AreaChart data={dados}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="data_formatada" 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            
            {/* Área de confiança */}
            <Area
              type="monotone"
              dataKey="superior"
              stroke="#10b981"
              fill="#d1fae5"
              fillOpacity={0.3}
              name="Cenário Otimista"
            />
            <Area
              type="monotone"
              dataKey="inferior"
              stroke="#ef4444"
              fill="#fee2e2"
              fillOpacity={0.3}
              name="Cenário Pessimista"
            />
            
            {/* Linha principal */}
            <Line
              type="monotone"
              dataKey="saldo"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ r: 4, fill: '#3b82f6' }}
              name="Saldo Estimado"
            />
          </AreaChart>
        ) : (
          <LineChart data={dados}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="data_formatada" 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="saldo"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ r: 4, fill: '#3b82f6' }}
              name="Saldo Estimado"
            />
          </LineChart>
        )}
      </ResponsiveContainer>

      {/* Alertas visuais */}
      {dados.some(d => d.vai_faltar_caixa) && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800 font-medium">
            ⚠️ Atenção: Projeção indica que o caixa pode ficar negativo nos próximos dias!
          </p>
        </div>
      )}
    </div>
  );
}
