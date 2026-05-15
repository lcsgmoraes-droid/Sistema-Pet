import React, { useState, useEffect } from 'react';
import { FiPlus, FiEdit2, FiTrash2, FiAlertCircle } from 'react-icons/fi';
import api from '../../api';
import ActionButton from '../../components/ui/ActionButton';
import EmptyState from '../../components/ui/EmptyState';
import IconActionButton from '../../components/ui/IconActionButton';
import LoadingState from '../../components/ui/LoadingState';

const Departamentos = () => {
  const [departamentos, setDepartamentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
  });

  useEffect(() => {
    carregarDepartamentos();
  }, []);

  const carregarDepartamentos = async () => {
    try {
      setLoading(true);
      const response = await api.get('/produtos/departamentos');
      setDepartamentos(response.data);
    } catch (error) {
      console.error('Erro ao carregar departamentos:', error);
      alert('Erro ao carregar departamentos');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editando) {
        await api.put(`/produtos/departamentos/${editando}`, formData);
      } else {
        await api.post('/produtos/departamentos', formData);
      }
      setShowModal(false);
      setEditando(null);
      setFormData({ nome: '', descricao: '' });
      carregarDepartamentos();
    } catch (error) {
      console.error('Erro ao salvar departamento:', error);
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert('Erro ao salvar departamento');
      }
    }
  };

  const handleEditar = (departamento) => {
    setEditando(departamento.id);
    setFormData({
      nome: departamento.nome,
      descricao: departamento.descricao || '',
    });
    setShowModal(true);
  };

  const handleExcluir = async (departamento) => {
    if (!window.confirm(`Deseja realmente excluir o departamento "${departamento.nome}"?`)) {
      return;
    }
    try {
      await api.delete(`/produtos/departamentos/${departamento.id}`);
      carregarDepartamentos();
    } catch (error) {
      console.error('Erro ao excluir departamento:', error);
      alert(error.response?.data?.detail || 'Erro ao excluir departamento');
    }
  };

  const handleNovoDepartamento = () => {
    setEditando(null);
    setFormData({ nome: '', descricao: '' });
    setShowModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingState label="Carregando departamentos..." />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Departamentos</h1>
          <p className="text-gray-600 mt-1">
            Departamentos agrupam categorias de produtos (ex: Alimentação, Higiene, Acessórios)
          </p>
        </div>
        <ActionButton
          onClick={handleNovoDepartamento}
          icon={FiPlus}
          intent="create"
          size="md"
        >
          Novo Departamento
        </ActionButton>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {departamentos.length === 0 ? (
          <EmptyState
            className="m-4"
            description="Crie o primeiro departamento para agrupar categorias de produtos."
            icon={FiAlertCircle}
            title="Nenhum departamento cadastrado"
            action={
              <ActionButton
                onClick={handleNovoDepartamento}
                icon={FiPlus}
                intent="create"
                tone="soft"
              >
                Criar primeiro departamento
              </ActionButton>
            }
          />
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">Descrição</th>
                <th className="text-right px-4 py-3 text-sm font-semibold text-gray-600">Ações</th>
              </tr>
            </thead>
            <tbody>
              {departamentos.map((dep) => (
                <tr key={dep.id} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{dep.nome}</td>
                  <td className="px-4 py-3 text-gray-600 text-sm">{dep.descricao || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <IconActionButton
                        onClick={() => handleEditar(dep)}
                        icon={FiEdit2}
                        intent="edit"
                        title="Editar"
                      />
                      <IconActionButton
                        onClick={() => handleExcluir(dep)}
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

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {editando ? 'Editar Departamento' : 'Novo Departamento'}
            </h2>

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Alimentação, Higiene, Acessórios..."
                  required
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Descrição opcional do departamento"
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

export default Departamentos;
