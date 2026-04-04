export default function CampanhasRankingLoteCard({
  setResultadoLote,
  setModalLote,
}) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
      <div>
        <p className="font-semibold text-blue-800">Envio em lote</p>
        <p className="text-sm text-blue-600">
          Envie um e-mail personalizado para todos os clientes de um nivel.
        </p>
      </div>
      <button
        onClick={() => {
          setResultadoLote(null);
          setModalLote(true);
        }}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        Enviar para nivel
      </button>
    </div>
  );
}
