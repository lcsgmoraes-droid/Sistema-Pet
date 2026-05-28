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

export function montarEstadoProdutoFormulario(prod = {}) {
  return {
    codigo: prod.codigo || "",
    nome: prod.nome || "",
    descricao: prod.descricao || "",
    categoria_id: prod.categoria_id || "",
    marca_id: prod.marca_id || "",
    departamento_id: prod.departamento_id || "",
    tipo: prod.tipo || "produto",
    preco_custo: prod.preco_custo || "",
    preco_venda: prod.preco_venda || "",
    margem_lucro: prod.margem_lucro || "",
    estoque_minimo: prod.estoque_minimo || "",
    estoque_maximo: prod.estoque_maximo || "",
    localizacao: prod.localizacao || "",
    observacoes: prod.observacoes || "",
    controle_lote: prod.controle_lote || false,
    status: prod.status || "ativo",
    preco_ecommerce: prod.preco_ecommerce ?? null,
    preco_ecommerce_promo: prod.preco_ecommerce_promo ?? null,
    preco_ecommerce_promo_inicio: prod.preco_ecommerce_promo_inicio ?? null,
    preco_ecommerce_promo_fim: prod.preco_ecommerce_promo_fim ?? null,
    preco_app: prod.preco_app ?? null,
    preco_app_promo: prod.preco_app_promo ?? null,
    preco_app_promo_inicio: prod.preco_app_promo_inicio ?? null,
    preco_app_promo_fim: prod.preco_app_promo_fim ?? null,
    anunciar_ecommerce: prod.anunciar_ecommerce ?? true,
    anunciar_app: prod.anunciar_app ?? true,
  };
}

export function validarProdutoParaSalvar(produto = {}) {
  if (!String(produto.nome || "").trim()) {
    return "Nome do produto é obrigatório";
  }

  if (!produto.preco_venda || parseFloat(produto.preco_venda) <= 0) {
    return "Preço de venda é obrigatório e deve ser maior que zero";
  }

  return null;
}

export function validarArquivoImagemProduto(file, maxUploadBytes = 10 * 1024 * 1024) {
  const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

  if (!allowedTypes.includes(file?.type)) {
    return "Apenas JPG, PNG e WebP são permitidos";
  }

  if ((file?.size || 0) > maxUploadBytes) {
    return "Imagem deve ter no maximo 10MB";
  }

  return null;
}

export function montarEstadoFornecedorProduto(fornecedor = {}) {
  return {
    fornecedor_id: fornecedor?.fornecedor_id || "",
    codigo_fornecedor: fornecedor?.codigo_fornecedor || "",
    preco_custo: fornecedor?.preco_custo || "",
    prazo_entrega: fornecedor?.prazo_entrega || "",
    estoque_fornecedor: fornecedor?.estoque_fornecedor || "",
    e_principal: fornecedor?.e_principal || false,
  };
}

export function montarEstadoMovimentoEstoque() {
  return {
    quantidade: "",
    numero_lote: "",
    preco_custo: "",
    data_validade: "",
    observacao: "",
  };
}

export function montarAbasProdutoFormulario({
  isEdit,
  imagens = [],
  fornecedores = [],
  lotes = [],
  variacoes = [],
  produto = {},
}) {
  const abas = [{ id: "dados", label: "\u{1F4CB} Dados B\u00E1sicos", count: null }];

  if (!isEdit) {
    return abas;
  }

  abas.push(
    { id: "imagens", label: "\u{1F5BC}\uFE0F Imagens", count: imagens.length },
    { id: "fornecedores", label: "\u{1F3ED} Fornecedores", count: fornecedores.length },
  );

  if (produto.controle_lote) {
    abas.push({ id: "lotes", label: "\u{1F4E6} Lotes", count: lotes.length });
  }

  if (produto.tipo_produto === "PAI") {
    abas.push({ id: "variacoes", label: "\u{1F539} Varia\u00E7\u00F5es", count: variacoes.length });
  }

  return abas;
}

export function montarPayloadProdutoParaSalvar(produto) {
  const { _mostrarCanais, ...restoProduto } = produto;
  const lojaFisicaAtiva = produto.status !== "inativo";

  return {
    ...restoProduto,
    preco_custo: parseFloat(produto.preco_custo) || 0,
    preco_venda: parseFloat(produto.preco_venda) || 0,
    margem_lucro: parseFloat(produto.margem_lucro) || 0,
    estoque_minimo: parseFloat(produto.estoque_minimo) || 0,
    estoque_maximo: parseFloat(produto.estoque_maximo) || 0,
    categoria_id: produto.categoria_id || null,
    marca_id: produto.marca_id || null,
    anunciar_ecommerce: lojaFisicaAtiva ? Boolean(produto.anunciar_ecommerce) : false,
    anunciar_app: lojaFisicaAtiva ? Boolean(produto.anunciar_app) : false,
  };
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
