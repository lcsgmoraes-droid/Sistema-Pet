import { FiCheckCircle, FiRefreshCw, FiTrash2 } from "react-icons/fi";
import PetIdentity from "../../components/ui/PetIdentity";

export default function LembreteCard({ lembrete, onCompletar, onRenovar, onCancelar }) {
  const diasRestantes = lembrete.dias_restantes;
  const dataProxima = new Date(lembrete.data_proxima_dose);
  const statusClass = diasRestantes < 0 ? "vencido" : diasRestantes <= 7 ? "proximo" : "futuro";
  const temDoseTotal = lembrete.dose_total && lembrete.dose_total > 0;
  const progressoPercentual = temDoseTotal ? (lembrete.dose_atual / lembrete.dose_total) * 100 : 0;

  return (
    <div className={`lembrete-card ${statusClass}`}>
      <div className="card-content">
        <div className="card-header">
          <h4>{lembrete.produto_nome}</h4>
          <div className="badges">
            {temDoseTotal && (
              <span className="dose-badge">
                Dose {lembrete.dose_atual}/{lembrete.dose_total}
              </span>
            )}
            <span className={`status-badge ${statusClass}`}>
              {diasRestantes < 0 ? "VENCIDO" : `${Math.abs(diasRestantes)}d`}
            </span>
          </div>
        </div>

        {temDoseTotal && (
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progressoPercentual}%` }} />
          </div>
        )}

        <div className="card-details">
          <div className="detail-row">
            <span className="label">Pet:</span>
            <span className="value">
              <PetIdentity
                fallback=""
                layout="inline"
                nameClassName="font-medium"
                record={lembrete}
              />
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Data:</span>
            <span className="value">{dataProxima.toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="detail-row">
            <span className="label">Quantidade:</span>
            <span className="value">{lembrete.quantidade}</span>
          </div>
          {lembrete.preco_estimado && (
            <div className="detail-row">
              <span className="label">Preco Est.:</span>
              <span className="value">R$ {lembrete.preco_estimado.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      <div className="card-actions">
        <button
          className="btn btn-success"
          onClick={() => onCompletar(lembrete.id)}
          title="Marcar como completado"
          type="button"
        >
          <FiCheckCircle /> Comprado
        </button>
        <button
          className="btn btn-primary"
          onClick={() => onRenovar(lembrete.id)}
          title="Renovar lembrete"
          type="button"
        >
          <FiRefreshCw /> Renovar
        </button>
        <button
          className="btn btn-danger"
          onClick={() => onCancelar(lembrete.id)}
          title="Cancelar lembrete"
          type="button"
        >
          <FiTrash2 />
        </button>
      </div>
    </div>
  );
}
