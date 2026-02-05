import { useState } from 'react';
import { X, DollarSign, Calculator, AlertCircle } from 'lucide-react';
import { abrirCaixa } from '../api/caixa';

const CEDULAS = [
  { valor: 200, cor: 'yellow' },
  { valor: 100, cor: 'blue' },
  { valor: 50, cor: 'orange' },
  { valor: 20, cor: 'yellow' },
  { valor: 10, cor: 'red' },
  { valor: 5, cor: 'purple' },
  { valor: 2, cor: 'blue' }
];

export default function ModalAbrirCaixa({ onClose, onSucesso }) {
  const [valorAbertura, setValorAbertura] = useState('');
  const [contaOrigem, setContaOrigem] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [notas, setNotas] = useState({
    n2: 0, n5: 0, n10: 0, n20: 0, n50: 0, n100: 0, n200: 0, moedas: 0
  });
  const [mostrarContagem, setMostrarContagem] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  // Calcular total das notas
  const calcularTotalNotas = () => {
    return (
      (notas.n200 * 200) + (notas.n100 * 100) + (notas.n50 * 50) +
      (notas.n20 * 20) + (notas.n10 * 10) + (notas.n5 * 5) + (notas.n2 * 2) +
      parseFloat(notas.moedas || 0)
    );
  };

  // Aplicar valor calculado
  const aplicarContagem = () => {
    const total = calcularTotalNotas();
    setValorAbertura(total.toFixed(2));
    setMostrarContagem(false);
  };

  // Limpar contagem
  const limparContagem = () => {
    setNotas({n2: 0, n5: 0, n10: 0, n20: 0, n50: 0, n100: 0, n200: 0, moedas: 0});
  };

  // Abrir caixa
  const handleAbrirCaixa = async () => {
    const valor = parseFloat(valorAbertura);

    if (!valor || valor < 0) {
      setErro('Informe um valor válido para abertura');
      return;
    }

    setLoading(true);
    setErro('');

    try {
      const dados = {
        valor_abertura: valor,
        conta_origem_nome: contaOrigem || 'Dinheiro em mãos',
        observacoes_abertura: observacoes
      };

      await abrirCaixa(dados);
      onSucesso();
    } catch (error) {
      console.error('Erro ao abrir caixa:', error);
      setErro(error.response?.data?.detail || 'Erro ao abrir caixa');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Abrir Caixa</h2>
              <p className="text-sm text-gray-500">
                Informe o valor inicial do caixa
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Botão Auxiliar Contagem */}
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">
              Valor de Abertura *
            </label>
            <button
              type="button"
              onClick={() => setMostrarContagem(!mostrarContagem)}
              className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg transition-colors"
            >
              <Calculator className="w-4 h-4" />
              <span>Auxiliar Contagem</span>
            </button>
          </div>

          {/* Calculadora de Notas */}
          {mostrarContagem && (
            <div className="mt-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-base font-bold text-gray-900 flex items-center">
                  <Calculator className="w-5 h-5 mr-2 text-blue-600" />
                  Auxiliar de Contagem
                </h4>
                <button
                  onClick={() => setMostrarContagem(false)}
                  className="p-1 hover:bg-blue-100 rounded-lg transition-colors"
                  type="button"
                >
                  <X className="w-5 h-5 text-gray-600" />
                </button>
              </div>

              <div className="space-y-3">
                {/* Notas de R$ 2 */}
                <div className="bg-white rounded-lg p-3 border-2 border-gray-200 hover:border-gray-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-gray-500 to-gray-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 2
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n2}
                        onChange={(e) => setNotas({...notas, n2: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-gray-500 focus:ring-2 focus:ring-gray-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-gray-600">
                      R$ {(notas.n2 * 2).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 5 */}
                <div className="bg-white rounded-lg p-3 border-2 border-purple-200 hover:border-purple-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 5
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n5}
                        onChange={(e) => setNotas({...notas, n5: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-purple-600">
                      R$ {(notas.n5 * 5).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 10 */}
                <div className="bg-white rounded-lg p-3 border-2 border-red-200 hover:border-red-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-red-500 to-red-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 10
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n10}
                        onChange={(e) => setNotas({...notas, n10: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-red-500 focus:ring-2 focus:ring-red-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-red-600">
                      R$ {(notas.n10 * 10).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 20 */}
                <div className="bg-white rounded-lg p-3 border-2 border-yellow-200 hover:border-yellow-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 20
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n20}
                        onChange={(e) => setNotas({...notas, n20: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-yellow-500 focus:ring-2 focus:ring-yellow-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-yellow-600">
                      R$ {(notas.n20 * 20).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 50 */}
                <div className="bg-white rounded-lg p-3 border-2 border-blue-200 hover:border-blue-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 50
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n50}
                        onChange={(e) => setNotas({...notas, n50: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-blue-600">
                      R$ {(notas.n50 * 50).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 100 */}
                <div className="bg-white rounded-lg p-3 border-2 border-green-200 hover:border-green-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-green-500 to-green-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 100
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n100}
                        onChange={(e) => setNotas({...notas, n100: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-green-500 focus:ring-2 focus:ring-green-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-green-600">
                      R$ {(notas.n100 * 100).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Notas de R$ 200 */}
                <div className="bg-white rounded-lg p-3 border-2 border-orange-200 hover:border-orange-400 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-orange-500 to-orange-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        R$ 200
                      </div>
                      <input
                        type="number"
                        min="0"
                        value={notas.n200}
                        onChange={(e) => setNotas({...notas, n200: parseInt(e.target.value) || 0})}
                        className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-orange-500 focus:ring-2 focus:ring-orange-200"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-500">×</span>
                    </div>
                    <span className="text-lg font-bold text-orange-600">
                      R$ {(notas.n200 * 200).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Moedas */}
              <div className="mt-4 pt-4 border-t-2 border-blue-300">
                <div className="bg-white rounded-lg p-4 border-2 border-amber-200 hover:border-amber-400 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <div className="bg-gradient-to-br from-amber-500 to-amber-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                        💰 Moedas
                      </div>
                    </div>
                    <span className="text-lg font-bold text-amber-600">
                      R$ {parseFloat(notas.moedas || 0).toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={notas.moedas}
                    onChange={(e) => setNotas({...notas, moedas: parseFloat(e.target.value) || 0})}
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
                    placeholder="0.00"
                  />
                </div>
              </div>

              {/* Total */}
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-4 mb-4 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-white font-semibold text-sm">TOTAL CONTADO</span>
                  <span className="text-3xl font-bold text-white">
                    R$ {calcularTotalNotas().toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Botões */}
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={limparContagem}
                  className="flex-1 px-4 py-3 border-2 border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-semibold transition-colors"
                >
                  🗑️ Limpar
                </button>
                <button
                  type="button"
                  onClick={aplicarContagem}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-semibold shadow-md transition-colors"
                >
                  ✓ Aplicar
                </button>
              </div>
            </div>
          )}

          {/* Campo de Valor de Abertura */}
          <div className="relative mt-2">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
              R$
            </span>
            <input
              type="number"
              step="0.01"
              value={valorAbertura}
              onChange={(e) => setValorAbertura(e.target.value)}
              placeholder="0,00"
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-lg font-semibold"
              autoFocus
            />
          </div>

          {/* Conta de Origem */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Conta de Origem
            </label>
            <select
              value={contaOrigem}
              onChange={(e) => setContaOrigem(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="Dinheiro em mãos">Dinheiro em mãos</option>
              <option value="Caixa geral">Caixa geral</option>
              <option value="Banco">Banco</option>
            </select>
          </div>

          {/* Observações */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observações (opcional)
            </label>
            <textarea
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              rows={3}
              placeholder="Ex: Troco do dia anterior..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50">
          {erro && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm">{erro}</span>
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>

            <button
              onClick={handleAbrirCaixa}
              disabled={loading || !valorAbertura}
              className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Abrindo...' : 'Abrir Caixa'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
