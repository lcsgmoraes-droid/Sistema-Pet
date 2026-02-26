/**
 * Modal de ImportaÃ§Ã£o de Produtos via Planilha Excel
 */
import { useState } from 'react';
import api from '../api';
import toast from 'react-hot-toast';

export default function ModalImportacaoProdutos({ isOpen, onClose, onSuccess }) {
  const [arquivo, setArquivo] = useState(null);
  const [importando, setImportando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [etapa, setEtapa] = useState('upload'); // 'upload', 'processando', 'resultado'

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
        setArquivo(file);
        setResultado(null);
      } else {
        toast.error('Arquivo deve ser Excel (.xlsx ou .xls)');
        e.target.value = '';
      }
    }
  };

  const baixarTemplate = async () => {
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const response = await api.get('/produtos/template-importacao', {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });

      // Criar URL para download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `template_produtos_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('Template baixado com sucesso!');
    } catch (error) {
      console.error('Erro ao baixar template:', error);
      toast.error('Erro ao baixar template');
    }
  };

  const handleImportar = async () => {
    if (!arquivo) {
      toast.error('Selecione um arquivo para importar');
      return;
    }

    setImportando(true);
    setEtapa('processando');

    try {
            const formData = new FormData();
      formData.append('file', arquivo);

      const response = await api.post(
        '/produtos/importar',
        formData
      );

      setResultado(response.data);
      setEtapa('resultado');
      
      if (response.data.total_sucesso > 0) {
        toast.success(`${response.data.total_sucesso} produtos processados com sucesso!`);
        if (onSuccess) {
          onSuccess();
        }
      }
      
      if (response.data.total_erros > 0) {
        toast.error(`${response.data.total_erros} produtos com erro`);
      }
    } catch (error) {
      console.error('Erro ao importar:', error);
      toast.error(error.response?.data?.detail || 'Erro ao importar produtos');
      setEtapa('upload');
    } finally {
      setImportando(false);
    }
  };

  const resetar = () => {
    setArquivo(null);
    setResultado(null);
    setEtapa('upload');
  };

  const fechar = () => {
    resetar();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <h2 className="text-xl font-bold text-white">ImportaÃ§Ã£o de Produtos em Lote</h2>
          </div>
          <button
            onClick={fechar}
            className="text-white hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {etapa === 'upload' && (
            <>
              {/* InstruÃ§Ãµes */}
              <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Como funciona
                </h3>
                <ul className="text-sm text-blue-800 space-y-1 ml-7">
                  <li>1. Baixe o template Excel clicando no botÃ£o abaixo</li>
                  <li>2. Preencha os dados dos produtos na planilha</li>
                  <li>3. Salve o arquivo e faÃ§a o upload aqui</li>
                  <li>4. Produtos novos serÃ£o criados, existentes serÃ£o atualizados (baseado no SKU)</li>
                </ul>
              </div>

              {/* BotÃ£o para baixar template */}
              <div className="mb-6">
                <button
                  onClick={baixarTemplate}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Baixar Template Excel
                </button>
              </div>

              {/* Upload de arquivo */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Selecione a Planilha Preenchida
                </label>
                <div className="flex items-center justify-center w-full">
                  <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <svg className="w-12 h-12 mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="mb-2 text-sm text-gray-500">
                        <span className="font-semibold">Clique para selecionar</span> ou arraste o arquivo
                      </p>
                      <p className="text-xs text-gray-500">Apenas arquivos Excel (.xlsx, .xls)</p>
                      
                      {arquivo && (
                        <div className="mt-4 flex items-center gap-2 text-blue-600">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <span className="font-medium">{arquivo.name}</span>
                        </div>
                      )}
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                    />
                  </label>
                </div>
              </div>
            </>
          )}

          {etapa === 'processando' && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-lg text-gray-700">Processando planilha...</p>
              <p className="text-sm text-gray-500 mt-2">Isso pode levar alguns segundos</p>
            </div>
          )}

          {etapa === 'resultado' && resultado && (
            <div className="space-y-6">
              {/* Resumo */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-600">{resultado.total_processado}</div>
                  <div className="text-sm text-blue-800 mt-1">Total Processado</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-600">{resultado.total_criados}</div>
                  <div className="text-sm text-green-800 mt-1">Criados</div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-600">{resultado.total_atualizados}</div>
                  <div className="text-sm text-yellow-800 mt-1">Atualizados</div>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-600">{resultado.total_erros}</div>
                  <div className="text-sm text-red-800 mt-1">Erros</div>
                </div>
              </div>

              {/* Produtos Criados */}
              {resultado.detalhes.criados.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h4 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Produtos Criados ({resultado.detalhes.criados.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="text-sm space-y-1">
                      {resultado.detalhes.criados.map((item, idx) => (
                        <li key={idx} className="text-green-800">
                          Linha {item.linha}: <span className="font-medium">{item.sku}</span> - {item.nome}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Produtos Atualizados */}
              {resultado.detalhes.atualizados.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h4 className="font-semibold text-yellow-900 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Produtos Atualizados ({resultado.detalhes.atualizados.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="text-sm space-y-1">
                      {resultado.detalhes.atualizados.map((item, idx) => (
                        <li key={idx} className="text-yellow-800">
                          Linha {item.linha}: <span className="font-medium">{item.sku}</span> - {item.nome}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Erros */}
              {resultado.detalhes.erros.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Erros ({resultado.detalhes.erros.length})
                  </h4>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="text-sm space-y-2">
                      {resultado.detalhes.erros.map((item, idx) => (
                        <li key={idx} className="text-red-800">
                          <strong>Linha {item.linha}</strong> ({item.sku}): {item.erro}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3 bg-gray-50">
          {etapa === 'upload' && (
            <>
              <button
                onClick={fechar}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleImportar}
                disabled={!arquivo || importando}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {importando ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Importando...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Importar Produtos
                  </>
                )}
              </button>
            </>
          )}
          
          {etapa === 'resultado' && (
            <>
              <button
                onClick={resetar}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Importar Novamente
              </button>
              <button
                onClick={fechar}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Concluir
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

