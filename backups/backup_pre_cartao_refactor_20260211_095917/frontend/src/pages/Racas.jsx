import { useState, useEffect } from 'react';
import api from '../api';
import { FiPlus, FiEdit2, FiTrash2, FiSave, FiX, FiAlertCircle, FiFilter } from 'react-icons/fi';
import './Cadastros.css';

const Racas = () => {
  const [racas, setRacas] = useState([]);
  const [especies, setEspecies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRaca, setEditingRaca] = useState(null);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEspecie, setFiltroEspecie] = useState('');
  
  const [formData, setFormData] = useState({
    nome: '',
    especie_id: '',
    ativo: true
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      setLoading(true);
      const [racasRes, especiesRes] = await Promise.all([
        api.get('/cadastros/racas'),
        api.get('/cadastros/especies', { params: { ativo: true } })
      ]);
      setRacas(racasRes.data);
      setEspecies(especiesRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (raca = null) => {
    if (raca) {
      setEditingRaca(raca);
      setFormData({
        nome: raca.nome,
        especie_id: raca.especie_id,
        ativo: raca.ativo
      });
    } else {
      setEditingRaca(null);
      setFormData({
        nome: '',
        especie_id: filtroEspecie || '',
        ativo: true
      });
    }
    setError('');
    setShowModal(true);
  };

  const fecharModal = () => {
    setShowModal(false);
    setEditingRaca(null);
    setFormData({ nome: '', especie_id: '', ativo: true });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validação
    if (!formData.nome || formData.nome.trim() === '') {
      setError('O nome da raça é obrigatório');
      return;
    }
    if (!formData.especie_id) {
      setError('Selecione uma espécie');
      return;
    }

    try {
      const payload = {
        nome: formData.nome,
        especie_id: parseInt(formData.especie_id),
        ativo: formData.ativo
      };

      if (editingRaca) {
        // Atualizar
        await api.put(`/cadastros/racas/${editingRaca.id}`, payload);
      } else {
        // Criar
        await api.post('/cadastros/racas', payload);
      }
      
      carregarDados();
      fecharModal();
    } catch (err) {
      console.error('Erro ao salvar raça:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar raça');
    }
  };

  const handleDelete = async (raca) => {
    if (!window.confirm(`Deseja realmente desativar a raça "${raca.nome}"?`)) {
      return;
    }

    try {
      await api.delete(`/cadastros/racas/${raca.id}`);
      carregarDados();
    } catch (err) {
      console.error('Erro ao desativar raça:', err);
      alert(err.response?.data?.detail || 'Erro ao desativar raça');
    }
  };

  const racasFiltradas = racas.filter(raca => {
    const matchNome = raca.nome.toLowerCase().includes(searchTerm.toLowerCase());
    const matchEspecie = !filtroEspecie || raca.especie_id === parseInt(filtroEspecie);
    return matchNome && matchEspecie;
  });

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Carregando raças...</p>
      </div>
    );
  }

  return (
    <div className="cadastros-container">
      <div className="page-header">
        <div>
          <h1>Raças de Animais</h1>
          <p className="page-subtitle">Gerencie as raças cadastradas por espécie</p>
        </div>
        <button className="btn btn-primary" onClick={() => abrirModal()}>
          <FiPlus /> Nova Raça
        </button>
      </div>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Buscar raça..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <div className="filter-group">
          <FiFilter />
          <select
            value={filtroEspecie}
            onChange={(e) => setFiltroEspecie(e.target.value)}
            className="filter-select"
          >
            <option value="">Todas as espécies</option>
            {especies.map(especie => (
              <option key={especie.id} value={especie.id}>
                {especie.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-info">
          {racasFiltradas.length} raça{racasFiltradas.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Espécie</th>
              <th>Status</th>
              <th>Criado em</th>
              <th className="actions-column">Ações</th>
            </tr>
          </thead>
          <tbody>
            {racasFiltradas.length === 0 ? (
              <tr>
                <td colSpan="5" className="empty-state">
                  {searchTerm || filtroEspecie ? 'Nenhuma raça encontrada' : 'Nenhuma raça cadastrada'}
                </td>
              </tr>
            ) : (
              racasFiltradas.map(raca => (
                <tr key={raca.id}>
                  <td>
                    <strong>{raca.nome}</strong>
                  </td>
                  <td>
                    <span className="badge badge-info">
                      {raca.especie_nome || 'N/A'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${raca.ativo ? 'badge-success' : 'badge-danger'}`}>
                      {raca.ativo ? 'Ativa' : 'Inativa'}
                    </span>
                  </td>
                  <td>
                    {new Date(raca.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="actions-column">
                    <button
                      className="btn-icon btn-edit"
                      onClick={() => abrirModal(raca)}
                      title="Editar"
                    >
                      <FiEdit2 />
                    </button>
                    {raca.ativo && (
                      <button
                        className="btn-icon btn-delete"
                        onClick={() => handleDelete(raca)}
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
              <h2>{editingRaca ? 'Editar Raça' : 'Nova Raça'}</h2>
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
                  <label>Espécie *</label>
                  <select
                    value={formData.especie_id}
                    onChange={(e) => setFormData({ ...formData, especie_id: e.target.value })}
                    required
                  >
                    <option value="">Selecione a espécie</option>
                    {especies.map(especie => (
                      <option key={especie.id} value={especie.id}>
                        {especie.nome}
                      </option>
                    ))}
                  </select>
                  {especies.length === 0 && (
                    <small className="text-danger">
                      Nenhuma espécie cadastrada. Cadastre uma espécie primeiro.
                    </small>
                  )}
                </div>

                <div className="form-group">
                  <label>Nome da Raça *</label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    placeholder="Ex: Labrador, Siamês, Calopsita..."
                    required
                    autoFocus
                  />
                  <small>
                    Exemplos: Labrador, Golden Retriever, SRD (Sem Raça Definida)
                  </small>
                </div>

                <div className="form-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.ativo}
                      onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                    />
                    <span>Raça ativa</span>
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

export default Racas;
