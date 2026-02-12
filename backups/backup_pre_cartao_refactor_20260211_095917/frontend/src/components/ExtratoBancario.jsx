import React, { useState } from 'react';
import { Upload, CheckCircle, XCircle, AlertCircle, FileText, TrendingUp, Brain } from 'lucide-react';
import api from '../api';

const ExtratoBancario = () => {
  const [arquivo, setArquivo] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [pendentes, setPendentes] = useState([]);
  const [loadingPendentes, setLoadingPendentes] = useState(false);
  const [padroes, setPadroes] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [viewMode, setViewMode] = useState('upload'); // upload, validacao, padroes, estatisticas

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setArquivo(file);
    }
  };

  const handleUpload = async () => {
    if (!arquivo) {
      alert('Selecione um arquivo primeiro');
      return;
    }

    const formData = new FormData();
    formData.append('arquivo', arquivo);

    setUploading(true);
    try {
      const response = await api.post('/api/ia/extrato/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setResultado(response.data);
      alert(`Upload concluído! ${response.data.categorias_aplicadas} categorias aplicadas automaticamente.`);
    } catch (error) {
      console.error('Erro no upload:', error);
      const mensagem = error.response?.data?.detail || error.message;
      alert('Erro ao processar arquivo: ' + mensagem);
    } finally {
      setUploading(false);
    }
  };

  const carregarPendentes = async () => {
    setLoadingPendentes(true);
    try {
      const response = await api.get('/api/ia/extrato/pendentes');
      setPendentes(response.data);
    } catch (error) {
      console.error('Erro ao carregar pendentes:', error);
      alert('Erro ao carregar lançamentos pendentes');
    } finally {
      setLoadingPendentes(false);
    }
  };

  const aprovarLancamento = async (id) => {
    try {
      await api.post('/api/ia/extrato/validar', {
        lancamento_id: id,
        aprovado: true
      });
      alert('Lançamento aprovado!');
      carregarPendentes();
    } catch (error) {
      console.error('Erro ao aprovar:', error);
      alert('Erro ao aprovar lançamento');
    }
  };

  const corrigirLancamento = async (id, categoria_correta) => {
    try {
      await api.post('/api/ia/extrato/validar', {
        lancamento_id: id,
        aprovado: false,
        categoria_correta_id: categoria_correta
      });
      alert('Lançamento corrigido e padrão aprendido!');
      carregarPendentes();
    } catch (error) {
      console.error('Erro ao corrigir:', error);
      alert('Erro ao corrigir lançamento');
    }
  };

  const carregarPadroes = async () => {
    try {
      const response = await api.get('/api/ia/extrato/padroes');
      setPadroes(response.data);
    } catch (error) {
      console.error('Erro ao carregar padrões:', error);
      alert('Erro ao carregar padrões aprendidos');
    }
  };

  const carregarEstatisticas = async () => {
    try {
      const response = await api.get('/api/ia/extrato/estatisticas');
      setEstatisticas(response.data);
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
      alert('Erro ao carregar estatísticas');
    }
  };

  // Carregar dados ao mudar de view
  React.useEffect(() => {
    if (viewMode === 'validacao') {
      carregarPendentes();
    } else if (viewMode === 'padroes') {
      carregarPadroes();
    } else if (viewMode === 'estatisticas') {
      carregarEstatisticas();
    }
  }, [viewMode]);

  return (
    <div className="space-y-6">
      {/* Navegação entre sub-views */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setViewMode('upload')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              viewMode === 'upload'
                ? 'bg-green-100 text-green-700 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Upload size={18} />
            Upload de Extrato
          </button>
          
          <button
            onClick={() => setViewMode('validacao')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              viewMode === 'validacao'
                ? 'bg-orange-100 text-orange-700 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <AlertCircle size={18} />
            Validação ({pendentes.length})
          </button>
          
          <button
            onClick={() => setViewMode('padroes')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              viewMode === 'padroes'
                ? 'bg-blue-100 text-blue-700 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Brain size={18} />
            Padrões IA
          </button>
          
          <button
            onClick={() => setViewMode('estatisticas')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              viewMode === 'estatisticas'
                ? 'bg-purple-100 text-purple-700 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <TrendingUp size={18} />
            Estatísticas
          </button>
        </div>
      </div>

      {/* View: Upload */}
      {viewMode === 'upload' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Upload className="text-green-600" />
            Upload de Extrato Bancário
          </h2>
          
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <FileText className="mx-auto mb-4 text-gray-400" size={48} />
              <p className="mb-2 text-gray-600">Arraste um arquivo ou clique para selecionar</p>
              <p className="text-sm text-gray-500 mb-4">
                ✅ Formatos: Excel (.xlsx, .xls), CSV (.csv), PDF (.pdf), OFX (.ofx)
              </p>
              
              <input
                type="file"
                onChange={handleFileSelect}
                accept=".xlsx,.xls,.csv,.pdf,.ofx"
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer"
              >
                Selecionar Arquivo
              </label>
              
              {arquivo && (
                <div className="mt-4 p-3 bg-green-50 rounded-lg">
                  <p className="text-green-700 font-medium">{arquivo.name}</p>
                  <p className="text-sm text-green-600">{(arquivo.size / 1024).toFixed(2)} KB</p>
                </div>
              )}
            </div>
            
            <button
              onClick={handleUpload}
              disabled={!arquivo || uploading}
              className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium"
            >
              {uploading ? 'Processando...' : 'Processar Extrato'}
            </button>
            
            {resultado && (
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="font-bold text-blue-900 mb-2">✅ Resultado do Processamento</h3>
                <div className="space-y-1 text-sm">
                  <p>• Total de lançamentos: <span className="font-bold">{resultado.total_lancamentos}</span></p>
                  <p>• Categorizados automaticamente: <span className="font-bold text-green-700">{resultado.categorias_aplicadas}</span></p>
                  <p>• Pendentes de validação: <span className="font-bold text-orange-700">{resultado.pendentes_validacao}</span></p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* View: Validação */}
      {viewMode === 'validacao' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <AlertCircle className="text-orange-600" />
            Lançamentos Pendentes de Validação ({pendentes.length})
          </h2>
          
          {loadingPendentes ? (
            <p className="text-center text-gray-600 py-8">Carregando...</p>
          ) : pendentes.length === 0 ? (
            <div className="text-center text-gray-600 py-8">
              <CheckCircle className="mx-auto mb-2 text-green-500" size={48} />
              <p>Nenhum lançamento pendente! 🎉</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendentes.map((lancamento) => (
                <div key={lancamento.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{lancamento.descricao}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Data: {new Date(lancamento.data).toLocaleDateString('pt-BR')} | 
                        Valor: R$ {Math.abs(lancamento.valor).toFixed(2)}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          Sugestão IA: {lancamento.categoria_sugerida}
                        </span>
                        <span className="text-xs text-gray-500">
                          Confiança: {(lancamento.confianca * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => aprovarLancamento(lancamento.id)}
                        className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                        title="Aprovar categoria sugerida"
                      >
                        <CheckCircle size={16} />
                      </button>
                      <button
                        onClick={() => {
                          const nova_categoria = prompt('Digite a categoria correta:');
                          if (nova_categoria) {
                            corrigirLancamento(lancamento.id, nova_categoria);
                          }
                        }}
                        className="px-3 py-2 bg-orange-600 text-white rounded hover:bg-orange-700 text-sm"
                        title="Corrigir categoria"
                      >
                        <XCircle size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* View: Padrões IA */}
      {viewMode === 'padroes' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Brain className="text-blue-600" />
            Padrões Aprendidos pela IA
          </h2>
          
          {padroes.length === 0 ? (
            <p className="text-center text-gray-600 py-8">Nenhum padrão aprendido ainda</p>
          ) : (
            <div className="space-y-3">
              {padroes.map((padrao, idx) => (
                <div key={idx} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-gray-800">Padrão: {padrao.descricao_padrao}</p>
                      <p className="text-sm text-gray-600 mt-1">Categoria: {padrao.categoria}</p>
                      <div className="mt-2 flex gap-2">
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                          ✓ {padrao.vezes_usado} vezes usado
                        </span>
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          Confiança: {(padrao.confianca * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* View: Estatísticas */}
      {viewMode === 'estatisticas' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <TrendingUp className="text-purple-600" />
              Estatísticas do Sistema IA
            </h2>
            
            {!estatisticas ? (
              <p className="text-center text-gray-600 py-8">Carregando estatísticas...</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-600 font-medium">Total de Padrões</p>
                  <p className="text-3xl font-bold text-blue-900 mt-1">{estatisticas.total_padroes}</p>
                </div>
                
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <p className="text-sm text-green-600 font-medium">Taxa de Acerto</p>
                  <p className="text-3xl font-bold text-green-900 mt-1">
                    {(estatisticas.taxa_acerto * 100).toFixed(1)}%
                  </p>
                </div>
                
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <p className="text-sm text-purple-600 font-medium">Confiança Média</p>
                  <p className="text-3xl font-bold text-purple-900 mt-1">
                    {(estatisticas.confianca_media * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExtratoBancario;
