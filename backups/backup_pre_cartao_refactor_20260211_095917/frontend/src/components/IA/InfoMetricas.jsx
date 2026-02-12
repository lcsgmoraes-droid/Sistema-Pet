/**
 * Painel informativo explicando as métricas do Dashboard IA
 */

import React, { useState } from 'react';
import { ChevronDown, Info } from 'lucide-react';

export default function InfoMetricas() {
  const [expandido, setExpandido] = useState(false);

  const metricas = [
    {
      titulo: 'Dias de Caixa',
      descricao: 'Quantos dias seu caixa consegue cobrir as despesas com o saldo atual. Se tem R$ 10.000 e gasta R$ 1.000/dia, terá 10 dias de caixa.',
      formula: 'Saldo Atual ÷ Despesa Média Diária',
      referencia: 'Últimos 30 dias'
    },
    {
      titulo: 'Saldo Estimado (Projeção)',
      descricao: 'Previsão do saldo do caixa para os próximos 15 dias, calculada usando inteligência artificial (Prophet) baseada em histórico de 30+ dias.',
      formula: 'Saldo Atual + Receitas Previstas - Despesas Previstas',
      referencia: 'Próximos 15 dias'
    },
    {
      titulo: 'Entrada/Saída Estimada',
      descricao: 'Previsão diária de quanto você deve receber (entradas) e gastar (saídas) nos próximos dias.',
      formula: 'Média histórica ÷ 30 dias × fator sazonalidade',
      referencia: 'Próximos 15 dias'
    },
    {
      titulo: 'Status do Caixa',
      descricao: 'Classificação da saúde financeira: CRITICO (<7 dias), ALERTA (7-15 dias) ou OK (>15 dias)',
      formula: 'Status = IF(dias_caixa < 7) "CRITICO" ELSE IF(dias_caixa < 15) "ALERTA" ELSE "OK"',
      referencia: 'Dados em tempo real'
    }
  ];

  const abas = [
    {
      nome: 'Visão Geral',
      conteudo: 'Mostra os índices principais de saúde do caixa: quanto tempo de saldo você tem, a tendência (melhorando/piorando), despesa média diária e score geral de saúde.',
      periodo: 'Últimos 30 dias de histórico'
    },
    {
      nome: 'Projeções 15 Dias',
      conteudo: 'Gráfico e tabela com a previsão de saldo diário para os próximos 15 dias. Usa algoritmo Prophet com inteligência artificial.',
      periodo: 'Próximos 15 dias a partir de hoje'
    },
    {
      nome: 'Alertas',
      conteudo: 'Lista automática de avisos: se o caixa está crítico, se há risco de falta de saldo, ou se a tendência está piorando.',
      periodo: 'Monitoramento contínuo'
    },
    {
      nome: 'Simulador',
      conteudo: 'Permite simular 3 cenários: OTIMISTA (+20% receita, -10% despesa), REALISTA (sem mudanças) e PESSIMISTA (-20% receita, +10% despesa).',
      periodo: 'Próximos 15 dias com mudanças aplicadas'
    }
  ];

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-6">
      <button
        onClick={() => setExpandido(!expandido)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <Info className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-bold text-gray-900">
            Entenda os Dados
          </h2>
        </div>
        <ChevronDown className={`w-5 h-5 text-blue-600 transition-transform ${expandido ? 'rotate-180' : ''}`} />
      </button>

      {expandido && (
        <div className="mt-6 space-y-8">
          {/* Seção: As 4 Abas */}
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-4">O que cada aba mostra?</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {abas.map((aba, idx) => (
                <div key={idx} className="bg-white p-4 rounded-lg border border-blue-100">
                  <h4 className="font-semibold text-gray-900 mb-2">{aba.nome}</h4>
                  <p className="text-sm text-gray-700 mb-2">{aba.conteudo}</p>
                  <p className="text-xs text-blue-600 font-medium">📅 {aba.periodo}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Seção: Métricas Principais */}
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-4">Métricas Explicadas</h3>
            <div className="space-y-4">
              {metricas.map((metrica, idx) => (
                <div key={idx} className="bg-white p-4 rounded-lg border border-blue-100">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-blue-600">{idx + 1}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900">{metrica.titulo}</h4>
                      <p className="text-sm text-gray-700 mt-1">{metrica.descricao}</p>
                      <div className="mt-2 text-xs space-y-1">
                        <p className="text-gray-600"><strong>Cálculo:</strong> {metrica.formula}</p>
                        <p className="text-blue-600"><strong>Período:</strong> {metrica.referencia}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Seção: Perguntas Comuns */}
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-4">Perguntas Frequentes</h3>
            <div className="space-y-3">
              <div className="bg-white p-4 rounded-lg border border-blue-100">
                <p className="font-semibold text-gray-900 text-sm mb-1">
                  ❓ Qual período a "Visão Geral" está analisando?
                </p>
                <p className="text-sm text-gray-700">
                  Os últimos <strong>30 dias</strong> de movimentações realizadas. Ela calcula a despesa média desse período para determinar quantos dias de caixa você tem.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-blue-100">
                <p className="font-semibold text-gray-900 text-sm mb-1">
                  ❓ O gráfico de Projeções é confiável?
                </p>
                <p className="text-sm text-gray-700">
                  Usa algoritmo Prophet (inteligência artificial) que aprende com os últimos <strong>30+ dias</strong> de dados. Quanto mais histórico, mais preciso. Funciona bem para tendências, mas não prevê eventos inesperados.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-blue-100">
                <p className="font-semibold text-gray-900 text-sm mb-1">
                  ❓ O Simulador altera meus dados reais?
                </p>
                <p className="text-sm text-gray-700">
                  <strong>NÃO!</strong> É apenas uma simulação. Mostra "E se..." ocorressem essas mudanças. Seus dados permanecem intactos.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-blue-100">
                <p className="font-semibold text-gray-900 text-sm mb-1">
                  ❓ Como interpretar "Dias de Caixa"?
                </p>
                <p className="text-sm text-gray-700">
                  <strong>10 dias</strong> = você pode cobrir <strong>10 dias de despesas</strong> com saldo atual. Se <strong>&lt;7 dias</strong> é crítico (risco iminente). Se <strong>7-15</strong> é alerta. Se <strong>&gt;15</strong> está ok.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-blue-100">
                <p className="font-semibold text-gray-900 text-sm mb-1">
                  ❓ Qual é a diferença entre "Saldo Atual" e "Saldo Estimado"?
                </p>
                <p className="text-sm text-gray-700">
                  <strong>Saldo Atual</strong> = saldo real hoje. <strong>Saldo Estimado</strong> = previsão do saldo daqui a X dias (levando em conta receitas/despesas esperadas).
                </p>
              </div>
            </div>
          </div>

          {/* Seção: Bom a Saber */}
          <div className="bg-blue-50 border border-blue-300 rounded-lg p-4">
            <p className="text-sm font-semibold text-blue-900 mb-2">💡 Dicas Importantes:</p>
            <ul className="text-sm text-blue-900 space-y-1">
              <li>• Clique em <strong>"Atualizar Projeção"</strong> para recalcular com dados mais recentes</li>
              <li>• Os Alertas aparecem automaticamente quando há risco (caixa &lt;7 dias ou tendência negativa)</li>
              <li>• Use o Simulador para planejar: "E se aumentar despesas de marketing em 20%?"</li>
              <li>• Se tiver menos de 30 dias de histórico, as projeções serão mais conservadoras</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
