import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const EstoqueBling = () => {
  const [produtos, setProdutos] = useState([]);
  const [produtosBling, setProdutosBling] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [filtro, setFiltro] = useState('todos'); // todos, sincronizados, nao_sincronizados
  const [buscaBling, setBuscaBling] = useState('');

  const getCategoriaNome = (produto) => {
    const categoria = produto?.categoria;
    if (!categoria) return null;
    if (typeof categoria === 'string') return categoria;
    if (typeof categoria === 'object') {
      return categoria.nome || categoria.descricao || `Categoria #${categoria.id ?? ''}`.trim();
    }
    return String(categoria);
  };

  useEffect(() => {
    carregarProdutos();
  }, []);

  const carregarProdutos = async () => {
    setLoading(true);
    try {
            const response = await api.get(`/produtos/`);
      setProdutos(response.data.items || []);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      toast.error('Erro ao carregar produtos');
      setProdutos([]);
    } finally {
      setLoading(false);
    }
  };

  const buscarProdutosBling = async () => {
    setLoading(true);
    try {
      const params = buscaBling ? { descricao: buscaBling } : {};
      const response = await api.get(`/bling-sync/produtos`, { params });
      setProdutosBling(response.data || []);
      toast.success(`✅ ${(response.data || []).length} produtos encontrados no Bling`);
    } catch (error) {
      console.error('Erro ao buscar no Bling:', error);
      toast.error(error.response?.data?.detail || 'Erro ao buscar produtos no Bling');
      setProdutosBling([]);
    } finally {
      setLoading(false);
    }
  };

  const vincularProdutoBling = async (produtoId, blingId) => {
    try {
      await api.post(
        `/bling-sync/vincular`,
        { produto_id: produtoId, bling_id: blingId }
      );
      toast.success('✅ Produto vinculado ao Bling com sucesso!');
      carregarProdutos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao vincular produto');
    }
  };

  const sincronizarEstoque = async (produtoId) => {
    setSincronizando(true);
    try {
      const response = await api.post(
        `/bling-sync/sincronizar-estoque/${produtoId}`,
        {}
      );
      
      toast.success(
        `✅ Estoque sincronizado!\nSistema: ${response.data.estoque_local} → Bling: ${response.data.estoque_bling}`,
        { duration: 4000 }
      );
      
      carregarProdutos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao sincronizar estoque');
    } finally {
      setSincronizando(false);
    }
  };

  const sincronizarTodos = async () => {
    setSincronizando(true);
    const produtosVinculados = produtos.filter(p => p.bling_id);
    
    if (produtosVinculados.length === 0) {
      toast.error('Nenhum produto vinculado ao Bling');
      setSincronizando(false);
      return;
    }

    let sucessos = 0;
    let erros = 0;

    for (const produto of produtosVinculados) {
      try {
        await api.post(
          `/bling-sync/sincronizar-estoque/${produto.id}`,
          {}
        );
        sucessos++;
      } catch (error) {
        erros++;
        console.error(`Erro ao sincronizar produto ${produto.id}:`, error);
      }
    }

    toast.success(
      `✅ Sincronização concluída!\n${sucessos} produtos atualizados${erros > 0 ? `, ${erros} erros` : ''}`,
      { duration: 5000 }
    );
    
    carregarProdutos();
    setSincronizando(false);
  };

  const reconciliarEstoques = async () => {
    setLoading(true);
    try {
            const response = await api.post(
        `/bling-sync/reconciliar`,
        {}
      );
      
      toast.success(
        `✅ Reconciliação concluída!\n${response.data.total_processados} produtos processados\n${response.data.diferencas_encontradas} diferenças encontradas`,
        { duration: 5000 }
      );
      
      carregarProdutos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao reconciliar estoques');
    } finally {
      setLoading(false);
    }
  };

  const produtosFiltrados = produtos.filter(p => {
    if (filtro === 'sincronizados') return p.bling_id;
    if (filtro === 'nao_sincronizados') return !p.bling_id;
    return true;
  });

  const estatisticas = {
    total: produtos.length,
    sincronizados: produtos.filter(p => p.bling_id).length,
    naoSincronizados: produtos.filter(p => !p.bling_id).length
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">🔄 Sincronização Bling</h1>
        <p className="text-gray-600">Gerencie a integração dos produtos com o Bling ERP</p>
      </div>

      {/* Estatísticas */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">{estatisticas.total}</div>
          <div className="text-sm text-gray-600">Total de Produtos</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{estatisticas.sincronizados}</div>
          <div className="text-sm text-gray-600">Vinculados ao Bling</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-orange-600">{estatisticas.naoSincronizados}</div>
          <div className="text-sm text-gray-600">Não Vinculados</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-purple-600">
            {estatisticas.total > 0 ? ((estatisticas.sincronizados / estatisticas.total) * 100).toFixed(1) : 0}%
          </div>
          <div className="text-sm text-gray-600">Taxa de Sincronização</div>
        </div>
      </div>

      {/* Ações Rápidas */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">⚡ Ações Rápidas</h2>
        <div className="flex gap-4">
          <button
            onClick={sincronizarTodos}
            disabled={sincronizando || estatisticas.sincronizados === 0}
            className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {sincronizando ? '⏳ Sincronizando...' : `🔄 Sincronizar Todos (${estatisticas.sincronizados})`}
          </button>
          <button
            onClick={reconciliarEstoques}
            disabled={loading || estatisticas.sincronizados === 0}
            className="flex-1 bg-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '⏳ Reconciliando...' : '🔍 Reconciliar Estoques'}
          </button>
        </div>
        <p className="text-sm text-gray-500 mt-3">
          <strong>Sincronizar:</strong> Atualiza o estoque do Bling com os valores do sistema. 
          <strong className="ml-4">Reconciliar:</strong> Compara e identifica diferenças entre os estoques.
        </p>
      </div>

      {/* Buscar no Bling */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">🔍 Buscar Produtos no Bling</h2>
        <div className="flex gap-4">
          <input
            type="text"
            value={buscaBling}
            onChange={(e) => setBuscaBling(e.target.value)}
            placeholder="Digite o nome do produto (deixe vazio para buscar todos)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && buscarProdutosBling()}
          />
          <button
            onClick={buscarProdutosBling}
            disabled={loading}
            className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
          >
            {loading ? '⏳ Buscando...' : '🔍 Buscar'}
          </button>
        </div>

        {/* Resultados da Busca */}
        {produtosBling.length > 0 && (
          <div className="mt-4 border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 font-semibold border-b">
              {produtosBling.length} produtos encontrados no Bling
            </div>
            <div className="max-h-64 overflow-y-auto">
              {produtosBling.map(pb => (
                <div key={pb.id} className="px-4 py-3 border-b hover:bg-gray-50 flex justify-between items-center">
                  <div>
                    <div className="font-semibold">{pb.descricao}</div>
                    <div className="text-sm text-gray-600">
                      ID Bling: {pb.id} | Código: {pb.codigo} | Estoque: {pb.estoque}
                    </div>
                  </div>
                  <select
                    onChange={(e) => e.target.value && vincularProdutoBling(parseInt(e.target.value), pb.id)}
                    className="px-3 py-2 border border-gray-300 rounded text-sm"
                  >
                    <option value="">Vincular ao produto...</option>
                    {produtos
                      .filter(p => !p.bling_id)
                      .map(p => (
                        <option key={p.id} value={p.id}>{p.codigo} - {p.nome}</option>
                      ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-4">
        <div className="flex gap-3">
          <button
            onClick={() => setFiltro('todos')}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filtro === 'todos' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Todos ({estatisticas.total})
          </button>
          <button
            onClick={() => setFiltro('sincronizados')}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filtro === 'sincronizados' 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ✅ Sincronizados ({estatisticas.sincronizados})
          </button>
          <button
            onClick={() => setFiltro('nao_sincronizados')}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filtro === 'nao_sincronizados' 
                ? 'bg-orange-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ⚠️ Não Sincronizados ({estatisticas.naoSincronizados})
          </button>
        </div>
      </div>

      {/* Lista de Produtos */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Produto</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Estoque Local</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">ID Bling</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading && produtosFiltrados.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                  ⏳ Carregando produtos...
                </td>
              </tr>
            ) : produtosFiltrados.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                  Nenhum produto encontrado com os filtros selecionados
                </td>
              </tr>
            ) : (
              produtosFiltrados.map(produto => (
                <tr key={produto.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm">{produto.codigo}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold">{produto.nome}</div>
                    {getCategoriaNome(produto) && (
                      <div className="text-xs text-gray-500">{getCategoriaNome(produto)}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-semibold ${
                      (produto.estoque_atual || 0) <= (produto.estoque_minimo || 0)
                        ? 'text-red-600'
                        : 'text-green-600'
                    }`}>
                      {produto.estoque_atual || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {produto.bling_id ? (
                      <span className="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-semibold">
                        {produto.bling_id}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {produto.bling_id ? (
                      <span className="inline-block bg-green-100 text-green-800 px-3 py-1 rounded-full text-xs font-semibold">
                        ✅ VINCULADO
                      </span>
                    ) : (
                      <span className="inline-block bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-xs font-semibold">
                        ⚠️ NÃO VINCULADO
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {produto.bling_id ? (
                      <button
                        onClick={() => sincronizarEstoque(produto.id)}
                        disabled={sincronizando}
                        className="text-blue-600 hover:text-blue-800 font-semibold text-sm disabled:text-gray-400"
                        title="Sincronizar estoque com Bling"
                      >
                        🔄 Sync
                      </button>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EstoqueBling;
