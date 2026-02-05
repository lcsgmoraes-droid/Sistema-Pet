import { useEffect, useState } from 'react';
import api from '../api';

export default function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [novaRole, setNovaRole] = useState({
    nome: '',
    descricao: '',
    permissions: []
  });

  async function carregarDados() {
    try {
      setLoading(true);
      const [rolesRes, permsRes] = await Promise.all([
        api.get('/roles'),
        api.get('/permissions')
      ]);
      setRoles(rolesRes.data);
      setPermissions(permsRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      alert('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  }

  async function salvarRole(e) {
    e.preventDefault();
    try {
      if (editingRole) {
        await api.put(`/roles/${editingRole.role_id}`, novaRole);
        alert('Role atualizada com sucesso!');
      } else {
        await api.post('/roles', novaRole);
        alert('Role criada com sucesso!');
      }
      setShowModal(false);
      setEditingRole(null);
      setNovaRole({ nome: '', descricao: '', permissions: [] });
      carregarDados();
    } catch (error) {
      console.error('Erro ao salvar role:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar role');
    }
  }

  function abrirEdicao(role) {
    setEditingRole(role);
    setNovaRole({
      nome: role.nome,
      descricao: role.descricao,
      permissions: role.permissions.map(p => p.permission_id)
    });
    setShowModal(true);
  }

  function togglePermission(permId) {
    setNovaRole(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permId)
        ? prev.permissions.filter(id => id !== permId)
        : [...prev.permissions, permId]
    }));
  }

  async function deletarRole(roleId) {
    if (!confirm('Tem certeza que deseja excluir esta role?')) return;
    
    try {
      await api.delete(`/roles/${roleId}`);
      alert('Role excluída com sucesso!');
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir role:', error);
      alert('Erro ao excluir role');
    }
  }

  useEffect(() => {
    carregarDados();
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Permissões (Roles)</h1>
          <p className="text-gray-600 mt-1">Gerencie roles e suas permissões</p>
        </div>
        <button
          onClick={() => {
            setEditingRole(null);
            setNovaRole({ nome: '', descricao: '', permissions: [] });
            setShowModal(true);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nova Role
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Carregando...</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {roles.length === 0 ? (
            <div className="col-span-full text-center py-12 text-gray-500">
              Nenhuma role encontrada
            </div>
          ) : (
            roles.map((role) => (
              <div key={role.role_id} className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{role.nome}</h3>
                    <p className="text-sm text-gray-600 mt-1">{role.descricao}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirEdicao(role)}
                      className="text-blue-600 hover:text-blue-700"
                      title="Editar"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => deletarRole(role.role_id)}
                      className="text-red-600 hover:text-red-700"
                      title="Excluir"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="mt-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Permissões:</p>
                  <div className="flex flex-wrap gap-2">
                    {role.permissions.length === 0 ? (
                      <span className="text-sm text-gray-400">Nenhuma permissão</span>
                    ) : (
                      role.permissions.map(p => (
                        <span key={p.permission_id} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          {p.nome}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Modal Nova/Editar Role */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">
                  {editingRole ? 'Editar Role' : 'Nova Role'}
                </h2>
                <button
                  onClick={() => {
                    setShowModal(false);
                    setEditingRole(null);
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <form onSubmit={salvarRole} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome da Role *
                  </label>
                  <input
                    type="text"
                    required
                    value={novaRole.nome}
                    onChange={(e) => setNovaRole({ ...novaRole, nome: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ex: Gerente, Vendedor, etc"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descrição
                  </label>
                  <textarea
                    value={novaRole.descricao}
                    onChange={(e) => setNovaRole({ ...novaRole, descricao: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows="2"
                    placeholder="Descrição da role"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Permissões *
                  </label>
                  <div className="border border-gray-300 rounded-lg p-4 max-h-64 overflow-y-auto">
                    {permissions.length === 0 ? (
                      <p className="text-gray-500 text-sm">Nenhuma permissão disponível</p>
                    ) : (
                      <div className="space-y-2">
                        {permissions.map(perm => (
                          <label key={perm.permission_id} className="flex items-start cursor-pointer hover:bg-gray-50 p-2 rounded">
                            <input
                              type="checkbox"
                              checked={novaRole.permissions.includes(perm.permission_id)}
                              onChange={() => togglePermission(perm.permission_id)}
                              className="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <div>
                              <div className="text-sm font-medium text-gray-900">{perm.nome}</div>
                              {perm.descricao && (
                                <div className="text-xs text-gray-500">{perm.descricao}</div>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingRole(null);
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    {editingRole ? 'Atualizar' : 'Criar'} Role
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
