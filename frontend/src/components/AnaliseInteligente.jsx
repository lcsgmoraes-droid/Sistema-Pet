import React, { useState, useEffect } from 'react';
import api from '../api';
import { 
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle, 
  ArrowUpRight, ArrowDownRight, Calendar, BarChart3, 
  Lightbulb, Target, DollarSign, TrendingDown as TrendDown,
  Award, Info
} from 'lucide-react';

const AnaliseInteligente = ({ dados, periodo }) => {
  const [analise, setAnalise] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comparacao, setComparacao] = useState(null);
  const [indicesMercado, setIndicesMercado] = useState(null);

  useEffect(() => {
    if (dados) {
      carregarAnalise();
      carregarIndicesMercado();
    }
  }, [dados, periodo]);

  const carregarIndicesMercado = async () => {
    try {
      const response = await api.get('/api/ia/dre/indices-mercado', {
        params: { setor: 'pet_shop' }
      });
      setIndicesMercado(response.data);
    } catch (error) {
      console.error('Erro ao carregar índices:', error);
    }
  };

  const carregarAnalise = async () => {
    setLoading(true);
    try {
      // Simular análise IA (substituir por endpoint real)
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const analiseGerada = gerarAnaliseIA(dados);
      setAnalise(analiseGerada);
      
      // Comparação com período anterior
      if (periodo.mes > 1) {
        const mesAnterior = await buscarDREMesAnterior(periodo);
        if (mesAnterior) {
          setComparacao(compararPeriodos(dados, mesAnterior));
        }
      }
    } catch (error) {
      console.error('Erro ao carregar análise:', error);
    } finally {
      setLoading(false);
    }
  };

  const buscarDREMesAnterior = async (periodo) => {
    try {
      const mesAnterior = periodo.mes === 1 ? 12 : periodo.mes - 1;
      const anoAnterior = periodo.mes === 1 ? periodo.ano - 1 : periodo.ano;
      
      const response = await api.get('/api/financeiro/dre', {
        params: { ano: anoAnterior, mes: mesAnterior }
      });
      return response.data;
    } catch (error) {
      return null;
    }
  };

  const compararPeriodos = (atual, anterior) => {
    const calcularVariacao = (valorAtual, valorAnterior) => {
      if (!valorAnterior || valorAnterior === 0) return null;
      return ((valorAtual - valorAnterior) / Math.abs(valorAnterior)) * 100;
    };

    return {
      receita: {
        atual: atual.receita_bruta || 0,
        anterior: anterior.receita_bruta || 0,
        variacao: calcularVariacao(atual.receita_bruta, anterior.receita_bruta)
      },
      lucro: {
        atual: atual.lucro_liquido || 0,
        anterior: anterior.lucro_liquido || 0,
        variacao: calcularVariacao(atual.lucro_liquido, anterior.lucro_liquido)
      },
      despesas: {
        atual: atual.total_despesas || 0,
        anterior: anterior.total_despesas || 0,
        variacao: calcularVariacao(atual.total_despesas, anterior.total_despesas)
      },
      margem: {
        atual: atual.margem_liquida || 0,
        anterior: anterior.margem_liquida || 0,
        variacao: calcularVariacao(atual.margem_liquida, anterior.margem_liquida)
      }
    };
  };

  const gerarAnaliseIA = (dados) => {
    const insights = [];
    const recomendacoes = [];
    const alertas = [];

    // Análise de Margem
    const margemLiquida = dados.margem_liquida || 0;
    if (margemLiquida < 5) {
      alertas.push({
        tipo: 'critico',
        titulo: 'Margem líquida crítica',
        descricao: `Margem de apenas ${margemLiquida.toFixed(1)}%. Ideal: acima de 10%`,
        icon: AlertTriangle
      });
      recomendacoes.push({
        prioridade: 'alta',
        titulo: 'Urgente: Revisar estrutura de custos',
        descricao: 'Margem muito baixa. Considere: aumentar preços, reduzir custos fixos, ou renegociar com fornecedores.'
      });
    } else if (margemLiquida < 10) {
      insights.push({
        tipo: 'atencao',
        titulo: 'Margem líquida abaixo do ideal',
        descricao: `${margemLiquida.toFixed(1)}% - Há espaço para melhoria`,
        icon: TrendingDown
      });
    } else {
      insights.push({
        tipo: 'positivo',
        titulo: 'Margem líquida saudável',
        descricao: `${margemLiquida.toFixed(1)}% - Acima da média do setor`,
        icon: CheckCircle
      });
    }

    // Análise de Receita vs Despesas
    const receita = dados.receita_bruta || 0;
    const despesas = dados.total_despesas || 0;
    if (despesas > receita * 0.8) {
      alertas.push({
        tipo: 'atencao',
        titulo: 'Despesas elevadas',
        descricao: `Despesas representam ${((despesas / receita) * 100).toFixed(0)}% da receita`,
        icon: AlertTriangle
      });
    }

    // Análise de CMV
    const cmv = dados.cmv || 0;
    const margemBruta = ((receita - cmv) / receita) * 100;
    if (margemBruta < 30) {
      recomendacoes.push({
        prioridade: 'media',
        titulo: 'Revisar custo dos produtos',
        descricao: `Margem bruta de ${margemBruta.toFixed(1)}%. Considere negociar com fornecedores ou ajustar preços.`
      });
    }

    // Insight de Lucro
    const lucro = dados.lucro_liquido || 0;
    if (lucro > 0) {
      insights.push({
        tipo: 'positivo',
        titulo: 'Resultado positivo',
        descricao: `Lucro de R$ ${lucro.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        icon: TrendingUp
      });
    } else {
      alertas.push({
        tipo: 'critico',
        titulo: 'Prejuízo no período',
        descricao: `Resultado negativo de R$ ${Math.abs(lucro).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        icon: TrendingDown
      });
      recomendacoes.push({
        prioridade: 'alta',
        titulo: 'Plano de recuperação necessário',
        descricao: 'Análise detalhada de custos e revisão de estratégia de precificação urgente.'
      });
    }

    // Score de Saúde Financeira
    let score = 50; // Base
    if (margemLiquida > 10) score += 20;
    if (margemLiquida > 5 && margemLiquida <= 10) score += 10;
    if (lucro > 0) score += 15;
    if (margemBruta > 30) score += 15;
    if (despesas < receita * 0.7) score += 10;

    return {
      insights,
      recomendacoes,
      alertas,
      score: Math.min(score, 100)
    };
  };

  const renderScoreSaude = (score) => {
    let cor = 'red';
    let texto = 'Crítico';
    if (score >= 80) {
      cor = 'green';
      texto = 'Excelente';
    } else if (score >= 60) {
      cor = 'yellow';
      texto = 'Bom';
    } else if (score >= 40) {
      cor = 'orange';
      texto = 'Regular';
    }

    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Target className="text-purple-600" />
          Score de Saúde Financeira
        </h3>
        <div className="flex items-center gap-6">
          <div className="relative w-32 h-32">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="#e5e7eb"
                strokeWidth="12"
                fill="none"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke={cor === 'green' ? '#10b981' : cor === 'yellow' ? '#fbbf24' : cor === 'orange' ? '#f59e0b' : '#ef4444'}
                strokeWidth="12"
                fill="none"
                strokeDasharray={`${(score / 100) * 351.86} 351.86`}
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-3xl font-bold text-gray-800">{score}</span>
            </div>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-800 mb-1">{texto}</p>
            <p className="text-sm text-gray-600">
              {score >= 80 && 'Sua saúde financeira está ótima! Continue assim.'}
              {score >= 60 && score < 80 && 'Boa saúde financeira. Pequenos ajustes podem melhorar.'}
              {score >= 40 && score < 60 && 'Situação estável, mas requer atenção.'}
              {score < 40 && 'Atenção! Medidas corretivas são necessárias.'}
            </p>
          </div>
        </div>
      </div>
    );
  };

  const renderComparativoMercado = () => {
    if (!indicesMercado || !dados) return null;

    const benchmarks = indicesMercado.benchmarks;
    const receita = dados.receita_liquida || 0;

    // Calcular percentuais atuais
    const cmvAtual = receita > 0 ? ((dados.cmv || 0) / receita) * 100 : 0;
    const margemBrutaAtual = dados.margem_bruta || 0;
    const margemLiquidaAtual = dados.margem_liquida || 0;
    const despesasAdminAtual = receita > 0 ? ((dados.despesas_admin || 0) / receita) * 100 : 0;
    const despesasTotaisAtual = receita > 0 ? ((dados.total_despesas || 0) / receita) * 100 : 0;

    const indicadores = [
      {
        nome: 'CMV',
        seu: cmvAtual,
        idealMin: benchmarks.cmv.min,
        idealMax: benchmarks.cmv.max,
        inverter: true, // Menor é melhor
        unidade: '%',
        cor: cmvAtual <= benchmarks.cmv.max ? 'green' : cmvAtual <= benchmarks.cmv.max * 1.1 ? 'yellow' : 'red'
      },
      {
        nome: 'Margem Bruta',
        seu: margemBrutaAtual,
        idealMin: benchmarks.margem_bruta.min,
        idealMax: benchmarks.margem_bruta.max,
        inverter: false, // Maior é melhor
        unidade: '%',
        cor: margemBrutaAtual >= benchmarks.margem_bruta.min ? 'green' : margemBrutaAtual >= benchmarks.margem_bruta.min * 0.9 ? 'yellow' : 'red'
      },
      {
        nome: 'Margem Líquida',
        seu: margemLiquidaAtual,
        idealMin: benchmarks.margem_liquida.min,
        idealMax: benchmarks.margem_liquida.max,
        inverter: false,
        unidade: '%',
        cor: margemLiquidaAtual >= benchmarks.margem_liquida.min ? 'green' : margemLiquidaAtual >= benchmarks.margem_liquida.min * 0.8 ? 'yellow' : 'red'
      },
      {
        nome: 'Despesas Admin',
        seu: despesasAdminAtual,
        idealMin: 0,
        idealMax: benchmarks.despesas_admin.max,
        inverter: true,
        unidade: '%',
        cor: despesasAdminAtual <= benchmarks.despesas_admin.max ? 'green' : despesasAdminAtual <= benchmarks.despesas_admin.max * 1.2 ? 'yellow' : 'red'
      },
      {
        nome: 'Despesas Totais',
        seu: despesasTotaisAtual,
        idealMin: 0,
        idealMax: benchmarks.despesas_totais.max,
        inverter: true,
        unidade: '%',
        cor: despesasTotaisAtual <= benchmarks.despesas_totais.max ? 'green' : despesasTotaisAtual <= benchmarks.despesas_totais.max * 1.2 ? 'yellow' : 'red'
      }
    ];

    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <BarChart3 className="text-indigo-600" />
            Seus Indicadores vs Mercado Pet Shop
          </h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Info size={16} />
            <span>Fonte: {indicesMercado.fonte}</span>
          </div>
        </div>

        <div className="space-y-4">
          {indicadores.map((ind, idx) => {
            const faixaIdeal = ind.idealMax - ind.idealMin;
            const centro = ind.idealMin + (faixaIdeal / 2);
            const dentroFaixa = ind.seu >= ind.idealMin && ind.seu <= ind.idealMax;

            return (
              <div key={idx} className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-700">{ind.nome}</span>
                  <div className="flex items-center gap-4">
                    <span className={`text-lg font-bold ${
                      ind.cor === 'green' ? 'text-green-600' : 
                      ind.cor === 'yellow' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {ind.seu.toFixed(1)}{ind.unidade}
                    </span>
                    <span className="text-sm text-gray-500">
                      Ideal: {ind.idealMin > 0 ? `${ind.idealMin.toFixed(0)}-` : ''}{ind.idealMax.toFixed(0)}{ind.unidade}
                    </span>
                  </div>
                </div>

                {/* Barra Visual */}
                <div className="relative h-8 bg-gray-200 rounded-full overflow-hidden">
                  {/* Faixa Ideal (Verde) */}
                  <div 
                    className="absolute h-full bg-green-200"
                    style={{
                      left: `${(ind.idealMin / 100) * 100}%`,
                      width: `${(faixaIdeal / 100) * 100}%`
                    }}
                  />
                  
                  {/* Marcador do Valor Atual */}
                  <div 
                    className="absolute h-full w-2 bg-gray-800 shadow-lg z-10"
                    style={{
                      left: `${Math.min(Math.max((ind.seu / 100) * 100, 0), 100)}%`,
                      transform: 'translateX(-50%)'
                    }}
                  >
                    <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      Você
                    </div>
                  </div>
                </div>

                {/* Status */}
                <div className="mt-2 flex items-center gap-2 text-sm">
                  {dentroFaixa ? (
                    <>
                      <CheckCircle size={16} className="text-green-600" />
                      <span className="text-green-600 font-medium">Dentro da faixa ideal!</span>
                    </>
                  ) : ind.seu < ind.idealMin ? (
                    <>
                      <TrendDown size={16} className="text-orange-600" />
                      <span className="text-orange-600">Abaixo do ideal ({(ind.idealMin - ind.seu).toFixed(1)}{ind.unidade} a menos)</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={16} className="text-red-600" />
                      <span className="text-red-600">Acima do ideal (+{(ind.seu - ind.idealMax).toFixed(1)}{ind.unidade})</span>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Legenda */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            💡 Faixa verde = Ideal para pet shops | Barra preta = Seu valor atual
          </p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Gerando análise inteligente...</p>
        </div>
      </div>
    );
  }

  if (!analise) {
    return (
      <div className="bg-gray-50 rounded-lg p-12 text-center">
        <Brain className="mx-auto mb-4 text-gray-400" size={64} />
        <p className="text-gray-600">Não há dados suficientes para análise</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Score de Saúde */}
      {renderScoreSaude(analise.score)}

      {/* Comparativo com Mercado - NOVO! */}
      {renderComparativoMercado()}

      {/* Comparação com Período Anterior */}
      {comparacao && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Calendar className="text-blue-600" />
            Comparação com Período Anterior
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(comparacao).map(([chave, valor]) => (
              <div key={chave} className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1 capitalize">{chave}</p>
                <p className="text-xl font-bold text-gray-800 mb-2">
                  R$ {valor.atual.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                {valor.variacao !== null && (
                  <div className={`flex items-center gap-1 text-sm ${valor.variacao > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {valor.variacao > 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                    <span className="font-semibold">{Math.abs(valor.variacao).toFixed(1)}%</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alertas */}
      {analise.alertas.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <AlertTriangle className="text-orange-600" />
            Pontos de Atenção
          </h3>
          <div className="space-y-3">
            {analise.alertas.map((alerta, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border-l-4 ${
                  alerta.tipo === 'critico'
                    ? 'bg-red-50 border-red-500'
                    : 'bg-yellow-50 border-yellow-500'
                }`}
              >
                <div className="flex items-start gap-3">
                  <alerta.icon
                    size={20}
                    className={alerta.tipo === 'critico' ? 'text-red-600' : 'text-yellow-600'}
                  />
                  <div>
                    <p className="font-semibold text-gray-800">{alerta.titulo}</p>
                    <p className="text-sm text-gray-600 mt-1">{alerta.descricao}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Insights */}
      {analise.insights.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <BarChart3 className="text-indigo-600" />
            Insights Inteligentes
          </h3>
          <div className="space-y-3">
            {analise.insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg ${
                  insight.tipo === 'positivo'
                    ? 'bg-green-50'
                    : insight.tipo === 'atencao'
                    ? 'bg-yellow-50'
                    : 'bg-blue-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <insight.icon
                    size={20}
                    className={
                      insight.tipo === 'positivo'
                        ? 'text-green-600'
                        : insight.tipo === 'atencao'
                        ? 'text-yellow-600'
                        : 'text-blue-600'
                    }
                  />
                  <div>
                    <p className="font-semibold text-gray-800">{insight.titulo}</p>
                    <p className="text-sm text-gray-600 mt-1">{insight.descricao}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recomendações */}
      {analise.recomendacoes.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Lightbulb className="text-yellow-600" />
            Recomendações Estratégicas
          </h3>
          <div className="space-y-3">
            {analise.recomendacoes.map((rec, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-semibold ${
                          rec.prioridade === 'alta'
                            ? 'bg-red-100 text-red-700'
                            : rec.prioridade === 'media'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {rec.prioridade.toUpperCase()}
                      </span>
                      <p className="font-semibold text-gray-800">{rec.titulo}</p>
                    </div>
                    <p className="text-sm text-gray-600">{rec.descricao}</p>
                  </div>
                  <DollarSign className="text-purple-600 flex-shrink-0 ml-3" size={24} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnaliseInteligente;
