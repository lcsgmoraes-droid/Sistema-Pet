import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

/**
 * ABA 3: AMARRAÇÃO AUTOMÁTICA (98%)
 * 
 * Objetivo:
 *   Vincular recebimentos (validados Aba 2) às vendas (conferidas Aba 1)
 *   e BAIXAR Contas a Receber.
 * 
 * Princípios:
 *   - 98% automático (se Abas 1 e 2 foram bem feitas!)
 *   - IDEMPOTENTE (se rodar 2x, não duplica baixa)
 *   - TRANSPARENTE (mostra quantas parcelas ANTES de processar)
 * 
 * Fluxo:
 *   1. Usuário seleciona data dos recebimentos
 *   2. Sistema mostra PREVIEW: "47 parcelas serão baixadas (R$ 15.300,00)"
 *   3. Usuário confirma
 *   4. Sistema processa amarração
 *   5. Mostra resultado + métrica de saúde (98% = OK, < 90% = CRÍTICO)
 * 
 * Resultado:
 *   contas_receber.status = 'recebido'
 *   conciliacao_metricas.taxa_amarracao_automatica = 98%
 */
export default function Aba3AmarracaoAutomatica({ onConcluida, status }) {
  const navigate = useNavigate();
  const [avisoOculto, setAvisoOculto] = useState(false);
  const [dataRecebimento, setDataRecebimento] = useState('');
  const [preview, setPreview] = useState(null);
  const [processando, setProcessando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState(null);

  const [operadoras, setOperadoras] = useState([]);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [carregandoOperadoras, setCarregandoOperadoras] = useState(true);

  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const response = await api.get('/api/operadoras-cartao?apenas_ativas=true');
        setOperadoras(response.data);

        const padrao = response.data.find((op) => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error('Erro ao carregar operadoras:', error);
        setErro('Erro ao carregar operadoras');
      } finally {
        setCarregandoOperadoras(false);
      }
    };

    carregarOperadoras();
  }, []);

  useEffect(() => {
    const raw = localStorage.getItem('conciliacao_aba3_aviso_ate');
    if (!raw) return;
    const expiraEm = Number(raw);
    if (Number.isFinite(expiraEm) && Date.now() < expiraEm) {
      setAvisoOculto(true);
    }
  }, []);

  const ocultarAviso = (dias) => {
    const expiraEm = Date.now() + dias * 24 * 60 * 60 * 1000;
    localStorage.setItem('conciliacao_aba3_aviso_ate', String(expiraEm));
    setAvisoOculto(true);
  };

  // Buscar preview quando data mudar
  useEffect(() => {
    if (dataRecebimento && operadoraSelecionada) {
      buscarPreview();
    } else {
      setPreview(null);
    }
  }, [dataRecebimento, operadoraSelecionada]);

  // Buscar preview (transparência)
  const buscarPreview = async () => {
    try {
      const response = await api.get('/api/conciliacao/aba3/preview-amarracao', {
        params: {
          data_recebimento: dataRecebimento,
          operadora: operadoraSelecionada?.nome
        }
      });
      setPreview(response.data);
    } catch (error) {
      console.error('Erro ao buscar preview:', error);
      setPreview(null);
    }
  };

  // Processar amarração
  const handleProcessar = async () => {
    if (!operadoraSelecionada || !dataRecebimento) {
      setErro('Selecione a operadora e a data primeiro');
      return;
    }

    setProcessando(true);
    setErro(null);

    try {
      const response = await api.post('/api/conciliacao/aba3/amarrar-automatico', {
        data_recebimento: dataRecebimento,
        operadora: operadoraSelecionada?.nome
      });

      setResultado(response.data);

    } catch (error) {
      console.error('Erro ao processar:', error);
      setErro(error.response?.data?.detail || 'Erro ao processar amarração');
    } finally {
      setProcessando(false);
    }
  };

  // Concluir processo
  const handleConcluir = () => {
    if (resultado) {
      const mensagem = `✅ Conciliação finalizada com sucesso!\n\n` +
        `📊 Resumo:\n` +
        `• ${resultado.parcelas_liquidadas} parcelas baixadas\n` +
        `• Valor total: R$ ${resultado.valor_total_liquidado?.toFixed(2)}\n` +
        `• Taxa de amarração: ${resultado.taxa_amarracao_automatica?.toFixed(1)}%`;
      
      alert(mensagem);
    }
    
    if (onConcluida) {
      onConcluida();
    }
    
    // Redirecionar para o histórico
    navigate('/financeiro/historico-conciliacoes');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Aba 3: Amarração Automática
        </h2>
        <p className="text-gray-600">
          Amarração 98% automática: recebimentos → vendas → baixa de parcelas
        </p>
      </div>

      {/* Aviso de Sequencia */}
      {!avisoOculto ? (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>Ordem recomendada:</strong> Execute a Aba 1 e Aba 2 antes para garantir que a amarracao encontre todos os recebimentos.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => ocultarAviso(30)}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Ocultar 30 dias
              </button>
              <button
                onClick={() => ocultarAviso(365)}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Ocultar 1 ano
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAvisoOculto(false)}
          className="text-xs text-blue-700 hover:text-blue-900"
        >
          Mostrar aviso de sequencia
        </button>
      )}

      {/* Alerta Importante */}
      <div className="bg-green-50 border-l-4 border-green-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-green-700">
              <strong>98% automático!</strong> Se as Abas 1 e 2 foram bem feitas, esta etapa é quase instantânea.
              Sistema vincula recebimentos às vendas pelo NSU e baixa as parcelas automaticamente.
            </p>
          </div>
        </div>
      </div>

      {/* Seleção de Operadora e Data */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Operadora:
            </label>
            <select
              value={operadoraSelecionada?.id || ''}
              onChange={(e) => {
                const op = operadoras.find((o) => String(o.id) === e.target.value);
                setOperadoraSelecionada(op || null);
              }}
              disabled={carregandoOperadoras}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Selecione a operadora</option>
              {operadoras.map((op) => (
                <option key={op.id} value={op.id}>
                  {op.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data dos recebimentos:
            </label>
            <input
              type="date"
              value={dataRecebimento}
              onChange={(e) => setDataRecebimento(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Selecione a operadora e a data dos recebimentos validados na Aba 2
        </p>
      </div>

      {/* Preview (Transparência) */}
      {preview && preview.recebimentos_validados > 0 && (
        <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4 flex-1">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                📊 Preview da Amarração
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-white rounded">
                  <span className="text-sm text-gray-700">Recebimentos validados:</span>
                  <span className="text-lg font-bold text-gray-900">
                    {preview.recebimentos_validados}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-blue-100 rounded border-2 border-blue-400">
                  <span className="text-sm font-semibold text-blue-900">
                    ✅ Parcelas que serão baixadas:
                  </span>
                  <span className="text-xl font-bold text-blue-900">
                    {preview.parcelas_a_baixar}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-green-100 rounded border-2 border-green-400">
                  <span className="text-sm font-semibold text-green-900">
                    💰 Valor total a liquidar:
                  </span>
                  <span className="text-xl font-bold text-green-900">
                    R$ {preview.valor_total?.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Vazio */}
      {preview && preview.recebimentos_validados === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            ⚠️ Nenhum recebimento validado encontrado para esta data.
            Verifique se a Aba 2 foi processada corretamente.
          </p>
        </div>
      )}

      {/* Botão Processar */}
      {preview && preview.parcelas_a_baixar > 0 && !resultado && (
        <button
          onClick={handleProcessar}
          disabled={processando}
          className={`
            w-full flex justify-center items-center gap-3 py-4 px-6 border-2 border-transparent rounded-lg shadow-lg text-base font-bold
            ${processando 
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white'
            }
          `}
        >
          {processando ? (
            <>
              <svg className="animate-spin h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Processando amarração...</span>
            </>
          ) : (
            <>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>✅ Processar → baixar {preview.parcelas_a_baixar} parcelas</span>
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
        <div className="space-y-6">
          {/* Card Principal - Resultado */}
          <div className={`border-l-4 p-6 rounded-lg ${
            resultado.alerta_saude === 'OK' 
              ? 'bg-green-50 border-green-400' 
              : 'bg-red-50 border-red-400'
          }`}>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {resultado.alerta_saude === 'OK' ? (
                  <svg className="h-8 w-8 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="h-8 w-8 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
              <div className="ml-4 flex-1">
                <h3 className={`text-xl font-bold mb-2 ${
                  resultado.alerta_saude === 'OK' ? 'text-green-900' : 'text-red-900'
                }`}>
                  {resultado.alerta_saude === 'OK' 
                    ? '✅ Amarração Concluída com Sucesso!' 
                    : '⚠️ Amarração Concluída com Alertas'
                  }
                </h3>
                
                {/* Mensagem de sucesso clara */}
                <p className="text-sm text-gray-700 font-medium mb-4 bg-green-100 border border-green-300 rounded px-3 py-2">
                  💰 {resultado.parcelas_liquidadas} conta(s) a receber foi(ram) baixada(s) com sucesso!
                  Valor total: R$ {resultado.valor_total_liquidado?.toFixed(2)}
                </p>

                {/* Estatísticas */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-white rounded p-4 shadow">
                    <p className="text-xs text-gray-500 uppercase mb-1">Amarrados</p>
                    <p className="text-3xl font-bold text-green-600">{resultado.amarrados}</p>
                  </div>
                  <div className="bg-white rounded p-4 shadow">
                    <p className="text-xs text-gray-500 uppercase mb-1">Órfãos</p>
                    <p className="text-3xl font-bold text-red-600">{resultado.orfaos}</p>
                  </div>
                  <div className="bg-white rounded p-4 shadow">
                    <p className="text-xs text-gray-500 uppercase mb-1">Parcelas Liquidadas</p>
                    <p className="text-2xl font-bold text-blue-600">{resultado.parcelas_liquidadas}</p>
                  </div>
                  <div className="bg-white rounded p-4 shadow">
                    <p className="text-xs text-gray-500 uppercase mb-1">Valor Liquidado</p>
                    <p className="text-xl font-bold text-purple-600">
                      R$ {resultado.valor_total_liquidado?.toFixed(2)}
                    </p>
                  </div>
                </div>

                {/* Métrica de Saúde */}
                <div className={`p-4 rounded-lg border-2 ${
                  resultado.alerta_saude === 'OK'
                    ? 'bg-green-100 border-green-400'
                    : 'bg-red-100 border-red-400'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        📊 Saúde do Sistema
                      </p>
                      <p className="text-xs text-gray-600">
                        Taxa de amarração automática
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-4xl font-bold ${
                        resultado.alerta_saude === 'OK' ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {resultado.taxa_amarracao_automatica?.toFixed(1)}%
                      </p>
                      <p className={`text-sm font-medium mt-1 ${
                        resultado.alerta_saude === 'OK' ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {resultado.alerta_saude === 'OK' ? '✅ SAUDÁVEL' : '🚨 CRÍTICO'}
                      </p>
                    </div>
                  </div>
                  {resultado.alerta_saude !== 'OK' && (
                    <p className="mt-3 text-xs text-red-700 font-medium">
                      ⚠️ Taxa abaixo de 90% indica problema na operação. Revise a Aba 1 (conferência de vendas).
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Recebimentos Órfãos */}
          {resultado.orfaos > 0 && resultado.lista_orfaos && (
            <div className="bg-white border-2 border-red-300 rounded-lg overflow-hidden">
              <div className="px-6 py-4 bg-red-50 border-b border-red-200">
                <h4 className="text-lg font-semibold text-red-900">
                  ⚠️ Recebimentos Órfãos ({resultado.orfaos})
                </h4>
                <p className="text-sm text-red-700 mt-1">
                  Estes recebimentos não têm venda correspondente. Precisa resolver na Aba 1.
                </p>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  {resultado.lista_orfaos.map((orfao, idx) => (
                    <div key={idx} className="flex items-center justify-between p-4 bg-red-50 rounded-lg border border-red-200">
                      <div>
                        <p className="text-sm font-bold text-red-900">NSU: {orfao.nsu}</p>
                        <p className="text-xs text-red-700">
                          Data: {orfao.data} • Valor: R$ {orfao.valor?.toFixed(2)}
                        </p>
                      </div>
                      <button className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700">
                        Resolver na Aba 1
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Botão Concluir */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              <p>🎉 Conciliação completa! Todas as 3 abas foram processadas.</p>
            </div>
            <button
              onClick={handleConcluir}
              className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold flex items-center gap-2 shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Concluir e Ver Histórico</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
