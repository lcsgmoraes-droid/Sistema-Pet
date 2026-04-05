function getCategoriaLabel(categoria) {
  return categoria === "maior_gasto" ? "Maior Gasto" : "Mais Compras";
}

export default function CampanhasDestaqueDesempateInfo({ desempateInfo }) {
  if (!desempateInfo?.length) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-4 space-y-2">
      <p className="font-semibold text-yellow-800 text-sm">Desempate aplicado</p>
      {desempateInfo.map((desempate, index) => (
        <div key={index} className="text-sm text-yellow-700 leading-relaxed">
          <span className="font-medium">{getCategoriaLabel(desempate.categoria)}:</span>{" "}
          <span className="line-through text-yellow-500">
            {desempate.pulado?.nome}
          </span>{" "}
          (1o lugar) ja ganhou em outra categoria - o{" "}
          <span className="font-medium">{desempate.posicao_eleito}o colocado</span>{" "}
          <span className="font-semibold text-yellow-800">
            {desempate.eleito?.nome}
          </span>{" "}
          foi selecionado no lugar.
        </div>
      ))}
    </div>
  );
}
