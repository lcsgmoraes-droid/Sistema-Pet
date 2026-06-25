import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import MoneyCell from "../../../components/ui/MoneyCell";

export default function ComissoesListagemResumo({ controller }) {
  const { erroResumo, loadingResumo, resumo } = controller;

  if (loadingResumo) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
            <div className="h-8 bg-gray-200 rounded w-32"></div>
          </div>
        ))}
      </div>
    );
  }

  if (erroResumo) {
    return (
      <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          ?????? N??o foi poss??vel carregar o resumo financeiro
        </p>
      </div>
    );
  }

  if (!resumo) return null;

  const cards = [
    {
      titulo: "Total Gerado",
      valor: resumo.total_gerado,
      intent: "blue",
    },
    {
      titulo: "Total Pago",
      valor: resumo.total_pago,
      intent: "emerald",
    },
    {
      titulo: "Total Pendente",
      valor: resumo.total_pendente,
      intent: "amber",
    },
    {
      titulo: "Saldo a Pagar",
      valor: resumo.saldo_a_pagar,
      intent: "violet",
    },
  ];

  return (
    <MetricGrid className="mb-6">
      {cards.map((card, index) => (
        <MetricCard
          key={index}
          intent={card.intent}
          label={card.titulo}
          value={<MoneyCell value={card.valor} />}
        />
      ))}
    </MetricGrid>
  );
}
