import React from "react";

function ProductRow({ itemJaAdicionado, produto, selecionarItem, temConfiguracao }) {
  const prodConfigurado = temConfiguracao("produto", produto.id);
  const prodAdicionado = itemJaAdicionado("produto", produto.id);

  if (prodConfigurado) {
    return null;
  }

  return (
    <div
      className={`p-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${
        prodAdicionado ? "bg-yellow-50" : ""
      }`}
      onClick={() => selecionarItem("produto", produto.id, produto.nome)}
    >
      <span className="text-sm">📌 {produto.nome}</span>
      {prodAdicionado && <span className="text-xs text-yellow-600">⏳ Na lista</span>}
    </div>
  );
}

function ProductList({ categoria, itemJaAdicionado, nivel, selecionarItem, temConfiguracao }) {
  if (!categoria.produtos?.length) {
    return null;
  }

  return (
    <div className="pl-6" style={{ paddingLeft: `${24 + nivel * 20}px` }}>
      {categoria.produtos.map((produto) => (
        <ProductRow
          key={`prod-${produto.id}`}
          itemJaAdicionado={itemJaAdicionado}
          produto={produto}
          selecionarItem={selecionarItem}
          temConfiguracao={temConfiguracao}
        />
      ))}
    </div>
  );
}

function CategoryRow({
  categoria,
  categoriasExpanded,
  itemJaAdicionado,
  nivel,
  selecionarItem,
  temConfiguracao,
  toggleCategoria,
}) {
  const indentacao = "  ".repeat(nivel);
  const icone = nivel === 0 ? "📦" : "→";
  const temFilhas = categoria.filhas && categoria.filhas.length > 0;
  const temProdutos = categoria.produtos && categoria.produtos.length > 0;
  const jaConfigurado = temConfiguracao("categoria", categoria.id);
  const expanded = categoriasExpanded[categoria.id];

  if (jaConfigurado) {
    if (!expanded) return null;

    return (
      <React.Fragment>
        {temFilhas &&
          categoria.filhas.map((filha) => (
            <CategoryRow
              key={`cat-${filha.id}`}
              categoria={filha}
              categoriasExpanded={categoriasExpanded}
              itemJaAdicionado={itemJaAdicionado}
              nivel={nivel + 1}
              selecionarItem={selecionarItem}
              temConfiguracao={temConfiguracao}
              toggleCategoria={toggleCategoria}
            />
          ))}
        {temProdutos && (
          <ProductList
            categoria={categoria}
            itemJaAdicionado={itemJaAdicionado}
            nivel={nivel}
            selecionarItem={selecionarItem}
            temConfiguracao={temConfiguracao}
          />
        )}
      </React.Fragment>
    );
  }

  return (
    <div className="border-b last:border-b-0">
      <div
        className={`p-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${
          itemJaAdicionado("categoria", categoria.id) ? "bg-yellow-50" : ""
        }`}
        style={{ paddingLeft: `${12 + nivel * 20}px` }}
        onClick={() => selecionarItem("categoria", categoria.id, `${indentacao}${categoria.nome}`)}
      >
        <div className="flex items-center gap-2">
          {(temFilhas || temProdutos) && (
            <button
              onClick={(event) => {
                event.stopPropagation();
                toggleCategoria(categoria.id);
              }}
              className="text-gray-500"
            >
              {expanded ? "▼" : "▶"}
            </button>
          )}
          <span className={nivel === 0 ? "font-medium" : "text-sm"}>
            {icone} {categoria.nome}
            {nivel > 0 && <span className="text-xs text-gray-500 ml-1">(Nível {nivel + 1})</span>}
          </span>
        </div>
        {itemJaAdicionado("categoria", categoria.id) && (
          <span className="text-xs text-yellow-600">⏳ Na lista</span>
        )}
      </div>

      {expanded && (
        <div>
          {temFilhas &&
            categoria.filhas.map((filha) => (
              <CategoryRow
                key={`cat-${filha.id}`}
                categoria={filha}
                categoriasExpanded={categoriasExpanded}
                itemJaAdicionado={itemJaAdicionado}
                nivel={nivel + 1}
                selecionarItem={selecionarItem}
                temConfiguracao={temConfiguracao}
                toggleCategoria={toggleCategoria}
              />
            ))}
          {temProdutos && (
            <ProductList
              categoria={categoria}
              itemJaAdicionado={itemJaAdicionado}
              nivel={nivel}
              selecionarItem={selecionarItem}
              temConfiguracao={temConfiguracao}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default function ComissaoProductTree({
  arvoreProdutos,
  categoriasExpanded,
  itemJaAdicionado,
  loading,
  selecionarItem,
  temConfiguracao,
  toggleCategoria,
}) {
  if (loading) {
    return <div className="text-center py-8">Carregando...</div>;
  }

  const regraGeralConfigurada = temConfiguracao("geral", 0);
  const regraGeralAdicionada = itemJaAdicionado("geral", 0);

  return (
    <div key={String(regraGeralConfigurada)} className="border rounded-lg max-h-96 overflow-y-auto">
      <div
        className={`p-3 border-b cursor-pointer transition-colors ${
          regraGeralConfigurada
            ? "bg-green-50 text-green-700 cursor-default"
            : regraGeralAdicionada
              ? "bg-yellow-50"
              : "bg-blue-50 hover:bg-blue-100"
        }`}
        onClick={() => {
          if (!regraGeralConfigurada) {
            selecionarItem("geral", 0, "Regra geral");
          }
        }}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-sm">Regra geral</p>
            <p className="text-xs text-gray-600">Todos os produtos e categorias deste parceiro</p>
          </div>
          {regraGeralConfigurada ? (
            <span className="text-xs font-medium text-green-700">Ja configurada</span>
          ) : regraGeralAdicionada ? (
            <span className="text-xs text-yellow-600">Na lista</span>
          ) : (
            <span className="text-xs font-medium text-blue-700">Selecionar tudo</span>
          )}
        </div>
      </div>
      {arvoreProdutos.map((categoria) => (
        <CategoryRow
          key={`cat-${categoria.id}`}
          categoria={categoria}
          categoriasExpanded={categoriasExpanded}
          itemJaAdicionado={itemJaAdicionado}
          nivel={0}
          selecionarItem={selecionarItem}
          temConfiguracao={temConfiguracao}
          toggleCategoria={toggleCategoria}
        />
      ))}
    </div>
  );
}
