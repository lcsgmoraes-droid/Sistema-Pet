import { useState, useEffect, useRef } from 'react';
import { X, AlertCircle, Clock, CheckCircle, Bell, Trash2, Search } from 'lucide-react';
import api from '../../api';
import toast from 'react-hot-toast';

export default function ModalPendenciasEstoque({ 
  isOpen, 
  onClose, 
  clienteId, 
  produtoId = null, 
  onPendenciaAdicionada = () => {} 
}) {
  const [modo, setModo] = useState('listar'); // 'listar' | 'adicionar'
  const [pendencias, setPendencias] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Estados para busca de produtos
  const [buscaProduto, setBuscaProduto] = useState('');
  const [produtosFiltrados, setProdutosFiltrados] = useState([]);
  const [mostrarLista, setMostrarLista] = useState(false);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const buscaRef = useRef(null);
  
  // Form para adicionar pendência
  const [formData, setFormData] = useState({
    produto_id: produtoId || '',
    quantidade_desejada: 1,
    prioridade: 'media',
    observacoes: ''
  });

  useEffect(() => {
    if (isOpen && clienteId) {
      carregarPendencias();
      if (!produtoId) {
        carregarProdutosSemEstoque();
      }
    }
  }, [isOpen, clienteId]);

  // Efeito para filtrar produtos conforme a busca
  useEffect(() => {
    if (buscaProduto.trim() === '') {
      setProdutosFiltrados(produtos); // Mostrar todos quando vazio
    } else {
      const filtrados = produtos.filter(prod =>
        prod.nome.toLowerCase().includes(buscaProduto.toLowerCase()) ||
        prod.codigo?.toLowerCase().includes(buscaProduto.toLowerCase())
      );
      setProdutosFiltrados(filtrados);
    }
  }, [buscaProduto, produtos]);

  // Efeito para fechar a lista ao clicar fora
  useEffect(() => {
    const handleClickFora = (event) => {
      if (buscaRef.current && !buscaRef.current.contains(event.target)) {
        setMostrarLista(false);
      }
    };

    document.addEventListener('mousedown', handleClickFora);
    return () => {
      document.removeEventListener('mousedown', handleClickFora);
    };
  }, []);

  const carregarPendencias = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/pendencias-estoque/cliente/${clienteId}`);
      // API retorna um objeto com propriedade 'pendencias', não array direto
      const data = response.data;
      setPendencias(Array.isArray(data?.pendencias) ? data.pendencias : []);
    } catch (error) {
      console.error('Erro ao carregar pendências:', error);
      toast.error('Erro ao carregar lista de espera');
      setPendencias([]); // Garantir que seja array vazio em caso de erro
    } finally {
      setLoading(false);
    }
  };

  const carregarProdutosSemEstoque = async () => {
    try {
      const response = await api.get('/produtos/', {
        params: { 
          page: 1,
          page_size: 1000,
          ativo: true
        }
      });
      // A API retorna um objeto com { items, total, page, page_size, pages }
      const produtosData = Array.isArray(response.data?.items) ? response.data.items : [];
      console.log('Produtos carregados:', produtosData.length, produtosData);
      setProdutos(produtosData);
      setProdutosFiltrados(produtosData); // Inicializar com todos os produtos
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      toast.error('Erro ao carregar produtos');
      setProdutos([]);
      setProdutosFiltrados([]);
    }
  };

  const selecionarProduto = (produto) => {
    setProdutoSelecionado(produto);
    setBuscaProduto(produto.nome);
    setFormData({ ...formData, produto_id: produto.id });
    setMostrarLista(false);
  };

  const limparSelecao = () => {
    setProdutoSelecionado(null);
    setBuscaProduto('');
    setFormData({ ...formData, produto_id: '' });
    setProdutosFiltrados(produtos);
  };

  const adicionarPendencia = async () => {
    if (!formData.produto_id) {
      toast.error('Selecione um produto');
      return;
    }

    // Converter prioridade de string para número
    const prioridadeMap = {
      'baixa': 0,
      'media': 1,
      'alta': 2
    };

    try {
      setLoading(true);
      await api.post('/pendencias-estoque/', {
        cliente_id: clienteId,
        produto_id: parseInt(formData.produto_id),
        quantidade_desejada: parseFloat(formData.quantidade_desejada),
        prioridade: prioridadeMap[formData.prioridade] || 1,
        observacoes: formData.observacoes || null
      });
      
      toast.success('Cliente adicionado à lista de espera!');
      setFormData({
        produto_id: '',
        quantidade_desejada: 1,
        prioridade: 'media',
        observacoes: ''
      });
      limparSelecao();
      setModo('listar');
      carregarPendencias();
      onPendenciaAdicionada();
    } catch (error) {
      console.error('Erro ao adicionar pendência:', error);
      toast.error(error.response?.data?.detail || 'Erro ao adicionar à lista de espera');
    } finally {
      setLoading(false);
    }
  };

  const cancelarPendencia = async (pendenciaId) => {
    if (!confirm('Deseja realmente cancelar esta pendência?')) return;

    try {
      await api.delete(`/pendencias-estoque/${pendenciaId}`);
      toast.success('Pendência cancelada');
      carregarPendencias();
    } catch (error) {
      console.error('Erro ao cancelar pendência:', error);
      toast.error('Erro ao cancelar pendência');
    }
  };

  const alterarPrioridade = async (pendenciaId, novaPrioridade) => {
    try {
      await api.put(`/pendencias-estoque/${pendenciaId}`, {
        prioridade: parseInt(novaPrioridade)
      });
      toast.success('Prioridade atualizada');
      carregarPendencias();
    } catch (error) {
      console.error('Erro ao alterar prioridade:', error);
      toast.error('Erro ao alterar prioridade');
    }
  };

  if (!isOpen) return null;

  const getPrioridadeColor = (prioridade) => {
    // prioridade vem como número: 0 = baixa, 1 = media, 2 = alta
    switch (prioridade) {
      case 2: return 'text-red-600 bg-red-50';
      case 1: return 'text-yellow-600 bg-yellow-50';
      case 0: return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getPrioridadeTexto = (prioridade) => {
    switch (prioridade) {
      case 2: return 'ALTA';
      case 1: return 'MÉDIA';
      case 0: return 'BAIXA';
      default: return 'N/A';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pendente': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'notificado': return <Bell className="w-4 h-4 text-blue-500" />;
      case 'finalizado': return <CheckCircle className="w-4 h-4 text-green-500" />;
      default: return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-50 to-blue-100">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold text-gray-800">
              Lista de Espera - Produtos Sem Estoque
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-1 rounded-full hover:bg-gray-200 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setModo('listar')}
            className={`flex-1 px-4 py-3 font-medium transition-colors ${
              modo === 'listar'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            Lista de Espera ({pendencias.length})
          </button>
          <button
            onClick={() => setModo('adicionar')}
            className={`flex-1 px-4 py-3 font-medium transition-colors ${
              modo === 'adicionar'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            Adicionar Pendência
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {modo === 'listar' ? (
            // Lista de pendências
            <div className="space-y-3">
              {loading ? (
                <p className="text-center text-gray-500 py-8">Carregando...</p>
              ) : pendencias.length === 0 ? (
                <div className="text-center py-12">
                  <AlertCircle className="w-16 h-16 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">Nenhuma pendência registrada</p>
                  <button
                    onClick={() => setModo('adicionar')}
                    className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Adicionar primeira pendência
                  </button>
                </div>
              ) : (
                pendencias.map((pend) => (
                  <div
                    key={pend.id}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {getStatusIcon(pend.status)}
                          <h3 className="font-semibold text-gray-900">
                            {pend.produto_nome || 'Produto não encontrado'}
                          </h3>
                          <span className={`px-2 py-1 text-xs font-medium rounded ${getPrioridadeColor(pend.prioridade)}`}>
                            {getPrioridadeTexto(pend.prioridade)}
                          </span>
                        </div>
                        
                        <div className="text-sm text-gray-600 space-y-1">
                          {pend.produto_codigo && (
                            <p>Código: <span className="font-medium">{pend.produto_codigo}</span></p>
                          )}
                          <p>Quantidade: {pend.quantidade_desejada} un.</p>
                          {pend.valor_referencia && (
                            <p>Valor ref.: R$ {parseFloat(pend.valor_referencia).toFixed(2)}</p>
                          )}
                          <p>Status: <span className="font-medium">{pend.status}</span></p>
                          <p>Registrado em: {new Date(pend.data_registro).toLocaleDateString('pt-BR')}</p>
                          {pend.data_notificacao && (
                            <p>Notificado em: {new Date(pend.data_notificacao).toLocaleDateString('pt-BR')}</p>
                          )}
                          {pend.observacoes && (
                            <p className="italic">Obs: {pend.observacoes}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-col gap-2 ml-4">
                        {pend.status === 'pendente' && (
                          <>
                            <select
                              value={pend.prioridade}
                              onChange={(e) => alterarPrioridade(pend.id, e.target.value)}
                              className="text-xs border rounded px-2 py-1"
                            >
                              <option value="0">Baixa</option>
                              <option value="1">Média</option>
                              <option value="2">Alta</option>
                            </select>
                            <button
                              onClick={() => cancelarPendencia(pend.id)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded"
                              title="Cancelar pendência"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            // Form para adicionar pendência
            <div className="space-y-4 max-w-lg mx-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Produto *
                </label>
                {produtoId ? (
                  <input
                    type="text"
                    value="Produto selecionado"
                    disabled
                    className="w-full px-3 py-2 border rounded-lg bg-gray-50"
                  />
                ) : (
                  <div ref={buscaRef} className="relative">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                      <input
                        type="text"
                        value={buscaProduto}
                        onChange={(e) => setBuscaProduto(e.target.value)}
                        onFocus={() => setMostrarLista(true)}
                        placeholder="Digite para buscar o produto..."
                        className="w-full pl-10 pr-10 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      {buscaProduto && (
                        <button
                          type="button"
                          onClick={limparSelecao}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    
                    {/* Lista de produtos filtrados */}
                    {mostrarLista && produtosFiltrados.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                        {produtosFiltrados.slice(0, 50).map((prod) => (
                          <button
                            key={prod.id}
                            type="button"
                            onClick={() => selecionarProduto(prod)}
                            className="w-full px-4 py-3 text-left hover:bg-blue-50 border-b last:border-b-0 transition-colors"
                          >
                            <div className="font-medium text-gray-900">{prod.nome}</div>
                            <div className="text-sm text-gray-500">
                              {prod.codigo && `Código: ${prod.codigo} • `}
                              Estoque: {prod.estoque_atual || 0}
                              {prod.preco_venda && ` • R$ ${parseFloat(prod.preco_venda).toFixed(2)}`}
                            </div>
                          </button>
                        ))}
                        {produtosFiltrados.length > 50 && (
                          <div className="px-4 py-2 text-sm text-gray-500 text-center bg-gray-50">
                            Mostrando 50 de {produtosFiltrados.length} produtos. Continue digitando para refinar.
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Mensagem quando não há resultados */}
                    {mostrarLista && buscaProduto && produtosFiltrados.length === 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg p-4">
                        <p className="text-gray-500 text-center">Nenhum produto encontrado</p>
                      </div>
                    )}
                    
                    {/* Produto selecionado */}
                    {produtoSelecionado && (
                      <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-green-900">
                              ✓ Produto selecionado
                            </p>
                            <p className="text-xs text-green-700 mt-1">
                              {produtoSelecionado.nome}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantidade Desejada *
                </label>
                <input
                  type="number"
                  min="1"
                  value={formData.quantidade_desejada}
                  onChange={(e) => setFormData({ ...formData, quantidade_desejada: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Prioridade
                </label>
                <select
                  value={formData.prioridade}
                  onChange={(e) => setFormData({ ...formData, prioridade: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="baixa">Baixa - Não tem pressa</option>
                  <option value="media">Média - Normal</option>
                  <option value="alta">Alta - Urgente</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Observações
                </label>
                <textarea
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  rows="3"
                  placeholder="Ex: Cliente pediu para avisar assim que chegar..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  <strong>📲 O cliente será notificado automaticamente via WhatsApp</strong> quando o produto entrar no estoque.
                </p>
              </div>

              <button
                onClick={adicionarPendencia}
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Adicionando...' : 'Adicionar à Lista de Espera'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
