import { useState, useEffect } from 'react';
import api from '../api';

export default function Subcategorias() {
  const [categorias, setCategorias] = useState([]);
  const [subcategorias, setSubcategorias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: null,
    categoria_id: '',
    nome: '',
    descricao: '',
    ativo: true
  });

  useEffect(() => {
    carregarCategorias();
    carregarSubcategorias();
  }, []);

  const carregarCategorias = async () => {
    try {
      const response = await api.get('/api/categorias-financeiras');
      setCategorias(response.data.filter(c => c.ativo));
    } catch (error) {
      console.error('Erro ao carregar categorias:', error);
      alert('Erro ao carregar categorias');
    }
  };

  const carregarSubcategorias = async () => {
    setLoading(true);
    try {
      const response = await api.get('/subcategorias');
      setSubcategorias(response.data);
    } catch (error) {
      console.error('Erro ao carregar subcategorias:', error);
      alert('Erro ao carregar subcategorias');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.categoria_id || !formData.nome) {
      alert('Preencha categoria e nome');
      return;
    }

    try {
      if (formData.id) {
        await api.put(`/subcategorias/${formData.id}`, formData);
      } else {
        await api.post('/subcategorias', formData);
      }
      
      setModalOpen(false);
      setFormData({ id: null, categoria_id: '', nome: '', descricao: '', ativo: true });
      carregarSubcategorias();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      alert('Erro ao salvar subcategoria');
    }
  };

  const handleEdit = (subcat) => {
    setFormData(subcat);
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Deseja realmente excluir esta subcategoria?')) return;
    
    try {
      await api.delete(`/subcategorias/${id}`);
      carregarSubcategorias();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      alert('Erro ao excluir subcategoria');
    }
  };

  const getNomeCategoria = (catId) => {
    const cat = categorias.find(c => c.id === catId);
    return cat ? cat.nome : '-';
  };

  // Agrupar por categoria
  const subcategoriasPorCategoria = subcategorias.reduce((acc, sub) => {
    const catId = sub.categoria_id;
    if (!acc[catId]) {
      acc[catId] = {
        categoria: getNomeCategoria(catId),
        itens: []
      };
    }
    acc[catId].itens.push(sub);
    return acc;
  }, {});

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Subcategorias</h1>
          <p className="text-sm text-gray-600 mt-1">
            Gerencie as subcategorias de produtos
          </p>
        </div>
        <button
          onClick={() => {
            setFormData({ id: null, categoria_id: '', nome: '', descricao: '', ativo: true });
            setModalOpen(true);
          }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <span>+</span>
          Nova Subcategoria
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">Carregando...</div>
      ) : (
        <div className="space-y-6">
          {Object.entries(subcategoriasPorCategoria).map(([catId, grupo]) => (
            <div key={catId} className="bg-white rounded-lg shadow">
              <div className="bg-gray-50 px-4 py-3 border-b">
                <h2 className="font-semibold text-lg text-gray-800">{grupo.categoria}</h2>
              </div>
              <div className="divide-y">
                {grupo.itens.map((sub) => (
                  <div key={sub.id} className="px-4 py-3 flex justify-between items-center hover:bg-gray-50">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{sub.nome}</div>
                      {sub.descricao && (
                        <div className="text-sm text-gray-600 mt-1">{sub.descricao}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${sub.ativo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {sub.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                      <button
                        onClick={() => handleEdit(sub)}
                        className="text-blue-600 hover:text-blue-800 px-3 py-1"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(sub.id)}
                        className="text-red-600 hover:text-red-800 px-3 py-1"
                      >
                        Excluir
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          
          {Object.keys(subcategoriasPorCategoria).length === 0 && (
            <div className="text-center py-8 text-gray-500">
              Nenhuma subcategoria cadastrada
            </div>
          )}
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {formData.id ? 'Editar' : 'Nova'} Subcategoria
            </h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Categoria *
                </label>
                <select
                  value={formData.categoria_id}
                  onChange={(e) => setFormData({...formData, categoria_id: parseInt(e.target.value)})}
                  className="w-full border rounded-lg px-3 py-2"
                  required
                >
                  <option value="">Selecione...</option>
                  {categorias.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({...formData, nome: e.target.value})}
                  className="w-full border rounded-lg px-3 py-2"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({...formData, descricao: e.target.value})}
                  className="w-full border rounded-lg px-3 py-2"
                  rows="3"
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.ativo}
                  onChange={(e) => setFormData({...formData, ativo: e.target.checked})}
                  className="mr-2"
                />
                <label className="text-sm text-gray-700">Ativo</label>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
