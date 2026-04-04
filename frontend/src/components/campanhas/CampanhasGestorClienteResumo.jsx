function getRankMeta(rankLabels, rankLevel) {
  return rankLabels[rankLevel] || rankLabels.bronze;
}

export default function CampanhasGestorClienteResumo({
  gestorCliente,
  gestorSaldo,
  rankLabels,
}) {
  if (!gestorCliente || !gestorSaldo) {
    return null;
  }

  const rank = getRankMeta(rankLabels, gestorSaldo.rank_level);

  return (
    <div className="bg-white rounded-xl border shadow-sm p-4 flex items-center gap-4">
      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-lg shrink-0">
        {gestorCliente.nome?.[0]?.toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-900 truncate">
          {gestorCliente.nome}
        </p>
        <p className="text-xs text-gray-400">
          ID #{gestorCliente.id} ·{" "}
          {gestorCliente.telefone || gestorCliente.celular || "Sem telefone"}
        </p>
      </div>
      <span
        className={`px-3 py-1 rounded-full text-sm font-medium shrink-0 ${rank.color}`}
      >
        {rank.emoji} {rank.label}
      </span>
    </div>
  );
}
