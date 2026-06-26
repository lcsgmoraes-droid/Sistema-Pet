import { FiBell } from "react-icons/fi";
import LembreteCard from "./LembreteCard";

export default function LembretesList({ controller }) {
  if (controller.loading) {
    return <div className="loading">Carregando lembretes...</div>;
  }

  if (controller.semPendencias) {
    return (
      <div className="empty-state">
        <FiBell size={48} />
        <h2>Nenhum lembrete pendente</h2>
        <p>Lembretes serao criados automaticamente para produtos recorrentes.</p>
      </div>
    );
  }

  return (
    <div className="lembretes-list">
      <LembretesSection
        className="danger"
        lembretes={controller.vencidos}
        title="Vencidos"
        controller={controller}
      />
      <LembretesSection
        className="warning"
        lembretes={controller.proximosEmBreve}
        title="Proximos em ate 7 dias"
        controller={controller}
      />
      <LembretesSection
        lembretes={controller.futuros}
        title="Proximos (mais de 7 dias)"
        controller={controller}
      />
    </div>
  );
}

function LembretesSection({ className = "", controller, lembretes, title }) {
  if (lembretes.length === 0) return null;

  return (
    <div className="section">
      <h3 className={`section-title ${className}`}>{title}</h3>
      {lembretes.map((lembrete) => (
        <LembreteCard
          key={lembrete.id}
          lembrete={lembrete}
          onCancelar={controller.cancelarLembrete}
          onCompletar={controller.completarLembrete}
          onRenovar={controller.renovarLembrete}
        />
      ))}
    </div>
  );
}
