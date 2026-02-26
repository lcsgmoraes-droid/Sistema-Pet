import { useState, useEffect } from 'react';
import api from '../api.js';
import { 
  FiPlus, FiEdit2, FiTrash2, FiSave, FiX, FiAlertCircle, 
  FiChevronDown, FiChevronRight, FiCheck 
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import './Cadastros.css';
import './EspeciesRacas.css';

const EspeciesRacas = () => {
  const [especies, setEspecies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedEspecies, setExpandedEspecies] = useState(new Set());
  const [showModalEspecie, setShowModalEspecie] = useState(false);
  const [showModalRaca, setShowModalRaca] = useState(false);
  const [editingEspecie, setEditingEspecie] = useState(null);
  const [editingRaca, setEditingRaca] = useState(null);
  const [especieSelecionada, setEspecieSelecionada] = useState(null);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formEspecie, setFormEspecie] = useState({
    nome: '',
    ativo: true
  });

  const [formRaca, setFormRaca] = useState({
    nome: '',
    especie_id: '',
    ativo: true
  });

  useEffect(() => {
    carregarEspeciesComRacas();
  }, []);

  const carregarEspeciesComRacas = async () => {
    try {
      setLoading(true);
      const [especiesRes, racasRes] = await Promise.all([
        api.get('/cadastros/especies'),
        api.get('/cadastros/racas')
      ]);
      
      // Agrupar raças por espécie
      const especiesComRacas = especiesRes.data.map(especie => ({
        ...especie,
        racas: racasRes.data.filter(r => r.especie_id === especie.id)
      }));
      
      setEspecies(especiesComRacas);
      
      // Expandir todas por padrão
      const todasEspecies = new Set(especiesComRacas.map(e => e.id));
      setExpandedEspecies(todasEspecies);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const toggleEspecie = (especieId) => {
    const newExpanded = new Set(expandedEspecies);
    if (newExpanded.has(especieId)) {
      newExpanded.delete(especieId);
    } else {
      newExpanded.add(especieId);
    }
    setExpandedEspecies(newExpanded);
  };

  // ========== ESPÉCIE ==========

  const abrirModalEspecie = (especie = null) => {
    if (especie) {
      setEditingEspecie(especie);
      setFormEspecie({
        nome: especie.nome,
        ativo: especie.ativo
      });
    } else {
      setEditingEspecie(null);
      setFormEspecie({ nome: '', ativo: true });
    }
    setError('');
    setShowModalEspecie(true);
  };

  const fecharModalEspecie = () => {
    setShowModalEspecie(false);
    setEditingEspecie(null);
    setFormEspecie({ nome: '', ativo: true });
    setError('');
  };

  const handleSubmitEspecie = async (e) => {
    e.preventDefault();
    setError('');

    if (!formEspecie.nome || formEspecie.nome.trim() === '') {
      setError('O nome da espécie é obrigatório');
      return;
    }

    try {
      if (editingEspecie) {
        await api.put(`/cadastros/especies/${editingEspecie.id}`, formEspecie);
      } else {
        await api.post('/cadastros/especies', formEspecie);
      }
      
      carregarEspeciesComRacas();
      fecharModalEspecie();
    } catch (err) {
      console.error('Erro ao salvar espécie:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar espécie');
    }
  };

  const handleDeleteEspecie = async (especie) => {
    if (!window.confirm(`Deseja realmente desativar a espécie "${especie.nome}"?\n\nIsso também desativará todas as raças vinculadas.`)) {
      return;
    }

    try {
      await api.delete(`/cadastros/especies/${especie.id}`);
      carregarEspeciesComRacas();
    } catch (err) {
      console.error('Erro ao desativar espécie:', err);
      alert(err.response?.data?.detail || 'Erro ao desativar espécie');
    }
  };

  // ========== RAÇA ==========

  const abrirModalRaca = (especie, raca = null) => {
    setEspecieSelecionada(especie);
    
    if (raca) {
      setEditingRaca(raca);
      setFormRaca({
        nome: raca.nome,
        especie_id: raca.especie_id,
        ativo: raca.ativo
      });
    } else {
      setEditingRaca(null);
      setFormRaca({
        nome: '',
        especie_id: especie.id,
        ativo: true
      });
    }
    setError('');
    setShowModalRaca(true);
  };

  const fecharModalRaca = () => {
    setShowModalRaca(false);
    setEditingRaca(null);
    setEspecieSelecionada(null);
    setFormRaca({ nome: '', especie_id: '', ativo: true });
    setError('');
  };

  const handleSubmitRaca = async (e) => {
    e.preventDefault();
    setError('');

    if (!formRaca.nome || formRaca.nome.trim() === '') {
      setError('O nome da raça é obrigatório');
      return;
    }

    try {
      const payload = {
        nome: formRaca.nome,
        especie_id: parseInt(formRaca.especie_id),
        ativo: formRaca.ativo
      };

      if (editingRaca) {
        await api.put(`/cadastros/racas/${editingRaca.id}`, payload);
      } else {
        await api.post('/cadastros/racas', payload);
      }
      
      carregarEspeciesComRacas();
      fecharModalRaca();
    } catch (err) {
      console.error('Erro ao salvar raça:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar raça');
    }
  };

  const handleDeleteRaca = async (raca) => {
    if (!window.confirm(`Deseja realmente desativar a raça "${raca.nome}"?`)) {
      return;
    }

    try {
      await api.delete(`/cadastros/racas/${raca.id}`);
      carregarEspeciesComRacas();
    } catch (err) {
      console.error('Erro ao desativar raça:', err);
      alert(err.response?.data?.detail || 'Erro ao desativar raça');
    }
  };

  // ========== FILTROS ==========

  const especiesFiltradas = especies.filter(especie =>
    especie.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    especie.racas.some(r => r.nome.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Carregando espécies e raças...</p>
      </div>
    );
  }

  return (
    <div className="cadastros-container">
      <div className="page-header">
        <div>
          <h1>Espécies e Raças</h1>
          <p className="page-subtitle">Gerencie as espécies de animais e suas raças</p>
        </div>
        <button className="btn btn-primary" onClick={() => abrirModalEspecie()}>
          <FiPlus /> Nova Espécie
        </button>
      </div>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Buscar espécie ou raça..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <div className="filter-info">
          {especiesFiltradas.length} espécie{especiesFiltradas.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="especies-list">
        {especiesFiltradas.length === 0 ? (
          <div className="empty-state">
            {searchTerm ? 'Nenhuma espécie ou raça encontrada' : 'Nenhuma espécie cadastrada'}
          </div>
        ) : (
          especiesFiltradas.map(especie => {
            const isExpanded = expandedEspecies.has(especie.id);
            const racasAtivas = especie.racas.filter(r => r.ativo);
            
            return (
              <div key={especie.id} className={`especie-card ${!especie.ativo ? 'inactive' : ''}`}>
                {/* Header da Espécie */}
                <div className="especie-header">
                  <div className="especie-info" onClick={() => toggleEspecie(especie.id)}>
                    <button className="expand-btn">
                      {isExpanded ? <FiChevronDown size={20} /> : <FiChevronRight size={20} />}
                    </button>
                    <PawPrint className="especie-icon" size={24} />
                    <div>
                      <h3 className="especie-nome">{especie.nome}</h3>
                      <span className="racas-count">
                        {racasAtivas.length} raça{racasAtivas.length !== 1 ? 's' : ''} ativa{racasAtivas.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {!especie.ativo && (
                      <span className="badge badge-danger">Inativa</span>
                    )}
                  </div>
                  
                  <div className="especie-actions">
                    <button
                      className="btn-icon btn-success"
                      onClick={() => abrirModalRaca(especie)}
                      title="Adicionar Raça"
                    >
                      <FiPlus />
                    </button>
                    <button
                      className="btn-icon btn-edit"
                      onClick={() => abrirModalEspecie(especie)}
                      title="Editar Espécie"
                    >
                      <FiEdit2 />
                    </button>
                    {especie.ativo && (
                      <button
                        className="btn-icon btn-delete"
                        onClick={() => handleDeleteEspecie(especie)}
                        title="Desativar Espécie"
                      >
                        <FiTrash2 />
                      </button>
                    )}
                  </div>
                </div>

                {/* Lista de Raças (Expansível) */}
                {isExpanded && (
                  <div className="racas-list">
                    {especie.racas.length === 0 ? (
                      <div className="empty-racas">
                        <p>Nenhuma raça cadastrada ainda</p>
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => abrirModalRaca(especie)}
                        >
                          <FiPlus /> Adicionar Primeira Raça
                        </button>
                      </div>
                    ) : (
                      <>
                        {especie.racas.map(raca => (
                          <div key={raca.id} className={`raca-item ${!raca.ativo ? 'inactive' : ''}`}>
                            <div className="raca-info">
                              <FiCheck className="raca-icon" size={16} />
                              <span className="raca-nome">{raca.nome}</span>
                              {!raca.ativo && (
                                <span className="badge badge-sm badge-danger">Inativa</span>
                              )}
                            </div>
                            <div className="raca-actions">
                              <button
                                className="btn-icon-sm btn-edit"
                                onClick={() => abrirModalRaca(especie, raca)}
                                title="Editar Raça"
                              >
                                <FiEdit2 size={14} />
                              </button>
                              {raca.ativo && (
                                <button
                                  className="btn-icon-sm btn-delete"
                                  onClick={() => handleDeleteRaca(raca)}
                                  title="Desativar Raça"
                                >
                                  <FiTrash2 size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Modal Espécie */}
      {showModalEspecie && (
        <div className="modal-overlay" onClick={fecharModalEspecie}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingEspecie ? 'Editar Espécie' : 'Nova Espécie'}</h2>
              <button className="btn-close" onClick={fecharModalEspecie}>
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSubmitEspecie}>
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
                    value={formEspecie.nome}
                    onChange={(e) => setFormEspecie({ ...formEspecie, nome: e.target.value })}
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
                      checked={formEspecie.ativo}
                      onChange={(e) => setFormEspecie({ ...formEspecie, ativo: e.target.checked })}
                    />
                    <span>Espécie ativa</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={fecharModalEspecie}>
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

      {/* Modal Raça */}
      {showModalRaca && (
        <div className="modal-overlay" onClick={fecharModalRaca}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {editingRaca ? 'Editar Raça' : 'Nova Raça'}
                {especieSelecionada && (
                  <span className="subtitle"> - {especieSelecionada.nome}</span>
                )}
              </h2>
              <button className="btn-close" onClick={fecharModalRaca}>
                <FiX />
              </button>
            </div>

            <form onSubmit={handleSubmitRaca}>
              <div className="modal-body">
                {error && (
                  <div className="alert alert-danger">
                    <FiAlertCircle /> {error}
                  </div>
                )}

                <div className="form-group">
                  <label>Nome da Raça *</label>
                  <input
                    type="text"
                    value={formRaca.nome}
                    onChange={(e) => setFormRaca({ ...formRaca, nome: e.target.value })}
                    placeholder="Ex: Labrador, Siamês, SRD..."
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
                      checked={formRaca.ativo}
                      onChange={(e) => setFormRaca({ ...formRaca, ativo: e.target.checked })}
                    />
                    <span>Raça ativa</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={fecharModalRaca}>
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

export default EspeciesRacas;
