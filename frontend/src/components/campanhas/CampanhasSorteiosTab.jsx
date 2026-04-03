export default function CampanhasSorteiosTab({
  loadingSorteios,
  sorteios,
  sorteioResultado,
  setSorteioResultado,
  setErroCriarSorteio,
  setModalSorteio,
  inscrevendo,
  inscreverSorteio,
  executandoSorteio,
  executarSorteio,
  cancelarSorteio,
  abrirCodigosOffline,
  rankLabels,
}) {
  const statusColors = {
    draft: "bg-gray-100 text-gray-600",
    open: "bg-blue-100 text-blue-700",
    drawn: "bg-green-100 text-green-700",
    cancelled: "bg-red-100 text-red-600",
  };

  const statusLabels = {
    draft: "Rascunho",
    open: "Inscrito",
    drawn: "Realizado",
    cancelled: "Cancelado",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Sorteios</h2>
          <p className="text-sm text-gray-500">
            Crie sorteios exclusivos por nivel de ranking. O resultado e
            auditavel via seed UUID.
          </p>
        </div>
        <button
          onClick={() => {
            setErroCriarSorteio("");
            setModalSorteio(true);
          }}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
        >
          + Novo Sorteio
        </button>
      </div>

      {sorteioResultado && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
          <p className="font-semibold text-purple-800 text-lg mb-1">
            Sorteio executado!
          </p>
          <p className="text-purple-700">
            Ganhador: <strong>{sorteioResultado.winner_name}</strong>
          </p>
          <p className="text-sm text-purple-600 mt-1">
            {sorteioResultado.total_participantes} participante(s) · Seed:{" "}
            <span className="font-mono text-xs">
              {sorteioResultado.seed_uuid?.slice(0, 16)}...
            </span>
          </p>
          <button
            onClick={() => setSorteioResultado(null)}
            className="mt-2 text-xs text-purple-500 hover:underline"
          >
            Fechar
          </button>
        </div>
      )}

      {loadingSorteios ? (
        <div className="p-8 text-center text-gray-400">
          Carregando sorteios...
        </div>
      ) : sorteios.length === 0 ? (
        <div className="bg-white rounded-xl border shadow-sm p-8 text-center text-gray-400">
          <p className="text-3xl mb-2">🎲</p>
          <p>Nenhum sorteio criado ainda.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorteios.map((sorteio) => (
            <div
              key={sorteio.id}
              className="bg-white rounded-xl border shadow-sm p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-semibold text-gray-900">
                      {sorteio.name}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        statusColors[sorteio.status] ||
                        "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {statusLabels[sorteio.status] || sorteio.status}
                    </span>
                    {sorteio.rank_filter && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                        {rankLabels[sorteio.rank_filter]?.emoji}{" "}
                        {rankLabels[sorteio.rank_filter]?.label ||
                          sorteio.rank_filter}
                        +
                      </span>
                    )}
                  </div>
                  {sorteio.prize_description && (
                    <p className="text-sm text-gray-600">
                      {sorteio.prize_description}
                    </p>
                  )}
                  {sorteio.description && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      {sorteio.description}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {sorteio.total_participantes || 0} participante(s)
                    {sorteio.draw_date &&
                      ` · Sorteio: ${new Date(sorteio.draw_date).toLocaleDateString(
                        "pt-BR",
                      )}`}
                  </p>
                </div>
                <div className="flex flex-col gap-2 items-end shrink-0">
                  {sorteio.status === "draft" && (
                    <button
                      onClick={() => inscreverSorteio(sorteio.id)}
                      disabled={inscrevendo === sorteio.id}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {inscrevendo === sorteio.id
                        ? "..."
                        : "Inscrever elegiveis"}
                    </button>
                  )}
                  {sorteio.status === "open" && (
                    <button
                      onClick={() => executarSorteio(sorteio.id)}
                      disabled={executandoSorteio === sorteio.id}
                      className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-700 disabled:opacity-50"
                    >
                      {executandoSorteio === sorteio.id
                        ? "..."
                        : "Executar sorteio"}
                    </button>
                  )}
                  {(sorteio.status === "draft" ||
                    sorteio.status === "open") && (
                    <button
                      onClick={() => cancelarSorteio(sorteio.id, sorteio.name)}
                      className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-medium hover:bg-red-100"
                    >
                      Cancelar
                    </button>
                  )}
                  {(sorteio.status === "open" ||
                    sorteio.status === "drawn") && (
                    <button
                      onClick={() => abrirCodigosOffline(sorteio)}
                      className="px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-100 border"
                    >
                      Codigos offline
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
