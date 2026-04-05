export default function CampanhasUnificacaoResultadoBanner({
  resultadoMerge,
  onDesfazer,
}) {
  if (!resultadoMerge) {
    return null;
  }

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm flex items-start justify-between gap-2">
      <div>
        <p className="font-semibold text-green-800">
          Clientes unificados! (Merge #{resultadoMerge.merge_id})
        </p>
        <p className="text-green-600">
          Transferidos: {resultadoMerge.transferencias?.cashback ?? 0}{" "}
          cashbacks, {resultadoMerge.transferencias?.carimbos ?? 0} carimbos,{" "}
          {resultadoMerge.transferencias?.cupons ?? 0} cupons,{" "}
          {resultadoMerge.transferencias?.ranking ?? 0} posicoes de ranking,{" "}
          {resultadoMerge.transferencias?.vendas ?? 0} vendas,{" "}
          {resultadoMerge.transferencias?.execucoes_campanhas ?? 0} execucoes
          de campanha.
        </p>
      </div>
      <button
        onClick={() => onDesfazer(resultadoMerge.merge_id)}
        className="text-xs text-red-600 hover:underline whitespace-nowrap"
      >
        Desfazer
      </button>
    </div>
  );
}
