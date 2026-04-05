export default function CampanhasSorteioResultadoBanner({
  sorteioResultado,
  onFechar,
}) {
  if (!sorteioResultado) {
    return null;
  }

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
      <p className="font-semibold text-purple-800 text-lg mb-1">
        Sorteio executado!
      </p>
      <p className="text-purple-700">
        Ganhador: <strong>{sorteioResultado.winner_name}</strong>
      </p>
      <p className="text-sm text-purple-600 mt-1">
        {sorteioResultado.total_participantes} participante(s) - Seed:{" "}
        <span className="font-mono text-xs">
          {sorteioResultado.seed_uuid?.slice(0, 16)}...
        </span>
      </p>
      <button
        onClick={onFechar}
        className="mt-2 text-xs text-purple-500 hover:underline"
      >
        Fechar
      </button>
    </div>
  );
}
