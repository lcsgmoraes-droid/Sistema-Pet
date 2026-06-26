import { useNavigate } from "react-router-dom";
import Aba2RecebimentosResult from "./Aba2RecebimentosResult";
import { Aba2RecebimentosModals } from "./Aba2RecebimentosSections";

export default function Aba2ConciliacaoRecebimentosView({
  avisoOculto,
  setAvisoOculto,
  ocultarAviso,
  operadoras,
  operadoraSelecionada,
  setOperadoraSelecionada,
  carregandoOperadoras,
  processando,
  setProcessando,
  arquivos,
  handleFileChange,
  todosArquivosEnviados,
  resultado,
  setResultado,
  erro,
  setErro,
  resetarTudo,
  handleClickValidar,
  handleValidar,
  handleAvancar,
  mostrarModalConfirmacao,
  setMostrarModalConfirmacao,
  mostrarModalDivergencia,
  setMostrarModalDivergencia,
  operadoraDetectada,
  setOperadoraDetectada,
  confiancaDeteccao,
  setIgnorarDivergenciaOperadora,
}) {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Aba 2: Conciliação de Recebimentos
          </h2>
          <p className="text-gray-600">
            Valide que dinheiro entrou na conta (3 arquivos: detalhados, recibo, OFX)
          </p>
        </div>
        <button
          onClick={() => navigate("/financeiro/historico-conciliacoes")}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-semibold">📜 Ver Histórico</span>
        </button>
      </div>

      {/* Aviso de Sequencia */}
      {!avisoOculto ? (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>Ordem recomendada:</strong> Aba 1 prepara os NSUs; esta Aba 2 valida os
                  recebimentos; a Aba 3 baixa as parcelas com seguranca.
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
      <div className="bg-purple-50 border-l-4 border-purple-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-purple-400" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-purple-700 mb-2">
              <strong>Esta aba NÃO conhece vendas.</strong> Apenas valida que o dinheiro entrou na
              conta. Validação em cascata: Recebimentos → Recibo → OFX (todos precisam bater).
            </p>
            <details className="text-xs text-purple-600 mt-2">
              <summary className="cursor-pointer font-semibold hover:text-purple-800">
                📋 Formato esperado dos arquivos
              </summary>
              <div className="mt-2 space-y-2 pl-4">
                <p>
                  <strong>Recebimentos Detalhados CSV da Stone:</strong>
                </p>
                <p className="text-xs font-mono">
                  DOCUMENTO;STONECODE;CATEGORIA;DATA DA VENDA;DATA DE VENCIMENTO;DATA DE VENCIMENTO
                  ORIGINAL;BANDEIRA;PRODUTO;STONE ID;QTD DE PARCELAS;Nº DA PARCELA;VALOR BRUTO;VALOR
                  LÍQUIDO;DESCONTO DE MDR;DESCONTO DE ANTECIPAÇÃO;DESCONTO UNIFICADO;ÚLTIMO
                  STATUS;DATA DO ÚLTIMO STATUS
                </p>
                <p className="text-xs text-purple-500">
                  Separador: ponto-e-vírgula (;) | Valores com vírgula decimal (21,012265)
                </p>

                <p className="mt-2">
                  <strong>Comprovante de Pagamentos CSV da Stone:</strong>
                </p>
                <p className="text-xs font-mono">
                  Valor;Bandeira;Modalidade;...;Identificador Rastreável do Pagamento;...;Status do
                  Pagamento (19 colunas)
                </p>
                <p className="text-xs text-purple-500">
                  Separador: ponto-e-vírgula (;) | Valores com vírgula decimal (202,11)
                </p>

                <p className="mt-2">
                  <strong>OFX:</strong>
                </p>
                <p className="text-xs">
                  Arquivo bancário padrão OFX com tags &lt;STMTTRN&gt;, &lt;TRNAMT&gt;,
                  &lt;TRNTYPE&gt;
                </p>
              </div>
            </details>
          </div>
        </div>
      </div>

      {/* Seleção de Operadora */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 border-2 border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            <svg
              className="h-8 w-8 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-semibold text-blue-900 mb-2">
              🏛 Operadora de Cartão:
            </label>
            <select
              value={operadoraSelecionada?.id || ""}
              onChange={(e) => {
                const op = operadoras.find((o) => o.id === parseInt(e.target.value));
                setOperadoraSelecionada(op);
                // Limpar resultado anterior ao trocar operadora
                setResultado(null);
                setErro(null);
                setIgnorarDivergenciaOperadora(false); // Resetar flag ao trocar operadora
                setOperadoraDetectada(null);
              }}
              disabled={carregandoOperadoras || processando}
              className="w-full border-2 border-blue-300 rounded-lg px-4 py-3 text-base font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Selecione a operadora...</option>
              {operadoras.map((op) => (
                <option key={op.id} value={op.id}>
                  {op.nome} {op.padrao ? "🎯 (Padrão)" : ""}
                </option>
              ))}
            </select>
            {operadoraSelecionada && (
              <p className="mt-2 text-xs text-blue-700">
                ✅ Operadora selecionada: <strong>{operadoraSelecionada.nome}</strong>
              </p>
            )}
            {!operadoraSelecionada && (
              <p className="mt-2 text-xs text-orange-600 font-medium">
                ⚠️ Selecione a operadora antes de fazer upload dos arquivos
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Uploads dos 3 Arquivos */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Arquivo 1: Recebimentos Detalhados */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-blue-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-recebimentos" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">
                  1️⃣ Recebimentos Detalhados
                </span>
                <span className="block text-xs text-gray-500 mb-3">
                  Arquivo CSV da Stone (18 colunas)
                </span>
                <input
                  id="file-recebimentos"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileChange("recebimentos", e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar CSV
                </span>
              </label>
              {arquivos.recebimentos && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.recebimentos.name}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Arquivo 2: Recibo Lote */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-green-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-recibo" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">
                  2️⃣ Recibo de Lote
                </span>
                <span className="block text-xs text-gray-500 mb-3">
                  CSV "Comprovante de Pagamentos" (19 colunas)
                </span>
                <input
                  id="file-recibo"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileChange("recibo", e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar CSV
                </span>
              </label>
              {arquivos.recibo && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.recibo.name}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Arquivo 3: OFX */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-purple-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-ofx" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">3️⃣ Extrato OFX</span>
                <span className="block text-xs text-gray-500 mb-3">Extrato bancário</span>
                <input
                  id="file-ofx"
                  type="file"
                  accept=".ofx,.xml"
                  onChange={(e) => handleFileChange("ofx", e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar OFX
                </span>
              </label>
              {arquivos.ofx && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.ofx.name}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Botão Validar */}
      {todosArquivosEnviados && !resultado && (
        <button
          onClick={handleClickValidar}
          disabled={processando || !operadoraSelecionada}
          className={`
            w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white
            ${processando ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"}
          `}
        >
          {processando ? (
            <>
              <svg
                className="animate-spin h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span>Validando recebimentos...</span>
            </>
          ) : (
            <>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              <span>Validar Cascata (3 arquivos)</span>
            </>
          )}
        </button>
      )}

      {/* Erro */}
      {erro && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{erro}</p>
              </div>
            </div>
            <button
              onClick={resetarTudo}
              className="ml-4 px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 text-xs font-medium rounded"
            >
              Limpar e Tentar Novamente
            </button>
          </div>
        </div>
      )}

      <Aba2RecebimentosResult
        handleAvancar={handleAvancar}
        resetarTudo={resetarTudo}
        resultado={resultado}
      />
      <Aba2RecebimentosModals
        confiancaDeteccao={confiancaDeteccao}
        handleValidar={handleValidar}
        mostrarModalConfirmacao={mostrarModalConfirmacao}
        mostrarModalDivergencia={mostrarModalDivergencia}
        operadoraDetectada={operadoraDetectada}
        operadoraSelecionada={operadoraSelecionada}
        operadoras={operadoras}
        resetarTudo={resetarTudo}
        setIgnorarDivergenciaOperadora={setIgnorarDivergenciaOperadora}
        setMostrarModalConfirmacao={setMostrarModalConfirmacao}
        setMostrarModalDivergencia={setMostrarModalDivergencia}
        setOperadoraSelecionada={setOperadoraSelecionada}
        setProcessando={setProcessando}
      />
    </div>
  );
}
