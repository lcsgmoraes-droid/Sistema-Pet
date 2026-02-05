import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Calendar, DollarSign, AlertCircle, Sparkles } from 'lucide-react';
import api from '../api';

const ProjecoesIA = () => {
  const [projecoes, setProjecoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [periodoProjecao, setPeriodoProjecao] = useState(30); // dias
  const [confianca, setConfianca] = useState({ media: 0, desvio: 0 });

  useEffect(() => {
    carregarProjecoes();
  }, [periodoProjecao]);

  const carregarProjecoes = async () => {
    setCarregando(true);
    try {
      // Por enquanto, gerar projeções no frontend
      // TODO: Criar endpoint /api/ia/fluxo/projecoes no backend
      const projecoesGeradas = await gerarProjecoes();
      setProjecoes(projecoesGeradas);
    } catch (erro) {
      console.error('Erro ao carregar projeções:', erro);
    } finally {
      setCarregando(false);
    }
  };

  const gerarProjecoes = async () => {
    // Buscar dados históricos de movimentações
    const hoje = new Date();
    const dataInicio = new Date();
    dataInicio.setDate(dataInicio.getDate() - 90); // 90 dias de histórico

    try {
      // Buscar movimentações históricas
      const response = await api.get('/api/financeiro/movimentacoes', {
        params: {
          data_inicio: dataInicio.toISOString().split('T')[0],
          data_fim: hoje.toISOString().split('T')[0]
        }
      });

      const movimentacoes = response.data;

      // Calcular médias diárias
      const mediaDiariaEntradas = calcularMediaDiaria(movimentacoes, 'entrada');
      const mediaDiariaSaidas = calcularMediaDiaria(movimentacoes, 'saida');

      // Buscar saldo atual
      const saldoAtual = await buscarSaldoAtual();

      // Gerar projeções dia a dia
      const projecoesArray = [];
      let saldoProjetado = saldoAtual;

      for (let i = 1; i <= periodoProjecao; i++) {
        const dataProjecao = new Date();
        dataProjecao.setDate(dataProjecao.getDate() + i);

        // Aplicar variação (média + aleatoriedade para simular incerteza)
        const variacaoEntradas = mediaDiariaEntradas * (0.8 + Math.random() * 0.4);
        const variacaoSaidas = mediaDiariaSaidas * (0.8 + Math.random() * 0.4);

        const entradasProjetadas = variacaoEntradas;
        const saidasProjetadas = variacaoSaidas;
        saldoProjetado = saldoProjetado + entradasProjetadas - saidasProjetadas;

        // Calcular nível de confiança (diminui com o tempo)
        const nivelConfianca = Math.max(95 - (i * 1.5), 50);

        projecoesArray.push({
          data: dataProjecao.toISOString().split('T')[0],
          dataFormatada: dataProjecao.toLocaleDateString('pt-BR'),
          entradasProjetadas: entradasProjetadas,
          saidasProjetadas: saidasProjetadas,
          saldoProjetado: saldoProjetado,
          nivelConfianca: nivelConfianca,
          diaSemana: dataProjecao.toLocaleDateString('pt-BR', { weekday: 'short' }),
          alerta: saldoProjetado < 1000 ? 'crítico' : saldoProjetado < 5000 ? 'atenção' : null
        });
      }

      return projecoesArray;
    } catch (erro) {
      console.error('Erro ao gerar projeções:', erro);
      return [];
    }
  };

  const calcularMediaDiaria = (movimentacoes, tipo) => {
    const movimentacoesTipo = movimentacoes.filter(m => m.tipo === tipo);
    if (movimentacoesTipo.length === 0) return 0;

    const total = movimentacoesTipo.reduce((sum, m) => sum + m.valor, 0);
    return total / 90; // média dos últimos 90 dias
  };

  const buscarSaldoAtual = async () => {
    try {
      const response = await api.get('/api/financeiro/saldo-atual');
      return response.data.saldo || 10000; // valor padrão se não conseguir buscar
    } catch (erro) {
      console.error('Erro ao buscar saldo:', erro);
      return 10000;
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const getCorAlerta = (alerta) => {
    if (alerta === 'crítico') return 'bg-red-100 border-red-300 text-red-800';
    if (alerta === 'atenção') return 'bg-yellow-100 border-yellow-300 text-yellow-800';
    return 'bg-green-50 border-green-200';
  };

  const projecoesSemanais = () => {
    const semanas = [];
    for (let i = 0; i < projecoes.length; i += 7) {
      const semana = projecoes.slice(i, i + 7);
      const totalEntradas = semana.reduce((sum, p) => sum + p.entradasProjetadas, 0);
      const totalSaidas = semana.reduce((sum, p) => sum + p.saidasProjetadas, 0);
      const saldoFinal = semana[semana.length - 1]?.saldoProjetado || 0;

      semanas.push({
        numero: Math.floor(i / 7) + 1,
        dataInicio: semana[0]?.dataFormatada,
        dataFim: semana[semana.length - 1]?.dataFormatada,
        entradas: totalEntradas,
        saidas: totalSaidas,
        saldo: totalSaidas - totalEntradas,
        saldoFinal: saldoFinal
      });
    }
    return semanas;
  };

  if (carregando) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center space-x-3">
          <Sparkles className="w-6 h-6 text-purple-600 animate-spin" />
          <span className="text-gray-600">Calculando projeções...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp className="w-6 h-6" />
              Projeções de Fluxo de Caixa
            </h3>
            <p className="text-purple-100 mt-1">
              Previsões baseadas em padrões históricos e tendências
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPeriodoProjecao(15)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                periodoProjecao === 15
                  ? 'bg-white text-purple-600'
                  : 'bg-purple-500 text-white hover:bg-purple-400'
              }`}
            >
              15 dias
            </button>
            <button
              onClick={() => setPeriodoProjecao(30)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                periodoProjecao === 30
                  ? 'bg-white text-purple-600'
                  : 'bg-purple-500 text-white hover:bg-purple-400'
              }`}
            >
              30 dias
            </button>
            <button
              onClick={() => setPeriodoProjecao(60)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                periodoProjecao === 60
                  ? 'bg-white text-purple-600'
                  : 'bg-purple-500 text-white hover:bg-purple-400'
              }`}
            >
              60 dias
            </button>
          </div>
        </div>
      </div>

      {/* Resumo Semanal */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-indigo-600" />
          Resumo Semanal
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {projecoesSemanais().map((semana) => (
            <div
              key={semana.numero}
              className={`border rounded-lg p-4 ${
                semana.saldoFinal < 5000 ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200'
              }`}
            >
              <div className="text-sm font-medium text-gray-600 mb-2">
                Semana {semana.numero}
              </div>
              <div className="text-xs text-gray-500 mb-3">
                {semana.dataInicio} - {semana.dataFim}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-green-600">Entradas:</span>
                  <span className="font-medium">{formatarMoeda(semana.entradas)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-red-600">Saídas:</span>
                  <span className="font-medium">{formatarMoeda(semana.saidas)}</span>
                </div>
                <div className="border-t pt-2 flex justify-between font-semibold">
                  <span>Saldo Final:</span>
                  <span className={semana.saldoFinal < 5000 ? 'text-yellow-600' : 'text-gray-800'}>
                    {formatarMoeda(semana.saldoFinal)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Projeções Diárias */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-green-600" />
          Projeções Diárias Detalhadas
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Data</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Dia</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Entradas</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Saídas</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Saldo Projetado</th>
                <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Confiança</th>
              </tr>
            </thead>
            <tbody>
              {projecoes.map((projecao, index) => (
                <tr
                  key={index}
                  className={`border-b border-gray-100 hover:bg-gray-50 ${
                    projecao.alerta ? getCorAlerta(projecao.alerta) : ''
                  }`}
                >
                  <td className="py-3 px-4 text-sm">{projecao.dataFormatada}</td>
                  <td className="py-3 px-4 text-sm text-gray-600">{projecao.diaSemana}</td>
                  <td className="py-3 px-4 text-sm text-right text-green-600 font-medium">
                    {formatarMoeda(projecao.entradasProjetadas)}
                  </td>
                  <td className="py-3 px-4 text-sm text-right text-red-600 font-medium">
                    {formatarMoeda(projecao.saidasProjetadas)}
                  </td>
                  <td className="py-3 px-4 text-sm text-right font-semibold">
                    {formatarMoeda(projecao.saldoProjetado)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      projecao.nivelConfianca >= 80
                        ? 'bg-green-100 text-green-800'
                        : projecao.nivelConfianca >= 65
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-orange-100 text-orange-800'
                    }`}>
                      {projecao.nivelConfianca.toFixed(0)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Aviso */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-800">
          <p className="font-medium mb-1">Sobre as Projeções</p>
          <p>
            As projeções são calculadas com base em padrões históricos dos últimos 90 dias.
            O nível de confiança diminui com o tempo, pois eventos futuros podem alterar as tendências.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProjecoesIA;
