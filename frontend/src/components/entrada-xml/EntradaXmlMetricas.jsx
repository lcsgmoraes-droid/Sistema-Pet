import PropTypes from "prop-types";
import MetricCard from "../ui/MetricCard";
import MetricGrid from "../ui/MetricGrid";

function FiltroMetricCard({ intent, label, onClick, subtitle, value }) {
  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className="cursor-pointer outline-none transition-transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
    >
      <MetricCard intent={intent} label={label} subtitle={subtitle} value={value} />
    </div>
  );
}

FiltroMetricCard.propTypes = {
  intent: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
  subtitle: PropTypes.string,
  value: PropTypes.node.isRequired,
};

FiltroMetricCard.defaultProps = {
  subtitle: undefined,
};

export default function EntradaXmlMetricas({ formatMoneyBRL, metricas, onFiltroStatus }) {
  return (
    <MetricGrid className="mb-6">
      <FiltroMetricCard
        intent="blue"
        label="Total de notas"
        value={metricas.total_notas}
        subtitle="Todas as importacoes"
        onClick={() => onFiltroStatus("todos")}
      />
      <FiltroMetricCard
        intent="amber"
        label="Pendentes"
        value={metricas.pendentes}
        subtitle="Aguardando conferencia"
        onClick={() => onFiltroStatus("pendente")}
      />
      <FiltroMetricCard
        intent="emerald"
        label="Conciliadas"
        value={metricas.conciliadas}
        subtitle="Entrada ja processada"
        onClick={() => onFiltroStatus("processada")}
      />
      <MetricCard
        intent="violet"
        label="Valor conciliado"
        value={formatMoneyBRL(metricas.valor_conciliado)}
        subtitle="Somente notas conciliadas"
      />
    </MetricGrid>
  );
}

EntradaXmlMetricas.propTypes = {
  formatMoneyBRL: PropTypes.func.isRequired,
  metricas: PropTypes.shape({
    total_notas: PropTypes.number,
    pendentes: PropTypes.number,
    conciliadas: PropTypes.number,
    com_erro: PropTypes.number,
    valor_conciliado: PropTypes.number,
  }).isRequired,
  onFiltroStatus: PropTypes.func.isRequired,
};
