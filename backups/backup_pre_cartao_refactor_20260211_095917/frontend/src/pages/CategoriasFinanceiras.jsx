import React, { useState, useEffect } from 'react';
import { FiPlus, FiEdit2, FiTrash2, FiTag, FiChevronDown, FiChevronRight } from 'react-icons/fi';
import api from '../api';
import { toast } from 'react-hot-toast';

const CategoriasFinanceiras = () => {
  const [categorias, setCategorias] = useState([]);
  const [subcategoriasDRE, setSubcategoriasDRE] = useState([]); // Subcategorias DRE
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showSubModal, setShowSubModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [editandoSub, setEditandoSub] = useState(null);
  const [categoriaExpandida, setCategoriaExpandida] = useState(new Set());
  const [filtroTipo, setFiltroTipo] = useState('todos');
  
  const [formData, setFormData] = useState({
    nome: '',
    tipo: 'despesa',
    cor: '#6366f1',
    icone: '📋',
    descricao: '',
    ativo: true,
    novasSubcategorias: []
  });

  const [formSubData, setFormSubData] = useState({
    categoria_id: null,
    nome: '',
    descricao: '',
    ativo: true
  });

  const icones = ['💰', '💸', '📋', '🏠', '⚡', '💧', '📡', '👥', '📦', '🔧', '🚗', '🍽️', '📝', '🛡️', '🛒', '✨', '🐕', '🩺', '🏨', '🎓'];
  const cores = ['#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899'];

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    await Promise.all([
      carregarCategorias(),
      carregarSubcategoriasDRE()
    ]);
  };

  const carregarCategorias = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/categorias-financeiras/');
      console.log('📂 Categorias carregadas:', response.data.length);
      console.log('🔍 Primeira categoria:', response.data[0]);
      setCategorias(response.data);
    } catch (error) {
      console.error('Erro ao carregar categorias:', error);
      toast.error('Erro ao carregar categorias financeiras');
    } finally {
      setLoading(false);
    }
  };

  const carregarSubcategoriasDRE = async () => {
    try {
      console.log('🔄 Iniciando carregamento de subcategorias DRE...');
      // ✅ OFICIAL: Busca todas as subcategorias DRE do tenant (PostgreSQL multi-tenant)
      const response = await api.get('/dre/subcategorias');
      console.log('✅ Resposta recebida:', response);
      console.log('📋 Subcategorias DRE carregadas:', response.data.length);
      console.log('🔍 Primeira subcategoria:', response.data[0]);
      console.log('📦 Todas as subcategorias:', response.data);
      setSubcategoriasDRE(response.data);
    } catch (error) {
      console.error('❌ ERRO ao carregar subcategorias DRE:', error);
      console.error('❌ Erro completo:', error.response?.data || error.message);
      console.error('❌ Status:', error.response?.status);
      // Retorna array vazio para não quebrar a UI
      setSubcategoriasDRE([]);
    }
  };

  const toggleExpansao = (categoriaId) => {
    const novasExpandidas = new Set(categoriaExpandida);
    if (novasExpandidas.has(categoriaId)) {
      novasExpandidas.delete(categoriaId);
    } else {
      novasExpandidas.add(categoriaId);
    }
    setCategoriaExpandida(novasExpandidas);
  };

  // Busca TODAS as Subcategorias DRE vinculadas à Categoria Financeira
  // Agora agrupa por categoria_id (não mais por dre_subcategoria_id individual)
  const getSubcategoriasDREDaCategoria = (categoria) => {
    // Se a categoria não tem dre_subcategoria_id, não tem vínculo DRE
    if (!categoria.dre_subcategoria_id) {
      return [];
    }
    
    // Buscar a subcategoria DRE principal vinculada
    const subPrincipal = subcategoriasDRE.find(s => s.id === categoria.dre_subcategoria_id);
    
    if (!subPrincipal) {
      console.log(`⚠️ Categoria "${categoria.nome}" tem dre_subcategoria_id=${categoria.dre_subcategoria_id} mas não encontrada`);
      return [];
    }
    
    // Retornar TODAS as subcategorias da mesma categoria DRE
    const todasSubcategorias = subcategoriasDRE.filter(s => s.categoria_id === subPrincipal.categoria_id);
    
    console.log(`📦 Categoria "${categoria.nome}" → ${todasSubcategorias.length} subcategorias DRE`);
    return todasSubcategorias;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.nome || !formData.tipo) {
      toast.error('Preencha nome e tipo');
      return;
    }

    try {
      let categoriaId;
      
      if (editando) {
        await api.put(`/api/categorias-financeiras/${editando}`, {
          nome: formData.nome,
          tipo: formData.tipo,
          cor: formData.cor,
          icone: formData.icone,
          descricao: formData.descricao,
          ativo: formData.ativo
        });
        categoriaId = editando;
        toast.success('Categoria atualizada com sucesso!');
      } else {
        const response = await api.post('/api/categorias-financeiras/', {
          nome: formData.nome,
          tipo: formData.tipo,
          cor: formData.cor,
          icone: formData.icone,
          descricao: formData.descricao,
          ativo: formData.ativo
        });
        categoriaId = response.data.id;
        toast.success('Categoria criada com sucesso!');

        // Criar subcategorias se houver
        if (formData.novasSubcategorias.length > 0) {
          const subsValidas = formData.novasSubcategorias.filter(sub => sub.nome.trim());
          for (const sub of subsValidas) {
            try {
              await api.post('/subcategorias/', {
                categoria_id: categoriaId,
                nome: sub.nome,
                descricao: sub.descricao,
                ativo: sub.ativo
              });
            } catch (subError) {
              console.error('Erro ao criar subcategoria:', subError);
              toast.error(`Erro ao criar subcategoria: ${sub.nome}`);
            }
          }
          if (subsValidas.length > 0) {
            toast.success(`${subsValidas.length} subcategoria(s) criada(s)!`);
          }
        }
      }
      
      setShowModal(false);
      resetForm();
      carregarDados(); // Recarrega categorias E subcategorias DRE
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar categoria');
    }
  };

  const handleEdit = async (categoria) => {
    // Carregar TODAS as subcategorias DRE vinculadas a esta categoria
    console.log(`🔧 Editando categoria "${categoria.nome}" (ID: ${categoria.id})`);
    
    // Buscar todas as subcategorias DRE desta categoria
    const subs = getSubcategoriasDREDaCategoria(categoria);
    console.log(`📦 Subcategorias DRE encontradas: ${subs.length}`, subs);
    
    const subsExistentes = subs.map(sub => ({
      id: sub.id,
      nome: sub.nome,
      descricao: sub.descricao || '',
      ativo: sub.ativo,
      tipo_custo: sub.tipo_custo,
      escopo_rateio: sub.escopo_rateio
    }));

    setFormData({
      nome: categoria.nome,
      tipo: categoria.tipo,
      cor: categoria.cor || '#6366f1',
      icone: categoria.icone || '📋',
      descricao: categoria.descricao || '',
      ativo: categoria.ativo,
      novasSubcategorias: subsExistentes
    });
    setEditando(categoria.id);
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Deseja realmente excluir esta categoria?')) return;
    
    try {
      await api.delete(`/api/categorias-financeiras/${id}`);
      toast.success('Categoria excluída com sucesso!');
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir categoria');
    }
  };

  const resetForm = () => {
    setFormData({
      nome: '',
      tipo: 'despesa',
      cor: '#6366f1',
      icone: '📋',
      descricao: '',
      ativo: true,
      novasSubcategorias: []
    });
    setEditando(null);
  };

  const adicionarSubcategoriaNova = (nome = '') => {
    setFormData({
      ...formData,
      novasSubcategorias: [...formData.novasSubcategorias, { nome, descricao: '', ativo: true }]
    });
  };

  const atualizarSubcategoriaNova = (index, field, value) => {
    const novasSubs = [...formData.novasSubcategorias];
    novasSubs[index][field] = value;
    setFormData({ ...formData, novasSubcategorias: novasSubs });
  };

  const removerSubcategoriaNova = (index) => {
    const novasSubs = formData.novasSubcategorias.filter((_, i) => i !== index);
    setFormData({ ...formData, novasSubcategorias: novasSubs });
  };

  const handleKeyDownSubcategoria = (e, index) => {
    if (e.key === 'Tab' && !e.shiftKey && index === formData.novasSubcategorias.length - 1) {
      e.preventDefault();
      adicionarSubcategoriaNova();
    }
  };

  const resetSubForm = () => {
    setFormSubData({
      categoria_id: null,
      nome: '',
      descricao: '',
      ativo: true
    });
    setEditandoSub(null);
  };

  const handleSubmitSub = async (e) => {
    e.preventDefault();
    
    if (!formSubData.categoria_id || !formSubData.nome) {
      toast.error('Preencha categoria e nome');
      return;
    }

    try {
      if (editandoSub) {
        await api.put(`/subcategorias/${editandoSub}`, formSubData);
        toast.success('Subcategoria atualizada!');
      } else {
        await api.post('/subcategorias', formSubData);
        toast.success('Subcategoria criada!');
      }
      
      setShowSubModal(false);
      resetSubForm();
      carregarSubcategorias();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar subcategoria');
    }
  };

  const handleEditSub = (sub) => {
    setFormSubData({
      categoria_id: sub.categoria_id,
      nome: sub.nome,
      descricao: sub.descricao || '',
      ativo: sub.ativo
    });
    setEditandoSub(sub.id);
    setShowSubModal(true);
  };

  const handleDeleteSub = async (id) => {
    if (!window.confirm('Deseja realmente excluir esta subcategoria?')) return;
    
    try {
      await api.delete(`/subcategorias/${id}`);
      toast.success('Subcategoria excluída!');
      carregarSubcategorias();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir subcategoria');
    }
  };

  const abrirModalSubcategoria = (categoriaId) => {
    setFormSubData({
      categoria_id: categoriaId,
      nome: '',
      descricao: '',
      ativo: true
    });
    setShowSubModal(true);
  };

  const categoriasFiltradas = categorias.filter(cat => {
    if (filtroTipo === 'todos') return true;
    return cat.tipo === filtroTipo;
  });

  const countDespesas = categorias.filter(c => c.tipo === 'despesa').length;
  const countReceitas = categorias.filter(c => c.tipo === 'receita').length;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">🏷️ Categorias Financeiras</h2>
          <p className="text-gray-600 mt-1">
            Organize suas receitas e despesas | 
            <span className="text-red-600 ml-2">💸 {countDespesas} despesas</span>
            <span className="text-green-600 ml-2">💰 {countReceitas} receitas</span>
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          <FiPlus /> Nova Categoria
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setFiltroTipo('todos')}
            className={`px-4 py-2 rounded-lg ${filtroTipo === 'todos' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            📊 Todas ({categorias.length})
          </button>
          <button
            onClick={() => setFiltroTipo('despesa')}
            className={`px-4 py-2 rounded-lg ${filtroTipo === 'despesa' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            💸 Despesas ({countDespesas})
          </button>
          <button
            onClick={() => setFiltroTipo('receita')}
            className={`px-4 py-2 rounded-lg ${filtroTipo === 'receita' ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            💰 Receitas ({countReceitas})
          </button>
        </div>
      </div>

      {/* Tabela em Cascata */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <div className="px-6 py-8 text-center text-gray-500">
            Carregando...
          </div>
        ) : categoriasFiltradas.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            Nenhuma categoria encontrada
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {categoriasFiltradas.map((cat) => {
              const subsDRE = getSubcategoriasDREDaCategoria(cat);
              const isExpanded = categoriaExpandida.has(cat.id);
              const temSubcategoria = subsDRE.length > 0;
              
              return (
                <div key={cat.id}>
                  {/* Categoria Principal */}
                  <div className="px-6 py-4 hover:bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      {/* Botão Expandir/Recolher - MELHORADO */}
                      <button
                        onClick={() => toggleExpansao(cat.id)}
                        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 transform hover:scale-105 ${
                          !temSubcategoria 
                            ? 'text-gray-300 cursor-not-allowed bg-gray-50' 
                            : isExpanded
                              ? 'text-white bg-gradient-to-r from-purple-600 to-purple-700 shadow-lg hover:shadow-xl'
                              : 'text-purple-600 bg-purple-100 hover:bg-purple-200 hover:text-purple-700 shadow-md hover:shadow-lg'
                        }`}
                        disabled={!temSubcategoria}
                        title={!temSubcategoria ? 'Sem subcategorias DRE' : isExpanded ? 'Recolher subcategorias' : 'Expandir subcategorias'}
                      >
                        {temSubcategoria ? (
                          isExpanded ? <FiChevronDown size={22} strokeWidth={2.5} /> : <FiChevronRight size={22} strokeWidth={2.5} />
                        ) : (
                          <FiChevronRight size={22} />
                        )}
                      </button>
                      
                      {/* Ícone e Nome */}
                      <div className="flex items-center gap-3 flex-1">
                        <span style={{ backgroundColor: cat.cor }} className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg">
                          {cat.icone || '📋'}
                        </span>
                        <div>
                          <div className="font-semibold text-gray-800">{cat.nome}</div>
                          {cat.descricao && (
                            <div className="text-sm text-gray-500">{cat.descricao}</div>
                          )}
                        </div>
                      </div>
                      
                      {/* Badges */}
                      <div className="flex items-center gap-2">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          cat.tipo === 'receita' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {cat.tipo === 'receita' ? '💰 Receita' : '💸 Despesa'}
                        </span>
                        
                        {temSubcategoria && (
                          <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium flex items-center gap-1">
                            <span>📊 DRE</span>
                            <span className="bg-purple-200 text-purple-900 px-1.5 rounded-full font-bold">
                              {subsDRE.length}
                            </span>
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Ações */}
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => handleEdit(cat)}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
                        title="Editar"
                      >
                        <FiEdit2 size={18} />
                      </button>
                      <button
                        onClick={() => handleDelete(cat.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-md"
                        title="Excluir"
                      >
                        <FiTrash2 size={18} />
                      </button>
                    </div>
                  </div>
                  
                  {/* Subcategorias DRE (Expansível) */}
                  {isExpanded && (
                    <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-t border-purple-100">
                      {temSubcategoria ? (
                        <>
                          <div className="px-6 py-2 bg-purple-100/50 border-b border-purple-200">
                            <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                              🏗️ Subcategorias DRE ({subsDRE.length})
                            </span>
                          </div>
                          {subsDRE.map((sub) => (
                            <div key={sub.id} className="px-6 py-3 flex items-center gap-4 ml-9">
                            <span className="text-purple-400 text-lg">└─</span>
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-700">{sub.nome}</div>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded">
                                  {sub.tipo_custo}
                                </span>
                                {sub.escopo_rateio && (
                                  <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded">
                                    {sub.escopo_rateio}
                                  </span>
                                )}
                              </div>
                            </div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              sub.ativo 
                                ? 'bg-green-100 text-green-700' 
                                : 'bg-gray-200 text-gray-600'
                            }`}>
                              {sub.ativo ? '✓ Ativo' : '✗ Inativo'}
                            </span>
                          </div>
                        ))}
                        </>
                      ) : (
                        <div className="px-6 py-4 ml-9 text-center">
                          <div className="text-gray-400 text-sm">
                            <div className="mb-2">📭</div>
                            <div className="font-medium">Nenhuma subcategoria DRE cadastrada</div>
                            <div className="text-xs mt-1">Configure subcategorias no módulo DRE</div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
            <div className="flex justify-between items-center p-6 border-b">
              <h3 className="text-xl font-bold">
                {editando ? 'Editar Categoria' : 'Nova Categoria'}
              </h3>
              <button onClick={() => { setShowModal(false); resetForm(); }} className="text-gray-500 hover:text-gray-700">
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({...formData, nome: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo *
                </label>
                <select
                  value={formData.tipo}
                  onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="despesa">💸 Despesa</option>
                  <option value="receita">💰 Receita</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ícone
                  </label>
                  <select
                    value={formData.icone}
                    onChange={(e) => setFormData({...formData, icone: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  >
                    {icones.map(i => (
                      <option key={i} value={i}>{i}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cor
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={formData.cor}
                      onChange={(e) => setFormData({...formData, cor: e.target.value})}
                      className="w-12 h-10 border border-gray-300 rounded-md"
                    />
                    <select
                      value={formData.cor}
                      onChange={(e) => setFormData({...formData, cor: e.target.value})}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      {cores.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({...formData, descricao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  rows="3"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="ativo"
                  checked={formData.ativo}
                  onChange={(e) => setFormData({...formData, ativo: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label htmlFor="ativo" className="text-sm text-gray-700">
                  Categoria ativa
                </label>
              </div>

              {/* Subcategorias DRE */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Subcategorias DRE (opcional)
                  </label>
                  <button
                    type="button"
                    onClick={() => adicionarSubcategoriaNova()}
                    className="text-sm text-purple-600 hover:text-purple-800 flex items-center gap-1"
                  >
                    <FiPlus size={14} /> Adicionar
                  </button>
                </div>

                {formData.novasSubcategorias.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                      {formData.novasSubcategorias.map((sub, index) => (
                        <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-md">
                          <input
                            type="text"
                            value={sub.nome}
                            onChange={(e) => atualizarSubcategoriaNova(index, 'nome', e.target.value)}
                            onKeyDown={(e) => handleKeyDownSubcategoria(e, index)}
                            placeholder="Nome da subcategoria (Tab para adicionar mais)"
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                          />
                          <button
                            type="button"
                            onClick={() => removerSubcategoriaNova(index)}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Remover"
                          >
                            <FiTrash2 size={16} />
                          </button>
                        </div>
                      ))}
                  </div>
                )}

                {formData.novasSubcategorias.length === 0 && (
                  <p className="text-sm text-gray-500 italic">
                    Clique em "Adicionar" ou crie a categoria primeiro e depois adicione subcategorias
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editando ? 'Atualizar' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Subcategoria */}
      {showSubModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">
              {editandoSub ? 'Editar Subcategoria DRE' : 'Nova Subcategoria DRE'}
            </h2>
            
            {/* Mostrar categoria pai */}
            {formSubData.categoria_id && categorias.find(c => c.id === formSubData.categoria_id) && (
              <div className="mb-4 p-3 bg-blue-50 rounded-md border border-blue-200">
                <span className="text-sm text-gray-600">Categoria: </span>
                <span className="font-semibold text-gray-800">
                  {categorias.find(c => c.id === formSubData.categoria_id).nome}
                </span>
              </div>
            )}

            <form onSubmit={handleSubmitSub}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome da Subcategoria *
                </label>
                <input
                  type="text"
                  value={formSubData.nome}
                  onChange={(e) => setFormSubData({...formSubData, nome: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  required
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formSubData.descricao}
                  onChange={(e) => setFormSubData({...formSubData, descricao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows="3"
                />
              </div>

              <div className="mb-6">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formSubData.ativo}
                    onChange={(e) => setFormSubData({...formSubData, ativo: e.target.checked})}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium text-gray-700">Ativo</span>
                </label>
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => { setShowSubModal(false); resetSubForm(); }}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editandoSub ? 'Atualizar' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoriasFinanceiras;
