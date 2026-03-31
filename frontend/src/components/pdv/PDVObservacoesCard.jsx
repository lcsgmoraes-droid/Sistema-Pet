export default function PDVObservacoesCard({
  modoVisualizacao,
  observacoes,
  onObservacoesChange,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Observações</h2>
      <textarea
        value={observacoes || ""}
        onChange={(e) => onObservacoesChange(e.target.value)}
        placeholder="Observações da venda (opcional)..."
        disabled={modoVisualizacao}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
        rows={3}
      />
    </div>
  );
}
