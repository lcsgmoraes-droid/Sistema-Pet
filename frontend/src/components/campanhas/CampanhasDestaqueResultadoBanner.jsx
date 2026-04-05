function getCategoriaLabel(categoria) {
  return categoria === "maior_gasto" ? "Maior Gasto" : "Mais Compras";
}

export default function CampanhasDestaqueResultadoBanner({
  destaqueResultado,
  onReset,
}) {
  if (!destaqueResultado) {
    return null;
  }

  return (
    <div className="bg-green-50 border border-green-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="font-semibold text-green-800">
          Premios enviados! ({destaqueResultado.enviados} vencedor(es))
        </p>
        <button
          onClick={onReset}
          className="text-xs text-gray-400 hover:text-gray-600 underline"
        >
          Enviar novamente
        </button>
      </div>
      <ul className="space-y-1.5">
        {(destaqueResultado.resultados || []).map((resultado, index) => (
          <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
            <span>{getCategoriaLabel(resultado.categoria)}:</span>
            {resultado.tipo_premio === "cupom" ? (
              <>
                <span className="font-mono font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">
                  {resultado.coupon_code}
                </span>
                {resultado.ja_existia && (
                  <span className="text-xs text-gray-400">(ja existia)</span>
                )}
              </>
            ) : (
              <span className="text-amber-700">Brinde registrado</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
