import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

/**
 * ABA 1: CONCILIAÇÃO DE VENDAS (PDV vs Stone)
 * 
 * Objetivo:
 *   Conferir e CORRIGIR vendas do PDV vs planilha Stone.
 *   NÃO mexe em financeiro (só prepara dados).
 * 
 * Fluxo:
 *   1. Selecionar operadora (filtro)
 *   2. Upload CSV vendas da operadora
 *   3. Sistema compara: PDV vs Operadora
 *   4. Mostra divergências (NSU, bandeira, parcelas, taxa)
 *   5. Usuário corrige ou aprova
 *   6. Marca vendas como conferidas
 * 
 * Resultado:
 *   vendas.conciliado_vendas = true
 *   Desbloqueia Aba 2
 */
export default function Aba1ConciliacaoVendas({ onConcluida, status }) {
  const navigate = useNavigate();
  const [operadoras, setOperadoras] = useState([]);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [arquivo, setArquivo] = useState(null);
  const [processando, setProcessando] = useState(false);
  const [carregandoOperadoras, setCarregandoOperadoras] = useState(true);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState(null);

  // 🆕 Carregar operadoras com tratamento de autenticação
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        // Verificar se há token antes de fazer a requisição
        const token = localStorage.getItem('access_token');
        if (!token) {
          console.error('❌ Token não encontrado. Redirecionando para login...');
          setErro('Você precisa estar logado para acessar esta página.');
          setTimeout(() => navigate('/login'), 2000);
          return;
        }

        console.log('🔄 Carregando operadoras...');
        const response = await api.get('/api/operadoras-cartao?apenas_ativas=true');
        console.log('✅ Operadoras carregadas:', response.data);
        setOperadoras(response.data);
        
        // Pré-selecionar operadora padrão
        const padrao = response.data.find(op => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
          console.log('📌 Operadora padrão selecionada:', padrao.nome);
        }
      } catch (error) {
        console.error('❌ Erro ao carregar operadoras:', error);
        
        // Tratamento específico por tipo de erro
        if (error.response?.status === 401) {
          setErro('Sessão expirada. Redirecionando para login...');
          localStorage.removeItem('access_token');
          setTimeout(() => navigate('/login'), 2000);
        } else if (error.response?.status === 403) {
          setErro('Você não tem permissão para acessar as operadoras.');
        } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
          setErro('Erro de conexão com o servidor. Verifique se o backend está rodando.');
        } else {
          setErro(error.response?.data?.detail || 'Erro ao carregar operadoras. Por favor, recarregue a página.');
        }
      } finally {
        setCarregandoOperadoras(false);
      }
    };
    carregarOperadoras();
  }, [navigate]);

  // Handler upload arquivo
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setArquivo(file);
      setErro(null);
    }
  };

  // Processar conciliação com tratamento robusto de erros
  const handleProcessar = async () => {
    if (!arquivo) {
      setErro('Selecione um arquivo CSV primeiro');
      return;
    }

    if (!operadoraSelecionada) {
      setErro('Selecione uma operadora');
      return;
    }

    // Verificar autenticação antes de processar
    const token = localStorage.getItem('access_token');
    if (!token) {
      setErro('Sessão expirada. Redirecionando para login...');
      setTimeout(() => navigate('/login'), 2000);
      return;
    }

    setProcessando(true);
    setErro(null);

    try {
      // Criar FormData para upload
      const formData = new FormData();
      formData.append('arquivo', arquivo);
      formData.append('operadora_id', operadoraSelecionada.id);

      console.log('📤 Enviando arquivo:', arquivo.name, 'para operadora:', operadoraSelecionada.nome);
      console.log('📝 Operadora ID:', operadoraSelecionada.id);

      // Chamar novo endpoint com persistência
      const response = await api.post('/api/conciliacao/aba1/upload-e-conciliar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      console.log('✅ Resposta da API:', response.data);

      setResultado(response.data);

      // Se processou com sucesso, marca como concluída
      if (response.data.success && response.data.persistido) {
        alert(`✅ Conciliação salva com sucesso!\nImportação ID: ${response.data.importacao_id}\nConferidas: ${response.data.conferidas}\nPendentes: ${response.data.sem_nsu}\nÓrfãs: ${response.data.orfaos}`);
        
        // Opcional: disparar callback para atualizar interface pai
        if (onConcluida) {
          setTimeout(() => {
            onConcluida();
          }, 500);
        }
      }

    } catch (error) {
      console.error('❌ Erro ao processar:', error);
      console.error('Detalhes do erro:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });

      // Tratamento específico por tipo de erro
      if (error.response?.status === 401) {
        setErro('Sessão expirada. Redirecionando para login...');
        localStorage.removeItem('access_token');
        setTimeout(() => navigate('/login'), 2000);
      } else if (error.response?.status === 400) {
        const detalhe = error.response?.data?.detail || 'Erro de validação';
        setErro(`Erro ao processar arquivo: ${detalhe}`);
      } else if (error.response?.status === 403) {
        setErro('Você não tem permissão para realizar esta operação.');
      } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
        setErro('Erro de conexão com o servidor. Verifique se o backend está rodando.');
      } else {
        setErro(error.response?.data?.detail || 'Erro ao processar arquivo. Por favor, tente novamente.');
      }
    } finally {
      setProcessando(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Aba 1: Conciliação de Vendas
        </h2>
        <p className="text-gray-600">
          Confira vendas do PDV vs planilha da operadora (NSU, bandeira, parcelas, taxa)
        </p>
      </div>

      {/* Loading state */}
      {carregandoOperadoras && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-sm text-blue-700">Carregando operadoras...</span>
          </div>
        </div>
      )}

      {/* 🆕 FILTRO DE OPERADORA */}
      {!carregandoOperadoras && operadoras.length > 0 && (
        <div className="bg-white border border-gray-300 rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Operadora de Cartão
          </label>
          <select
            value={operadoraSelecionada?.id || ''}
            onChange={(e) => {
              const op = operadoras.find(o => o.id === parseInt(e.target.value));
              setOperadoraSelecionada(op);
              setArquivo(null); // Limpar arquivo ao trocar operadora
              setResultado(null);
              setErro(null);
            }}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione a operadora...</option>
            {operadoras.map((op) => (
              <option key={op.id} value={op.id}>
                {op.nome} {op.padrao && '(Padrão)'}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Selecione a operadora para conciliar vendas específicas
          </p>
        </div>
      )}

      {/* Aviso quando não há operadoras */}
      {!carregandoOperadoras && operadoras.length === 0 && !erro && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-yellow-800">Nenhuma operadora cadastrada</p>
              <p className="text-xs text-yellow-700 mt-1">
                Configure pelo menos uma operadora de cartão antes de conciliar vendas.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Alerta Importante */}
      {!carregandoOperadoras && operadoras.length > 0 && (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>Esta aba NÃO mexe em financeiro.</strong> Apenas corrige cadastro das vendas.
              Se parcelas/valor/taxa mudarem, o sistema regenerará as Contas a Receber automaticamente.
            </p>
          </div>
        </div>
      </div>
      )}

      {/* Upload */}
      {!carregandoOperadoras && operadoras.length > 0 && (
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-6">
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="mt-4">
            <label htmlFor="file-upload" className="cursor-pointer">
              <span className="mt-2 block text-sm font-medium text-gray-900">
                Upload CSV Vendas {operadoraSelecionada?.nome || 'da Operadora'}
              </span>
              <span className="mt-1 block text-xs text-gray-500">
                Arquivo com vendas do dia anterior (D+1)
              </span>
              <input
                id="file-upload"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="sr-only"
              />
              <span className="mt-3 inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                Selecionar Arquivo
              </span>
            </label>
            {arquivo && (
              <p className="mt-2 text-sm text-green-600 font-medium">
                ✓ {arquivo.name}
              </p>
            )}
          </div>
        </div>
      </div>
      )}

      {/* Botão Processar */}
      {arquivo && !resultado && (
        <button
          onClick={handleProcessar}
          disabled={processando}
          className={`
            w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white
            ${processando ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}
          `}
        >
          {processando ? (
            <>
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Processando vendas...</span>
            </>
          ) : (
            <>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Processar Conciliação de Vendas</span>
            </>
          )}
        </button>
      )}

      {/* Erro */}
      {erro && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{erro}</p>
            </div>
          </div>
        </div>
      )}

      {/* Resultado */}
      {resultado && resultado.success && (
        <div className="space-y-4">
          {/* Resumo */}
          <div className="bg-green-50 border-l-4 border-green-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-medium text-green-800">
                  Conciliação de Vendas Concluída{resultado.persistido && ' e Salva'}!
                </h3>
                {resultado.persistido && (
                  <div className="mt-2 mb-3 p-3 bg-white rounded border border-green-200">
                    <p className="text-xs text-gray-700 font-medium mb-1">📦 Dados salvos permanentemente:</p>
                    <div className="text-xs text-gray-600 space-y-1">
                      <p>• <strong>Importação ID:</strong> {resultado.importacao_id}</p>
                      <p>• <strong>Arquivo ID:</strong> {resultado.arquivo_id}</p>
                      <p className="text-green-600 mt-2">
                        ✨ Você pode sair e voltar - a conciliação está no histórico!
                      </p>
                    </div>
                  </div>
                )}
                <div className="mt-2 text-sm text-green-700">
                  <ul className="list-disc list-inside space-y-1">
                    <li><strong>{resultado.conferidas}</strong> vendas conferidas (OK)</li>
                    <li><strong>{resultado.corrigidas}</strong> vendas com divergências</li>
                    <li><strong>{resultado.sem_nsu}</strong> vendas sem NSU (precisa vincular)</li>
                    <li><strong>{resultado.orfaos}</strong> NSUs Stone sem venda no PDV</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Divergências */}
          {resultado.divergencias && resultado.divergencias.length > 0 && (
            <div className="bg-white border border-yellow-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-yellow-50 border-b border-yellow-200">
                <h4 className="text-sm font-semibold text-yellow-900">
                  ⚠️ Divergências Encontradas ({resultado.divergencias.length})
                </h4>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Venda</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PDV</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stone</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ação Sugerida</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {resultado.divergencias.map((div, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {div.tipo === 'nsu_duplicado' ? (
                            <div>
                              <div className="font-semibold text-red-600">NSU: {div.nsu}</div>
                              <div className="text-xs text-gray-500 mt-1">
                                {div.vendas.map((v, i) => (
                                  <div key={i}>Venda {v.numero_venda}</div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <span>Venda {div.numero_venda || div.venda_id}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 text-xs font-medium rounded ${
                            div.tipo === 'nsu_duplicado' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {div.tipo}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {div.tipo === 'nsu_duplicado' ? `${div.vendas.length} vendas` : div.pdv}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                          {div.tipo === 'nsu_duplicado' ? '1 transação Stone' : div.stone}
                        </td>
                        <td className="px-4 py-3 text-sm text-blue-600">{div.acao_sugerida}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Vendas sem NSU */}
          {resultado.vendas_sem_nsu && resultado.vendas_sem_nsu.length > 0 && (
            <div className="bg-white border border-orange-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-orange-50 border-b border-orange-200">
                <h4 className="text-sm font-semibold text-orange-900">
                  🔗 Vendas Sem NSU ({resultado.vendas_sem_nsu.length})
                </h4>
              </div>
              <div className="p-4">
                <p className="text-sm text-gray-600 mb-3">
                  Estas vendas precisam ter NSU vinculado manualmente:
                </p>
                <div className="space-y-2">
                  {resultado.vendas_sem_nsu.map((venda, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div>
                        <span className="text-sm font-medium text-gray-900">
                          Venda {venda.numero}
                        </span>
                        <span className="ml-3 text-sm text-gray-600">
                          R$ {venda.valor.toFixed(2)}
                        </span>
                      </div>
                      <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                        Vincular NSU
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Botão Avançar */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              <p>✅ Aba 1 concluída. Você pode avançar para a Aba 2.</p>
            </div>
            <button
              onClick={onConcluida}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium"
            >
              Avançar para Aba 2 →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
