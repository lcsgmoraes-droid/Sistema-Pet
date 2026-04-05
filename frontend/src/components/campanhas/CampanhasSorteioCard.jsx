const STATUS_COLORS = {
  draft: "bg-gray-100 text-gray-600",
  open: "bg-blue-100 text-blue-700",
  drawn: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-600",
};

const STATUS_LABELS = {
  draft: "Rascunho",
  open: "Inscrito",
  drawn: "Realizado",
  cancelled: "Cancelado",
};

export default function CampanhasSorteioCard({
  sorteio,
  rankLabels,
  inscrevendo,
  onInscrever,
  executandoSorteio,
  onExecutar,
  onCancelar,
  onAbrirCodigosOffline,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-gray-900">{sorteio.name}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                STATUS_COLORS[sorteio.status] || "bg-gray-100 text-gray-600"
              }`}
            >
              {STATUS_LABELS[sorteio.status] || sorteio.status}
            </span>
            {sorteio.rank_filter && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                {rankLabels[sorteio.rank_filter]?.emoji}{" "}
                {rankLabels[sorteio.rank_filter]?.label || sorteio.rank_filter}
                +
              </span>
            )}
          </div>
          {sorteio.prize_description && (
            <p className="text-sm text-gray-600">{sorteio.prize_description}</p>
          )}
          {sorteio.description && (
            <p className="text-xs text-gray-400 mt-0.5">
              {sorteio.description}
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            {sorteio.total_participantes || 0} participante(s)
            {sorteio.draw_date &&
              ` - Sorteio: ${new Date(sorteio.draw_date).toLocaleDateString(
                "pt-BR",
              )}`}
          </p>
        </div>
        <div className="flex flex-col gap-2 items-end shrink-0">
          {sorteio.status === "draft" && (
            <button
              onClick={() => onInscrever(sorteio.id)}
              disabled={inscrevendo === sorteio.id}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {inscrevendo === sorteio.id ? "..." : "Inscrever elegiveis"}
            </button>
          )}
          {sorteio.status === "open" && (
            <button
              onClick={() => onExecutar(sorteio.id)}
              disabled={executandoSorteio === sorteio.id}
              className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              {executandoSorteio === sorteio.id ? "..." : "Executar sorteio"}
            </button>
          )}
          {(sorteio.status === "draft" || sorteio.status === "open") && (
            <button
              onClick={() => onCancelar(sorteio.id, sorteio.name)}
              className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-medium hover:bg-red-100"
            >
              Cancelar
            </button>
          )}
          {(sorteio.status === "open" || sorteio.status === "drawn") && (
            <button
              onClick={() => onAbrirCodigosOffline(sorteio)}
              className="px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-100 border"
            >
              Codigos offline
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
