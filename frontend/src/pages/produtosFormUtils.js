export function organizarCategoriasHierarquicas(categorias) {
  if (!categorias || categorias.length === 0) return [];

  const categoriasMap = {};
  categorias.forEach((categoria) => {
    categoriasMap[categoria.id] = { ...categoria, filhas: [] };
  });

  const raizes = [];
  categorias.forEach((categoria) => {
    if (categoria.categoria_pai_id) {
      if (categoriasMap[categoria.categoria_pai_id]) {
        categoriasMap[categoria.categoria_pai_id].filhas.push(
          categoriasMap[categoria.id],
        );
      }
    } else {
      raizes.push(categoriasMap[categoria.id]);
    }
  });

  const aplanar = (categoriasParaAplanar, nivel = 0) =>
    categoriasParaAplanar.flatMap((categoria) => [
      { ...categoria, nivel },
      ...aplanar(categoria.filhas || [], nivel + 1),
    ]);

  return aplanar(raizes);
}

export function formatarValorMonetarioProduto(valor) {
  if (!valor || valor === "") return "R$ 0,00";
  const numero = typeof valor === "string" ? parseFloat(valor) : valor;
  if (Number.isNaN(numero)) return "R$ 0,00";
  return `R$ ${numero.toFixed(2).replace(".", ",")}`;
}

export function formatarPorcentagemProduto(valor) {
  if (!valor || valor === "") return "0,00%";
  const numero = typeof valor === "string" ? parseFloat(valor) : valor;
  if (Number.isNaN(numero)) return "0,00%";
  return `${numero.toFixed(2).replace(".", ",")}%`;
}

export function calcularMargemPercentual(custo, venda) {
  const custoNumerico = parseFloat(custo) || 0;
  const vendaNumerica = parseFloat(venda) || 0;

  if (custoNumerico <= 0) {
    return null;
  }

  const margem = ((vendaNumerica - custoNumerico) / custoNumerico) * 100;
  return margem.toFixed(2);
}

export function montarPayloadFornecedorProduto(dados) {
  return {
    ...dados,
    preco_custo: parseFloat(dados.preco_custo) || null,
    prazo_entrega: parseInt(dados.prazo_entrega, 10) || null,
    estoque_fornecedor: parseFloat(dados.estoque_fornecedor) || null,
  };
}

export function montarPayloadMovimentoEstoque(tipo, dados) {
  const payload = {
    quantidade: parseFloat(dados.quantidade),
    observacao: dados.observacao || null,
  };

  if (tipo === "entrada") {
    payload.numero_lote = dados.numero_lote || null;
    payload.preco_custo = parseFloat(dados.preco_custo) || 0;
    payload.data_validade = dados.data_validade || null;
  }

  return payload;
}
