export default function LembretesHeader({ controller }) {
  return (
    <div className="lembretes-header">
      <h1>Lembretes de Recorrencia</h1>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-number">{controller.lembretes.length}</span>
          <span className="stat-label">Total de Lembretes</span>
        </div>
        <div className="stat-card warning">
          <span className="stat-number">{controller.proximosEmBreve.length}</span>
          <span className="stat-label">Proximos em 7 dias</span>
        </div>
        <div className="stat-card danger">
          <span className="stat-number">{controller.vencidos.length}</span>
          <span className="stat-label">Vencidos</span>
        </div>
      </div>
    </div>
  );
}
