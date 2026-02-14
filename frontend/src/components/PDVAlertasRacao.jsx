import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  X,
  Check,
  ShoppingCart,
  TrendingUp,
  Package,
  Heart,
  Sparkles
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../api';

/**
 * Componente de Alertas e Sugestões Inteligentes para PDV - Fase 5
 * 
 * Features:
 * - Alerta automático de alergia ao adicionar ração
 * - Sugestões de produtos similares
 * - Cross-sell inteligente (comprado junto)
 * - Produtos complementares
 * 
 * @param {number} produtoId - ID do produto sendo adicionado
 * @param {number} clienteId - ID do cliente da venda
 * @param {array} carrinho - Lista de IDs dos produtos no carrinho
 * @param {function} onAddProduto - Callback para adicionar produto ao carrinho
 * @version 1.0.0 (2026-02-14)
 */
const PDVAlertasRacao = ({ 
  produtoId, 
  clienteId, 
  carrinho = [],
  onAddProduto,
  onClose 
}) => {
  // ============================================================================
  // STATES
  // ============================================================================
  
  const [loading, setLoading] = useState(true);
  const [alerta, setAlerta] = useState(null);
  const [sugestoesSimilares, setSugestoesSimilares] = useState([]);
  const [sugestoesCrossSell, setSugestoesCrossSell] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState('alertas');
  
  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  useEffect(() => {
    if (produtoId && clienteId) {
      carregarDados();
    }
  }, [produtoId, clienteId]);
  
  // ============================================================================
  // FUNÇÕES DE CARREGAMENTO
  // ============================================================================
  
  const carregarDados = async () => {
    try {
      setLoading(true);
      
      // Verificar alergia
      if (clienteId) {
        await verificarAlergia();
      }
      
      // Carregar sugestões similares
      await carregarSugestoesSimilares();
      
      // Carregar cross-sell se houver outros produtos no carrinho
      if (carrinho && carrinho.length > 0) {
        await carregarCrossSell();
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      setLoading(false);
    }
  };
  
  const verificarAlergia = async () => {
    try {
      const res = await api.post(
        `/pdv/racoes/verificar-alergia/${produtoId}?cliente_id=${clienteId}`
      );
      
      if (res.data.tem_alerta) {
        setAlerta(res.data);
        setAbaAtiva('alertas'); // Forçar aba de alertas se houver problema
      }
    } catch (error) {
      console.error('Erro ao verificar alergia:', error);
    }
  };
  
  const carregarSugestoesSimilares = async () => {
    try {
      const res = await api.get(`/pdv/racoes/produtos-similares/${produtoId}?limite=5`);
      setSugestoesSimilares(res.data.sugestoes_similares || []);
    } catch (error) {
      console.error('Erro ao carregar sugestões:', error);
    }
  };
  
  const carregarCrossSell = async () => {
    try {
      const produtosIds = [...carrinho, produtoId].join('&produtos_carrinho=');
      const res = await api.post(`/pdv/racoes/cross-sell?produtos_carrinho=${produtosIds}`);
      
      // Achatar sugestões de todos os produtos
      const todasSugestoes = [];
      res.data.forEach(item => {
        item.sugestoes.forEach(sug => {
          // Não adicionar duplicatas
          if (!todasSugestoes.find(s => s.produto_id === sug.produto_id)) {
            todasSugestoes.push(sug);
          }
        });
      });
      
      setSugestoesCrossSell(todasSugestoes);
    } catch (error) {
      console.error('Erro ao carregar cross-sell:', error);
    }
  };
  
  // ============================================================================
  // HANDLERS
  // ============================================================================
  
  const handleAddSugestao = (produto) => {
    if (onAddProduto) {
      onAddProduto(produto.produto_id);
      toast.success(`${produto.nome} adicionado ao carrinho`);
    }
  };
  
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  const renderAlerta = () => {
    if (!alerta || !alerta.tem_alerta) {
      return (
        <div className="text-center py-8">
          <Check className="h-12 w-12 text-green-500 mx-auto mb-3" />
          <p className="text-green-700 font-semibold">Nenhum alerta de alergia</p>
          <p className="text-sm text-gray-600 mt-1">
            Este produto é seguro para os pets do cliente
          </p>
        </div>
      );
    }
    
    return (
      <div className="space-y-4">
        {/* Alerta Principal */}
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-800 font-bold text-lg mb-2">
                {alerta.mensagem}
              </p>
              <p className="text-sm text-red-700">
                <strong>Produto:</strong> {alerta.produto_nome}
              </p>
            </div>
          </div>
        </div>
        
        {/* Pets Afetados */}
        {alerta.pets_afetados && alerta.pets_afetados.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-900 flex items-center gap-2">
              <Heart className="h-5 w-5 text-red-500" />
              Pets Afetados
            </h4>
            
            {alerta.pets_afetados.map((pet, idx) => (
              <div key={idx} className="bg-white border border-red-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-900">{pet.pet_nome}</span>
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                    {pet.pet_especie}
                  </span>
                </div>
                <div className="text-sm text-gray-700">
                  <strong>Alergias:</strong>{' '}
                  {pet.alergias.map((a, i) => (
                    <span key={i} className="inline-block bg-red-100 text-red-800 px-2 py-0.5 rounded mr-1 mb-1">
                      {a}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Recomendação */}
        {sugestoesSimilares.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-900 font-semibold mb-2">💡 Recomendação</p>
            <p className="text-sm text-blue-800">
              Veja produtos similares na aba "Produtos Similares" que não contêm estes alergenos.
            </p>
            <button
              onClick={() => setAbaAtiva('similares')}
              className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              Ver Alternativas
            </button>
          </div>
        )}
      </div>
    );
  };
  
  const renderSugestoesSimilares = () => {
    if (sugestoesSimilares.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Package className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          Nenhum produto similar encontrado
        </div>
      );
    }
    
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-600 mb-4">
          Produtos com características similares (espécie, porte, fase, sabor)
        </p>
        
        {sugestoesSimilares.map((produto) => (
          <div 
            key={produto.produto_id}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-1">{produto.nome}</h4>
                <p className="text-sm text-gray-600">{produto.marca}</p>
              </div>
              <div className="ml-4 flex items-center gap-1">
                <Sparkles className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-semibold text-yellow-600">
                  {produto.similaridade_score}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <div>
                <p className="text-lg font-bold text-gray-900">
                  R$ {produto.preco_venda.toFixed(2)}
                </p>
                {produto.preco_kg && (
                  <p className="text-xs text-gray-500">
                    R$ {produto.preco_kg.toFixed(2)}/kg
                  </p>
                )}
              </div>
              
              <div className="flex items-center gap-2">
                {produto.disponivel_estoque ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    Em estoque ({produto.estoque_quantidade})
                  </span>
                ) : (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                    Sem estoque
                  </span>
                )}
                
                <button
                  onClick={() => handleAddSugestao(produto)}
                  disabled={!produto.disponivel_estoque}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm flex items-center gap-1"
                >
                  <ShoppingCart className="h-4 w-4" />
                  Adicionar
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  const renderCrossSell = () => {
    if (sugestoesCrossSell.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <TrendingUp className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          <p>Nenhuma sugestão de compra conjunta</p>
          <p className="text-xs text-gray-400 mt-1">
            Adicione mais produtos ao carrinho para ver sugestões
          </p>
        </div>
      );
    }
    
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-600 mb-4">
          🔥 Clientes que compraram produtos do carrinho também compraram:
        </p>
        
        {sugestoesCrossSell.map((produto) => (
          <div 
            key={produto.produto_id}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:border-green-300 transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-1">{produto.nome}</h4>
                <p className="text-sm text-gray-600">{produto.marca}</p>
              </div>
              <div className="ml-4">
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                  {produto.frequencia_compra_conjunta}x comprado junto
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <div>
                <p className="text-lg font-bold text-gray-900">
                  R$ {produto.preco_venda.toFixed(2)}
                </p>
              </div>
              
              <div className="flex items-center gap-2">
                {produto.disponivel_estoque ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    Disponível
                  </span>
                ) : (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                    Sem estoque
                  </span>
                )}
                
                <button
                  onClick={() => handleAddSugestao(produto)}
                  disabled={!produto.disponivel_estoque}
                  className="px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm flex items-center gap-1"
                >
                  <ShoppingCart className="h-4 w-4" />
                  Adicionar
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================
  
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl">
        <div className="text-center text-gray-500">Carregando...</div>
      </div>
    );
  }
  
  return (
    <div className="bg-white rounded-lg shadow-lg max-w-2xl">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-blue-600" />
          Assistente Inteligente
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
      
      {/* Abas */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setAbaAtiva('alertas')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            abaAtiva === 'alertas'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <AlertTriangle className="h-4 w-4 inline mr-2" />
          Alertas
          {alerta?.tem_alerta && (
            <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
              !
            </span>
          )}
        </button>
        
        <button
          onClick={() => setAbaAtiva('similares')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            abaAtiva === 'similares'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Package className="h-4 w-4 inline mr-2" />
          Similares ({sugestoesSimilares.length})
        </button>
        
        <button
          onClick={() => setAbaAtiva('crosssell')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            abaAtiva === 'crosssell'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <TrendingUp className="h-4 w-4 inline mr-2" />
          Comprado Junto ({sugestoesCrossSell.length})
        </button>
      </div>
      
      {/* Conteúdo das Abas */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {abaAtiva === 'alertas' && renderAlerta()}
        {abaAtiva === 'similares' && renderSugestoesSimilares()}
        {abaAtiva === 'crosssell' && renderCrossSell()}
      </div>
    </div>
  );
};

export default PDVAlertasRacao;
