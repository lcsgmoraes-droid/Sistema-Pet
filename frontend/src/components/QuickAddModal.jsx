import { useState } from "react";
import { FiAlertCircle, FiSave, FiX } from "react-icons/fi";
import api from "../api";
import "./QuickAddModal.css";

/**
 * Modal rapido para adicionar especie ou raca sem sair do formulario de Pet.
 */
const QuickAddModal = ({ tipo, especieId, especieNome, onSuccess, onClose }) => {
  const [nome, setNome] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isRaca = tipo === "raca";
  const especieIdNormalizado = Number.parseInt(especieId, 10);
  const especieValida = Number.isInteger(especieIdNormalizado) && especieIdNormalizado > 0;
  const fieldId = `quick-add-${tipo || "item"}-nome`;

  const getApiErrorMessage = (err) => {
    const detail = err.response?.data?.detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => item?.msg || item?.message)
        .filter(Boolean)
        .join(" ");
      if (messages) return messages;
    }
    if (typeof detail === "string") return detail;
    return "Nao foi possivel salvar agora. Revise os dados e tente novamente.";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!nome || nome.trim() === "") {
      setError(`O nome ${tipo === "especie" ? "da especie" : "da raca"} e obrigatorio.`);
      return;
    }

    if (isRaca && !especieValida) {
      setError(
        "Selecione uma especie antes de cadastrar a raca. Escolha uma especie no campo anterior e tente novamente.",
      );
      return;
    }

    try {
      setSaving(true);
      let response;

      if (tipo === "especie") {
        response = await api.post("/cadastros/especies", {
          nome: nome.trim(),
          ativo: true,
        });
      } else {
        response = await api.post("/cadastros/racas", {
          nome: nome.trim(),
          especie_id: especieIdNormalizado,
          ativo: true,
        });
      }

      if (onSuccess) {
        onSuccess(response.data);
      }

      onClose();
    } catch (err) {
      console.error("Erro ao salvar:", err);
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="quick-modal-overlay" onClick={onClose}>
      <div className="quick-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="quick-modal-header">
          <h3>
            {tipo === "especie" ? "Nova especie" : "Nova raca"}
            {isRaca && especieNome && <span className="quick-subtitle"> - {especieNome}</span>}
          </h3>
          <button className="quick-btn-close" type="button" onClick={onClose}>
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
              <label htmlFor={fieldId}>
                Nome {tipo === "especie" ? "da especie" : "da raca"} *
              </label>
              <input
                id={fieldId}
                name={fieldId}
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder={
                  tipo === "especie" ? "Ex: Cao, Gato, Ave..." : "Ex: Labrador, SRD, Siames..."
                }
                required
                autoFocus
                disabled={saving}
              />
            </div>

            <div className="quick-info">
              <p>
                {tipo === "especie"
                  ? "Esta especie ficara disponivel para todos os pets."
                  : `Esta raca sera adicionada a especie "${especieNome || "selecionada"}".`}
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
              disabled={saving || (isRaca && !especieValida)}
            >
              <FiSave /> {saving ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickAddModal;
