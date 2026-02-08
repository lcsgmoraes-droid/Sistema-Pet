import { useState } from 'react';
import { FiPlus, FiSave, FiX, FiAlertCircle } from 'react-icons/fi';
import api from '../api';
import './QuickAddModal.css';

/**
 * Modal rápido para adicionar Espécie ou Raça sem sair do formulário de Pet
 * @param {string} tipo - 'especie' ou 'raca'
 * @param {number} especieId - ID da espécie (obrigatório se tipo='raca')
 * @param {string} especieNome - Nome da espécie (para exibição)
 * @param {function} onSuccess - Callback chamado após sucesso (recebe o novo item)
 * @param {function} onClose - Callback para fechar o modal
 */
const QuickAddModal = ({ tipo, especieId, especieNome, onSuccess, onClose }) => {
  const [nome, setNome] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!nome || nome.trim() === '') {
      setError(`O nome ${tipo === 'especie' ? 'da espécie' : 'da raça'} é obrigatório`);
      return;
    }

    try {
      setSaving(true);
      let response;

      if (tipo === 'especie') {
        response = await api.post('/cadastros/especies', {
          nome: nome.trim(),
          ativo: true
        });
      } else {
        if (!especieId) {
          setError('Selecione uma espécie primeiro');
          return;
        }
        response = await api.post('/cadastros/racas', {
          nome: nome.trim(),
          especie_id: especieId,
          ativo: true
        });
      }

      // Chamar callback de sucesso
      if (onSuccess) {
        onSuccess(response.data);
      }

      // Fechar modal
      onClose();
    } catch (err) {
      console.error('Erro ao salvar:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="quick-modal-overlay" onClick={onClose}>
      <div className="quick-modal-content" onClick={e => e.stopPropagation()}>
        <div className="quick-modal-header">
          <h3>
            {tipo === 'especie' ? '🐾 Nova Espécie' : '✨ Nova Raça'}
            {tipo === 'raca' && especieNome && (
              <span className="quick-subtitle"> - {especieNome}</span>
            )}
          </h3>
          <button className="quick-btn-close" onClick={onClose}>
            <FiX />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="quick-modal-body">
            {error && (
              <div className="quick-alert quick-alert-danger">
                <FiAlertCircle /> {error}
              </div>
            )}

            <div className="quick-form-group">
              <label>
                Nome {tipo === 'especie' ? 'da Espécie' : 'da Raça'} *
              </label>
              <input
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder={
                  tipo === 'especie' 
                    ? 'Ex: Cão, Gato, Ave...' 
                    : 'Ex: Labrador, SRD, Siamês...'
                }
                required
                autoFocus
                disabled={saving}
              />
            </div>

            <div className="quick-info">
              <p>
                💡 {tipo === 'especie' 
                  ? 'Esta espécie ficará disponível para todos os pets' 
                  : `Esta raça será adicionada à espécie "${especieNome}"`
                }
              </p>
            </div>
          </div>

          <div className="quick-modal-footer">
            <button 
              type="button" 
              className="quick-btn quick-btn-secondary" 
              onClick={onClose}
              disabled={saving}
            >
              Cancelar
            </button>
            <button 
              type="submit" 
              className="quick-btn quick-btn-primary"
              disabled={saving}
            >
              <FiSave /> {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickAddModal;
