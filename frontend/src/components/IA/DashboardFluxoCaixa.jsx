/**
 * ABA 5: Dashboard Fluxo de Caixa Preditivo
 * 
 * Dashboard principal com:
 * - Cards de Ã­ndices de saÃºde
 * - GrÃ¡fico de projeÃ§Ãµes 15 dias
 * - Alertas automÃ¡ticos
 * - Simulador de cenÃ¡rios
 */

import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-hot-toast';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  DollarSign,
  Calendar,
  Activity,
  RefreshCw
} from 'lucide-react';

import IndicesSaudeCards from './IndicesSaudeCards';
import GraficoProjecoes from './GraficoProjecoes';
import AlertasCaixa from './AlertasCaixa';
import SimuladorCenarios from './SimuladorCenarios';
import InfoMetricas from './InfoMetricas';

export default function DashboardFluxoCaixa({ userId }) {
  const [loading, setLoading] = useState(true);
  const [indices, setIndices] = useState(null);
  const [projecoes, setProjecoes] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState('visao-geral'); // visao-geral, projecoes, alertas, simulador

  // Carregar dados ao montar
  useEffect(() => {
    carregarDados();
  }, [userId]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // Carregar Ã­ndices, projeÃ§Ãµes e alertas em paralelo
      const [indicesRes, projecoesRes, alertasRes] = await Promise.all([
        api.get(`/ia/fluxo/indices-saude/${userId}`, { headers }),
        api.get(`/ia/fluxo/projecoes/${userId}?dias=15`, { headers }),
        api.get(`/ia/fluxo/alertas/${userId}`, { headers })
      ]);

      setIndices(indicesRes.data);
      setProjecoes(projecoesRes.data || []);
      setAlertas(alertasRes.data || []);
    } catch (error) {
      console.error('Erro ao carregar dados IA:', error);
      toast.error('Erro ao carregar dados da IA');
    } finally {
      setLoading(false);
    }
  };

  const gerarNovaProjecao = async () => {
    const toastId = toast.loading('Gerando projeÃ§Ã£o com Prophet...');
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      await api.post(`/ia/fluxo/projetar-15-dias/${userId}`, {}, { headers });
      
      toast.success('ProjeÃ§Ã£o gerada com sucesso!', { id: toastId });
      carregarDados();
    } catch (error) {
      console.error('Erro ao gerar projeÃ§Ã£o:', error);
      toast.error('Erro ao gerar projeÃ§Ã£o', { id: toastId });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Painel Informativo */}
      <InfoMetricas />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            ðŸ¤– Fluxo de Caixa Preditivo
          </h1>
          <p className="text-gray-600 mt-1">
            InteligÃªncia artificial analisando seu caixa
          </p>
        </div>

        <button
          onClick={gerarNovaProjecao}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar ProjeÃ§Ã£o
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setAbaAtiva('visao-geral')}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === 'visao-geral'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          VisÃ£o Geral
        </button>
        <button
          onClick={() => setAbaAtiva('projecoes')}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === 'projecoes'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          ProjeÃ§Ãµes 15 Dias
        </button>
        <button
          onClick={() => setAbaAtiva('alertas')}
          className={`px-4 py-2 font-medium transition-colors relative ${
            abaAtiva === 'alertas'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Alertas
          {alertas.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {alertas.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setAbaAtiva('simulador')}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === 'simulador'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Simulador
        </button>
      </div>

      {/* ConteÃºdo */}
      <div className="space-y-6">
        {abaAtiva === 'visao-geral' && (
          <>
            <div className="bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-green-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>ðŸ“Š VisÃ£o Geral:</strong> AnÃ¡lise dos Ãºltimos <strong>30 dias</strong> para calcular a saÃºde do caixa. 
                Mostra quanto tempo vocÃª consegue manter o negÃ³cio com saldo atual.
              </p>
            </div>
            <IndicesSaudeCards indices={indices} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <GraficoProjecoes projecoes={projecoes.slice(0, 7)} titulo="PrÃ³ximos 7 Dias" />
              <AlertasCaixa alertas={alertas.slice(0, 3)} />
            </div>
          </>
        )}

        {abaAtiva === 'projecoes' && (
          <>
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>ðŸ“ˆ ProjeÃ§Ã£o 15 Dias:</strong> PrevisÃ£o usando inteligÃªncia artificial (Prophet). 
                Baseada em <strong>30+ dias de histÃ³rico</strong> para prever entradas e saÃ­das dos prÃ³ximos <strong>15 dias</strong>. 
                Quanto mais histÃ³rico, mais precisa a previsÃ£o.
              </p>
            </div>
            <GraficoProjecoes projecoes={projecoes} titulo="ProjeÃ§Ã£o 15 Dias com Prophet" detalhado />
          </>
        )}

        {abaAtiva === 'alertas' && (
          <>
            <div className="bg-gradient-to-r from-orange-50 to-red-50 border-l-4 border-orange-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>âš ï¸ Alertas:</strong> Avisos automÃ¡ticos gerados em tempo real. 
                <strong> CrÃ­tico</strong> = menos de 7 dias de caixa (risco iminente). 
                <strong> Alerta</strong> = 7-15 dias (atenÃ§Ã£o necessÃ¡ria).
                <strong> OK</strong> = mais de 15 dias (situaÃ§Ã£o confortÃ¡vel).
              </p>
            </div>
            <AlertasCaixa alertas={alertas} />
          </>
        )}

        {abaAtiva === 'simulador' && (
          <>
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-l-4 border-purple-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>ðŸŽ¯ Simulador:</strong> Teste 3 cenÃ¡rios para os <strong>prÃ³ximos 15 dias</strong>. 
                <strong> Otimista:</strong> +20% receita, -10% despesa. 
                <strong> Realista:</strong> sem mudanÃ§as. 
                <strong> Pessimista:</strong> -20% receita, +10% despesa. 
                <strong>Seus dados reais nÃ£o sÃ£o alterados!</strong>
              </p>
            </div>
            <SimuladorCenarios userId={userId} projecoesBase={projecoes} />
          </>
        )}
      </div>
    </div>
  );
}

