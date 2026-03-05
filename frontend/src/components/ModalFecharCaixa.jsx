import { useState, useEffect } from 'react';
import { X, DollarSign, TrendingUp, TrendingDown, Receipt, Calculator, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { fecharCaixa, obterResumoCaixa, obterVendasCaixa } from '../api/caixa';
import CurrencyInput from './CurrencyInput';

export default function ModalFecharCaixa({ caixaId, onClose, onSuccess }) {
  const [resumo, setResumo] = useState(null);
  const [valorContado, setValorContado] = useState(0);
  const [observacoes, setObservacoes] = useState('');
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [mostrarContagem, setMostrarContagem] = useState(false);
  const [formaExpandida, setFormaExpandida] = useState(null);
  const [vendasDetalhe, setVendasDetalhe] = useState({});
  const [loadingVendas, setLoadingVendas] = useState(null);
  const [confirmandoDiferenca, setConfirmandoDiferenca] = useState(false);
  const [mostrarDicasDiferenca, setMostrarDicasDiferenca] = useState(false);
  const [notas, setNotas] = useState({
    n100: '',
    n50: '',
    n20: '',
    n10: '',
    n5: '',
    n2: '',
    moedas: ''
  });

  useEffect(() => {
    carregarResumo();
  }, [caixaId]);

  const carregarResumo = async () => {
    try {
      const data = await obterResumoCaixa(caixaId);
      setResumo(data);
      // Campo vazio — o funcionário deve contar e preencher manualmente
      setValorContado(0);
    } catch (error) {
      console.error('Erro ao carregar resumo:', error);
      setErro('Não foi possível carregar os dados do caixa. Feche e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const calcularDiferenca = () => {
    if (!resumo || !valorContado) return 0;
    return valorContado - resumo.totais.saldo_atual;
  };

  const calcularTotalNotas = () => {
    return (
      (parseInt(notas.n100) || 0) * 100 +
      (parseInt(notas.n50) || 0) * 50 +
      (parseInt(notas.n20) || 0) * 20 +
      (parseInt(notas.n10) || 0) * 10 +
      (parseInt(notas.n5) || 0) * 5 +
      (parseInt(notas.n2) || 0) * 2 +
      parseFloat(notas.moedas || 0)
    );
  };

  const carregarVendasForma = async (forma) => {
    if (formaExpandida === forma) {
      setFormaExpandida(null);
      return;
    }
    setFormaExpandida(forma);
    if (vendasDetalhe[forma]) return;
    setLoadingVendas(forma);
    try {
      const data = await obterVendasCaixa(caixaId, forma);
      setVendasDetalhe(prev => ({ ...prev, [forma]: data }));
    } catch (err) {
      console.error('Erro ao carregar vendas:', err);
      setVendasDetalhe(prev => ({ ...prev, [forma]: [] }));
    } finally {
      setLoadingVendas(null);
    }
  };

  const aplicarContagem = () => {
    const total = calcularTotalNotas();
    setValorContado(total);
    setMostrarContagem(false);
  };

  const limparContagem = () => {
    setNotas({
      n100: '',
      n50: '',
      n20: '',
      n10: '',
      n5: '',
      n2: '',
      moedas: ''
    });
  };

  const handleFechar = async () => {
    if (!(valorContado > 0)) {
      setErro('Informe o valor contado no caixa');
      return;
    }

    const dif = calcularDiferenca();
    if (Math.abs(dif) > 0.01 && !confirmandoDiferenca) {
      setConfirmandoDiferenca(true);
      return;
    }

    await executarFechamento();
  };

  const executarFechamento = async () => {
    setSalvando(true);
    setErro(null);
    try {
      await fecharCaixa(caixaId, {
        valor_informado: valorContado,
        observacoes_fechamento: observacoes || null
      });
      
      setSucesso(true);
      // Aguarda 1s mostrando sucesso antes de fechar
      setTimeout(() => {
        onSuccess();
      }, 800);
    } catch (error) {
      console.error('Erro ao fechar caixa:', error);
      const mensagem = error.response?.data?.detail || 'Erro ao fechar caixa. Tente novamente.';
      setErro(mensagem);
    } finally {
      setSalvando(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!resumo) {
    return null;
  }

  const diferenca = calcularDiferenca();

  return (
    <>
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-red-600 to-orange-600 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold flex items-center">
                <Receipt className="w-7 h-7 mr-3" />
                Fechar Caixa
              </h2>
              <p className="text-red-100 mt-1">
                Caixa #{resumo.caixa.numero_caixa} - {resumo.caixa.usuario_nome}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Conteúdo */}
        <div className="p-6 space-y-6">
          {/* Resumo do Caixa */}
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-6 border-2 border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <Calculator className="w-5 h-5 mr-2 text-gray-700" />
                Resumo do Movimento
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Abertura */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="text-sm text-gray-600 mb-1">Valor de Abertura</div>
                <div className="text-2xl font-bold text-gray-900">
                  R$ {resumo.caixa.valor_abertura.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(resumo.caixa.data_abertura).toLocaleString('pt-BR')}
                </div>
              </div>

              {/* Entradas (renomeado de Vendas) */}
              <div className="bg-white rounded-lg p-4 border border-green-200">
                <div className="flex items-center text-sm text-green-700 mb-1">
                  <Receipt className="w-4 h-4 mr-1" />
                  Entradas
                </div>
                <div className="text-2xl font-bold text-green-600">
                  + R$ {resumo.totais.vendas.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Movimento de entrada
                </div>
              </div>

              {/* Suprimentos */}
              <div className="bg-white rounded-lg p-4 border border-blue-200">
                <div className="flex items-center text-sm text-blue-700 mb-1">
                  <TrendingUp className="w-4 h-4 mr-1" />
                  Suprimentos
                </div>
                <div className="text-2xl font-bold text-blue-600">
                  + R$ {resumo.totais.suprimentos.toFixed(2)}
                </div>
              </div>

              {/* Sangrias */}
              <div className="bg-white rounded-lg p-4 border border-orange-200">
                <div className="flex items-center text-sm text-orange-700 mb-1">
                  <TrendingDown className="w-4 h-4 mr-1" />
                  Sangrias
                </div>
                <div className="text-2xl font-bold text-orange-600">
                  - R$ {resumo.totais.sangrias.toFixed(2)}
                </div>
              </div>

              {/* Despesas */}
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <div className="flex items-center text-sm text-red-700 mb-1">
                  <DollarSign className="w-4 h-4 mr-1" />
                  Despesas
                </div>
                <div className="text-2xl font-bold text-red-600">
                  - R$ {resumo.totais.despesas.toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          {/* Valor Contado */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-semibold text-gray-900">
                Valor Contado no Caixa *
              </label>
              <button
                type="button"
                onClick={() => setMostrarContagem(!mostrarContagem)}
                className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors border border-blue-200"
                title="Auxiliar na contagem de notas"
              >
                <Calculator className="w-4 h-4" />
                <span>Auxiliar Contagem</span>
              </button>
            </div>

            {/* Painel de Contagem de Notas */}
            {mostrarContagem && (
              <div className="mt-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-base font-bold text-gray-900 flex items-center">
                    <Calculator className="w-5 h-5 mr-2 text-blue-600" />
                    Auxiliar de Contagem
                  </h4>
                  <button
                    onClick={() => setMostrarContagem(false)}
                    className="text-gray-400 hover:text-gray-600 p-1"
                  >
                    <X className="w-5 h-5" />
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
                          value={notas.n2}
                          onChange={(e) => setNotas({...notas, n2: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-gray-500 focus:ring-2 focus:ring-gray-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-gray-600">
                        R$ {((parseInt(notas.n2) || 0) * 2).toFixed(2)}
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
                          value={notas.n5}
                          onChange={(e) => setNotas({...notas, n5: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-purple-600">
                        R$ {((parseInt(notas.n5) || 0) * 5).toFixed(2)}
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
                          value={notas.n10}
                          onChange={(e) => setNotas({...notas, n10: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-red-500 focus:ring-2 focus:ring-red-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-red-600">
                        R$ {((parseInt(notas.n10) || 0) * 10).toFixed(2)}
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
                          value={notas.n20}
                          onChange={(e) => setNotas({...notas, n20: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-yellow-500 focus:ring-2 focus:ring-yellow-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-yellow-600">
                        R$ {((parseInt(notas.n20) || 0) * 20).toFixed(2)}
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
                          value={notas.n50}
                          onChange={(e) => setNotas({...notas, n50: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-blue-600">
                        R$ {((parseInt(notas.n50) || 0) * 50).toFixed(2)}
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
                          value={notas.n100}
                          onChange={(e) => setNotas({...notas, n100: e.target.value})}
                          className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-green-500 focus:ring-2 focus:ring-green-200"
                          placeholder=""
                        />
                        <span className="text-xs text-gray-500">×</span>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        R$ {((parseInt(notas.n100) || 0) * 100).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Moedas */}
                <div className="mt-4 pt-4 border-t-2 border-blue-300">
                  <div className="bg-white rounded-lg p-4 border-2 border-amber-200 hover:border-amber-400 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="bg-gradient-to-br from-amber-500 to-amber-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                          💰 Moedas
                        </div>
                        <input
                          type="number"
                          step="0.01"
                          value={notas.moedas}
                          onChange={(e) => setNotas({...notas, moedas: e.target.value})}
                          className="w-32 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
                          placeholder=""
                        />
                      </div>
                      <span className="text-lg font-bold text-amber-600">
                        R$ {(parseFloat(notas.moedas) || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Total e Botões */}
                <div className="mt-5 pt-5 border-t-2 border-blue-300">
                  <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-4 mb-4 shadow-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-semibold text-sm">TOTAL CONTADO</span>
                      <span className="text-3xl font-bold text-white">
                        R$ {calcularTotalNotas().toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="flex space-x-3">
                    <button
                      type="button"
                      onClick={limparContagem}
                      className="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-semibold transition-colors"
                    >
                      🗑️ Limpar
                    </button>
                    <button
                      type="button"
                      onClick={aplicarContagem}
                      className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 font-bold shadow-md transition-all"
                    >
                      ✓ Aplicar
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            <div className="relative">
              <DollarSign className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <CurrencyInput
                value={valorContado}
                onChange={setValorContado}
                className="w-full pl-10 pr-4 py-3 text-lg font-semibold border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0,00"
                autoFocus
              />
            </div>

            {/* Diferença */}
            {!!valorContado && Math.abs(diferenca) > 0.01 && (
              <button
                type="button"
                onClick={() => setMostrarDicasDiferenca(true)}
                className={`mt-3 w-full p-4 rounded-lg border-2 text-left hover:opacity-90 transition-opacity ${
                  diferenca > 0
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-yellow-50 border-yellow-300'
                }`}
                title="Clique para ver possíveis causas"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900">
                    {diferenca > 0 ? '⚠️ Sobra' : '⚠️ Falta'}:
                  </span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xl font-bold ${
                      diferenca > 0 ? 'text-blue-600' : 'text-yellow-700'
                    }`}>
                      R$ {Math.abs(diferenca).toFixed(2)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      diferenca > 0 ? 'bg-blue-200 text-blue-800' : 'bg-yellow-200 text-yellow-800'
                    }`}>
                      Ver possíveis causas →
                    </span>
                  </div>
                </div>
              </button>
            )}

            {!!valorContado && Math.abs(diferenca) <= 0.01 && (
              <div className="mt-3 p-4 rounded-lg border-2 bg-green-50 border-green-300">
                <div className="flex items-center justify-center space-x-2 text-green-700 font-semibold">
                  <span className="text-2xl">✓</span>
                  <span>Caixa conferido - Valores corretos!</span>
                </div>
              </div>
            )}
          </div>

          {/* Observações */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Observações (opcional)
            </label>
            <textarea
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Adicione observações sobre o fechamento..."
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
          </div>

          {/* 📊 Vendas por Forma de Pagamento - INFORMATIVO */}
          {resumo.vendas_por_forma_pagamento && Object.keys(resumo.vendas_por_forma_pagamento).length > 0 && (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
              <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center">
                <Receipt className="w-4 h-4 mr-1.5 text-blue-600" />
                Vendas por Forma de Pagamento (Informativo)
              </h4>
              
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(resumo.vendas_por_forma_pagamento).map(([forma, dados]) => {
                  const ehDinheiro = forma === 'Dinheiro';
                  return (
                    <div 
                      key={forma} 
                      className={`bg-white rounded-lg p-3 border ${
                        formaExpandida === forma
                          ? 'border-blue-400 bg-blue-50 shadow-md'
                          : ehDinheiro ? 'border-green-300 bg-green-50' : 'border-gray-200'
                      } hover:shadow-sm transition-shadow cursor-pointer select-none`}
                      title="Clique para ver detalhes das vendas"
                      onClick={() => carregarVendasForma(forma)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 rounded-full ${
                              forma === 'Dinheiro' ? 'bg-green-500' :
                              forma === 'PIX' ? 'bg-purple-500' :
                              forma.includes('Débito') ? 'bg-blue-500' :
                              forma.includes('Crédito') ? 'bg-orange-500' :
                              'bg-gray-400'
                            }`}></div>
                            <span className="text-xs font-semibold text-gray-700">{forma}</span>
                            {ehDinheiro && (
                              <span className="text-xs bg-green-600 text-white px-1.5 py-0.5 rounded">CAIXA</span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">{dados.quantidade} venda{dados.quantidade !== 1 ? 's' : ''}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-gray-900">
                            R$ {dados.total.toFixed(2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Painel de detalhes das vendas por forma */}
              {formaExpandida && (
                <div className="mt-3 border-t border-blue-200 pt-3">
                  <div className="flex items-center justify-between mb-2">
                    <h5 className="text-xs font-bold text-gray-700">Vendas — {formaExpandida}</h5>
                    <button
                      onClick={() => setFormaExpandida(null)}
                      className="text-xs text-gray-400 hover:text-gray-600"
                    >✕ fechar</button>
                  </div>
                  {loadingVendas === formaExpandida ? (
                    <div className="text-xs text-gray-500 py-2">Carregando...</div>
                  ) : (
                    <div className="space-y-1 max-h-44 overflow-y-auto">
                      {(vendasDetalhe[formaExpandida] || []).length === 0 ? (
                        <div className="text-xs text-gray-400">Nenhuma venda encontrada.</div>
                      ) : (
                        (vendasDetalhe[formaExpandida] || []).map(v => (
                          <div key={v.id} className="flex justify-between items-center text-xs py-1.5 px-2 rounded bg-white border border-gray-100">
                            <div>
                              <span className="font-semibold text-gray-700">{v.numero_venda}</span>
                              <span className="text-gray-500 ml-1.5">{v.cliente_nome || 'Consumidor'}</span>
                            </div>
                            <div className="text-right">
                              <span className="text-gray-400 mr-2">{v.hora_venda}</span>
                              <span className="font-bold text-gray-800">R$ {(v.valor_nesta_forma ?? v.total).toFixed(2)}</span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="mt-3 pt-3 border-t border-blue-200 text-xs text-gray-600">
                💡 <strong>Dica:</strong> Apenas <strong>Dinheiro</strong> afeta o saldo físico do caixa. Demais formas vão para banco/financeiro.
              </div>
            </div>
          )}

          {/* Mensagem de erro da API */}
          {erro && (
            <div className="bg-red-50 border-2 border-red-400 rounded-xl p-4 flex items-start space-x-3">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-red-800 text-sm mb-1">Não foi possível fechar o caixa</div>
                <div className="text-red-700 text-sm">{erro}</div>
              </div>
            </div>
          )}

          {/* Mensagem de sucesso */}
          {sucesso && (
            <div className="bg-green-50 border-2 border-green-400 rounded-xl p-4 flex items-center space-x-3">
              <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
              <div className="font-bold text-green-800">Caixa fechado com sucesso!</div>
            </div>
          )}

          {/* Botões / Confirmação de diferença */}
          {confirmandoDiferenca ? (
            <div className="pt-4 border-t">
              <div className="bg-amber-50 border-2 border-amber-400 rounded-xl p-4 mb-3">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-amber-800">Diferença de caixa detectada</div>
                    <div className="text-amber-700 text-sm mt-1">
                      Existe uma diferença de{' '}
                      <strong>R$ {Math.abs(calcularDiferenca()).toFixed(2)}</strong>{' '}
                      <strong>{calcularDiferenca() > 0 ? 'a mais' : 'a menos'}</strong>{' '}no caixa.
                      A diferença ficará registrada no histórico.
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setConfirmandoDiferenca(false)}
                  disabled={salvando}
                  className="flex-1 px-4 py-3 border-2 border-amber-300 text-amber-700 rounded-lg hover:bg-amber-100 font-semibold transition-colors disabled:opacity-50"
                >
                  Voltar e corrigir
                </button>
                <button
                  type="button"
                  onClick={executarFechamento}
                  disabled={salvando}
                  className="flex-1 px-4 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
                >
                  {salvando ? (
                    <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div><span>Fechando...</span></>
                  ) : (
                    <><AlertTriangle className="w-4 h-4" /><span>Sim, fechar com diferença</span></>
                  )}
                </button>
              </div>
            </div>
          ) : (
          <div className="flex items-center justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={salvando}
              className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancelar
            </button>
            <button
              onClick={handleFechar}
              disabled={salvando || valorContado <= 0}
              className="px-8 py-3 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {salvando ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Fechando...</span>
                </>
              ) : (
                <>
                  <Receipt className="w-5 h-5" />
                  <span>Fechar Caixa</span>
                </>
              )}
            </button>
          </div>
          )}
        </div>
      </div>
    </div>

    {/* Modal de Dicas de Diferença */}
    {mostrarDicasDiferenca && (
      <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[60] p-4">
        <div className="bg-white rounded-xl w-full max-w-lg max-h-[85vh] overflow-y-auto shadow-2xl">
          <div className={`p-5 rounded-t-xl text-white ${diferenca > 0 ? 'bg-blue-600' : 'bg-yellow-600'}`}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold">
                  {diferenca > 0 ? '💰 Sobrou dinheiro no caixa' : '⚠️ Faltou dinheiro no caixa'}
                </h3>
                <p className="text-sm opacity-90 mt-0.5">
                  Diferença de R$ {Math.abs(diferenca).toFixed(2)} — possíveis causas
                </p>
              </div>
              <button onClick={() => setMostrarDicasDiferenca(false)} className="p-1 hover:bg-white hover:bg-opacity-20 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {diferenca < 0 ? (
              // FALTOU dinheiro
              <>
                <p className="text-sm text-gray-600">
                  O caixa deveria ter <strong>R$ {(resumo?.totais?.saldo_atual ?? 0).toFixed(2)}</strong>, mas você contou <strong>R$ {valorContado.toFixed(2)}</strong>. Alguém saiu com dinheiro que não foi registrado, ou houve um erro de registro. Veja as causas mais comuns:
                </p>

                <div className="space-y-3">
                  <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="font-semibold text-yellow-800 text-sm mb-1">💸 Troco dado a mais</div>
                    <div className="text-xs text-yellow-700">O funcionário pode ter calculado errado o troco em alguma venda em dinheiro e devolvido mais do que devia. Verifique as vendas em dinheiro do dia e confira se os valores batem com o que foi recebido.</div>
                  </div>

                  <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="font-semibold text-yellow-800 text-sm mb-1">🏷️ Forma de pagamento lançada errada</div>
                    <div className="text-xs text-yellow-700">Uma venda pode ter sido registrada como "Dinheiro", mas o cliente pagou no cartão ou PIX. Nesse caso, o caixa esperava receber aquele valor em espécie, mas não recebeu. Verifique as vendas em dinheiro e confirme com o cliente ou pelo extrato do maquininha.</div>
                  </div>

                  <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="font-semibold text-yellow-800 text-sm mb-1">📋 Despesa paga sem lançar no caixa</div>
                    <div className="text-xs text-yellow-700">Alguém pode ter pago uma despesa (fornecedor, frete, material) com o dinheiro do caixa sem registrar como "Despesa". O dinheiro saiu fisicamente mas o sistema não sabe. Pergunte à equipe se houve algum pagamento assim.</div>
                  </div>

                  <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="font-semibold text-yellow-800 text-sm mb-1">🔄 Sangria não registrada</div>
                    <div className="text-xs text-yellow-700">Dinheiro pode ter sido retirado do caixa sem passar pelo fluxo de Sangria no sistema. Pergunte se alguém retirou dinheiro para troco ou outro fim sem registrar.</div>
                  </div>

                  <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="font-semibold text-yellow-800 text-sm mb-1">🔢 Erro na contagem</div>
                    <div className="text-xs text-yellow-700">Recomendamos contar o dinheiro uma segunda vez, separando por cédula (R$ 100, R$ 50, R$ 20, R$ 10, R$ 5, R$ 2) e somando as moedas por fim. Use o auxiliar de contagem desta tela.</div>
                  </div>
                </div>
              </>
            ) : (
              // SOBROU dinheiro
              <>
                <p className="text-sm text-gray-600">
                  O caixa deveria ter <strong>R$ {(resumo?.totais?.saldo_atual ?? 0).toFixed(2)}</strong>, mas você contou <strong>R$ {valorContado.toFixed(2)}</strong>. Entrou mais dinheiro do que foi registrado. Veja as causas mais comuns:
                </p>

                <div className="space-y-3">
                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="font-semibold text-blue-800 text-sm mb-1">📥 Venda recebida mas não registrada</div>
                    <div className="text-xs text-blue-700">O cliente pagou em dinheiro, mas a venda não foi fechada no sistema. O dinheiro entrou no caixa físico sem que o sistema soubesse. Verifique se há vendas em aberto ou atendimentos que não foram finalizados.</div>
                  </div>

                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="font-semibold text-blue-800 text-sm mb-1">💳 Forma de pagamento lançada errada</div>
                    <div className="text-xs text-blue-700">Uma venda foi registrada como cartão ou PIX, mas o cliente pagou em dinheiro. O sistema não contou esse valor como dinheiro no caixa. Confira as vendas do dia e veja se todas as formas de pagamento foram registradas corretamente.</div>
                  </div>

                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="font-semibold text-blue-800 text-sm mb-1">💰 Troco dado a menos</div>
                    <div className="text-xs text-blue-700">O funcionário pode ter devolvido menos troco do que devia em alguma venda. O dinheiro ficou no caixa, mas o cliente levou menos do que era correto. Vale revisar as vendas com pagamento em dinheiro.</div>
                  </div>

                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="font-semibold text-blue-800 text-sm mb-1">📋 Suprimento não registrado</div>
                    <div className="text-xs text-blue-700">Alguém pode ter colocado dinheiro no caixa (para troco ou reforço) sem registrar como Suprimento no sistema. Pergunte se houve alguma entrada de dinheiro que não foi registrada.</div>
                  </div>

                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="font-semibold text-blue-800 text-sm mb-1">🔢 Erro na contagem</div>
                    <div className="text-xs text-blue-700">Recomendamos contar o dinheiro uma segunda vez, separando por cédula (R$ 100, R$ 50, R$ 20, R$ 10, R$ 5, R$ 2) e somando as moedas por fim. Use o auxiliar de contagem desta tela.</div>
                  </div>
                </div>
              </>
            )}

            <div className="pt-3 border-t">
              <button
                onClick={() => setMostrarDicasDiferenca(false)}
                className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-900 text-white rounded-lg font-semibold transition-colors"
              >
                Entendi — voltar ao fechamento
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
