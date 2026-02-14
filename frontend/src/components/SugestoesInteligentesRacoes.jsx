import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  Copy,
  Edit,
  PackageX,
  TrendingDown,
  CheckCircle,
  XCircle,
  RefreshCw,
  Download,
  Search
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../api';

/**
 * Painel de Sugestões Inteligentes - Fase 6
 * 
 * Features:
 * - Detecção de duplicatas
 * - Sugestões de padronização de nomes
 * - Gaps de estoque em segmentos importantes
 * - Score de saúde do cadastro
 * 
 * @version 1.0.0 (2026-02-14)
 */
const SugestoesInteligentesRacoes = () => {
  // ============================================================================
  // STATES
  // ============================================================================
  
  const [loading, setLoading] = useState(true);
  const [relatorioCompleto, setRelatorioCompleto] = useState(null);
  const [duplicatas, setDuplicatas] = useState([]);
  const [padronizacoes, setPadronizacoes] = useState([]);
  const [gapsEstoque, setGapsEstoque] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState('resumo');
  
  // Filtros
  const [filtroThreshold, setFiltroThreshold] = useState(0.80);
  const [filtroTipoSegmento, setFiltroTipoSegmento] = useState('porte');
  
  // Seleção de produto para mesclar (índice da duplicata -> 'produto_1' ou 'produto_2')
  const [produtosSelecionados, setProdutosSelecionados] = useState({});
  
  // Edição de nomes sugeridos (produto_id -> {editando: boolean, nome: string})
  const [nomesEditados, setNomesEditados] = useState({});
  
  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  useEffect(() => {
    carregarRelatorioCompleto();
  }, []);
  
  // ============================================================================
  // FUNÇÕES DE CARREGAMENTO
  // ============================================================================
  
  const carregarRelatorioCompleto = async () => {
    try {
      setLoading(true);
      const res = await api.get('/racoes/sugestoes/relatorio-completo');
      setRelatorioCompleto(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar relatório:', error);
      toast.error('Erro ao carregar relatório de sugestões');
      setLoading(false);
    }
  };
  
  const carregarDuplicatas = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/racoes/sugestoes/duplicatas?threshold_similaridade=${filtroThreshold}`);
      setDuplicatas(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar duplicatas:', error);
      toast.error('Erro ao carregar duplicatas');
      setLoading(false);
    }
  };
  
  const carregarPadronizacoes = async () => {
    try {
      setLoading(true);
      const res = await api.get('/racoes/sugestoes/padronizar-nomes?limite=50');
      setPadronizacoes(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar padronizações:', error);
      toast.error('Erro ao carregar sugestões de padronização');
      setLoading(false);
    }
  };
  
  const carregarGapsEstoque = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/racoes/sugestoes/gaps-estoque?tipo_segmento=${filtroTipoSegmento}`);
      setGapsEstoque(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar gaps:', error);
      toast.error('Erro ao carregar gaps de estoque');
      setLoading(false);
    }
  };
  
  // ============================================================================
  // HANDLERS
  // ============================================================================
  
  const handleMudarAba = (aba) => {
    setAbaAtiva(aba);
    
    // Carregar dados específicos da aba
    if (aba === 'duplicatas' && duplicatas.length === 0) {
      carregarDuplicatas();
    } else if (aba === 'padronizacao' && padronizacoes.length === 0) {
      carregarPadronizacoes();
    } else if (aba === 'gaps' && gapsEstoque.length === 0) {
      carregarGapsEstoque();
    }
  };
  
  const handleAplicarPadronizacao = async (padronizacao) => {
    try {
      // Usar nome editado se houver, senão usar sugestão original
      const nomeEditado = nomesEditados[padronizacao.produto_id];
      const nomeFinal = nomeEditado?.nome || padronizacao.nome_sugerido;
      
      await api.patch(`/produtos/${padronizacao.produto_id}`, {
        nome: nomeFinal
      });
      
      toast.success('Nome atualizado com sucesso!');
      
      // Remover da lista
      setPadronizacoes(prev => prev.filter(p => p.produto_id !== padronizacao.produto_id));
      
      // Limpar estado de edição
      setNomesEditados(prev => {
        const novo = { ...prev };
        delete novo[padronizacao.produto_id];
        return novo;
      });
      
      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error('Erro ao aplicar padronização:', error);
      toast.error('Erro ao atualizar nome do produto');
    }
  };
  
  const handleIgnorarDuplicata = async (duplicata) => {
    try {
      await api.post('/racoes/sugestoes/duplicatas/ignorar', null, {
        params: {
          produto_id_1: duplicata.produto_1.id,
          produto_id_2: duplicata.produto_2.id
        }
      });
      
      toast.success('Duplicata ignorada com sucesso!');
      
      // Remover da lista
      setDuplicatas(prev => prev.filter(d => 
        !(d.produto_1.id === duplicata.produto_1.id && d.produto_2.id === duplicata.produto_2.id)
      ));
      
      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error('Erro ao ignorar duplicata:', error);
      toast.error('Erro ao ignorar duplicata');
    }
  };
  
  const handleSelecionarProduto = (duplicataIndex, produto) => {
    setProdutosSelecionados(prev => ({
      ...prev,
      [duplicataIndex]: produto
    }));
  };
  
  const handleConfirmarMesclagem = async (duplicata, duplicataIndex) => {
    const produtoSelecionado = produtosSelecionados[duplicataIndex];
    
    if (!produtoSelecionado) {
      toast.error('Selecione qual produto deseja manter antes de confirmar');
      return;
    }
    
    const produto_id_manter = produtoSelecionado === 'produto_1' ? duplicata.produto_1.id : duplicata.produto_2.id;
    const produto_id_remover = produtoSelecionado === 'produto_1' ? duplicata.produto_2.id : duplicata.produto_1.id;
    const nome_manter = produtoSelecionado === 'produto_1' ? duplicata.produto_1.nome : duplicata.produto_2.nome;
    const nome_remover = produtoSelecionado === 'produto_1' ? duplicata.produto_2.nome : duplicata.produto_1.nome;
    
    try {
      const response = await api.post('/racoes/sugestoes/duplicatas/mesclar', null, {
        params: {
          produto_id_manter,
          produto_id_remover,
          transferir_estoque: true
        }
      });
      
      toast.success(response.data.mensagem);
      
      // Remover da lista
      setDuplicatas(prev => prev.filter(d => 
        !(d.produto_1.id === duplicata.produto_1.id && d.produto_2.id === duplicata.produto_2.id)
      ));
      
      // Limpar seleção
      setProdutosSelecionados(prev => {
        const novo = { ...prev };
        delete novo[duplicataIndex];
        return novo;
      });
      
      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error('Erro ao mesclar produtos:', error);
      toast.error('Erro ao mesclar produtos');
    }
  };
  
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  const renderResumo = () => {
    if (!relatorioCompleto) return null;
    
    const { score_saude, classificacao, cor, resumo, recomendacoes } = relatorioCompleto;
    
    return (
      <div className="space-y-6">
        {/* Score de Saúde */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Score de Saúde do Cadastro</h3>
            <button
              onClick={carregarRelatorioCompleto}
              className="text-blue-600 hover:text-blue-700"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
          </div>
          
          <div className="flex items-center gap-6">
            <div className={`w-32 h-32 rounded-full flex items-center justify-center border-8 ${
              cor === 'green' ? 'border-green-500' :
              cor === 'blue' ? 'border-blue-500' :
              cor === 'yellow' ? 'border-yellow-500' :
              'border-red-500'
            }`}>
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900">{score_saude}</div>
                <div className="text-xs text-gray-600">pontos</div>
              </div>
            </div>
            
            <div className="flex-1">
              <div className={`inline-block px-4 py-2 rounded-full text-white font-semibold mb-3 ${
                cor === 'green' ? 'bg-green-500' :
                cor === 'blue' ? 'bg-blue-500' :
                cor === 'yellow' ? 'bg-yellow-500' :
                'bg-red-500'
              }`}>
                {classificacao}
              </div>
              
              <p className="text-gray-700 mb-4">
                {score_saude >= 90 && "Parabéns! Seu cadastro de rações está excelente."}
                {score_saude >= 70 && score_saude < 90 && "Seu cadastro está em bom estado, mas há algumas melhorias possíveis."}
                {score_saude >= 50 && score_saude < 70 && "Atenção! Existem vários pontos de melhoria no cadastro."}
                {score_saude < 50 && "CRÍTICO! É necessário realizar melhorias urgentes no cadastro."}
              </p>
            </div>
          </div>
        </div>
        
        {/* Cards de Resumo */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <Copy className="h-5 w-5 text-orange-500" />
              <span className="text-2xl font-bold text-gray-900">{resumo.duplicatas_detectadas}</span>
            </div>
            <div className="text-sm text-gray-600">Duplicatas Detectadas</div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <Edit className="h-5 w-5 text-blue-500" />
              <span className="text-2xl font-bold text-gray-900">{resumo.nomes_padronizar}</span>
            </div>
            <div className="text-sm text-gray-600">Nomes para Padronizar</div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <PackageX className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold text-gray-900">{resumo.gaps_criticos}</span>
            </div>
            <div className="text-sm text-gray-600">Gaps de Estoque Críticos</div>
          </div>
        </div>
        
        {/* Recomendações */}
        {recomendacoes && recomendacoes.filter(Boolean).length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Recomendações Prioritárias
            </h4>
            <ul className="space-y-2">
              {recomendacoes.filter(Boolean).map((rec, idx) => (
                <li key={idx} className="flex items-center gap-2 text-blue-800">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };
  
  const renderDuplicatas = () => {
    if (loading) {
      return <div className="text-center py-8 text-gray-500">Carregando...</div>;
    }
    
    if (duplicatas.length === 0) {
      return (
        <div className="text-center py-8">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
          <p className="text-gray-700 font-semibold">Nenhuma duplicata detectada!</p>
          <p className="text-sm text-gray-600 mt-1">Seu cadastro está livre de produtos duplicados</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mr-2">
              Threshold de Similaridade:
            </label>
            <input
              type="range"
              min="0.5"
              max="1"
              step="0.05"
              value={filtroThreshold}
              onChange={(e) => setFiltroThreshold(parseFloat(e.target.value))}
              className="w-32"
            />
            <span className="ml-2 text-sm text-gray-600">{(filtroThreshold * 100).toFixed(0)}%</span>
          </div>
          
          <button
            onClick={carregarDuplicatas}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            Buscar Duplicatas
          </button>
        </div>
        
        {duplicatas.map((dup, idx) => (
          <div key={idx} className="bg-white border-2 border-orange-200 rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Copy className="h-5 w-5 text-orange-500" />
                <span className="font-semibold text-gray-900">
                  Similaridade: {(dup.score_similaridade * 100).toFixed(0)}%
                </span>
              </div>
              <span className={`text-xs px-2 py-1 rounded ${
                dup.score_similaridade >= 0.9 ? 'bg-red-100 text-red-700' :
                dup.score_similaridade >= 0.8 ? 'bg-orange-100 text-orange-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>
                {dup.sugestao_acao}
              </span>
            </div>
            
            <div className="mb-3 text-sm text-gray-700 bg-blue-50 p-2 rounded">
              👆 <strong>Clique no produto que deseja MANTER</strong> (o outro será inativado e terá o estoque transferido)
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Produto 1 */}
              <div 
                onClick={() => handleSelecionarProduto(idx, 'produto_1')}
                className={`rounded p-3 cursor-pointer transition-all border-2 ${
                  produtosSelecionados[idx] === 'produto_1'
                    ? 'bg-green-50 border-green-500 shadow-lg'
                    : produtosSelecionados[idx] === 'produto_2'
                    ? 'bg-red-50 border-red-300 opacity-60'
                    : 'bg-gray-50 border-gray-200 hover:border-blue-400 hover:shadow-md'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="text-xs text-gray-500">Produto 1 (ID: {dup.produto_1.id})</div>
                  {produtosSelecionados[idx] === 'produto_1' && (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                </div>
                <div className="font-semibold text-gray-900 mb-2">{dup.produto_1.nome}</div>
                <div className="text-sm text-gray-600">
                  <div>Marca: {dup.produto_1.marca}</div>
                  <div>Preço: R$ {dup.produto_1.preco.toFixed(2)}</div>
                  <div>Estoque: {dup.produto_1.estoque}</div>
                </div>
                {produtosSelecionados[idx] === 'produto_1' && (
                  <div className="mt-2 text-xs font-semibold text-green-700 bg-green-100 px-2 py-1 rounded">
                    ✓ ESTE PRODUTO SERÁ MANTIDO
                  </div>
                )}
                {produtosSelecionados[idx] === 'produto_2' && (
                  <div className="mt-2 text-xs text-red-700 bg-red-100 px-2 py-1 rounded">
                    ✗ Este produto será inativado
                  </div>
                )}
              </div>
              
              {/* Produto 2 */}
              <div 
                onClick={() => handleSelecionarProduto(idx, 'produto_2')}
                className={`rounded p-3 cursor-pointer transition-all border-2 ${
                  produtosSelecionados[idx] === 'produto_2'
                    ? 'bg-green-50 border-green-500 shadow-lg'
                    : produtosSelecionados[idx] === 'produto_1'
                    ? 'bg-red-50 border-red-300 opacity-60'
                    : 'bg-gray-50 border-gray-200 hover:border-blue-400 hover:shadow-md'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="text-xs text-gray-500">Produto 2 (ID: {dup.produto_2.id})</div>
                  {produtosSelecionados[idx] === 'produto_2' && (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                </div>
                <div className="font-semibold text-gray-900 mb-2">{dup.produto_2.nome}</div>
                <div className="text-sm text-gray-600">
                  <div>Marca: {dup.produto_2.marca}</div>
                  <div>Preço: R$ {dup.produto_2.preco.toFixed(2)}</div>
                  <div>Estoque: {dup.produto_2.estoque}</div>
                </div>
                {produtosSelecionados[idx] === 'produto_2' && (
                  <div className="mt-2 text-xs font-semibold text-green-700 bg-green-100 px-2 py-1 rounded">
                    ✓ ESTE PRODUTO SERÁ MANTIDO
                  </div>
                )}
                {produtosSelecionados[idx] === 'produto_1' && (
                  <div className="mt-2 text-xs text-red-700 bg-red-100 px-2 py-1 rounded">
                    ✗ Este produto será inativado
                  </div>
                )}
              </div>
            </div>
            
            {/* Razões */}
            <div className="mt-3 flex flex-wrap gap-1">
              {dup.razoes.map((razao, i) => (
                <span key={i} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                  {razao}
                </span>
              ))}
            </div>
            
            {/* Botões de Ação */}
            <div className="mt-4 flex gap-2 justify-end">
              <button
                onClick={() => handleIgnorarDuplicata(dup)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 flex items-center gap-2 text-sm"
              >
                <XCircle className="h-4 w-4" />
                Ignorar (Não é Duplicata)
              </button>
              
              {produtosSelecionados[idx] ? (
                <button
                  onClick={() => handleConfirmarMesclagem(dup, idx)}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center gap-2 text-sm font-semibold shadow-md"
                >
                  <CheckCircle className="h-4 w-4" />
                  Confirmar Mesclagem
                </button>
              ) : (
                <button
                  disabled
                  className="px-4 py-2 bg-gray-300 text-gray-500 rounded-md flex items-center gap-2 text-sm cursor-not-allowed"
                >
                  <Copy className="h-4 w-4" />
                  Selecione um Produto
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  const renderPadronizacoes = () => {
    if (loading) {
      return <div className="text-center py-8 text-gray-500">Carregando...</div>;
    }
    
    if (padronizacoes.length === 0) {
      return (
        <div className="text-center py-8">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
          <p className="text-gray-700 font-semibold">Todos os nomes estão padronizados!</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-3">
        {padronizacoes.map((pad, idx) => (
          <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="text-xs text-gray-500 mb-1">ID: {pad.produto_id}</div>
                <div className="mb-2">
                  <div className="text-sm font-semibold text-gray-900 mb-1">Nome Atual:</div>
                  <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded">{pad.nome_atual}</div>
                </div>
                <div>
                  <div className="text-sm font-semibold text-green-700 mb-1">Nome Sugerido:</div>
                  {nomesEditados[pad.produto_id]?.editando ? (
                    <input
                      type="text"
                      value={nomesEditados[pad.produto_id]?.nome || pad.nome_sugerido}
                      onChange={(e) => setNomesEditados(prev => ({
                        ...prev,
                        [pad.produto_id]: { editando: true, nome: e.target.value }
                      }))}
                      className="w-full text-sm text-green-900 bg-green-50 p-2 rounded font-medium border-2 border-blue-400 focus:outline-none focus:border-blue-600"
                      autoFocus
                    />
                  ) : (
                    <div className="text-sm text-green-900 bg-green-50 p-2 rounded font-medium">
                      {nomesEditados[pad.produto_id]?.nome || pad.nome_sugerido}
                    </div>
                  )}
                </div>
              </div>
              
              <div className="ml-4 flex items-center gap-2">
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                  {(pad.confianca * 100).toFixed(0)}% confiança
                </span>
              </div>
            </div>
            
            <div className="text-xs text-gray-600 mb-3">
              <strong>Razão:</strong> {pad.razao}
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => handleAplicarPadronizacao(pad)}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm flex items-center gap-1"
              >
                <CheckCircle className="h-4 w-4" />
                Aplicar {nomesEditados[pad.produto_id]?.nome ? 'Edição' : 'Sugestão'}
              </button>
              
              {nomesEditados[pad.produto_id]?.editando ? (
                <button
                  onClick={() => setNomesEditados(prev => {
                    const novo = { ...prev };
                    delete novo[pad.produto_id];
                    return novo;
                  })}
                  className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 text-sm flex items-center gap-1"
                >
                  <XCircle className="h-4 w-4" />
                  Cancelar Edição
                </button>
              ) : (
                <>
                  <button
                    onClick={() => setNomesEditados(prev => ({
                      ...prev,
                      [pad.produto_id]: { editando: true, nome: nomesEditados[pad.produto_id]?.nome || pad.nome_sugerido }
                    }))}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm flex items-center gap-1"
                  >
                    <Edit className="h-4 w-4" />
                    Editar
                  </button>
                  
                  <button
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm flex items-center gap-1"
                  >
                    <XCircle className="h-4 w-4" />
                    Ignorar
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  const renderGapsEstoque = () => {
    if (loading) {
      return <div className="text-center py-8 text-gray-500">Carregando...</div>;
    }
    
    if (gapsEstoque.length === 0) {
      return (
        <div className="text-center py-8">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
          <p className="text-gray-700 font-semibold">Nenhum gap crítico de estoque!</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mr-2">
              Analisar por:
            </label>
            <select
              value={filtroTipoSegmento}
              onChange={(e) => setFiltroTipoSegmento(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
            >
              <option value="porte">Porte</option>
              <option value="fase">Fase</option>
              <option value="sabor">Sabor</option>
              <option value="linha">Linha</option>
              <option value="especie">Espécie</option>
            </select>
          </div>
          
          <button
            onClick={carregarGapsEstoque}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            Analisar
          </button>
        </div>
        
        {gapsEstoque.map((gap, idx) => (
          <div 
            key={idx}
            className={`rounded-lg p-4 border-2 ${
              gap.importancia === 'Alta' ? 'bg-red-50 border-red-300' :
              gap.importancia === 'Média' ? 'bg-yellow-50 border-yellow-300' :
              'bg-gray-50 border-gray-300'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className={`h-5 w-5 ${
                    gap.importancia === 'Alta' ? 'text-red-600' :
                    gap.importancia === 'Média' ? 'text-yellow-600' :
                    'text-gray-600'
                  }`} />
                  <span className="font-bold text-gray-900 text-lg">{gap.segmento_valor}</span>
                </div>
                <div className="text-sm text-gray-700">
                  {gap.produtos_sem_estoque} de {gap.total_produtos} produtos sem estoque ({gap.percentual_sem_estoque}%)
                </div>
              </div>
              
              <span className={`px-3 py-1 rounded text-xs font-semibold ${
                gap.importancia === 'Alta' ? 'bg-red-600 text-white' :
                gap.importancia === 'Média' ? 'bg-yellow-500 text-white' :
                'bg-gray-500 text-white'
              }`}>
                {gap.importancia}
              </span>
            </div>
            
            <div className="bg-white bg-opacity-50 rounded p-3 mb-3">
              <div className="text-sm text-gray-700">
                <strong>Faturamento Histórico (90 dias):</strong> R$ {gap.faturamento_historico.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </div>
            </div>
            
            <div className={`text-sm font-medium ${
              gap.importancia === 'Alta' ? 'text-red-800' :
              gap.importancia === 'Média' ? 'text-yellow-800' :
              'text-gray-800'
            }`}>
              💡 {gap.sugestao}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================
  
  if (loading && abaAtiva === 'resumo') {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <AlertCircle className="h-7 w-7 text-blue-600" />
            Sugestões Inteligentes
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Otimize seu cadastro de rações com sugestões automáticas
          </p>
        </div>
      </div>
      
      {/* Abas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex space-x-1 p-2">
            <button
              onClick={() => handleMudarAba('resumo')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === 'resumo'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <CheckCircle className="h-4 w-4 inline mr-2" />
              Resumo Geral
            </button>
            
            <button
              onClick={() => handleMudarAba('duplicatas')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === 'duplicatas'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Copy className="h-4 w-4 inline mr-2" />
              Duplicatas
              {relatorioCompleto?.resumo?.duplicatas_detectadas > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-orange-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.duplicatas_detectadas}
                </span>
              )}
            </button>
            
            <button
              onClick={() => handleMudarAba('padronizacao')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === 'padronizacao'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Edit className="h-4 w-4 inline mr-2" />
              Padronização
              {relatorioCompleto?.resumo?.nomes_padronizar > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.nomes_padronizar}
                </span>
              )}
            </button>
            
            <button
              onClick={() => handleMudarAba('gaps')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === 'gaps'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <PackageX className="h-4 w-4 inline mr-2" />
              Gaps de Estoque
              {relatorioCompleto?.resumo?.gaps_criticos > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.gaps_criticos}
                </span>
              )}
            </button>
          </div>
        </div>
        
        <div className="p-4">
          {abaAtiva === 'resumo' && renderResumo()}
          {abaAtiva === 'duplicatas' && renderDuplicatas()}
          {abaAtiva === 'padronizacao' && renderPadronizacoes()}
          {abaAtiva === 'gaps' && renderGapsEstoque()}
        </div>
      </div>
    </div>
  );
};

export default SugestoesInteligentesRacoes;
