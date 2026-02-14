import React, { useState, useEffect } from 'react';
import { Sparkles, AlertCircle, CheckCircle, XCircle, RefreshCw, Info } from 'lucide-react';
import api from '../api';
import toast from 'react-hot-toast';

/**
 * Componente para Classificação Inteligente de Rações
 * Mostra campos IA e permite classificação automática
 */
function ClassificacaoRacaoIA({ produtoId, nomeProduto, onAtualizar }) {
  const [classificacao, setClassificacao] = useState(null);
  const [loading, setLoading] = useState(false);
  const [classificandoIA, setClassificandoIA] = useState(false);

  useEffect(() => {
    if (produtoId) {
      carregarClassificacao();
    }
  }, [produtoId]);

  const carregarClassificacao = async () => {
    if (!produtoId) return;
    
    try {
      const response = await api.get(`/produtos/${produtoId}`);
      const produto = response.data;
      
      setClassificacao({
        porte_animal: produto.porte_animal || [],
        fase_publico: produto.fase_publico || [],
        tipo_tratamento: produto.tipo_tratamento || [],
        sabor_proteina: produto.sabor_proteina || '',
        peso_embalagem: produto.peso_embalagem || null,
        auto_classificar_nome: produto.auto_classificar_nome !== false
      });
    } catch (error) {
      console.error('Erro ao carregar classificação:', error);
    }
  };

  const classificarIA = async () => {
    if (!produtoId) {
      toast.error('Salve o produto antes de classificar com IA');
      return;
    }

    setClassificandoIA(true);
    try {
      const response = await api.post(`/produtos/${produtoId}/classificar-ia`, null, {
        params: { forcar: true }
      });

      toast.success(
        `✨ ${response.data.campos_atualizados.length} campos identificados! Score: ${response.data.confianca.score}%`,
        { duration: 5000 }
      );

      // Atualizar estado local
      await carregarClassificacao();
      
      // Notificar componente pai para recarregar
      if (onAtualizar) {
        onAtualizar();
      }

    } catch (error) {
      console.error('Erro ao classificar:', error);
      const mensagem = error.response?.data?.detail || 'Erro ao classificar produto';
      toast.error(mensagem);
    } finally {
      setClassificandoIA(false);
    }
  };

  if (!classificacao) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-gray-500">Carregando informações de ração...</p>
      </div>
    );
  }

  const calcularCompletude = () => {
    const campos = [
      classificacao.porte_animal?.length > 0,
      classificacao.fase_publico?.length > 0,
      classificacao.sabor_proteina,
      classificacao.peso_embalagem
    ];
    const preenchidos = campos.filter(Boolean).length;
    return Math.round((preenchidos / campos.length) * 100);
  };

  const completude = calcularCompletude();

  const getStatusCompletude = () => {
    if (completude === 100) return { cor: 'bg-green-100 text-green-800', icone: CheckCircle, texto: 'Completo' };
    if (completude >= 75) return { cor: 'bg-yellow-100 text-yellow-800', icone: AlertCircle, texto: 'Quase completo' };
    if (completude >= 50) return { cor: 'bg-orange-100 text-orange-800', icone: AlertCircle, texto: 'Incompleto' };
    return { cor: 'bg-red-100 text-red-800', icone: XCircle, texto: 'Muito incompleto' };
  };

  const status = getStatusCompletude();
  const Icone = status.icone;

  return (
    <div className="space-y-4">
      {/* Header com Status e Botão IA */}
      <div className="flex items-center justify-between bg-gradient-to-r from-indigo-50 to-purple-50 p-4 rounded-lg border border-indigo-200">
        <div className="flex items-center gap-3">
          <Sparkles className="w-6 h-6 text-indigo-600" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800">
              Classificação Inteligente de Ração
            </h3>
            <p className="text-sm text-gray-600">
              Análise automática baseada no nome do produto
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${status.cor}`}>
            <Icone className="w-5 h-5" />
            <div>
              <p className="text-xs font-medium">{status.texto}</p>
              <p className="text-lg font-bold">{completude}%</p>
            </div>
          </div>

          <button
            onClick={classificarIA}
            disabled={classificandoIA || !nomeProduto}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
          >
            {classificandoIA ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                Classificando...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Classificar com IA
              </>
            )}
          </button>
        </div>
      </div>

      {/* Informação sobre o nome do produto */}
      {nomeProduto && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-blue-900">Nome sendo analisado:</p>
            <p className="text-blue-700 font-mono">{nomeProduto}</p>
          </div>
        </div>
      )}

      {/* Grid de Campos Classificados */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Porte Animal */}
        <div className="bg-white border rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Porte do Animal
          </label>
          {classificacao.porte_animal && classificacao.porte_animal.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {classificacao.porte_animal.map((porte, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium"
                >
                  {porte}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 italic text-sm">Não identificado</p>
          )}
        </div>

        {/* Fase/Público */}
        <div className="bg-white border rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Fase / Público
          </label>
          {classificacao.fase_publico && classificacao.fase_publico.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {classificacao.fase_publico.map((fase, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium"
                >
                  {fase}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 italic text-sm">Não identificado</p>
          )}
        </div>

        {/* Sabor/Proteína */}
        <div className="bg-white border rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sabor / Proteína Principal
          </label>
          {classificacao.sabor_proteina ? (
            <span className="inline-flex px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium">
              {classificacao.sabor_proteina}
            </span>
          ) : (
            <p className="text-gray-400 italic text-sm">Não identificado</p>
          )}
        </div>

        {/* Peso Embalagem */}
        <div className="bg-white border rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Peso da Embalagem
          </label>
          {classificacao.peso_embalagem ? (
            <span className="inline-flex px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
              {classificacao.peso_embalagem} kg
            </span>
          ) : (
            <p className="text-gray-400 italic text-sm">Não identificado</p>
          )}
        </div>
      </div>

      {/* Tratamentos Especiais */}
      {classificacao.tipo_tratamento && classificacao.tipo_tratamento.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tratamentos Especiais
          </label>
          <div className="flex flex-wrap gap-2">
            {classificacao.tipo_tratamento.map((tratamento, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-rose-100 text-rose-800 rounded-full text-sm font-medium"
              >
                {tratamento}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Rodapé com Informações */}
      <div className="bg-gray-50 border rounded-lg p-4 text-sm text-gray-600">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium text-gray-700 mb-1">Como funciona:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>A IA analisa o nome do produto e identifica automaticamente características</li>
              <li>Suporta múltiplas classificações (ex: "Todas as raças")</li>
              <li>Os campos são atualizados apenas se identificados com confiança</li>
              <li>Você pode reclassificar a qualquer momento clicando em "Classificar com IA"</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ClassificacaoRacaoIA;
