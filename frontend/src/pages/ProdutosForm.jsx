/**
 * Formulário de Cadastro/Edição de Produtos
 * Com abas: Dados, Imagens, Fornecedores, Lotes
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  getProduto,
  createProduto,
  updateProduto,
  getCategorias,
  getMarcas,
  gerarSKU,
  uploadImagemProduto,
  deleteImagemProduto,
  getFornecedoresProduto,
  addFornecedorProduto,
  updateFornecedorProduto,
  deleteFornecedorProduto,
  getLotes,
  entradaEstoque,
  saidaFIFO,
  formatarMoeda,
  formatarData
} from '../api/produtos';
import api from '../api';

export default function ProdutosForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);
  
  const [abaAtiva, setAbaAtiva] = useState('dados');
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  
  // Listas auxiliares
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [clientes, setClientes] = useState([]);
  
  // Dados do produto
  const [produto, setProduto] = useState({
    codigo: '',
    nome: '',
    descricao: '',
    categoria_id: '',
    marca_id: '',
    preco_custo: '',
    preco_venda: '',
    margem_lucro: '',
    estoque_minimo: '',
    estoque_maximo: '',
    localizacao: '',
    observacoes: '',
    controle_lote: false,
    status: 'ativo'
  });
  
  // Imagens
  const [imagens, setImagens] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  
  // Fornecedores
  const [fornecedores, setFornecedores] = useState([]);
  const [showModalFornecedor, setShowModalFornecedor] = useState(false);
  const [fornecedorEdit, setFornecedorEdit] = useState(null);
  
  // Lotes
  const [lotes, setLotes] = useState([]);
  const [showModalLote, setShowModalLote] = useState(false);
  const [tipoMovimento, setTipoMovimento] = useState('entrada');
  
  // Variações (Sprint 2)
  const [variacoes, setVariacoes] = useState([]);
  const [loadingVariacoes, setLoadingVariacoes] = useState(false);
  
  // Carregar dados iniciais
  useEffect(() => {
    carregarCategorias();
    carregarMarcas();
    carregarClientes();
    
    if (isEdit) {
      carregarProduto();
    }
  }, [id]);
  
  const carregarCategorias = async () => {
    try {
      const response = await getCategorias({ apenas_ativas: true });
      setCategorias(response.data);
    } catch (error) {
      console.error('Erro ao carregar categorias:', error);
    }
  };
  
  const carregarMarcas = async () => {
    try {
      const response = await getMarcas({ apenas_ativas: true });
      setMarcas(response.data);
    } catch (error) {
      console.error('Erro ao carregar marcas:', error);
    }
  };
  
  const carregarClientes = async () => {
    try {
      const response = await api.get('/clientes', {
        params: { tipo: 'fornecedor', apenas_ativos: true }
      });
      setClientes(response.data);
    } catch (error) {
      console.error('Erro ao carregar clientes:', error);
    }
  };
  
  const carregarProduto = async () => {
    try {
      setLoading(true);
      const response = await getProduto(id);
      const prod = response.data;
      
      setProduto({
        codigo: prod.codigo || '',
        nome: prod.nome || '',
        descricao: prod.descricao || '',
        categoria_id: prod.categoria_id || '',
        marca_id: prod.marca_id || '',
        preco_custo: prod.preco_custo || '',
        preco_venda: prod.preco_venda || '',
        margem_lucro: prod.margem_lucro || '',
        estoque_minimo: prod.estoque_minimo || '',
        estoque_maximo: prod.estoque_maximo || '',
        localizacao: prod.localizacao || '',
        observacoes: prod.observacoes || '',
        controle_lote: prod.controle_lote || false,
        status: prod.status || 'ativo'
      });
      
      // Carregar imagens
      if (prod.imagens && prod.imagens.length > 0) {
        setImagens(prod.imagens);
      }
      
      // Carregar fornecedores
      carregarFornecedores();
      
      // Carregar lotes se tiver controle
      if (prod.controle_lote) {
        carregarLotes();
      }
      
      // 🔒 SPRINT 2: Carregar variações se for produto PAI
      if (prod.tipo_produto === 'PAI') {
        carregarVariacoes();
      }
      
    } catch (error) {
      console.error('Erro ao carregar produto:', error);
      alert('Erro ao carregar produto');
      navigate('/produtos');
    } finally {
      setLoading(false);
    }
  };
  
  const carregarFornecedores = async () => {
    if (!id) return;
    try {
      const response = await getFornecedoresProduto(id);
      setFornecedores(response.data);
    } catch (error) {
      console.error('Erro ao carregar fornecedores:', error);
    }
  };
  
  const carregarLotes = async () => {
    if (!id) return;
    try {
      const response = await getLotes(id);
      setLotes(response.data);
    } catch (error) {
      console.error('Erro ao carregar lotes:', error);
    }
  };
  
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setProduto(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Calcular margem automaticamente
    if (name === 'preco_custo' || name === 'preco_venda') {
      calcularMargem(
        name === 'preco_custo' ? value : produto.preco_custo,
        name === 'preco_venda' ? value : produto.preco_venda
      );
    }
  };
  
  const calcularMargem = (custo, venda) => {
    const c = parseFloat(custo) || 0;
    const v = parseFloat(venda) || 0;
    if (c > 0) {
      const margem = ((v - c) / c) * 100;
      setProduto(prev => ({
        ...prev,
        margem_lucro: margem.toFixed(2)
      }));
    }
  };
  
  // 🔒 SPRINT 2: Carregar variações do produto PAI
  const carregarVariacoes = async () => {
    if (!id) return;
    
    try {
      setLoadingVariacoes(true);
      const response = await api.get(`/produtos/${id}/variacoes`);
      setVariacoes(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar variações:', error);
      setVariacoes([]);
    } finally {
      setLoadingVariacoes(false);
    }
  };
  
  const handleGerarCodigo = async () => {
    try {
      const response = await gerarSKU();
      setProduto(prev => ({ ...prev, codigo: response.data.sku }));
    } catch (error) {
      console.error('Erro ao gerar código:', error);
      alert('Erro ao gerar código');
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validações
    if (!produto.nome.trim()) {
      alert('Nome do produto é obrigatório');
      return;
    }
    
    if (!produto.preco_venda || parseFloat(produto.preco_venda) <= 0) {
      alert('Preço de venda é obrigatório e deve ser maior que zero');
      return;
    }
    
    try {
      setSalvando(true);
      
      const dados = {
        ...produto,
        preco_custo: parseFloat(produto.preco_custo) || 0,
        preco_venda: parseFloat(produto.preco_venda) || 0,
        margem_lucro: parseFloat(produto.margem_lucro) || 0,
        estoque_minimo: parseFloat(produto.estoque_minimo) || 0,
        estoque_maximo: parseFloat(produto.estoque_maximo) || 0,
        categoria_id: produto.categoria_id || null,
        marca_id: produto.marca_id || null,
      };
      
      if (isEdit) {
        await updateProduto(id, dados);
        alert('Produto atualizado com sucesso!');
      } else {
        const response = await createProduto(dados);
        alert('Produto cadastrado com sucesso!');
        navigate(`/produtos/${response.data.id}/editar`);
      }
      
    } catch (error) {
      console.error('Erro ao salvar produto:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar produto');
    } finally {
      setSalvando(false);
    }
  };
  
  // ==================== IMAGENS ====================
  
  const handleUploadImagem = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validações
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('Apenas JPG, PNG e WebP são permitidos');
      return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
      alert('Imagem deve ter no máximo 5MB');
      return;
    }
    
    try {
      setUploadingImage(true);
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await uploadImagemProduto(id, formData);
      setImagens(prev => [...prev, response.data]);
      
      alert('Imagem enviada com sucesso!');
      
    } catch (error) {
      console.error('Erro ao enviar imagem:', error);
      alert(error.response?.data?.detail || 'Erro ao enviar imagem');
    } finally {
      setUploadingImage(false);
      e.target.value = '';
    }
  };
  
  const handleDeleteImagem = async (imagemId) => {
    if (!confirm('Deseja realmente excluir esta imagem?')) return;
    
    try {
      await deleteImagemProduto(imagemId);
      setImagens(prev => prev.filter(img => img.id !== imagemId));
      alert('Imagem excluída com sucesso!');
    } catch (error) {
      console.error('Erro ao excluir imagem:', error);
      alert('Erro ao excluir imagem');
    }
  };
  
  const handleSetPrincipal = async (imagemId) => {
    try {
      await api.put(`/produtos/imagens/${imagemId}`, { e_principal: true });
      setImagens(prev => prev.map(img => ({
        ...img,
        e_principal: img.id === imagemId
      })));
      alert('Imagem principal atualizada!');
    } catch (error) {
      console.error('Erro ao definir imagem principal:', error);
      alert('Erro ao definir imagem principal');
    }
  };
  
  // ==================== FORNECEDORES ====================
  
  const handleAddFornecedor = () => {
    setFornecedorEdit(null);
    setShowModalFornecedor(true);
  };
  
  const handleEditFornecedor = (fornecedor) => {
    setFornecedorEdit(fornecedor);
    setShowModalFornecedor(true);
  };
  
  const handleSaveFornecedor = async (dados) => {
    try {
      if (fornecedorEdit) {
        await updateFornecedorProduto(fornecedorEdit.id, dados);
        alert('Fornecedor atualizado!');
      } else {
        await addFornecedorProduto(id, dados);
        alert('Fornecedor vinculado!');
      }
      
      carregarFornecedores();
      setShowModalFornecedor(false);
      
    } catch (error) {
      console.error('Erro ao salvar fornecedor:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar fornecedor');
    }
  };
  
  const handleDeleteFornecedor = async (fornecedorId) => {
    if (!confirm('Deseja realmente desvincular este fornecedor?')) return;
    
    try {
      await deleteFornecedorProduto(fornecedorId);
      carregarFornecedores();
      alert('Fornecedor desvinculado!');
    } catch (error) {
      console.error('Erro ao desvincular fornecedor:', error);
      alert('Erro ao desvincular fornecedor');
    }
  };
  
  // ==================== LOTES ====================
  
  const handleMovimentoEstoque = (tipo) => {
    setTipoMovimento(tipo);
    setShowModalLote(true);
  };
  
  const handleSaveMovimento = async (dados) => {
    try {
      if (tipoMovimento === 'entrada') {
        await entradaEstoque(id, dados);
        alert('Entrada registrada com sucesso!');
      } else {
        await saidaFIFO(id, dados);
        alert('Saída registrada com sucesso!');
      }
      
      carregarLotes();
      carregarProduto();
      setShowModalLote(false);
      
    } catch (error) {
      console.error('Erro ao registrar movimento:', error);
      alert(error.response?.data?.detail || 'Erro ao registrar movimento');
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isEdit ? 'Editar Produto' : 'Novo Produto'}
            </h1>
            <p className="text-gray-600 mt-1">
              {isEdit ? `Código: ${produto.codigo}` : 'Preencha os dados do produto'}
            </p>
          </div>
          
          <button
            onClick={() => navigate('/produtos')}
            className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
          >
            ✕ Fechar
          </button>
        </div>
      </div>
      
      {/* Abas */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          <button
            onClick={() => setAbaAtiva('dados')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
              abaAtiva === 'dados'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📋 Dados Básicos
          </button>
          
          {isEdit && (
            <>
              <button
                onClick={() => setAbaAtiva('imagens')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                  abaAtiva === 'imagens'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🖼️ Imagens ({imagens.length})
              </button>
              
              <button
                onClick={() => setAbaAtiva('fornecedores')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                  abaAtiva === 'fornecedores'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🏭 Fornecedores ({fornecedores.length})
              </button>
              
              {produto.controle_lote && (
                <button
                  onClick={() => setAbaAtiva('lotes')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                    abaAtiva === 'lotes'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  📦 Lotes ({lotes.length})
                </button>
              )}
              
              {/* 🔒 SPRINT 2: Aba de Variações para produtos PAI */}
              {produto.tipo_produto === 'PAI' && (
                <button
                  onClick={() => setAbaAtiva('variacoes')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                    abaAtiva === 'variacoes'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  🔹 Variações ({variacoes.length})
                </button>
              )}
            </>
          )}
        </nav>
      </div>
      
      {/* Conteúdo das Abas */}
      {abaAtiva === 'dados' && (
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
          {/* Código e Nome */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Código / SKU
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  name="codigo"
                  value={produto.codigo}
                  onChange={handleChange}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="SKU-001"
                />
                <button
                  type="button"
                  onClick={handleGerarCodigo}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition"
                  title="Gerar código automaticamente"
                >
                  🔄
                </button>
              </div>
            </div>
            
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nome do Produto *
              </label>
              <input
                type="text"
                name="nome"
                value={produto.nome}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ex: Ração Premium para Cães Adultos 15kg"
              />
            </div>
          </div>
          
          {/* Descrição */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descrição
            </label>
            <textarea
              name="descricao"
              value={produto.descricao}
              onChange={handleChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Descrição detalhada do produto..."
            />
          </div>
          
          {/* Categoria e Marca */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Categoria
              </label>
              <select
                name="categoria_id"
                value={produto.categoria_id}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Selecione...</option>
                {categorias.map(cat => (
                  <option key={cat.id} value={cat.id}>
                    {cat.nome}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Marca
              </label>
              <select
                name="marca_id"
                value={produto.marca_id}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Selecione...</option>
                {marcas.map(marca => (
                  <option key={marca.id} value={marca.id}>
                    {marca.nome}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Preços e Margem */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preço de Custo
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                <input
                  type="number"
                  name="preco_custo"
                  value={produto.preco_custo}
                  onChange={handleChange}
                  step="0.01"
                  min="0"
                  className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0,00"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preço de Venda *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                <input
                  type="number"
                  name="preco_venda"
                  value={produto.preco_venda}
                  onChange={handleChange}
                  step="0.01"
                  min="0"
                  required
                  className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0,00"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Margem de Lucro (%)
              </label>
              <input
                type="number"
                name="margem_lucro"
                value={produto.margem_lucro}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
                placeholder="0,00"
              />
            </div>
          </div>
          
          {/* Estoque */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Estoque Mínimo
              </label>
              <input
                type="number"
                name="estoque_minimo"
                value={produto.estoque_minimo}
                onChange={handleChange}
                step="0.01"
                min="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Estoque Máximo
              </label>
              <input
                type="number"
                name="estoque_maximo"
                value={produto.estoque_maximo}
                onChange={handleChange}
                step="0.01"
                min="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Localização
              </label>
              <input
                type="text"
                name="localizacao"
                value={produto.localizacao}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ex: Prateleira A1"
              />
            </div>
          </div>
          
          {/* Controle de Lote e Status */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg">
              <input
                type="checkbox"
                name="controle_lote"
                checked={produto.controle_lote}
                onChange={handleChange}
                className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              />
              <div>
                <label className="text-sm font-medium text-gray-700 cursor-pointer">
                  Controlar por Lotes
                </label>
                <p className="text-xs text-gray-500">
                  Ativa o sistema FIFO de estoque por lotes
                </p>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <select
                name="status"
                value={produto.status}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="ativo">Ativo</option>
                <option value="inativo">Inativo</option>
              </select>
            </div>
          </div>
          
          {/* Observações */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observações
            </label>
            <textarea
              name="observacoes"
              value={produto.observacoes}
              onChange={handleChange}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Observações internas..."
            />
          </div>
          
          {/* Botões */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => navigate('/produtos')}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
            >
              Cancelar
            </button>
            
            <button
              type="submit"
              disabled={salvando}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"
            >
              {salvando ? 'Salvando...' : (isEdit ? 'Atualizar' : 'Cadastrar')}
            </button>
          </div>
        </form>
      )}
      
      {abaAtiva === 'imagens' && isEdit && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Imagens do Produto</h2>
            
            <label className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition cursor-pointer">
              {uploadingImage ? 'Enviando...' : '+ Adicionar Imagem'}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleUploadImagem}
                disabled={uploadingImage}
                className="hidden"
              />
            </label>
          </div>
          
          {imagens.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">📷 Nenhuma imagem cadastrada</p>
              <p className="text-sm">Clique em "Adicionar Imagem" para enviar fotos do produto</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-4">
              {imagens.map(img => (
                <div key={img.id} className="relative group border rounded-lg overflow-hidden">
                  <img
                    src={`http://localhost:8000${img.url}`}
                    alt={img.descricao || 'Imagem do produto'}
                    className="w-full h-48 object-cover"
                  />
                  
                  {img.e_principal && (
                    <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                      Principal
                    </div>
                  )}
                  
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                    {!img.e_principal && (
                      <button
                        onClick={() => handleSetPrincipal(img.id)}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        title="Definir como principal"
                      >
                        ⭐ Principal
                      </button>
                    )}
                    
                    <button
                      onClick={() => handleDeleteImagem(img.id)}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                      title="Excluir"
                    >
                      🗑️ Excluir
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Dica:</strong> A primeira imagem marcada como "Principal" será exibida na listagem de produtos. 
              Formatos aceitos: JPG, PNG, WebP (máx. 5MB).
            </p>
          </div>
        </div>
      )}
      
      {abaAtiva === 'fornecedores' && isEdit && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Fornecedores do Produto</h2>
            
            <button
              onClick={handleAddFornecedor}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              + Adicionar Fornecedor
            </button>
          </div>
          
          {fornecedores.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">🏭 Nenhum fornecedor vinculado</p>
              <p className="text-sm">Clique em "Adicionar Fornecedor" para vincular fornecedores a este produto</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fornecedor</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Preço Custo</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Prazo (dias)</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Principal</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {fornecedores.map(forn => (
                    <tr key={forn.id} className={!forn.ativo ? 'opacity-50' : ''}>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{forn.fornecedor_nome}</p>
                          <p className="text-xs text-gray-500">{forn.fornecedor_cpf_cnpj}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">{forn.codigo_fornecedor || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-right">
                        {forn.preco_custo ? formatarMoeda(forn.preco_custo) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.prazo_entrega || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.estoque_fornecedor || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        {forn.e_principal && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Principal</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <button
                          onClick={() => handleEditFornecedor(forn)}
                          className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDeleteFornecedor(forn.id)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Excluir
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      
      {abaAtiva === 'lotes' && isEdit && produto.controle_lote && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Controle de Lotes (FIFO)</h2>
            
            <div className="flex gap-2">
              <button
                onClick={() => handleMovimentoEstoque('entrada')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                ➕ Entrada
              </button>
              <button
                onClick={() => handleMovimentoEstoque('saida')}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                ➖ Saída
              </button>
            </div>
          </div>
          
          {lotes.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">📦 Nenhum lote cadastrado</p>
              <p className="text-sm">Registre uma entrada de estoque para criar o primeiro lote</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lote</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Qtd Atual</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Qtd Inicial</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo Unit.</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Validade</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Data Entrada</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {lotes.map(lote => (
                    <tr key={lote.id} className={lote.quantidade_atual === 0 ? 'opacity-50' : ''}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{lote.numero_lote}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center font-semibold">
                        {lote.quantidade_atual}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 text-center">{lote.quantidade_inicial}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-right">
                        {formatarMoeda(lote.preco_custo)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center">
                        {lote.data_validade ? formatarData(lote.data_validade) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 text-center">
                        {formatarData(lote.data_entrada)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">
              <strong>FIFO:</strong> As saídas de estoque consomem automaticamente os lotes mais antigos primeiro (First In, First Out).
            </p>
          </div>
        </div>
      )}
      
      {/* 🔒 SPRINT 2: Aba de Variações para produtos PAI */}
      {abaAtiva === 'variacoes' && isEdit && produto.tipo_produto === 'PAI' && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Variações do Produto</h2>
              <p className="text-sm text-gray-500 mt-1">
                Gerencie as variações deste produto (cor, tamanho, etc.)
              </p>
            </div>
            
            <button
              onClick={() => navigate(`/produtos/novo?produto_pai_id=${id}`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
            >
              <span>➕</span> Nova Variação
            </button>
          </div>
          
          {loadingVariacoes ? (
            <div className="text-center py-12 text-gray-500">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4">Carregando variações...</p>
            </div>
          ) : variacoes.length === 0 ? (
            <div className="text-center py-12 text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
              <p className="text-lg mb-2">🔹 Nenhuma variação cadastrada</p>
              <p className="text-sm mb-4">Este produto não possui variações ainda</p>
              <button
                onClick={() => navigate(`/produtos/novo?produto_pai_id=${id}`)}
                className="text-blue-600 hover:underline font-medium"
              >
                Criar primeira variação →
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Tabela de Variações */}
              <div className="overflow-x-auto border border-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Variação</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Código</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Preço</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {variacoes.map(variacao => (
                      <tr key={variacao.id} className="hover:bg-gray-50 transition">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">{variacao.nome}</span>
                          </div>
                          {variacao.variation_signature && (
                            <div className="text-xs text-gray-500 mt-1">
                              {variacao.variation_signature.split('|').join(' • ')}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-sm font-mono text-gray-600">{variacao.codigo}</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-semibold text-gray-900">
                            {formatarMoeda(variacao.preco_venda)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            (variacao.estoque_atual || 0) > 0 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {variacao.estoque_atual || 0}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            variacao.ativo 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {variacao.ativo ? 'Ativo' : 'Inativo'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => navigate(`/produtos/${variacao.id}/editar`)}
                              className="text-blue-600 hover:text-blue-900 transition"
                              title="Editar variação"
                            >
                              ✏️
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Informações */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  <strong>💡 Dica:</strong> Cada variação funciona como um produto independente com preço e estoque próprios.
                  O produto pai serve apenas como agrupador e não pode ser vendido diretamente.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Modais */}
      {showModalFornecedor && (
        <ModalFornecedor
          fornecedor={fornecedorEdit}
          clientes={clientes}
          onSave={handleSaveFornecedor}
          onClose={() => setShowModalFornecedor(false)}
        />
      )}
      
      {showModalLote && (
        <ModalMovimentoEstoque
          tipo={tipoMovimento}
          onSave={handleSaveMovimento}
          onClose={() => setShowModalLote(false)}
        />
      )}
    </div>
  );
}

// ==================== MODAL FORNECEDOR ====================

function ModalFornecedor({ fornecedor, clientes, onSave, onClose }) {
  const [dados, setDados] = useState({
    fornecedor_id: fornecedor?.fornecedor_id || '',
    codigo_fornecedor: fornecedor?.codigo_fornecedor || '',
    preco_custo: fornecedor?.preco_custo || '',
    prazo_entrega: fornecedor?.prazo_entrega || '',
    estoque_fornecedor: fornecedor?.estoque_fornecedor || '',
    e_principal: fornecedor?.e_principal || false,
  });
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      ...dados,
      preco_custo: parseFloat(dados.preco_custo) || null,
      prazo_entrega: parseInt(dados.prazo_entrega) || null,
      estoque_fornecedor: parseFloat(dados.estoque_fornecedor) || null,
    });
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold">
            {fornecedor ? 'Editar Fornecedor' : 'Adicionar Fornecedor'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fornecedor *
            </label>
            <select
              value={dados.fornecedor_id}
              onChange={(e) => setDados({ ...dados, fornecedor_id: e.target.value })}
              required
              disabled={Boolean(fornecedor)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione...</option>
              {clientes.map(cli => (
                <option key={cli.id} value={cli.id}>{cli.nome}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Código no Fornecedor
            </label>
            <input
              type="text"
              value={dados.codigo_fornecedor}
              onChange={(e) => setDados({ ...dados, codigo_fornecedor: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="SKU-FORNECEDOR-001"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preço de Custo
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
              <input
                type="number"
                value={dados.preco_custo}
                onChange={(e) => setDados({ ...dados, preco_custo: e.target.value })}
                step="0.01"
                min="0"
                className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0,00"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Prazo de Entrega (dias)
            </label>
            <input
              type="number"
              value={dados.prazo_entrega}
              onChange={(e) => setDados({ ...dados, prazo_entrega: e.target.value })}
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="7"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Estoque no Fornecedor
            </label>
            <input
              type="number"
              value={dados.estoque_fornecedor}
              onChange={(e) => setDados({ ...dados, estoque_fornecedor: e.target.value })}
              step="0.01"
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="100"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={dados.e_principal}
              onChange={(e) => setDados({ ...dados, e_principal: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded"
            />
            <label className="text-sm font-medium text-gray-700">
              Fornecedor Principal
            </label>
          </div>
          
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Salvar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==================== MODAL MOVIMENTO ESTOQUE ====================

function ModalMovimentoEstoque({ tipo, onSave, onClose }) {
  const [dados, setDados] = useState({
    quantidade: '',
    numero_lote: '',
    preco_custo: '',
    data_validade: '',
    observacao: '',
  });
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    const payload = {
      quantidade: parseFloat(dados.quantidade),
      observacao: dados.observacao || null,
    };
    
    if (tipo === 'entrada') {
      payload.numero_lote = dados.numero_lote || null;
      payload.preco_custo = parseFloat(dados.preco_custo) || 0;
      payload.data_validade = dados.data_validade || null;
    }
    
    onSave(payload);
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold">
            {tipo === 'entrada' ? '➕ Entrada de Estoque' : '➖ Saída de Estoque'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Quantidade *
            </label>
            <input
              type="number"
              value={dados.quantidade}
              onChange={(e) => setDados({ ...dados, quantidade: e.target.value })}
              step="0.01"
              min="0.01"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="0"
              autoFocus
            />
          </div>
          
          {tipo === 'entrada' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Número do Lote
                </label>
                <input
                  type="text"
                  value={dados.numero_lote}
                  onChange={(e) => setDados({ ...dados, numero_lote: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="LOTE-001"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preço de Custo
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                  <input
                    type="number"
                    value={dados.preco_custo}
                    onChange={(e) => setDados({ ...dados, preco_custo: e.target.value })}
                    step="0.01"
                    min="0"
                    className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0,00"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data de Validade
                </label>
                <input
                  type="date"
                  value={dados.data_validade}
                  onChange={(e) => setDados({ ...dados, data_validade: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observação
            </label>
            <textarea
              value={dados.observacao}
              onChange={(e) => setDados({ ...dados, observacao: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Observações sobre este movimento..."
            />
          </div>
          
          {tipo === 'saida' && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>FIFO:</strong> A saída será descontada automaticamente dos lotes mais antigos primeiro.
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className={`px-4 py-2 text-white rounded-lg ${
                tipo === 'entrada'
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              Confirmar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
