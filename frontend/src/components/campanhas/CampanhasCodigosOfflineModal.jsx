export default function CampanhasCodigosOfflineModal({
  modalCodigosOffline,
  setModalCodigosOffline,
  loadingCodigosOffline,
  codigosOffline,
  RANK_LABELS,
}) {
  if (!modalCodigosOffline) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">
              Codigos offline - {modalCodigosOffline.name}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Lista de participantes para sorteio fisico
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200"
            >
              Imprimir
            </button>
            <button
              onClick={() => setModalCodigosOffline(null)}
              className="text-gray-400 hover:text-gray-600 text-xl ml-2"
            >
              x
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loadingCodigosOffline ? (
            <div className="text-center text-gray-400 py-8">Carregando...</div>
          ) : codigosOffline.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              Nenhum participante encontrado.
            </div>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                  <th className="text-center p-2 border-b w-16">No</th>
                  <th className="text-left p-2 border-b">Cliente</th>
                  <th className="text-center p-2 border-b">Nivel</th>
                </tr>
              </thead>
              <tbody>
                {codigosOffline.map((c) => (
                  <tr
                    key={c.numero}
                    className="border-b last:border-0 hover:bg-gray-50"
                  >
                    <td className="p-2 text-center font-mono font-semibold text-gray-700">
                      {c.numero}
                    </td>
                    <td className="p-2 text-gray-700">
                      {c.nome || `Cliente #${c.customer_id}`}
                    </td>
                    <td className="p-2 text-center text-xs text-gray-500">
                      {c.rank_level
                        ? `${RANK_LABELS[c.rank_level]?.emoji || ""} ${RANK_LABELS[c.rank_level]?.label || c.rank_level}`
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="px-6 py-3 border-t text-xs text-gray-400">
          {codigosOffline.length} participante(s) - Sorteio:{" "}
          {modalCodigosOffline.name}
        </div>
      </div>
    </div>
  );
}
