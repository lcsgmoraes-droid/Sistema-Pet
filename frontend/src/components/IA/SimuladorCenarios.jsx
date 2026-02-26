/**
 * Simulador de CenÃ¡rios
 * Permite simular cenÃ¡rios otimista, pessimista e realista
 */

import React, { useState } from 'react';
import api from '../../api';
import { toast } from 'react-hot-toast';
import { TrendingUp, TrendingDown, Minus, Play } from 'lucide-react';
import GraficoProjecoes from './GraficoProjecoes';

const CENARIOS = [
  {
    id: 'otimista',
    nome: 'Otimista',
    descricao: 'Aumento de 20% nas receitas e reduÃ§Ã£o de 10% nas despesas',
    icon: TrendingUp,
    color: 'green'
  },
  {
    id: 'realista',
    nome: 'Realista',
    descricao: 'MantÃ©m o padrÃ£o atual de receitas e despesas',
    icon: Minus,
    color: 'blue'
  },
  {
    id: 'pessimista',
    nome: 'Pessimista',
    descricao: 'ReduÃ§Ã£o de 20% nas receitas e aumento de 10% nas despesas',
    icon: TrendingDown,
    color: 'red'
  }
];

export default function SimuladorCenarios({ userId, projecoesBase = [] }) {
  const [cenarioSelecionado, setCenarioSelecionado] = useState('realista');
  const [simulando, setSimulando] = useState(false);
  const [resultadoSimulacao, setResultadoSimulacao] = useState(null);

  const simularCenario = async () => {
    setSimulando(true);
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const response = await api.post(
        `/api/ia/fluxo/simular-cenario/${userId}`,
        { cenario: cenarioSelecionado },
        { headers }
      );

      setResultadoSimulacao(response.data);
      toast.success(`CenÃ¡rio ${cenarioSelecionado} simulado com sucesso!`);
    } catch (error) {
      console.error('Erro ao simular cenÃ¡rio:', error);
      toast.error('Erro ao simular cenÃ¡rio');
    } finally {
      setSimulando(false);
    }
  };

  const cenarioConfig = CENARIOS.find(c => c.id === cenarioSelecionado);
  const Icon = cenarioConfig?.icon;

  return (
    <div className="space-y-6">
      {/* Seletor de CenÃ¡rios */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Simulador de CenÃ¡rios
        </h3>
        <p className="text-gray-600 mb-6">
          Simule diferentes cenÃ¡rios para entender o impacto no seu fluxo de caixa
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {CENARIOS.map((cenario) => {
            const CenarioIcon = cenario.icon;
            const isSelected = cenarioSelecionado === cenario.id;

            return (
              <button
                key={cenario.id}
                onClick={() => setCenarioSelecionado(cenario.id)}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  isSelected
                    ? `border-${cenario.color}-500 bg-${cenario.color}-50`
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <CenarioIcon
                    className={`w-6 h-6 ${
                      isSelected
                        ? `text-${cenario.color}-600`
                        : 'text-gray-400'
                    }`}
                  />
                  <h4 className={`font-semibold ${
                    isSelected
                      ? `text-${cenario.color}-900`
                      : 'text-gray-900'
                  }`}>
                    {cenario.nome}
                  </h4>
                </div>
                <p className={`text-sm ${
                  isSelected
                    ? `text-${cenario.color}-700`
                    : 'text-gray-600'
                }`}>
                  {cenario.descricao}
                </p>
              </button>
            );
          })}
        </div>

        <button
          onClick={simularCenario}
          disabled={simulando}
          className="w-full md:w-auto px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {simulando ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              Simulando...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Simular CenÃ¡rio
            </>
          )}
        </button>
      </div>

      {/* Resultado da SimulaÃ§Ã£o */}
      {resultadoSimulacao && (
        <>
          {/* ComparaÃ§Ã£o de MÃ©tricas */}
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              ComparaÃ§Ã£o: Base vs {cenarioConfig?.nome}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* ProjeÃ§Ã£o Base */}
              <div>
                <h4 className="font-medium text-gray-700 mb-3">CenÃ¡rio Atual</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Saldo Final</span>
                    <span className="font-semibold text-gray-900">
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                      }).format(projecoesBase?.[projecoesBase?.length - 1]?.saldo_estimado || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">VariaÃ§Ã£o</span>
                    <span className="font-semibold text-gray-900">
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                      }).format(
                      (projecoesBase?.[projecoesBase?.length - 1]?.saldo_estimado || 0) -
                      (projecoesBase?.[0]?.saldo_estimado || 0)
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* ProjeÃ§Ã£o Simulada */}
              <div>
                <h4 className="font-medium text-gray-700 mb-3">CenÃ¡rio {cenarioConfig?.nome}</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Saldo Final</span>
                    <span className={`font-semibold ${
                      cenarioSelecionado === 'otimista' ? 'text-green-600' :
                      cenarioSelecionado === 'pessimista' ? 'text-red-600' :
                      'text-blue-600'
                    }`}>
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                      }).format(
                        resultadoSimulacao?.projecoes_ajustadas?.[resultadoSimulacao?.projecoes_ajustadas?.length - 1]?.saldo_ajustado || 0
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">VariaÃ§Ã£o</span>
                    <span className={`font-semibold ${
                      cenarioSelecionado === 'otimista' ? 'text-green-600' :
                      cenarioSelecionado === 'pessimista' ? 'text-red-600' :
                      'text-blue-600'
                    }`}>
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                      }).format(
                        (resultadoSimulacao?.projecoes_ajustadas?.[resultadoSimulacao?.projecoes_ajustadas?.length - 1]?.saldo_ajustado || 0) -
                        (resultadoSimulacao?.projecoes_ajustadas?.[0]?.saldo_ajustado || 0)
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* DiferenÃ§a */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-700">DiferenÃ§a no Saldo Final</span>
                <span className={`text-xl font-bold ${
                  (resultadoSimulacao?.projecoes_ajustadas?.[resultadoSimulacao?.projecoes_ajustadas?.length - 1]?.saldo_ajustado || 0) >
                  (projecoesBase?.[projecoesBase?.length - 1]?.saldo_estimado || 0)
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {new Intl.NumberFormat('pt-BR', {
                    style: 'currency',
                    currency: 'BRL'
                  }).format(
                    (resultadoSimulacao?.projecoes_ajustadas?.[resultadoSimulacao?.projecoes_ajustadas?.length - 1]?.saldo_ajustado || 0) -
                    (projecoesBase?.[projecoesBase?.length - 1]?.saldo_estimado || 0)
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* GrÃ¡fico da SimulaÃ§Ã£o */}
          <GraficoProjecoes
            projecoes={resultadoSimulacao?.projecoes_ajustadas || []}
            titulo={`ProjeÃ§Ã£o - CenÃ¡rio ${cenarioConfig?.nome}`}
            detalhado
          />
        </>
      )}

      {/* CenÃ¡rio Base */}
      {!resultadoSimulacao && projecoesBase && projecoesBase.length > 0 && (
        <GraficoProjecoes
          projecoes={projecoesBase}
          titulo="ProjeÃ§Ã£o Atual (CenÃ¡rio Base)"
          detalhado
        />
      )}
    </div>
  );
}

