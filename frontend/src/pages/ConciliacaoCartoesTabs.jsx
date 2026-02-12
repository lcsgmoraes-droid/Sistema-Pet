import { useState, useEffect } from 'react';
import Aba1ConciliacaoVendasV2 from './Aba1ConciliacaoVendasV2';
import Aba2ConciliacaoRecebimentos from './Aba2ConciliacaoRecebimentos';
import Aba3AmarracaoAutomatica from './Aba3AmarracaoAutomatica';

/**
 * Container das 3 Abas de Conciliação
 * 
 * ARQUITETURA:
 * - Aba 1: Conciliação de Vendas (PDV vs Stone) - PREPARATÓRIA
 * - Aba 2: Conciliação de Recebimentos (3 arquivos) - VALIDAÇÃO
 * - Aba 3: Amarração Automática (baixa parcelas) - 98% AUTOMÁTICA
 * 
 * ORDEM RECOMENDADA:
 * - Aba 2 recomendada apos Aba 1
 * - Aba 3 recomendada apos Aba 2
 * 
 * PRINCÍPIOS:
 * - Aba 1 não mexe em financeiro (só prepara)
 * - Aba 2 não conhece vendas (só valida dinheiro)
 * - Aba 3 é 98% automática (se Abas 1 e 2 OK)
 */
export default function ConciliacaoCartoesTabs() {
  const [abaAtiva, setAbaAtiva] = useState(1);
  const [mostrarAviso, setMostrarAviso] = useState(false);
  const [abaDestino, setAbaDestino] = useState(null);
  const [naoMostrarAviso, setNaoMostrarAviso] = useState(false);
  
  // Status das abas
  const [aba1Status, setAba1Status] = useState('pendente'); // pendente | processado | erro
  const [aba2Status, setAba2Status] = useState('pendente'); // pendente | processado | erro
  const [aba3Status, setAba3Status] = useState('pendente'); // pendente | processado | erro
  
  // Controle de acesso
  const podeAcessarAba2 = true;
  const podeAcessarAba3 = true;

  useEffect(() => {
    const skip = localStorage.getItem('conciliacao_tabs_skip_aviso');
    setNaoMostrarAviso(skip === 'true');
  }, []);

  // DEBUG: Monitorar mudanças no abaAtiva
  useEffect(() => {
    console.log('🔄 abaAtiva MUDOU PARA:', abaAtiva);
  }, [abaAtiva]);
  
  // Handlers
  const handleAba1Concluida = () => {
    console.log('✅ Aba 1 concluída, marcando como processado');
    setAba1Status('processado');
    // Não avança automaticamente - usuário pode revisar antes de ir para Aba 2
  };
  
  const handleAba2Concluida = () => {
    console.log('✅ Aba 2 concluída, marcando como processado e avançando para Aba 3');
    setAba2Status('processado');
    // Avança imediatamente para Aba 3
    console.log('🚀 Mudando para Aba 3 imediatamente...');
    console.log('🔍 abaAtiva ANTES de setAbaAtiva:', abaAtiva);
    setAbaAtiva(prev => {
      console.log('🔍 abaAtiva ANTERIOR (dentro do setState):', prev);
      console.log('🔍 Retornando novo valor:', 3);
      return 3;
    });
    console.log('✅ setAbaAtiva(3) executado');
  };
  
  const handleAba3Concluida = () => {
    console.log('✅ Aba 3 concluída, marcando como processado');
    setAba3Status('processado');
    // Conciliação completa!
  };

  const abrirAbaComAviso = (numeroAba) => {
    if (naoMostrarAviso || numeroAba === 1) {
      setAbaAtiva(numeroAba);
      return;
    }

    setAbaDestino(numeroAba);
    setMostrarAviso(true);
  };

  const handleContinuarAviso = () => {
    if (abaDestino) {
      setAbaAtiva(abaDestino);
    }
    setMostrarAviso(false);
  };

  const handleNaoMostrarAviso = () => {
    localStorage.setItem('conciliacao_tabs_skip_aviso', 'true');
    setNaoMostrarAviso(true);
    if (abaDestino) {
      setAbaAtiva(abaDestino);
    }
    setMostrarAviso(false);
  };
  
  // Renderizar ícone de status
  const renderStatusIcon = (status) => {
    switch (status) {
      case 'processado':
        return <span className="text-green-600 text-xl">✅</span>;
      case 'pendente':
        return <span className="text-yellow-600 text-xl">⏳</span>;
      case 'bloqueado':
        return <span className="text-gray-400 text-xl">🔒</span>;
      case 'erro':
        return <span className="text-red-600 text-xl">❌</span>;
      default:
        return null;
    }
  };
  
  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          Conciliação de Cartões - 3 Etapas
        </h1>
        <p className="text-gray-600">
          Processo completo: Vendas → Recebimentos → Amarração (baixa automática)
        </p>
      </div>
      
      {/* Alertas de Ordem */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700 font-medium">
              Ordem recomendada: <strong>Aba 1</strong> → <strong>Aba 2</strong> → <strong>Aba 3</strong>. As abas ficam abertas, mas a sequencia evita divergencias.
            </p>
          </div>
        </div>
      </div>
      
      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex -mb-px space-x-8">
          {/* Aba 1 */}
          <button
            onClick={() => abrirAbaComAviso(1)}
            disabled={false} // Sempre acessível
            className={`
              flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
              ${abaAtiva === 1
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span className="text-lg">1️⃣</span>
            <span>Conciliação de Vendas</span>
            {renderStatusIcon(aba1Status)}
            {aba1Status === 'pendente' && (
              <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                Obrigatória
              </span>
            )}
          </button>
          
          {/* Aba 2 */}
          <button
            onClick={() => abrirAbaComAviso(2)}
            disabled={false}
            className={`
              flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
              ${abaAtiva === 2
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span className="text-lg">2️⃣</span>
            <span>Conciliação de Recebimentos</span>
            {renderStatusIcon(aba2Status)}
            {aba2Status === 'pendente' && (
              <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                Recomendada apos Aba 1
              </span>
            )}
          </button>
          
          {/* Aba 3 */}
          <button
            onClick={() => abrirAbaComAviso(3)}
            disabled={false}
            className={`
              flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
              ${abaAtiva === 3
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span className="text-lg">3️⃣</span>
            <span>Amarração Automática</span>
            {renderStatusIcon(aba3Status)}
            {aba3Status === 'pendente' && (
              <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                Recomendada apos Aba 2
              </span>
            )}
          </button>
        </nav>
      </div>
      
      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {abaAtiva === 1 && (
          <Aba1ConciliacaoVendasV2 
            onConcluida={handleAba1Concluida}
            status={aba1Status}
          />
        )}
        
        {abaAtiva === 2 && (
          <Aba2ConciliacaoRecebimentos 
            onConcluida={handleAba2Concluida}
            status={aba2Status}
          />
        )}
        
        {abaAtiva === 3 && (
          <Aba3AmarracaoAutomatica 
            onConcluida={handleAba3Concluida}
            status={aba3Status}
          />
        )}
      </div>

      {/* Modal de Ordem Recomendada */}
      {mostrarAviso && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Ordem recomendada das etapas
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              A sequencia <strong>Aba 1 → Aba 2 → Aba 3</strong> reduz divergencias e garante que a amarracao automatica encontre todos os recebimentos.
            </p>
            <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-700 mb-4">
              <p><strong>Aba 1:</strong> prepara vendas e NSUs.</p>
              <p><strong>Aba 2:</strong> valida que o dinheiro entrou.</p>
              <p><strong>Aba 3:</strong> baixa parcelas automaticamente.</p>
            </div>
            <div className="flex items-center justify-between">
              <button
                onClick={() => setMostrarAviso(false)}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancelar
              </button>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleNaoMostrarAviso}
                  className="px-3 py-2 text-sm text-blue-700 hover:text-blue-900"
                >
                  Nao mostrar novamente
                </button>
                <button
                  onClick={handleContinuarAviso}
                  className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded hover:bg-blue-700"
                >
                  Continuar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Rodapé Informativo */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">
          ℹ️ Como funciona:
        </h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>
            <strong>Aba 1:</strong> Confere NSU, bandeira, parcelas, taxa (prepara dados)
          </li>
          <li>
            <strong>Aba 2:</strong> Valida que dinheiro entrou na conta (3 arquivos: detalhados, recibo, OFX)
          </li>
          <li>
            <strong>Aba 3:</strong> Vincula recebimentos às vendas e baixa parcelas automaticamente (98%!)
          </li>
        </ul>
      </div>
    </div>
  );
}
