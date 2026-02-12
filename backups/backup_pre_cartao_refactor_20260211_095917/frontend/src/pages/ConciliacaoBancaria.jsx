import React, { useState, useEffect } from 'react';
import { 
  Upload, Filter, CheckCircle, AlertCircle, Clock, TrendingUp,
  FileText, BarChart3, Settings, Download, RefreshCw, Eye, EyeOff
} from 'lucide-react';
import { api } from '../services/api';

export default function ConciliacaoBancaria() {
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [regras, setRegras] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  
  // Filtros
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [statusFiltro, setStatusFiltro] = useState('todos');
  const [ocultarConciliadas, setOcultarConciliadas] = useState(true);
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  
  // Modais
  const [movimentacaoEmClassificacao, setMovimentacaoEmClassificacao] = useState(null);
  const [mostrarModalRegras, setMostrarModalRegras] = useState(false);
  
  // Carregar dados iniciais
  useEffect(() => {
    carregarContasBancarias();
    carregarRegras();
  }, []);
  
  // Carregar movimentações quando mudar filtros
  useEffect(() => {
    if (contasBancarias.length > 0 && contaSelecionada) {
      carregarMovimentacoes();
      carregarEstatisticas();
    }
  }, [contaSelecionada, statusFiltro, ocultarConciliadas, dataInicio, dataFim]);
  
  const carregarContasBancarias = async () => {
    try {
      const res = await api.get('/api/contas-bancarias', {
        params: { apenas_ativas: true }
      });
      console.log('📊 Contas bancárias carregadas:', res.data);
      // Filtrar apenas instituições bancárias (para evitar poluir com caixa, carteiras, etc)
      const instituicoesBancarias = res.data.filter(conta => conta.instituicao_bancaria);
      setContasBancarias(instituicoesBancarias);
      // Não auto-seleciona - usuário deve escolher clicando no card
    } catch (error) {
      console.error('❌ Erro ao carregar contas bancárias:', error);
      console.error('Detalhes:', error.response?.data);
    }
  };
  
  const carregarMovimentacoes = async () => {
    try {
      setLoading(true);
      const params = {};
      
      if (contaSelecionada) params.conta_bancaria_id = contaSelecionada;
      if (statusFiltro !== 'todos') params.status = statusFiltro;
      params.ocultar_conciliadas = ocultarConciliadas;
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      params.limit = 200;
      
      const res = await api.get('/api/conciliacao/movimentacoes', { params });
      
      setMovimentacoes(res.data);
    } catch (error) {
      console.error('Erro ao carregar movimentações:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const carregarEstatisticas = async () => {
    try {
      const params = {};
      if (contaSelecionada) params.conta_bancaria_id = contaSelecionada;
      const res = await api.get('/api/conciliacao/estatisticas', { params });
      setEstatisticas(res.data);
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
    }
  };
  
  const carregarRegras = async () => {
    try {
      const res = await api.get('/api/conciliacao/regras');
      setRegras(res.data);
    } catch (error) {
      console.error('Erro ao carregar regras:', error);
    }
  };
  
  const handleUploadOFX = async (event) => {
    const file = event.target.files[0];
    console.log('📤 Upload OFX iniciado:', { file, contaSelecionada });
    
    if (!file) return;
    
    if (!contaSelecionada) {
      alert('Selecione uma conta bancária primeiro');
      return;
    }
    
    try {
      setUploadingFile(true);
      const formData = new FormData();
      formData.append('arquivo', file);
      
      console.log('📤 Enviando arquivo para API...');
      const res = await api.post(
        `/api/conciliacao/upload-ofx?conta_bancaria_id=${contaSelecionada}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      console.log('✅ Upload concluído:', res.data);
      alert(`✅ OFX importado com sucesso!\n\n` +
            `📊 Total de transações: ${res.data.total_transacoes}\n` +
            `⏳ Pendentes: ${res.data.pendentes}\n` +
            `📅 Período: ${res.data.periodo_inicio || 'N/A'} a ${res.data.periodo_fim || 'N/A'}`);
      
      // Recarrega dados
      carregarMovimentacoes();
      carregarEstatisticas();
      
    } catch (error) {
      console.error('❌ Erro ao fazer upload:', error);
      alert('❌ Erro ao processar OFX: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploadingFile(false);
      event.target.value = ''; // Reset input
    }
  };
  
  const classificarMovimentacao = async (movimentacao, dados) => {
    try {
      await api.post(
        `/api/conciliacao/movimentacoes/${movimentacao.id}/classificar`,
        dados
      );
      
      // Recarrega dados
      carregarMovimentacoes();
      carregarEstatisticas();
      carregarRegras();
      setMovimentacaoEmClassificacao(null);
      
    } catch (error) {
      console.error('Erro ao classificar:', error);
      alert('❌ Erro ao classificar movimentação');
    }
  };
  
  const getStatusBadge = (status, confianca) => {
    const badges = {
      'conciliado': <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800 flex items-center gap-1">
        <CheckCircle size={12} /> Conciliado
      </span>,
      'sugerido': <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 flex items-center gap-1">
        <AlertCircle size={12} /> Sugerido ({confianca}%)
      </span>,
      'pendente': <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800 flex items-center gap-1">
        <Clock size={12} /> Pendente
      </span>,
      'manual': <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 flex items-center gap-1">
        <Settings size={12} /> Manual
      </span>
    };
    return badges[status] || badges['pendente'];
  };
  
  const formatarValor = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };
  
  const formatarData = (dataStr) => {
    if (!dataStr) return '-';
    const data = new Date(dataStr);
    return data.toLocaleDateString('pt-BR');
  };
  
  const limparSelecaoConta = () => {
    setContaSelecionada(null);
  };
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Conciliação Bancária</h1>
            <p className="text-gray-600 mt-1">Sistema inteligente de classificação automática</p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={() => setMostrarModalRegras(true)}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <Settings size={18} />
              Regras ({regras.length})
            </button>
            
            <label className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
              uploadingFile || !contaSelecionada 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
            } text-white`}>
              {uploadingFile ? (
                <>
                  <RefreshCw size={18} className="animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload OFX
                </>
              )}
              <input
                type="file"
                accept=".ofx,.OFX"
                onChange={handleUploadOFX}
                className="hidden"
                disabled={uploadingFile || !contaSelecionada}
              />
            </label>
          </div>
        </div>
        
        {/* Seletor de Contas Bancárias */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <CheckCircle size={20} className="text-blue-600" />
                Selecione a Conta Bancária
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Escolha a conta para visualizar movimentações e fazer upload de extrato OFX
              </p>
            </div>
            {contaSelecionada && (
              <button
                onClick={limparSelecaoConta}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Limpar Seleção
              </button>
            )}
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {contasBancarias.map((conta) => {
              const selecionado = contaSelecionada === conta.id;
              const corConta = conta.cor || '#3B82F6'; // Azul padrão se não tiver cor
              
              // Estilos inline baseados na cor da conta
              const estiloCard = selecionado ? {
                backgroundColor: corConta,
                borderColor: corConta,
                color: '#ffffff'
              } : {
                backgroundColor: `${corConta}15`, // 15 = ~10% de opacidade
                borderColor: `${corConta}40`,
                color: corConta
              };
              
              return (
                <button
                  key={conta.id}
                  onClick={() => setContaSelecionada(conta.id)}
                  style={estiloCard}
                  className={`border-2 rounded-lg p-4 transition-all duration-200 transform font-medium ${
                    selecionado ? 'scale-105 shadow-lg' : 'hover:scale-102 hover:shadow-md'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {conta.icone && <span className="text-xl">{conta.icone}</span>}
                      <span className="font-semibold text-sm">{conta.nome}</span>
                    </div>
                    {selecionado && (
                      <CheckCircle size={20} className="flex-shrink-0" />
                    )}
                  </div>
                  {conta.banco && (
                    <div className={`text-xs mt-1 ${selecionado ? 'opacity-90' : 'opacity-70'}`}>
                      {conta.banco}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
          
          {contasBancarias.length === 0 && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-800">
                  <span className="font-semibold">Nenhuma instituição bancária cadastrada.</span>
                  {' '}Vá em Financeiro → Contas Bancárias e marque o checkbox "🏦 Instituição Bancária" nas contas que são bancos reais (não caixa físico).
                </div>
              </div>
            </div>
          )}
          
          {!contaSelecionada && contasBancarias.length > 0 && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle size={18} className="text-yellow-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <span className="font-semibold">Nenhuma conta selecionada.</span>
                  {' '}Clique em uma conta acima para visualizar movimentações e fazer upload de extrato OFX.
                </div>
              </div>
            </div>
          )}
          
          {contaSelecionada && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-2">
                <CheckCircle size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <span className="font-semibold">
                    {contasBancarias.find(c => c.id === contaSelecionada)?.nome} selecionada.
                  </span>
                  {' '}Visualizando movimentações desta conta. Pronto para upload de extrato OFX.
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Estatísticas */}
        {estatisticas && contaSelecionada && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total</p>
                  <p className="text-2xl font-bold text-gray-900">{estatisticas.total_movimentacoes}</p>
                </div>
                <FileText className="text-gray-400" size={24} />
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow-sm border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Conciliadas</p>
                  <p className="text-2xl font-bold text-green-600">{estatisticas.conciliadas}</p>
                </div>
                <CheckCircle className="text-green-400" size={24} />
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow-sm border border-yellow-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Sugeridas</p>
                  <p className="text-2xl font-bold text-yellow-600">{estatisticas.sugeridas}</p>
                </div>
                <AlertCircle className="text-yellow-400" size={24} />
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow-sm border border-red-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Pendentes</p>
                  <p className="text-2xl font-bold text-red-600">{estatisticas.pendentes}</p>
                </div>
                <Clock className="text-red-400" size={24} />
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow-sm border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Automação</p>
                  <p className="text-2xl font-bold text-blue-600">{estatisticas.taxa_automacao}%</p>
                </div>
                <TrendingUp className="text-blue-400" size={24} />
              </div>
            </div>
          </div>
        )}
        
        {/* Filtros - só mostra se tiver conta selecionada */}
        {contaSelecionada && (
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <Filter size={18} className="text-gray-400" />
                <span className="text-sm font-medium text-gray-700">Filtros:</span>
              </div>
              
              <select
                value={statusFiltro}
                onChange={(e) => setStatusFiltro(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="todos">Todos os status</option>
                <option value="pendente">Pendente</option>
                <option value="sugerido">Sugerido</option>
                <option value="conciliado">Conciliado</option>
                <option value="manual">Manual</option>
              </select>
              
              <input
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="Data início"
              />
              
              <input
                type="date"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="Data fim"
              />
              
              <button
                onClick={() => setOcultarConciliadas(!ocultarConciliadas)}
                className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${
                  ocultarConciliadas ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                }`}
              >
                {ocultarConciliadas ? <EyeOff size={16} /> : <Eye size={16} />}
                {ocultarConciliadas ? 'Ocultar' : 'Mostrar'} Conciliadas
              </button>
              
              <button
                onClick={carregarMovimentacoes}
                className="ml-auto px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-2"
              >
                <RefreshCw size={16} />
                Atualizar
              </button>
            </div>
          </div>
        )}
        
        {/* Lista de Movimentações - só mostra se tiver conta selecionada */}
        {contaSelecionada && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vinculado</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                      <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
                      Carregando...
                    </td>
                  </tr>
                ) : movimentacoes.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                      Nenhuma movimentação encontrada. Faça upload de um arquivo OFX.
                    </td>
                  </tr>
                ) : (
                  movimentacoes.map(mov => (
                    <tr key={mov.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {formatarData(mov.data_movimento)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                        {mov.memo || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 text-xs rounded ${
                          mov.tipo === 'CREDIT' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {mov.tipo === 'CREDIT' ? 'Crédito' : 'Débito'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium">
                        <span className={mov.tipo === 'CREDIT' ? 'text-green-600' : 'text-red-600'}>
                          {mov.tipo === 'CREDIT' ? '+' : '-'} {formatarValor(Math.abs(mov.valor))}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {getStatusBadge(mov.status_conciliacao, mov.confianca_sugestao)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                        {mov.fornecedor_nome || mov.tipo_vinculo || '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {mov.status_conciliacao !== 'conciliado' && (
                          <button
                            onClick={() => setMovimentacaoEmClassificacao(mov)}
                            className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                          >
                            Classificar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        )}
        
        {/* Modal de Classificação */}
        {movimentacaoEmClassificacao && (
          <ModalClassificacao
            movimentacao={movimentacaoEmClassificacao}
            onClose={() => setMovimentacaoEmClassificacao(null)}
            onClassificar={classificarMovimentacao}
          />
        )}
        
        {/* Modal de Regras */}
        {mostrarModalRegras && (
          <ModalRegras
            regras={regras}
            onClose={() => setMostrarModalRegras(false)}
            onAtualizar={carregarRegras}
          />
        )}
        
      </div>
    </div>
  );
}

// Componente Modal de Classificação
function ModalClassificacao({ movimentacao, onClose, onClassificar }) {
  const [tipoVinculo, setTipoVinculo] = useState(movimentacao.tipo_vinculo || 'fornecedor');
  const [criarRegra, setCriarRegra] = useState(true);
  const [recorrente, setRecorrente] = useState(false);
  const [periodicidade, setPeriodicidade] = useState('mensal');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onClassificar(movimentacao, {
      tipo_vinculo: tipoVinculo,
      criar_regra: criarRegra,
      recorrente,
      periodicidade: recorrente ? periodicidade : null
    });
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Classificar Movimentação</h2>
        </div>
        
        <div className="p-6 space-y-4">
          {/* Dados da movimentação */}
          <div className="p-4 bg-gray-50 rounded-lg space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Data:</span>
              <span className="text-sm font-medium">{new Date(movimentacao.data_movimento).toLocaleDateString('pt-BR')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Valor:</span>
              <span className="text-sm font-medium">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(movimentacao.valor)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Descrição:</span>
              <span className="text-sm font-medium truncate ml-4">{movimentacao.memo}</span>
            </div>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Vínculo
              </label>
              <select
                value={tipoVinculo}
                onChange={(e) => setTipoVinculo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="fornecedor">Pagamento a Fornecedor</option>
                <option value="taxa">Taxa Bancária</option>
                <option value="transferencia">Transferência Entre Contas</option>
                <option value="recebimento">Recebimento de Cliente</option>
              </select>
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="criar_regra"
                checked={criarRegra}
                onChange={(e) => setCriarRegra(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="criar_regra" className="text-sm text-gray-700">
                Criar regra automática para movimentações similares
              </label>
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="recorrente"
                checked={recorrente}
                onChange={(e) => setRecorrente(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="recorrente" className="text-sm text-gray-700">
                Movimentação recorrente (criar provisões futuras)
              </label>
            </div>
            
            {recorrente && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Periodicidade
                </label>
                <select
                  value={periodicidade}
                  onChange={(e) => setPeriodicidade(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="mensal">Mensal</option>
                  <option value="anual">Anual</option>
                  <option value="trimestral">Trimestral</option>
                  <option value="semestral">Semestral</option>
                </select>
              </div>
            )}
            
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Classificar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Componente Modal de Regras
function ModalRegras({ regras, onClose, onAtualizar }) {
  const [regrasLocais, setRegrasLocais] = useState(regras);
  
  const excluirRegra = async (regraId) => {
    if (!confirm('Deseja realmente desativar esta regra?')) return;
    
    try {
      await api.delete(`/api/conciliacao/regras/${regraId}`);
      
      onAtualizar();
      const novasRegras = regrasLocais.filter(r => r.id !== regraId);
      setRegrasLocais(novasRegras);
    } catch (error) {
      console.error('Erro ao excluir regra:', error);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Regras de Aprendizado</h2>
            <p className="text-sm text-gray-600 mt-1">Sistema aprende com suas classificações</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        
        <div className="p-6">
          {regrasLocais.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Settings size={48} className="mx-auto mb-4 text-gray-300" />
              <p>Nenhuma regra criada ainda.</p>
              <p className="text-sm mt-2">Classifique movimentações para criar regras automáticas.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {regrasLocais.map(regra => (
                <div key={regra.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                          {regra.padrao_memo}
                        </span>
                        {regra.tipo_operacao && (
                          <span className="text-xs text-gray-600">
                            {regra.tipo_operacao}
                          </span>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Confiança:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  regra.confianca >= 80 ? 'bg-green-500' :
                                  regra.confianca >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${regra.confianca}%` }}
                              />
                            </div>
                            <span className="font-medium">{regra.confianca}%</span>
                          </div>
                        </div>
                        
                        <div>
                          <span className="text-gray-600">Aplicada:</span>
                          <p className="font-medium mt-1">{regra.vezes_aplicada}x</p>
                        </div>
                        
                        <div>
                          <span className="text-gray-600">Confirmada:</span>
                          <p className="font-medium mt-1">{regra.vezes_confirmada}x</p>
                        </div>
                      </div>
                      
                      {regra.fornecedor_nome && (
                        <p className="text-sm text-gray-600 mt-2">
                          → {regra.fornecedor_nome}
                        </p>
                      )}
                    </div>
                    
                    <button
                      onClick={() => excluirRegra(regra.id)}
                      className="ml-4 px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded"
                    >
                      Desativar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
