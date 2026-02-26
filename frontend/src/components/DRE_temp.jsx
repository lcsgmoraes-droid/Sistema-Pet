import React, { useState, useEffect } from 'react';
import api from '../api';
import toast from 'react-hot-toast';
import { 
  TrendingUp, TrendingDown, DollarSign, Calendar, 
  RefreshCw, Download, FileText, Percent, Upload, 
  CheckCircle, MessageCircle, Brain, Sparkles
} from 'lucide-react';

const DRE = () => {
  // Controle de tabs
  const [tabAtiva, setTabAtiva] = useState('demonstrativo'); // demonstrativo, extrato, analise
  
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);
  
  // Filtros
  const obterDataLocal = () => {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    return `${ano}-${mes}`;
  };
  
  const [periodo, setPeriodo] = useState(obterDataLocal());

  useEffect(() => {
    carregarDRE();
  }, []);

  const carregarDRE = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const [ano, mes] = periodo.split('-');
      
      const response = await api.get(`/financeiro/dre`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { ano, mes }
      });
      
      setDados(response.data);
    } catch (error) {
      console.error('Erro ao carregar DRE:', error);
      alert('Erro ao carregar DRE: ' + (error.response?.data?.detail || error.message));
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

  const formatarPercentual = (valor) => {
    return `${(valor || 0).toFixed(2)}%`;
  };

  const calcularPercentual = (valor, total) => {
    if (!total || total === 0) return 0;
    return (valor / total * 100);
  };

  const handlePeriodoPreset = (preset) => {
    const hoje = new Date();
    let novaData;

    switch (preset) {
      case 'mes_atual':
        novaData = obterDataLocal();
        break;
      case 'mes_anterior':
        const mesPassado = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
        novaData = `${mesPassado.getFullYear()}-${String(mesPassado.getMonth() + 1).padStart(2, '0')}`;
        break;
      case 'ano_atual':
        novaData = `${hoje.getFullYear()}-01`;
        break;
      default:
        return;
    }

    setPeriodo(novaData);
    setTimeout(() => carregarDRE(), 100);
  };

  const exportarPDF = async () => {
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const [ano, mes] = periodo.split('-');
      toast.loading('Gerando PDF...', { id: 'pdf' });
      
      const response = await api.get(
        `/financeiro/dre/export/pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { ano, mes },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `dre_${mes}_${ano}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('ðŸ“„ PDF exportado com sucesso!', { id: 'pdf' });
    } catch (error) {
      console.error('Erro ao exportar PDF:', error);
      toast.error('Erro ao exportar PDF', { id: 'pdf' });
    }
  };

  const exportarExcel = async () => {
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const [ano, mes] = periodo.split('-');
      toast.loading('Gerando Excel...', { id: 'excel' });
      
      const response = await api.get(
        `/financeiro/dre/export/excel`,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { ano, mes },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `dre_${mes}_${ano}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('ðŸ“Š Excel exportado com sucesso!', { id: 'excel' });
    } catch (error) {
      console.error('Erro ao exportar Excel:', error);
      toast.error('Erro ao exportar Excel', { id: 'excel' });
    }
  };

  if (loading && !dados) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4" size={48} />
          <p className="text-gray-600">Carregando DRE...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">ðŸ“Š DRE - DemonstraÃ§Ã£o do Resultado</h1>
          <p className="text-gray-600 mt-1">AnÃ¡lise gerencial de receitas, custos e lucro</p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={exportarPDF}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            title="Exportar para PDF"
          >
            <FileText size={18} />
            PDF
          </button>
          <button
            onClick={exportarExcel}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            title="Exportar para Excel"
          >
            <Download size={18} />
            Excel
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* BotÃµes de perÃ­odo rÃ¡pido */}
          <div className="flex gap-2">
            <button
              onClick={() => handlePeriodoPreset('mes_atual')}
              className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100"
            >
              MÃªs Atual
            </button>
            <button
              onClick={() => handlePeriodoPreset('mes_anterior')}
              className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100"
            >
              MÃªs Anterior
            </button>
            <button
              onClick={() => handlePeriodoPreset('ano_atual')}
              className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100"
            >
              Ano Atual
            </button>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              PerÃ­odo (MÃªs/Ano)
            </label>
            <input
              type="month"
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={carregarDRE}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
            >
              <RefreshCw size={18} />
              Atualizar
            </button>
          </div>
        </div>
      </div>

      {/* ConteÃºdo do DRE */}
      {dados && (
        <div className="space-y-6">
          {/* Cards de Resumo */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-green-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Receita Bruta</span>
                <TrendingUp className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.receita_bruta || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Base de cÃ¡lculo</div>
            </div>

            <div className="bg-red-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Custos e Despesas</span>
                <TrendingDown className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.custos_despesas_total || 0)}</div>
              <div className="text-xs mt-1 opacity-80">{formatarPercentual(calcularPercentual(dados.custos_despesas_total, dados.receita_bruta))} da receita</div>
            </div>

            <div className="bg-blue-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Lucro LÃ­quido</span>
                <DollarSign className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.lucro_liquido || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Resultado final</div>
            </div>

            <div className="bg-purple-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Margem LÃ­quida</span>
                <Percent className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarPercentual(dados.margem_liquida || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Rentabilidade</div>
            </div>
          </div>

          {/* Tabela DRE Detalhada */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    DescriÃ§Ã£o
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Valor
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    % Receita
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* RECEITA BRUTA */}
                <tr className="bg-green-50">
                  <td className="px-6 py-4 font-bold text-green-800">
                    (+) RECEITA BRUTA
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-green-800">
                    {formatarMoeda(dados.receita_bruta || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-green-800">
                    100,00%
                  </td>
                </tr>
                
                <tr>
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Vendas de Produtos
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.vendas_produtos || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.vendas_produtos, dados.receita_bruta))}
                  </td>
                </tr>
                
                <tr className="bg-gray-50">
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Vendas de ServiÃ§os
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.vendas_servicos || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.vendas_servicos, dados.receita_bruta))}
                  </td>
                </tr>

                {/* DEDUÃ‡Ã•ES */}
                <tr className="bg-orange-50">
                  <td className="px-6 py-4 font-bold text-orange-800">
                    (-) DEDUÃ‡Ã•ES DA RECEITA
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-orange-800">
                    {formatarMoeda(dados.deducoes_total || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-orange-800">
                    {formatarPercentual(calcularPercentual(dados.deducoes_total, dados.receita_bruta))}
                  </td>
                </tr>

                <tr>
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Descontos Concedidos
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.descontos || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.descontos, dados.receita_bruta))}
                  </td>
                </tr>

                <tr className="bg-gray-50">
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    DevoluÃ§Ãµes
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.devolucoes || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.devolucoes, dados.receita_bruta))}
                  </td>
                </tr>

                {/* RECEITA LÃQUIDA */}
                <tr className="bg-blue-50 border-t-2 border-blue-200">
                  <td className="px-6 py-4 font-bold text-blue-800">
                    (=) RECEITA LÃQUIDA
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-blue-800">
                    {formatarMoeda(dados.receita_liquida || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-blue-800">
                    {formatarPercentual(calcularPercentual(dados.receita_liquida, dados.receita_bruta))}
                  </td>
                </tr>

                {/* CUSTOS */}
                <tr className="bg-red-50">
                  <td className="px-6 py-4 font-bold text-red-800">
                    (-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-red-800">
                    {formatarMoeda(dados.cmv || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-red-800">
                    {formatarPercentual(calcularPercentual(dados.cmv, dados.receita_bruta))}
                  </td>
                </tr>

                {/* LUCRO BRUTO */}
                <tr className="bg-green-100 border-t-2 border-green-200">
                  <td className="px-6 py-4 font-bold text-green-900">
                    (=) LUCRO BRUTO
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-green-900">
                    {formatarMoeda(dados.lucro_bruto || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-green-900">
                    {formatarPercentual(calcularPercentual(dados.lucro_bruto, dados.receita_bruta))}
                  </td>
                </tr>

                {/* DESPESAS OPERACIONAIS */}
                <tr className="bg-yellow-50">
                  <td className="px-6 py-4 font-bold text-yellow-900">
                    (-) DESPESAS OPERACIONAIS
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-yellow-900">
                    {formatarMoeda(dados.despesas_operacionais || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-yellow-900">
                    {formatarPercentual(calcularPercentual(dados.despesas_operacionais, dados.receita_bruta))}
                  </td>
                </tr>

                <tr>
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Despesas com Pessoal
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.despesas_pessoal || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.despesas_pessoal, dados.receita_bruta))}
                  </td>
                </tr>

                <tr className="bg-gray-50">
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Despesas Administrativas
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.despesas_administrativas || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.despesas_administrativas, dados.receita_bruta))}
                  </td>
                </tr>

                <tr>
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Taxas de CartÃ£o
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.taxas_cartao || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.taxas_cartao, dados.receita_bruta))}
                  </td>
                </tr>

                <tr className="bg-gray-50">
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Outras Despesas
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.outras_despesas || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.outras_despesas, dados.receita_bruta))}
                  </td>
                </tr>

                {/* RESULTADO OPERACIONAL */}
                <tr className="bg-purple-100 border-t-2 border-purple-200">
                  <td className="px-6 py-4 font-bold text-purple-900">
                    (=) RESULTADO OPERACIONAL
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-purple-900">
                    {formatarMoeda(dados.resultado_operacional || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-purple-900">
                    {formatarPercentual(calcularPercentual(dados.resultado_operacional, dados.receita_bruta))}
                  </td>
                </tr>

                {/* RESULTADO FINANCEIRO */}
                <tr className="bg-indigo-50">
                  <td className="px-6 py-4 font-bold text-indigo-800">
                    (+/-) RESULTADO FINANCEIRO
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-indigo-800">
                    {formatarMoeda(dados.resultado_financeiro || 0)}
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-indigo-800">
                    {formatarPercentual(calcularPercentual(dados.resultado_financeiro, dados.receita_bruta))}
                  </td>
                </tr>

                <tr>
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Receitas Financeiras
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.receitas_financeiras || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.receitas_financeiras, dados.receita_bruta))}
                  </td>
                </tr>

                <tr className="bg-gray-50">
                  <td className="px-6 py-3 pl-12 text-gray-700">
                    Despesas Financeiras
                  </td>
                  <td className="px-6 py-3 text-right text-gray-700">
                    {formatarMoeda(dados.despesas_financeiras || 0)}
                  </td>
                  <td className="px-6 py-3 text-right text-gray-600">
                    {formatarPercentual(calcularPercentual(dados.despesas_financeiras, dados.receita_bruta))}
                  </td>
                </tr>

                {/* LUCRO LÃQUIDO */}
                <tr className="bg-gradient-to-r from-green-100 to-green-200 border-t-4 border-green-400">
                  <td className="px-6 py-5 font-bold text-green-900 text-lg">
                    (=) LUCRO/PREJUÃZO LÃQUIDO
                  </td>
                  <td className="px-6 py-5 text-right font-bold text-green-900 text-lg">
                    {formatarMoeda(dados.lucro_liquido || 0)}
                  </td>
                  <td className="px-6 py-5 text-right font-bold text-green-900 text-lg">
                    {formatarPercentual(dados.margem_liquida || 0)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!dados && !loading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <FileText className="mx-auto mb-4 text-gray-400" size={64} />
          <p className="text-gray-600 text-lg">Selecione um perÃ­odo e clique em Atualizar para visualizar o DRE</p>
        </div>
      )}
        </>
      )}
      
      {/* ConteÃºdo da Tab Extrato BancÃ¡rio */}
      {tabAtiva === 'extrato' && (
        <div className="space-y-6">
          <ExtratoBancarioTab />
        </div>
      )}
      
      {/* ConteÃºdo da Tab AnÃ¡lise Inteligente */}
      {tabAtiva === 'analise' && (
        <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg p-12 text-center border-2 border-dashed border-purple-300">
          <Brain className="mx-auto mb-4 text-purple-600" size={64} />
          <h3 className="text-2xl font-bold text-purple-900 mb-2">AnÃ¡lise Inteligente em Desenvolvimento</h3>
          <p className="text-purple-700 text-lg mb-4">
            Insights automÃ¡ticos, comparaÃ§Ãµes temporais e recomendaÃ§Ãµes estratÃ©gicas
          </p>
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-800 rounded-full">
            <Sparkles size={16} className="animate-pulse" />
            <span className="font-medium">Em breve disponÃ­vel</span>
          </div>
        </div>
      )}
    </div>
  );
};

// ===================================================================
// COMPONENTE: Tab de Extrato BancÃ¡rio com IA
// ===================================================================

const ExtratoBancarioTab = () => {
  const [arquivo, setArquivo] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [pendentes, setPendentes] = useState([]);
  const [loadingPendentes, setLoadingPendentes] = useState(false);
  const [padroes, setPadroes] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [viewMode, setViewMode] = useState('upload'); // upload, validacao, padroes, estatisticas

  useEffect(() => {
    if (viewMode === 'validacao') {
      carregarPendentes();
    } else if (viewMode === 'padroes') {
      carregarPadroes();
    } else if (viewMode === 'estatisticas') {
      carregarEstatisticas();
    }
  }, [viewMode]);

  const handleFileSelect = (e) => {

