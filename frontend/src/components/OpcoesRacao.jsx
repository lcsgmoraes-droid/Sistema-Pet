import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Save, X, Settings, ChevronRight } from 'lucide-react';
import api from '../api';
import toast from 'react-hot-toast';
import { getGuiaClassNames } from '../utils/guiaHighlight';

function OpcoesRacao() {
  const guiaAtiva = new URLSearchParams(window.location.search).get('guia');
  const destacarOpcoesRacao = guiaAtiva === 'racao-opcoes';
  const guiaClasses = getGuiaClassNames(destacarOpcoesRacao);
  const [abaAtiva, setAbaAtiva] = useState('linhas');
  const [dados, setDados] = useState({});
  const [loading, setLoading] = useState(false);
  const [editando, setEditando] = useState(null);
  const [formData, setFormData] = useState({ nome: '', descricao: '', ordem: 0, ativo: true });
  const [formPeso, setFormPeso] = useState({ peso_kg: 0, descricao: '', ordem: 0, ativo: true });

  const abas = [
    { id: 'linhas', nome: 'Linhas de Ração', endpoint: '/opcoes-racao/linhas', icon: '📦' },
    { id: 'portes', nome: 'Portes', endpoint: '/opcoes-racao/portes', icon: '🐕' },
    { id: 'fases', nome: 'Fases/Público', endpoint: '/opcoes-racao/fases', icon: '👶' },
    { id: 'tratamentos', nome: 'Tratamentos', endpoint: '/opcoes-racao/tratamentos', icon: '💊' },
    { id: 'sabores', nome: 'Sabores/Proteínas', endpoint: '/opcoes-racao/sabores', icon: '🍖' },
    { id: 'apresentacoes', nome: 'Apresentações (Peso)', endpoint: '/opcoes-racao/apresentacoes', icon: '⚖️' },
  ];

  const abaConfig = abas.find(a => a.id === abaAtiva);

  useEffect(() => {
    carregarDados();
  }, [abaAtiva]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const response = await api.get(abaConfig.endpoint, {
        params: { apenas_ativos: false }
      });
      setDados(prev => ({ ...prev, [abaAtiva]: response.data }));
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error(`Erro ao carregar ${abaConfig.nome.toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({ nome: '', descricao: '', ordem: 0, ativo: true });
    setFormPeso({ peso_kg: 0, descricao: '', ordem: 0, ativo: true });
    setEditando(null);
  };

  const handleEditar = (item) => {
    setEditando(item.id);
    if (abaAtiva === 'apresentacoes') {
      setFormPeso({
        peso_kg: item.peso_kg,
        descricao: item.descricao || '',
        ordem: item.ordem || 0,
        ativo: item.ativo
      });
    } else {
      setFormData({
        nome: item.nome,
        descricao: item.descricao || '',
        ordem: item.ordem || 0,
        ativo: item.ativo
      });
    }
  };

  const handleSalvar = async () => {
    try {
      const payload = abaAtiva === 'apresentacoes' ? formPeso : formData;
      
      if (editando) {
        // Atualizar
        await api.put(`${abaConfig.endpoint}/${editando}`, payload);
        toast.success('Atualizado com sucesso!');
      } else {
        // Criar novo
        await api.post(abaConfig.endpoint, payload);
        toast.success('Criado com sucesso!');
      }
      
      resetForm();
      carregarDados();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar');
    }
  };

  const handleDeletar = async (id) => {
    if (!confirm('Tem certeza que deseja inativar este item?')) return;
    
    try {
      await api.delete(`${abaConfig.endpoint}/${id}`);
      toast.success('Inativado com sucesso!');
      carregarDados();
    } catch (error) {
      console.error('Erro ao deletar:', error);
      toast.error('Erro ao inativar');
    }
  };

  const dadosAba = dados[abaAtiva] || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {destacarOpcoesRacao && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: escolha a aba e use o formulario <strong>Adicionar Novo</strong> para cadastrar as opcoes de classificacao.
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-8 h-8 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-800">
            Opções de Classificação de Rações
          </h1>
        </div>
        <p className="text-gray-600">
          Gerencie os valores disponíveis para classificação de produtos de ração
        </p>
      </div>

      {/* Abas */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex overflow-x-auto">
            {abas.map((aba) => (
              <button
                key={aba.id}
                onClick={() => {
                  setAbaAtiva(aba.id);
                  resetForm();
                }}
                className={`
                  flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap
                  ${abaAtiva === aba.id
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <span className="text-xl">{aba.icon}</span>
                {aba.nome}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Formulário de Criação/Edição */}
        <div className="lg:col-span-1">
          <div
            className={`bg-white rounded-lg shadow p-6 ${
              destacarOpcoesRacao ? guiaClasses.box : ''
            }`}
          >
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              {editando ? 'Editar' : 'Adicionar Novo'}
            </h2>

            {abaAtiva === 'apresentacoes' ? (
              // Form para apresentações (peso)
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Peso (kg) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    value={formPeso.peso_kg}
                    onChange={(e) => setFormPeso({ ...formPeso, peso_kg: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Ex: 15.0"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descrição
                  </label>
                  <input
                    type="text"
                    value={formPeso.descricao}
                    onChange={(e) => setFormPeso({ ...formPeso, descricao: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Ex: 15kg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ordem
                  </label>
                  <input
                    type="number"
                    value={formPeso.ordem}
                    onChange={(e) => setFormPeso({ ...formPeso, ordem: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="ativo-peso"
                    checked={formPeso.ativo}
                    onChange={(e) => setFormPeso({ ...formPeso, ativo: e.target.checked })}
                    className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                  />
                  <label htmlFor="ativo-peso" className="text-sm text-gray-700">
                    Ativo
                  </label>
                </div>
              </div>
            ) : (
              // Form padrão (nome, descrição, etc)
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome *
                  </label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder={`Ex: ${abaAtiva === 'linhas' ? 'Premium' : abaAtiva === 'portes' ? 'Pequeno' : 'Filhote'}`}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descrição
                  </label>
                  <textarea
                    value={formData.descricao}
                    onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    rows="2"
                    placeholder="Descrição opcional"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ordem
                  </label>
                  <input
                    type="number"
                    value={formData.ordem}
                    onChange={(e) => setFormData({ ...formData, ordem: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="ativo"
                    checked={formData.ativo}
                    onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                    className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                  />
                  <label htmlFor="ativo" className="text-sm text-gray-700">
                    Ativo
                  </label>
                </div>
              </div>
            )}

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleSalvar}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
              >
                <Save className="w-4 h-4" />
                {editando ? 'Atualizar' : 'Adicionar'}
              </button>
              
              {editando && (
                <button
                  onClick={resetForm}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Lista de Itens */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                {abaConfig.nome} Cadastrados ({dadosAba.length})
              </h2>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  <span className="ml-3 text-gray-600">Carregando...</span>
                </div>
              ) : dadosAba.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-gray-400 mb-2">
                    <Plus className="w-16 h-16 mx-auto" />
                  </div>
                  <p className="text-gray-600">Nenhum item cadastrado ainda</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Use o formulário ao lado para adicionar
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {dadosAba.map((item) => (
                    <div
                      key={item.id}
                      className={`
                        flex items-center justify-between p-4 border rounded-lg transition
                        ${editando === item.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}
                        ${!item.ativo && 'opacity-50'}
                      `}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{abaConfig.icon}</span>
                          <div>
                            <h3 className="font-medium text-gray-900">
                              {abaAtiva === 'apresentacoes' ? (
                                `${item.peso_kg}kg${item.descricao ? ` - ${item.descricao}` : ''}`
                              ) : (
                                item.nome
                              )}
                            </h3>
                            {item.descricao && abaAtiva !== 'apresentacoes' && (
                              <p className="text-sm text-gray-500">{item.descricao}</p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 mr-2">
                          Ordem: {item.ordem}
                        </span>
                        
                        {!item.ativo && (
                          <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">
                            Inativo
                          </span>
                        )}
                        
                        <button
                          onClick={() => handleEditar(item)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          title="Editar"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        
                        <button
                          onClick={() => handleDeletar(item.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                          title="Inativar"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Dica */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <ChevronRight className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900 mb-1">Dica</h3>
            <p className="text-sm text-blue-800">
              Os valores cadastrados aqui serão usados no cadastro de produtos e na classificação automática por IA.
              Mantenha ativos apenas os valores que você utiliza no seu negócio.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OpcoesRacao;
