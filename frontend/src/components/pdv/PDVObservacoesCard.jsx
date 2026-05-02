import Panel from "../ui/Panel";

export default function PDVObservacoesCard({
  modoVisualizacao,
  observacoes,
  onObservacoesChange,
}) {
  return (
    <Panel padding="lg">
      <h2 className="mb-3 text-base font-semibold text-gray-900">Observacoes</h2>
      <textarea
        value={observacoes || ""}
        onChange={(e) => onObservacoesChange(e.target.value)}
        placeholder="Observacoes da venda (opcional)..."
        disabled={modoVisualizacao}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50"
        rows={2}
      />
    </Panel>
  );
}
