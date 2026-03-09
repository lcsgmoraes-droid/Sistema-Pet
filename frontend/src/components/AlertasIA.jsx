import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, AlertCircle, TrendingUp, TrendingDown, 
  Clock, DollarSign, Calendar, CheckCircle, X, Sparkles 
} from 'lucide-react';
import api from '../api';

const AlertasIA = ({ compacto = false }) => {
  const [alertas, setAlertas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [filtroSeveridade, setFiltroSeveridade] = useState('todos'); // todos, crítico, atenção, info

  useEffect(() => {
    carregarAlertas();
  }, []);

  const carregarAlertas = async () => {
    setCarregando(true);
    try {
      // Por enquanto, gerar alertas no frontend
      // TODO: Criar endpoint /api/ia/fluxo/alertas no backend
      const alertasGerados = await gerarAlertas();
      setAlertas(alertasGerados);
    } catch (erro) {
      console.error('Erro ao carregar alertas:', erro);
    } finally {
      setCarregando(false);
    }
  };

  const gerarAlertas = async () => {
    const alertasArray = [];
    const hoje = new Date();

    try {
      // 1. Verificar saldo atual
      const saldoAtual = await buscarSaldoAtual();
      if (saldoAtual < 1000) {
        alertasArray.push({
          id: 'saldo-critico',
          tipo: 'saldo',
          severidade: 'crítico',
          titulo: 'Saldo Crítico',
          mensagem: `Seu saldo está abaixo de R$ 1.000,00. Saldo atual: ${formatarMoeda(saldoAtual)}`,
          recomendacao: 'Considere adiar pagamentos não essenciais ou antecipar recebimentos.',
          icone: AlertTriangle,
          data: hoje.toISOString()
        });
      } else if (saldoAtual < 5000) {
        alertasArray.push({
          id: 'saldo-atencao',
          tipo: 'saldo',
          severidade: 'atenção',
          titulo: 'Saldo Baixo',
          mensagem: `Seu saldo está em nível de atenção: ${formatarMoeda(saldoAtual)}`,
          recomendacao: 'Monitore suas despesas e prepare-se para possíveis necessidades de caixa.',
          icone: AlertCircle,
          data: hoje.toISOString()
        });
      }

      // 2. Verificar vencimentos próximos (próximos 7 dias)
      const vencimentosProximos = await buscarVencimentosProximos(7);
      if (vencimentosProximos.length > 0) {
        const totalVencimentos = vencimentosProximos.reduce((sum, v) => sum + v.valor, 0);
        alertasArray.push({
          id: 'vencimentos-proximos',
          tipo: 'vencimento',
          severidade: 'atenção',
          titulo: `${vencimentosProximos.length} Pagamentos Vencendo`,
          mensagem: `Você tem ${vencimentosProximos.length} pagamentos vencendo nos próximos 7 dias, totalizando ${formatarMoeda(totalVencimentos)}`,
          recomendacao: 'Verifique se há saldo suficiente para cobrir estes pagamentos.',
          icone: Calendar,
          data: hoje.toISOString(),
          detalhes: vencimentosProximos
        });
      }

      // 3. Verificar vencimentos atrasados
      const vencimentosAtrasados = await buscarVencimentosAtrasados();
      if (vencimentosAtrasados.length > 0) {
        const totalAtrasados = vencimentosAtrasados.reduce((sum, v) => sum + v.valor, 0);
        alertasArray.push({
          id: 'vencimentos-atrasados',
          tipo: 'atraso',
          severidade: 'crítico',
          titulo: `${vencimentosAtrasados.length} Pagamentos Atrasados`,
          mensagem: `Você tem ${vencimentosAtrasados.length} pagamentos em atraso, totalizando ${formatarMoeda(totalAtrasados)}`,
          recomendacao: 'Priorize a quitação destes débitos para evitar juros e multas.',
          icone: AlertTriangle,
          data: hoje.toISOString(),
          detalhes: vencimentosAtrasados
        });
      }

      // 4. Análise de gastos anormais (comparar últimos 30 dias com média histórica)
      const gastosRecentes = await analisarGastosRecentes();
      if (gastosRecentes.variacao > 30) {
        alertasArray.push({
          id: 'gastos-anormais',
          tipo: 'anomalia',
          severidade: 'atenção',
          titulo: 'Gastos Acima do Normal',
          mensagem: `Suas despesas aumentaram ${gastosRecentes.variacao.toFixed(0)}% em relação à média histórica`,
          recomendacao: 'Revise seus gastos recentes e identifique possíveis despesas extraordinárias.',
          icone: TrendingUp,
          data: hoje.toISOString(),
          detalhes: gastosRecentes
        });
      }

      // 5. Verificar padrão de recorrências
      const recorrenciasPendentes = await verificarRecorrencias();
      if (recorrenciasPendentes.length > 0) {
        alertasArray.push({
          id: 'recorrencias-pendentes',
          tipo: 'recorrencia',
          severidade: 'info',
          titulo: 'Despesas Recorrentes Próximas',
          mensagem: `${recorrenciasPendentes.length} despesas recorrentes vencerão em breve`,
          recomendacao: 'Certifique-se de que há saldo para cobrir estas despesas automáticas.',
          icone: Clock,
          data: hoje.toISOString(),
          detalhes: recorrenciasPendentes
        });
      }

      // 6. Projeção de saldo negativo
      const projecaoNegativa = await verificarProjecaoNegativa(15);
      if (projecaoNegativa.diasAteNegativo > 0) {
        alertasArray.push({
          id: 'projecao-negativa',
          tipo: 'projecao',
          severidade: 'crítico',
          titulo: 'Risco de Saldo Negativo',
          mensagem: `Com o padrão atual, seu saldo pode ficar negativo em ${projecaoNegativa.diasAteNegativo} dias`,
          recomendacao: 'Tome medidas urgentes para aumentar receitas ou reduzir despesas.',
          icone: TrendingDown,
          data: hoje.toISOString(),
          detalhes: projecaoNegativa
        });
      }

      return alertasArray.sort((a, b) => {
        const ordem = { crítico: 0, atenção: 1, info: 2 };
        return ordem[a.severidade] - ordem[b.severidade];
      });
    } catch (erro) {
      console.error('Erro ao gerar alertas:', erro);
      return [];
    }
  };

  const buscarSaldoAtual = async () => {
    try {
      const response = await api.get('/financeiro/saldo-atual');
      return response.data.saldo || 10000;
    } catch (erro) {
      return 10000; // valor padrão
    }
  };

  const buscarVencimentosProximos = async (dias) => {
    try {
      const hoje = new Date();
      const dataLimite = new Date();
      dataLimite.setDate(dataLimite.getDate() + dias);

      const response = await api.get('/financeiro/contas-pagar', {
        params: {
          data_inicio: hoje.toISOString().split('T')[0],
          data_fim: dataLimite.toISOString().split('T')[0],
          status: 'pendente'
        }
      });

      return response.data || [];
    } catch (erro) {
      return [];
    }
  };

  const buscarVencimentosAtrasados = async () => {
    try {
      const response = await api.get('/financeiro/contas-pagar', {
        params: {
          atrasadas: true
        }
      });
      return response.data || [];
    } catch (erro) {
      return [];
    }
  };

  const analisarGastosRecentes = async () => {
    try {
      // Buscar gastos dos últimos 30 dias
      const hoje = new Date();
      const inicio = new Date();
      inicio.setDate(inicio.getDate() - 30);

      const response = await api.get('/financeiro/analise-gastos', {
        params: {
          data_inicio: inicio.toISOString().split('T')[0],
          data_fim: hoje.toISOString().split('T')[0]
        }
      });

      return response.data || { variacao: 0 };
    } catch (erro) {
      return { variacao: 0 };
    }
  };

  const verificarRecorrencias = async () => {
    try {
      const response = await api.get('/financeiro/recorrencias-proximas');
      return response.data || [];
    } catch (erro) {
      return [];
    }
  };

  const verificarProjecaoNegativa = async (dias) => {
    try {
      const response = await api.get('/ia/fluxo/projecao-saldo', {
        params: { dias }
      });
      return response.data || { diasAteNegativo: 0 };
    } catch (erro) {
      return { diasAteNegativo: 0 };
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const marcarComoResolvido = (alertaId) => {
    setAlertas(alertas.filter(a => a.id !== alertaId));
  };

  const getCorSeveridade = (severidade) => {
    switch (severidade) {
      case 'crítico':
        return {
          bg: 'bg-red-50',
          border: 'border-red-300',
          text: 'text-red-800',
          badge: 'bg-red-100 text-red-800'
        };
      case 'atenção':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-300',
          text: 'text-yellow-800',
          badge: 'bg-yellow-100 text-yellow-800'
        };
      case 'info':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-300',
          text: 'text-blue-800',
          badge: 'bg-blue-100 text-blue-800'
        };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-300',
          text: 'text-gray-800',
          badge: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const alertasFiltrados = alertas.filter(alerta => {
    if (filtroSeveridade === 'todos') return true;
    return alerta.severidade === filtroSeveridade;
  });

  if (carregando) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-purple-600 animate-spin" />
          <span className="text-sm text-gray-600">Analisando alertas...</span>
        </div>
      </div>
    );
  }

  // Modo compacto: usado no dashboard na coluna lateral
  if (compacto) {
    return (
      <div className="flex flex-col h-full">
        <div className="bg-gradient-to-r from-orange-500 to-red-500 px-4 py-3 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-semibold">Alertas IA</span>
          </div>
          <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
            {alertas.length} alerta{alertas.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {alertasFiltrados.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
              <p className="text-sm font-medium text-green-700">Tudo em ordem!</p>
              <p className="text-xs text-gray-500 mt-1">Nenhum alerta no momento.</p>
            </div>
          ) : (
            alertasFiltrados.map((alerta) => {
              const cores = getCorSeveridade(alerta.severidade);
              const Icone = alerta.icone;
              return (
                <div
                  key={alerta.id}
                  className={`${cores.bg} border ${cores.border} rounded-lg p-2.5`}
                >
                  <div className="flex items-start gap-2">
                    <Icone className={`w-4 h-4 mt-0.5 flex-shrink-0 ${cores.text}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 mb-0.5">
                        <p className={`text-xs font-semibold ${cores.text} truncate`}>
                          {alerta.titulo}
                        </p>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full flex-shrink-0 ${cores.badge}`}>
                          {alerta.severidade}
                        </span>
                      </div>
                      <p className={`text-xs ${cores.text} opacity-90 line-clamp-2`}>
                        {alerta.mensagem}
                      </p>
                    </div>
                    <button
                      onClick={() => marcarComoResolvido(alerta.id)}
                      className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  }

  // Modo completo (página dedicada)
  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="bg-gradient-to-r from-orange-600 to-red-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold flex items-center gap-2">
              <AlertTriangle className="w-6 h-6" />
              Alertas Inteligentes
            </h3>
            <p className="text-orange-100 mt-1">
              Avisos automáticos sobre situações que requerem atenção
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setFiltroSeveridade('todos')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filtroSeveridade === 'todos'
                  ? 'bg-white text-orange-600'
                  : 'bg-orange-500 text-white hover:bg-orange-400'
              }`}
            >
              Todos ({alertas.length})
            </button>
            <button
              onClick={() => setFiltroSeveridade('crítico')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filtroSeveridade === 'crítico'
                  ? 'bg-white text-orange-600'
                  : 'bg-orange-500 text-white hover:bg-orange-400'
              }`}
            >
              Críticos ({alertas.filter(a => a.severidade === 'crítico').length})
            </button>
          </div>
        </div>
      </div>

      {/* Lista de Alertas */}
      {alertasFiltrados.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <h4 className="text-lg font-semibold text-green-800 mb-2">
            Tudo em ordem!
          </h4>
          <p className="text-green-700">
            Não há alertas no momento. Seu fluxo de caixa está saudável.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {alertasFiltrados.map((alerta) => {
            const cores = getCorSeveridade(alerta.severidade);
            const Icone = alerta.icone;

            return (
              <div
                key={alerta.id}
                className={`${cores.bg} border ${cores.border} rounded-lg p-5 transition-all hover:shadow-md`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`${cores.text} mt-1`}>
                      <Icone className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className={`font-semibold ${cores.text}`}>
                          {alerta.titulo}
                        </h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${cores.badge}`}>
                          {alerta.severidade}
                        </span>
                      </div>
                      <p className={`text-sm mb-3 ${cores.text}`}>
                        {alerta.mensagem}
                      </p>
                      <div className="bg-white bg-opacity-50 rounded-lg p-3 mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">
                          💡 Recomendação:
                        </p>
                        <p className="text-sm text-gray-600">
                          {alerta.recomendacao}
                        </p>
                      </div>
                      {alerta.detalhes && (
                        <details className="text-sm">
                          <summary className="cursor-pointer font-medium text-gray-700 hover:text-gray-900">
                            Ver detalhes
                          </summary>
                          <div className="mt-2 pl-4 border-l-2 border-gray-300">
                            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                              {JSON.stringify(alerta.detalhes, null, 2)}
                            </pre>
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => marcarComoResolvido(alerta.id)}
                    className="ml-4 text-gray-400 hover:text-gray-600 transition-colors"
                    title="Marcar como resolvido"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AlertasIA;
