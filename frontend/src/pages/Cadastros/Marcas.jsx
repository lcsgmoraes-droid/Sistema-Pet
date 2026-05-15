import React, { useEffect, useState } from 'react';
import { FiAlertCircle, FiEdit2, FiPlus, FiTrash2 } from 'react-icons/fi';
import { createMarca, deleteMarca, getMarcas, updateMarca } from '../../api/produtos';
import ActionButton from '../../components/ui/ActionButton';
import EmptyState from '../../components/ui/EmptyState';
import IconActionButton from '../../components/ui/IconActionButton';
import LoadingState from '../../components/ui/LoadingState';

const Marcas = () => {
  const [marcas, setMarcas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
  });

  useEffect(() => {
    carregarMarcas();
  }, []);

  const carregarMarcas = async () => {
    try {
      setLoading(true);
      const response = await getMarcas();
      setMarcas(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar marcas:', error);
      alert('Nao foi possivel carregar as marcas.');
    } finally {
      setLoading(false);
    }
  };

  const limparCachesCatalogos = () => {
    sessionStorage.removeItem('produtos_catalogos_cache_v1');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      if (editando) {
        await updateMarca(editando, formData);
      } else {
        await createMarca(formData);
      }

      limparCachesCatalogos();
      setShowModal(false);
      setEditando(null);
      setFormData({ nome: '', descricao: '' });
      await carregarMarcas();
    } catch (error) {
      console.error('Erro ao salvar marca:', error);
      alert(error.response?.data?.detail || 'Nao foi possivel salvar a marca.');
    }
  };

  const handleEditar = (marca) => {
    setEditando(marca.id);
    setFormData({
      nome: marca.nome,
      descricao: marca.descricao || '',
    });
    setShowModal(true);
  };

  const handleExcluir = async (marca) => {
    if (!window.confirm(`Deseja realmente excluir a marca "${marca.nome}"?`)) {
      return;
    }

    try {
      await deleteMarca(marca.id);
      limparCachesCatalogos();
      await carregarMarcas();
    } catch (error) {
      console.error('Erro ao excluir marca:', error);
      alert(error.response?.data?.detail || 'Nao foi possivel excluir a marca.');
    }
  };

  const handleNovaMarca = () => {
    setEditando(null);
    setFormData({ nome: '', descricao: '' });
    setShowModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingState label="Carregando marcas..." />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Marcas</h1>
          <p className="text-gray-600 mt-1">
            Marcas ajudam a organizar produtos, filtros e relatorios de estoque.
          </p>
        </div>
        <ActionButton
          onClick={handleNovaMarca}
          icon={FiPlus}
          intent="create"
          size="md"
        >
          Nova Marca
        </ActionButton>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {marcas.length === 0 ? (
          <EmptyState
            className="m-4"
            description="Crie a primeira marca para classificar produtos no cadastro e nos filtros."
            icon={FiAlertCircle}
            title="Nenhuma marca cadastrada"
            action={(
              <ActionButton
                onClick={handleNovaMarca}
                icon={FiPlus}
                intent="create"
                tone="soft"
              >
                Criar primeira marca
              </ActionButton>
            )}
          />
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">Descricao</th>
                <th className="text-right px-4 py-3 text-sm font-semibold text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {marcas.map((marca) => (
                <tr key={marca.id} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{marca.nome}</td>
                  <td className="px-4 py-3 text-gray-600 text-sm">{marca.descricao || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <IconActionButton
                        onClick={() => handleEditar(marca)}
                        icon={FiEdit2}
                        intent="edit"
                        title="Editar"
                      />
                      <IconActionButton
                        onClick={() => handleExcluir(marca)}
                        icon={FiTrash2}
                        intent="delete"
                        title="Excluir"
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {editando ? 'Editar Marca' : 'Nova Marca'}
            </h2>

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="marca-nome" className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  id="marca-nome"
                  name="nome"
                  type="text"
                  value={formData.nome}
                  onChange={(event) => setFormData({ ...formData, nome: event.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Royal Canin, Premier, Zee.Dog..."
                  required
                />
              </div>

              <div className="mb-6">
                <label htmlFor="marca-descricao" className="block text-sm font-medium text-gray-700 mb-1">
                  Descricao
                </label>
                <textarea
                  id="marca-descricao"
                  name="descricao"
                  value={formData.descricao}
                  onChange={(event) => setFormData({ ...formData, descricao: event.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Descricao opcional da marca"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-3">
                <ActionButton
                  onClick={() => setShowModal(false)}
                  intent="neutral"
                  tone="soft"
                >
                  Cancelar
                </ActionButton>
                <ActionButton
                  type="submit"
                  intent={editando ? 'edit' : 'create'}
                >
                  {editando ? 'Salvar' : 'Criar'}
                </ActionButton>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Marcas;
