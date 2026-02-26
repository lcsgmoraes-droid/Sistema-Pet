/**
 * DASHBOARD FINANCEIRO - Resumo Geral
 * VisÃ£o consolidada de contas a pagar e a receber
 * Atualizado: 2025-01-10
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import toast from 'react-hot-toast';
import { Building2, Wallet, CreditCard, Plus } from 'lucide-react';

export default function DashboardFinanceiro() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [resumoPagar, setResumoPagar] = useState(null);
  const [resumoReceber, setResumoReceber] = useState(null);
  const [contas, setContas] = useState([]);
  const [resumoContas, setResumoContas] = useState(null);

  useEffect(() => {
    carregarDashboard();
  }, []);

  const carregarDashboard = async () => {
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const config = { headers: { Authorization: `Bearer ${token}` } };

      const [resPagar, resReceber, resContas, resResumo] = await Promise.all([
        api.get(`/contas-pagar/dashboard/resumo`, config),
        api.get(`/contas-receber/dashboard/resumo`, config),
        api.get(`/contas-bancarias?apenas_ativas=true`, config),
        api.get(`/contas-bancarias/resumo/saldos`, config)
      ]);

      setResumoPagar(resPagar.data);
      setResumoReceber(resReceber.data);
      setContas(resContas.data);
      setResumoContas(resResumo.data);
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
      toast.error('Erro ao carregar resumo financeiro');
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const saldoLiquido = (resumoReceber?.total_pendente || 0) - (resumoPagar?.total_pendente || 0);

  const TIPOS_CONTA = {
    'banco': { label: 'Bancos', icon: Building2 },
    'caixa': { label: 'Caixas', icon: Wallet },
    'digital': { label: 'Digitais', icon: CreditCard }
  };

  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">ï¿½ Financeiro/ContÃ¡bil</h1>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + Nova Conta a Pagar
          </button>
          <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            + Nova Conta a Receber
          </button>
        </div>
      </div>
      {/* MENU DE NAVEGAÃ‡ÃƒO RÃPIDA */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="grid grid-cols-6 gap-3">
          <button
            onClick={() => navigate('/financeiro/vendas')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-blue-50 transition group"
          >
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center group-hover:bg-blue-200">
              <span className="text-xl">ðŸ›’</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Vendas</span>
          </button>

          <button
            onClick={() => navigate('/financeiro/contas-receber')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-green-50 transition group"
          >
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center group-hover:bg-green-200">
              <span className="text-xl">ðŸ“¥</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Contas a Receber</span>
          </button>

          <button
            onClick={() => navigate('/financeiro/contas-pagar')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-red-50 transition group"
          >
            <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center group-hover:bg-red-200">
              <span className="text-xl">ðŸ“¤</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Contas a Pagar</span>
          </button>

          <button
            onClick={() => navigate('/financeiro/contas')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-indigo-50 transition group"
          >
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center group-hover:bg-indigo-200">
              <span className="text-xl">ðŸ¦</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Contas BancÃ¡rias</span>
          </button>

          <button
            onClick={() => navigate('/financeiro/formas-pagamento')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-purple-50 transition group"
          >
            <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center group-hover:bg-purple-200">
              <span className="text-xl">ðŸ’³</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Formas Pagamento</span>
          </button>

          <button
            onClick={() => navigate('/financeiro/fluxo-caixa')}
            className="flex flex-col items-center gap-2 p-3 rounded-lg hover:bg-yellow-50 transition group"
          >
            <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center group-hover:bg-yellow-200">
              <span className="text-xl">ðŸ“Š</span>
            </div>
            <span className="text-xs font-medium text-gray-700">Fluxo de Caixa</span>
          </button>
        </div>
      </div>
      {/* CONTAS BANCÃRIAS */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">ðŸ¦ Contas BancÃ¡rias</h2>
          <button
            onClick={() => navigate('/financeiro/contas')}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
          >
            Ver todas
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Card Saldo Total */}
          <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-4 text-white">
            <p className="text-blue-100 text-sm mb-1">Saldo Total</p>
            <p className="text-3xl font-bold mb-1">{formatarMoeda(resumoContas?.total_geral || 0)}</p>
            <p className="text-xs text-blue-200">
              {contas.length} {contas.length === 1 ? 'conta' : 'contas'}
            </p>
          </div>

          {/* Cards por Tipo */}
          {Object.entries(TIPOS_CONTA).map(([tipo, config]) => {
            const Icon = config.icon;
            const valor = resumoContas?.por_tipo?.[tipo] || 0;
            return (
              <div key={tipo} className="bg-white rounded-xl p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <Icon className="w-5 h-5 text-gray-400" />
                  <p className="text-xs text-gray-500">{config.label}</p>
                </div>
                <p className="text-xl font-bold text-gray-800">{formatarMoeda(valor)}</p>
              </div>
            );
          })}
        </div>

        {/* Mini lista de contas */}
        {contas.length > 0 && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
            {contas.slice(0, 3).map(conta => (
              <div key={conta.id} className="bg-white rounded-lg p-3 flex items-center gap-3 border border-gray-100">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                  style={{ backgroundColor: `${conta.cor}20` }}
                >
                  {conta.icone}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{conta.nome}</p>
                  <p className="text-xs text-gray-600">{formatarMoeda(conta.saldo_atual)}</p>
                </div>
              </div>
            ))}
            {contas.length > 3 && (
              <button
                onClick={() => navigate('/financeiro/contas')}
                className="bg-gray-50 rounded-lg p-3 flex items-center justify-center gap-2 border border-gray-200 hover:bg-gray-100 transition"
              >
                <Plus className="w-4 h-4 text-gray-600" />
                <span className="text-sm text-gray-600">Ver mais {contas.length - 3}</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* SALDO LÃQUIDO */}
      <div className={`p-6 rounded-xl ${saldoLiquido >= 0 ? 'bg-green-50 border-2 border-green-300' : 'bg-red-50 border-2 border-red-300'}`}>
        <div className="text-center">
          <p className="text-sm font-medium text-gray-600 mb-2">Saldo LÃ­quido Previsto</p>
          <p className={`text-4xl font-bold ${saldoLiquido >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatarMoeda(saldoLiquido)}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            (Contas a Receber - Contas a Pagar)
          </p>
        </div>
      </div>

      {/* CARDS RESUMO */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* CONTAS A PAGAR */}
        <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-red-500">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-gray-800">ðŸ“¤ Contas a Pagar</h2>
              <p className="text-sm text-gray-500">Despesas e obrigaÃ§Ãµes</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-red-600">
                {formatarMoeda(resumoPagar?.total_pendente)}
              </p>
              <p className="text-xs text-gray-500">Total Pendente</p>
            </div>
          </div>

          <div className="space-y-3">
            {/* Vencidas */}
            <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
              <div>
                <p className="font-semibold text-red-700">âš ï¸ Vencidas</p>
                <p className="text-xs text-gray-600">{resumoPagar?.vencidas?.quantidade || 0} contas</p>
              </div>
              <p className="font-bold text-red-700">
                {formatarMoeda(resumoPagar?.vencidas?.total)}
              </p>
            </div>

            {/* Vence Hoje */}
            <div className="flex justify-between items-center p-3 bg-orange-50 rounded-lg">
              <p className="font-semibold text-orange-700">ðŸ”” Vence Hoje</p>
              <p className="font-bold text-orange-700">
                {formatarMoeda(resumoPagar?.vence_hoje)}
              </p>
            </div>

            {/* PrÃ³ximos 7 dias */}
            <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
              <p className="font-semibold text-yellow-700">ðŸ“… PrÃ³ximos 7 dias</p>
              <p className="font-bold text-yellow-700">
                {formatarMoeda(resumoPagar?.proximos_7_dias)}
              </p>
            </div>

            {/* PrÃ³ximos 30 dias */}
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <p className="font-semibold text-blue-700">ðŸ“Š PrÃ³ximos 30 dias</p>
              <p className="font-bold text-blue-700">
                {formatarMoeda(resumoPagar?.proximos_30_dias)}
              </p>
            </div>

            {/* Pago no MÃªs */}
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border-t-2">
              <p className="font-semibold text-gray-700">âœ… Pago no MÃªs</p>
              <p className="font-bold text-green-600">
                {formatarMoeda(resumoPagar?.pago_mes_atual)}
              </p>
            </div>
          </div>

          <button 
            onClick={() => navigate('/financeiro/contas-pagar')}
            className="w-full mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Ver Todas as Contas a Pagar â†’
          </button>
        </div>

        {/* CONTAS A RECEBER */}
        <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-green-500">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-gray-800">ðŸ“¥ Contas a Receber</h2>
              <p className="text-sm text-gray-500">Receitas e valores a receber</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-green-600">
                {formatarMoeda(resumoReceber?.total_pendente)}
              </p>
              <p className="text-xs text-gray-500">Total Pendente</p>
            </div>
          </div>

          <div className="space-y-3">
            {/* NÃ£o Recebidas */}
            <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
              <div>
                <p className="font-semibold text-red-700">âš ï¸ NÃ£o Recebidas (Vencidas)</p>
                <p className="text-xs text-gray-600">{resumoReceber?.vencidas?.quantidade || 0} contas</p>
              </div>
              <p className="font-bold text-red-700">
                {formatarMoeda(resumoReceber?.vencidas?.total)}
              </p>
            </div>

            {/* Receber Hoje */}
            <div className="flex justify-between items-center p-3 bg-orange-50 rounded-lg">
              <p className="font-semibold text-orange-700">ðŸ”” Receber Hoje</p>
              <p className="font-bold text-orange-700">
                {formatarMoeda(resumoReceber?.vence_hoje)}
              </p>
            </div>

            {/* A Receber - 7 dias */}
            <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
              <p className="font-semibold text-yellow-700">ðŸ“… A Receber (7 dias)</p>
              <p className="font-bold text-yellow-700">
                {formatarMoeda(resumoReceber?.proximos_7_dias)}
              </p>
            </div>

            {/* A Receber - 30 dias */}
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <p className="font-semibold text-blue-700">ðŸ“Š A Receber (30 dias)</p>
              <p className="font-bold text-blue-700">
                {formatarMoeda(resumoReceber?.proximos_30_dias)}
              </p>
            </div>

            {/* Recebido no MÃªs */}
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border-t-2">
              <p className="font-semibold text-gray-700">âœ… Recebido no MÃªs</p>
              <p className="font-bold text-green-600">
                {formatarMoeda(resumoReceber?.recebido_mes_atual)}
              </p>
            </div>
          </div>

          <button 
            onClick={() => navigate('/financeiro/contas-receber')}
            className="w-full mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Ver Todas as Contas a Receber â†’
          </button>
        </div>
      </div>
    </div>
  );
}

