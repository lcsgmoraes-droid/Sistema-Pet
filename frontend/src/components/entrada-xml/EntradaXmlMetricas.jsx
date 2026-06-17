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

export default function EntradaXmlMetricas({ formatMoneyBRL, notasEntrada, onFiltroStatus }) {
  const totalNotas = notasEntrada.length;
  const pendentes = notasEntrada.filter((nota) => nota.status === "pendente").length;
  const conciliadas = notasEntrada.filter((nota) => nota.status === "processada");
  const valorConciliado = conciliadas.reduce((total, nota) => total + (nota.valor_total || 0), 0);

  return (
    <MetricGrid className="mb-6">
      <FiltroMetricCard
        intent="blue"
        label="Total de notas"
        value={totalNotas}
        subtitle="Todas as importacoes"
        onClick={() => onFiltroStatus("todos")}
      />
      <FiltroMetricCard
        intent="amber"
        label="Pendentes"
        value={pendentes}
        subtitle="Aguardando conferencia"
        onClick={() => onFiltroStatus("pendente")}
      />
      <FiltroMetricCard
        intent="emerald"
        label="Conciliadas"
        value={conciliadas.length}
        subtitle="Entrada ja processada"
        onClick={() => onFiltroStatus("processada")}
      />
      <MetricCard
        intent="violet"
        label="Valor conciliado"
        value={formatMoneyBRL(valorConciliado)}
        subtitle="Somente notas conciliadas"
      />
    </MetricGrid>
  );
}

EntradaXmlMetricas.propTypes = {
  formatMoneyBRL: PropTypes.func.isRequired,
  notasEntrada: PropTypes.arrayOf(
    PropTypes.shape({
      status: PropTypes.string,
      valor_total: PropTypes.number,
    }),
  ).isRequired,
  onFiltroStatus: PropTypes.func.isRequired,
};
