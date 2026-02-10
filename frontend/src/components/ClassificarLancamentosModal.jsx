import React, { useState, useEffect } from 'react';
import { 
  FiX, FiCheck, FiAlertCircle, FiDollarSign, FiCalendar, 
  FiZap, FiLoader, FiCheckCircle, FiXCircle, FiFilter 
} from 'react-icons/fi';
import api from '../api';
import { toast } from 'react-hot-toast';

const ClassificarLancamentosModal = ({ isOpen, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [pendentes, setPendentes] = useState({ contas_pagar: [], contas_receber: [] });
  const [sugestoes, setSugestoes] = useState({});
  const [classificados, setClassificados] = useState(new Set());
  const [filtro, setFiltro] = useState('todos'); // todos, pagar, receber
  const [autoClassificando, setAutoClassificando] = useState(false);

  useEffect(() => {
    if (isOpen) {
      carregarPendentes();
    }
  }, [isOpen]);

  const carregarPendentes = async () => {
    setLoading(true);
    try {
      const response = await api.get('/dre/classificar/pendentes', {
        params: { limit: 100 }
      });
      
      setPendentes(response.data);
      
      // Buscar sugestões para cada lançamento
      await carregarSugestoes(response.data);
      
      toast.success(`${response.data.total_pendentes} lançamentos pendentes encontrados`);
    } catch (error) {
      console.error('Erro ao carregar pendentes:', error);
      toast.error('Erro ao carregar lançamentos pendentes');
    } finally {
      setLoading(false);
    }
  };

  const carregarSugestoes = async (dados) => {
    const novasSugestoes = {};
    
    // Buscar sugestões para contas a pagar
    for (const cp of dados.contas_pagar) {
      try {
        const response = await api.post('/dre/classificar/sugerir', {
          tipo: 'pagar',
          lancamento_id: cp.id
        });
        novasSugestoes[`pagar_${cp.id}`] = response.data;
      } catch (error) {
        console.error(`Erro ao buscar sugestões para pagar #${cp.id}:`, error);
        novasSugestoes[`pagar_${cp.id}`] = [];
      }
    }
    
    // Buscar sugestões para contas a receber
    for (const cr of dados.contas_receber) {
      try {
        const response = await api.post('/dre/classificar/sugerir', {
          tipo: 'receber',
          lancamento_id: cr.id
        });
        novasSugestoes[`receber_${cr.id}`] = response.data;
      } catch (error) {
        console.error(`Erro ao buscar sugestões para receber #${cr.id}:`, error);
        novasSugestoes[`receber_${cr.id}`] = [];
      }
    }
    
    setSugestoes(novasSugestoes);
  };

  const aplicarClassificacao = async (tipo, lancamentoId, sugestao) => {
    setProcessando(true);
    try {
      await api.post('/dre/classificar/aplicar', {
        tipo,
        lancamento_id: lancamentoId,
        dre_subcategoria_id: sugestao.dre_subcategoria_id,
        canal: null, // Será inferido do lançamento
        regra_id: sugestao.regra_id,
        forma_classificacao: 'sugestao_aceita'
      });
      
      // Marcar como classificado
      setClassificados(prev => new Set([...prev, `${tipo}_${lancamentoId}`]));
      
      toast.success(`✅ Classificado: ${sugestao.subcategoria_nome}`);
    } catch (error) {
      console.error('Erro ao aplicar classificação:', error);
      toast.error('Erro ao aplicar classificação');
    } finally {
      setProcessando(false);
    }
  };

  const autoClassificar = async () => {
    setAutoClassificando(true);
    try {
      const response = await api.post('/dre/classificar/auto-classificar-pendentes', null, {
        params: {
          apenas_alta_confianca: true
        }
      });
      
      toast.success(
        `🤖 Auto-classificação concluída!\n${response.data.total_classificado} de ${response.data.total_processado} lançamentos classificados`,
        { duration: 5000 }
      );
      
      // Recarregar pendentes
      await carregarPendentes();
      
      if (onSuccess) onSuccess();
    } catch (error) {
      console.error('Erro ao auto-classificar:', error);
      toast.error('Erro ao executar auto-classificação');
    } finally {
      setAutoClassificando(false);
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
  };

  const getConfiancaColor = (confianca) => {
    if (confianca >= 90) return 'text-green-600 bg-green-100';
    if (confianca >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const lancamentosFiltrados = () => {
    if (filtro === 'pagar') {
      return pendentes.contas_pagar.map(cp => ({ ...cp, tipo: 'pagar' }));
    } else if (filtro === 'receber') {
      return pendentes.contas_receber.map(cr => ({ ...cr, tipo: 'receber' }));
    } else {
      return [
        ...pendentes.contas_pagar.map(cp => ({ ...cp, tipo: 'pagar' })),
        ...pendentes.contas_receber.map(cr => ({ ...cr, tipo: 'receber' }))
      ];
    }
  };

  const lancamentos = lancamentosFiltrados().filter(
    l => !classificados.has(`${l.tipo}_${l.id}`)
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-t-lg">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              🏷️ Classificar Lançamentos Pendentes
            </h2>
            <p className="text-sm text-purple-100 mt-1">
              {lancamentos.length} lançamentos aguardando classificação DRE
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white hover:bg-opacity-20 p-2 rounded-lg transition-colors"
          >
            <FiX size={24} />
          </button>
        </div>

        {/* Filtros e Ações */}
        <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
          <div className="flex gap-2">
            <button
              onClick={() => setFiltro('todos')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filtro === 'todos'
                  ? 'bg-purple-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              📊 Todos ({pendentes.contas_pagar.length + pendentes.contas_receber.length})
            </button>
            <button
              onClick={() => setFiltro('pagar')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filtro === 'pagar'
                  ? 'bg-red-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              💸 A Pagar ({pendentes.contas_pagar.length})
            </button>
            <button
              onClick={() => setFiltro('receber')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filtro === 'receber'
                  ? 'bg-green-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              💰 A Receber ({pendentes.contas_receber.length})
            </button>
          </div>

          <button
            onClick={autoClassificar}
            disabled={autoClassificando || lancamentos.length === 0}
            className="flex items-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white px-6 py-2 rounded-lg font-medium hover:from-green-700 hover:to-emerald-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
          >
            {autoClassificando ? (
              <>
                <FiLoader className="animate-spin" size={20} />
                Auto-Classificando...
              </>
            ) : (
              <>
                <FiZap size={20} />
                Auto-Classificar (Alta Confiança)
              </>
            )}
          </button>
        </div>

        {/* Lista de Lançamentos */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <FiLoader className="animate-spin text-purple-600" size={48} />
            </div>
          ) : lancamentos.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <FiCheckCircle size={64} className="text-green-500 mb-4" />
              <p className="text-xl font-semibold">Nenhum lançamento pendente!</p>
              <p className="text-sm mt-2">Todos os lançamentos foram classificados.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {lancamentos.map((lancamento) => {
                const key = `${lancamento.tipo}_${lancamento.id}`;
                const sugestoesLancamento = sugestoes[key] || [];
                const melhorSugestao = sugestoesLancamento[0];

                return (
                  <div
                    key={key}
                    className="border border-gray-200 rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow"
                  >
                    {/* Cabeçalho do Lançamento */}
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-bold ${
                              lancamento.tipo === 'pagar'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-green-100 text-green-700'
                            }`}
                          >
                            {lancamento.tipo === 'pagar' ? '💸 A Pagar' : '💰 A Receber'}
                          </span>
                          <span className="text-sm text-gray-500">
                            #{lancamento.id}
                          </span>
                        </div>
                        <h3 className="font-semibold text-gray-800 text-lg mb-1">
                          {lancamento.descricao}
                        </h3>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          {lancamento.beneficiario && (
                            <span className="flex items-center gap-1">
                              👤 {lancamento.beneficiario}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <FiDollarSign size={14} />
                            {formatarMoeda(lancamento.valor)}
                          </span>
                          <span className="flex items-center gap-1">
                            <FiCalendar size={14} />
                            {formatarData(lancamento.data_vencimento)}
                          </span>
                          {lancamento.tipo_documento && (
                            <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                              {lancamento.tipo_documento}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Sugestões */}
                    {sugestoesLancamento.length === 0 ? (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-center gap-2">
                        <FiAlertCircle className="text-yellow-600" size={20} />
                        <span className="text-sm text-yellow-700">
                          Nenhuma sugestão automática. Classifique manualmente.
                        </span>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-xs font-semibold text-gray-600 uppercase mb-2">
                          🤖 Sugestões de Classificação:
                        </p>
                        {sugestoesLancamento.slice(0, 3).map((sugestao, index) => (
                          <div
                            key={index}
                            className={`flex justify-between items-center p-3 rounded-lg border-2 ${
                              index === 0
                                ? 'border-purple-300 bg-purple-50'
                                : 'border-gray-200 bg-gray-50'
                            }`}
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-gray-800">
                                  {sugestao.subcategoria_nome}
                                </span>
                                <span
                                  className={`px-2 py-1 rounded-full text-xs font-bold ${getConfiancaColor(
                                    sugestao.confianca
                                  )}`}
                                >
                                  {sugestao.confianca}% confiança
                                </span>
                                {index === 0 && (
                                  <span className="px-2 py-1 bg-purple-600 text-white rounded-full text-xs font-bold">
                                    ⭐ Melhor
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-600">
                                {sugestao.motivo}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                Regra: {sugestao.regra_nome}
                              </p>
                            </div>
                            <button
                              onClick={() =>
                                aplicarClassificacao(lancamento.tipo, lancamento.id, sugestao)
                              }
                              disabled={processando}
                              className="ml-4 flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <FiCheck size={18} />
                              Aceitar
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-between items-center rounded-b-lg">
          <div className="text-sm text-gray-600">
            <span className="font-semibold">{classificados.size}</span> classificados nesta sessão
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (classificados.size > 0 && onSuccess) {
                  onSuccess();
                }
                onClose();
              }}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
            >
              Fechar
            </button>
            {classificados.size > 0 && (
              <button
                onClick={carregarPendentes}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
              >
                Atualizar Lista
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClassificarLancamentosModal;
