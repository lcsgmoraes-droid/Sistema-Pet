import React, { useState, useEffect } from 'react';
import api from '../api';
import toast from 'react-hot-toast';
import { 
  TrendingUp, TrendingDown, DollarSign, Calendar, 
  RefreshCw, Download, FileText, Percent, Upload, 
  CheckCircle, MessageCircle, Brain, Sparkles
} from 'lucide-react';
import ExtratoBancario from './ExtratoBancario';
import ChatIAModal from './ChatIAModal';
import AnaliseInteligente from './AnaliseInteligente';

const DRE = () => {
  // Controle de tabs
  const [tabAtiva, setTabAtiva] = useState('demonstrativo'); // demonstrativo, extrato, analise
  
  // Modal Chat IA
  const [chatIAAberto, setChatIAAberto] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);
  
  // Canais de venda (ABA 7)
  const [canaisDisponiveis] = useState([
    { id: 'loja_fisica', nome: 'Loja Física', cor: 'blue' },
    { id: 'mercado_livre', nome: 'Mercado Livre', cor: 'yellow' },
    { id: 'shopee', nome: 'Shopee', cor: 'orange' },
    { id: 'amazon', nome: 'Amazon', cor: 'green' }
  ]);
  const [canaisSelecionados, setCanaisSelecionados] = useState(['loja_fisica']); // Loja Física por padrão
  
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
      const [ano, mes] = periodo.split('-');
      
      // Enviar os canais selecionados para o backend
      const canaisParam = canaisSelecionados.join(',');
      
      const response = await api.get(`/financeiro/dre/canais`, {
        params: { ano, mes, canais: canaisParam }
      });
      
      setDados(response.data);
    } catch (error) {
      console.error('Erro ao carregar DRE:', error);
      toast.error('Erro ao carregar DRE: ' + (error.response?.data?.detail || error.message));
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
  
  // Funções para gerenciar canais
  const toggleCanal = (canalId) => {
    setCanaisSelecionados(prev => {
      const novosCanais = prev.includes(canalId)
        ? prev.filter(id => id !== canalId)
        : [...prev, canalId];
      
      return novosCanais;
    });
  };

  const limparSelecaoCanais = () => {
    setCanaisSelecionados([]);
  };
  
  // Recarregar DRE quando os canais selecionados mudarem
  useEffect(() => {
    if (dados) {
      carregarDRE();
    }
  }, [canaisSelecionados]);

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
      const [ano, mes] = periodo.split('-');
      toast.loading('Gerando PDF...', { id: 'pdf' });
      
      const response = await api.get(
        `/financeiro/dre/export/pdf`,
        {
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
      const [ano, mes] = periodo.split('-');
      toast.loading('Gerando Excel...', { id: 'excel' });
      
      const response = await api.get(
        `/financeiro/dre/export/excel`,
        {
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
          <h1 className="text-3xl font-bold text-gray-800">📊 DRE - Demonstração do Resultado</h1>
          <p className="text-gray-600 mt-1">Análise gerencial de receitas, custos e lucro</p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setChatIAAberto(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
            title="Consultar Especialista IA"
          >
            <MessageCircle size={20} />
            <span className="font-medium">Chat IA</span>
            <Sparkles size={16} className="animate-pulse" />
          </button>
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

      {/* Tabs de Navegação */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setTabAtiva('demonstrativo')}
            className={`${
              tabAtiva === 'demonstrativo'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors`}
          >
            <FileText size={18} />
            Demonstrativo
          </button>
          
          <button
            onClick={() => setTabAtiva('extrato')}
            className={`${
              tabAtiva === 'extrato'
                ? 'border-green-500 text-green-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors`}
          >
            <Upload size={18} />
            Extrato Bancário
            <span className="ml-1 px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full font-bold">
              IA
            </span>
          </button>
          
          <button
            onClick={() => setTabAtiva('analise')}
            className={`${
              tabAtiva === 'analise'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors`}
          >
            <Brain size={18} />
            Análise Inteligente
            <span className="ml-1 px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full font-bold">
              EM BREVE
            </span>
          </button>
        </nav>
      </div>

      {/* Conteúdo da Tab Demonstrativo */}
      {tabAtiva === 'demonstrativo' && (
        <>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Botões de período rápido */}
          <div className="flex gap-2">
            <button
              onClick={() => handlePeriodoPreset('mes_atual')}
              className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100"
            >
              Mês Atual
            </button>
            <button
              onClick={() => handlePeriodoPreset('mes_anterior')}
              className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100"
            >
              Mês Anterior
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
              Período (Mês/Ano)
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

      {/* Conteúdo do DRE */}
      {dados && (
        <div className="space-y-6">
          {/* Cards de Resumo */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-green-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Receita Bruta</span>
                <TrendingUp className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.totais?.receita_bruta || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Base de cálculo</div>
            </div>

            <div className="bg-red-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">CMV</span>
                <TrendingDown className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.totais?.cmv || 0)}</div>
              <div className="text-xs mt-1 opacity-80">{formatarPercentual(calcularPercentual(dados.totais?.cmv, dados.totais?.receita_bruta))} da receita</div>
            </div>

            <div className="bg-blue-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Lucro Bruto</span>
                <DollarSign className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarMoeda(dados.totais?.lucro_bruto || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Após custos</div>
            </div>

            <div className="bg-purple-500 text-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-90">Margem Bruta</span>
                <Percent className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{formatarPercentual(dados.totais?.margem_bruta || 0)}</div>
              <div className="text-xs mt-1 opacity-80">Rentabilidade</div>
            </div>
          </div>

          {/* Seletor de Canais - ABA 7 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <CheckCircle size={20} className="text-blue-600" />
                  Análise por Canal de Vendas
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Selecione os canais para adicionar suas métricas na tabela DRE
                </p>
              </div>
              {canaisSelecionados.length > 0 && (
                <button
                  onClick={limparSelecaoCanais}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  Limpar Seleção
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {canaisDisponiveis.map(canal => {
                const selecionado = canaisSelecionados.includes(canal.id);
                const corClasses = {
                  blue: selecionado ? 'bg-blue-600 text-white border-blue-600' : 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100',
                  yellow: selecionado ? 'bg-yellow-500 text-white border-yellow-500' : 'bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100',
                  orange: selecionado ? 'bg-orange-500 text-white border-orange-500' : 'bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100',
                  green: selecionado ? 'bg-green-600 text-white border-green-600' : 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100'
                };
                
                return (
                  <button
                    key={canal.id}
                    onClick={() => toggleCanal(canal.id)}
                    className={`${corClasses[canal.cor]} border-2 rounded-lg p-4 transition-all duration-200 transform ${
                      selecionado ? 'scale-105 shadow-lg' : 'hover:scale-102'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{canal.nome}</span>
                      {selecionado && (
                        <CheckCircle size={20} className="flex-shrink-0" />
                      )}
                    </div>
                    {selecionado && (
                      <div className="text-xs mt-1 opacity-90">
                        Ativo na tabela
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            
            {canaisSelecionados.length > 0 && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <Brain size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    <span className="font-semibold">{canaisSelecionados.length} canal(is) selecionado(s).</span>
                    {' '}As métricas de cada canal serão adicionadas na tabela DRE abaixo com suas respectivas receitas, custos e lucros.
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Tabela DRE Detalhada */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Descrição
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
                {/* Renderizar linhas vindas da API */}
                {dados?.linhas?.map((linha, idx) => {
                  // Classes de estilo baseadas no nÃ­vel e tipo
                  const ehTotal = linha.nivel === 0;
                  const ehSubitem = linha.nivel === 1;
                  
                  // Background baseado na cor do canal
                  const bgStyle = linha.cor_bg !== '#ffffff' ? { backgroundColor: linha.cor_bg } : {};
                  
                  // Cor do texto
                  const textStyle = { color: linha.cor };
                  
                  return (
                    <tr 
                      key={idx} 
                      style={bgStyle}
                      className={ehTotal ? 'font-bold' : ''}
                    >
                      <td 
                        className={`px-6 py-3 ${ehSubitem ? 'pl-12' : ''} ${ehTotal ? 'font-bold' : ''}`}
                        style={textStyle}
                      >
                        {linha.descricao}
                      </td>
                      <td 
                        className={`px-6 py-3 text-right ${ehTotal ? 'font-bold' : ''}`}
                        style={textStyle}
                      >
                        {formatarMoeda(linha.valor)}
                      </td>
                      <td 
                        className={`px-6 py-3 text-right ${ehTotal ? 'font-bold' : ''}`}
                        style={textStyle}
                      >
                        {formatarPercentual(linha.percentual)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Seletor de Canais (removido - nÃ£o necessÃ¡rio com novo endpoint) */}
          {canaisSelecionados.length === 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                ðŸ’¡ A DRE agora mostra automaticamente todos os canais com vendas no perÃ­odo selecionado.
              </p>
            </div>
          )}
        </div>
      )}

      {!dados && !loading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <FileText className="mx-auto mb-4 text-gray-400" size={64} />
          <p className="text-gray-600 text-lg">Selecione um período e clique em Atualizar para visualizar o DRE</p>
        </div>
      )}
        </>
      )}

      {/* Conteúdo da Tab Extrato Bancário */}
      {tabAtiva === 'extrato' && (
        <ExtratoBancario />
      )}

      {/* Conteúdo da Tab Análise Inteligente */}
      {tabAtiva === 'analise' && (
        <AnaliseInteligente dados={dados} periodo={{ mes: periodo.mes, ano: periodo.ano }} />
      )}
      
      {/* Modal Chat IA */}
      <ChatIAModal 
        isOpen={chatIAAberto}
        onClose={() => setChatIAAberto(false)}
        contexto={{
          tipo: 'DRE',
          periodo: `${periodo.mes}/${periodo.ano}`,
          valor: dados?.lucro_liquido,
          dados: dados
        }}
      />
    </div>
  );
};

export default DRE;
