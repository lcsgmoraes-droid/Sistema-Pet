export default function BanhoTosaInsumoAcoes({
  insumo,
  removing,
  estornando,
  onEstornar,
  onRemover,
}) {
  if (insumo.movimentacao_estorno_id) {
    return (
      <div className="flex flex-col items-start gap-1 sm:items-end">
        <span className="text-xs font-bold text-sky-600">Estoque estornado</span>
        <RemoveButton insumo={insumo} removing={removing} onRemover={onRemover} />
      </div>
    );
  }

  if (insumo.movimentacao_estoque_id) {
    return (
      <button
        type="button"
        disabled={estornando}
        onClick={() => onEstornar(insumo)}
        className="text-xs font-bold text-amber-600 hover:text-amber-700 disabled:opacity-60"
      >
        {estornando ? "Estornando..." : "Estornar estoque"}
      </button>
    );
  }

  return <RemoveButton insumo={insumo} removing={removing} onRemover={onRemover} />;
}

function RemoveButton({ insumo, removing, onRemover }) {
  return (
    <button
      type="button"
      disabled={removing}
      onClick={() => onRemover(insumo)}
      className="text-xs font-bold text-rose-600 hover:text-rose-700 disabled:opacity-60"
    >
      {removing ? "Removendo..." : "Remover"}
    </button>
  );
}
