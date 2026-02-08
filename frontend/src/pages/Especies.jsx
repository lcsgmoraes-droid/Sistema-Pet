import { useState, useEffect } from 'react';
import api from '../api';
import { FiPlus, FiEdit2, FiTrash2, FiSave, FiX, FiAlertCircle, FiCheck } from 'react-icons/fi';
import './Cadastros.css';

const Especies = () => {
  const [especies, setEspecies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingEspecie, setEditingEspecie] = useState(null);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    nome: '',
    ativo: true
  });

  useEffect(() => {
    carregarEspecies();
  }, []);

  const carregarEspecies = async () => {
    try {
      setLoading(true);
      const response = await api.get('/cadastros/especies');
      setEspecies(response.data);
    } catch (err) {
      console.error('Erro ao carregar espécies:', err);
      setError('Erro ao carregar espécies');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (especie = null) => {
    if (especie) {
      setEditingEspecie(especie);
      setFormData({
        nome: especie.nome,
        ativo: especie.ativo
      });
    } else {
      setEditingEspecie(null);
      setFormData({
        nome: '',
        ativo: true
      });
    }
    setError('');
    setShowModal(true);
  };

  const fecharModal = () => {
    setShowModal(false);
    setEditingEspecie(null);
    setFormData({ nome: '', ativo: true });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validação
    if (!formData.nome || formData.nome.trim() === '') {
      setError('O nome da espécie é obrigatório');
      return;
    }

    try {
      if (editingEspecie) {
        // Atualizar
        await api.put(`/cadastros/especies/${editingEspecie.id}`, formData);
      } else {
        // Criar
        await api.post('/cadastros/especies', formData);
      }
      
      carregarEspecies();
      fecharModal();
    } catch (err) {
      console.error('Erro ao salvar espécie:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar espécie');
    }
  };

  const handleDelete = async (especie) => {
    if (!window.confirm(`Deseja realmente desativar a espécie "${especie.nome}"?`)) {
      return;
    }

    try {
      await api.delete(`/cadastros/especies/${especie.id}`);
      carregarEspecies();
    } catch (err) {
      console.error('Erro ao desativar espécie:', err);
      alert(err.response?.data?.detail || 'Erro ao desativar espécie');
    }
  };

  const especiesFiltradas = especies.filter(especie =>
    especie.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Carregando espécies...</p>
      </div>
    );
  }

  return (
    <div className="cadastros-container">
      <div className="page-header">
        <div>
          <h1>Espécies de Animais</h1>
          <p className="page-subtitle">Gerencie as espécies cadastradas no sistema</p>
        </div>
        <button className="btn btn-primary" onClick={() => abrirModal()}>
          <FiPlus /> Nova Espécie
        </button>
      </div>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Buscar espécie..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <div className="filter-info">
          {especiesFiltradas.length} espécie{especiesFiltradas.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Status</th>
              <th>Criado em</th>
              <th className="actions-column">Ações</th>
            </tr>
          </thead>
          <tbody>
            {especiesFiltradas.length === 0 ? (
              <tr>
                <td colSpan="4" className="empty-state">
                  {searchTerm ? 'Nenhuma espécie encontrada' : 'Nenhuma espécie cadastrada'}
                </td>
              </tr>
            ) : (
              especiesFiltradas.map(especie => (
                <tr key={especie.id}>
                  <td>
                    <strong>{especie.nome}</strong>
                  </td>
                  <td>
                    <span className={`badge ${especie.ativo ? 'badge-success' : 'badge-danger'}`}>
                      {especie.ativo ? 'Ativa' : 'Inativa'}
                    </span>
                  </td>
                  <td>
                    {new Date(especie.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="actions-column">
                    <button
                      className="btn-icon btn-edit"
                      onClick={() => abrirModal(especie)}
                      title="Editar"
                    >
                      <FiEdit2 />
                    </button>
                    {especie.ativo && (
                      <button
                        className="btn-icon btn-delete"
                        onClick={() => handleDelete(especie)}
                        title="Desativar"
                      >
                        <FiTrash2 />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={fecharModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingEspecie ? 'Editar Espécie' : 'Nova Espécie'}</h2>
              <button className="btn-close" onClick={fecharModal}>
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && (
                  <div className="alert alert-danger">
                    <FiAlertCircle /> {error}
                  </div>
                )}

                <div className="form-group">
                  <label>Nome da Espécie *</label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    placeholder="Ex: Cão, Gato, Ave, Réptil..."
                    required
                    autoFocus
                  />
                  <small>Exemplos: Cão, Gato, Ave, Réptil, Coelho, Peixe, Hamster</small>
                </div>

                <div className="form-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.ativo}
                      onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                    />
                    <span>Espécie ativa</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={fecharModal}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  <FiSave /> Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Especies;
