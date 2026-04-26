export default function ExameIAListas({ achadosImagem, condutasSugeridas, limitacoesIA }) {
  if (achadosImagem.length === 0 && condutasSugeridas.length === 0 && limitacoesIA.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-3 md:grid-cols-3">
      <ListaIA titulo="Achados da imagem" itens={achadosImagem} vazio="Sem achados visuais destacados." />
      <ListaIA titulo="Condutas sugeridas" itens={condutasSugeridas} vazio="Sem conduta sugerida automaticamente." />
      <ListaIA titulo="Limitacoes" itens={limitacoesIA} vazio="Sem limitacoes especiais registradas." />
    </div>
  );
}

function ListaIA({ itens, titulo, vazio }) {
  return (
    <div className="rounded-lg border border-indigo-100 bg-gray-50 px-3 py-3">
      <p className="font-medium text-gray-800">{titulo}</p>
      {itens.length > 0 ? (
        <ul className="mt-2 space-y-1 text-gray-600">
          {itens.map((item, index) => (
            <li key={`${titulo}_${index}`}>- {item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-gray-500">{vazio}</p>
      )}
    </div>
  );
}
