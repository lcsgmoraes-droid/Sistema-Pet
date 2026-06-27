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
        categoriasMap[categoria.categoria_pai_id].filhas.push(categoriasMap[categoria.id]);
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

export function normalizarCodigosBarrasAlternativosCampo(valor) {
  if (!valor) return "";

  if (Array.isArray(valor)) {
    return valor
      .map((item) => String(item).trim())
      .filter(Boolean)
      .join(", ");
  }

  const texto = String(valor).trim();
  if (!texto) return "";

  try {
    const parsed = JSON.parse(texto);
    if (Array.isArray(parsed)) {
      return parsed
        .map((item) => String(item).trim())
        .filter(Boolean)
        .join(", ");
    }
  } catch {
    // Mantem compatibilidade com cadastros antigos salvos como texto simples.
  }

  return texto;
}

export function normalizarCodigosBarrasAlternativosPayload(valor) {
  const texto = normalizarCodigosBarrasAlternativosCampo(valor);
  if (!texto.trim()) return null;

  const vistos = new Set();
  const codigos = texto
    .split(/[,;\n]+/)
    .map((item) => item.replace(/\D/g, ""))
    .filter((item) => {
      if (!item || vistos.has(item)) return false;
      vistos.add(item);
      return true;
    });

  return codigos.length ? JSON.stringify(codigos) : null;
}

export function deveMostrarTipoProdutoNoFormulario({ tipoProduto } = {}) {
  return tipoProduto !== "VARIACAO";
}

export function normalizarTipoComercialProduto(tipo) {
  const valor = String(tipo || "produto")
    .trim()
    .toLowerCase();
  if (valor === "ambos") return "produto_servico";
  if (valor === "servi\u00e7o") return "servico";
  if (["produto", "servico", "produto_servico"].includes(valor)) return valor;
  return "produto";
}

export function produtoControlaEstoque(produto = {}) {
  const tipo = normalizarTipoComercialProduto(produto.tipo);
  return tipo !== "servico" && produto.tipo_produto !== "PAI";
}

export function aplicarTipoServicoSemEstoque(produto = {}) {
  const tipo = normalizarTipoComercialProduto(produto.tipo);
  if (tipo !== "servico") {
    return { ...produto, tipo };
  }
  return {
    ...produto,
    tipo,
    tipo_produto: "SIMPLES",
    tipo_kit: null,
    e_kit_fisico: false,
    controle_lote: false,
    estoque_minimo: "",
    estoque_maximo: "",
    participa_sugestao_compra: false,
  };
}

export function montarEstadoProdutoClonado(prod = {}) {
  const tipoOrigem = prod.tipo_produto || "SIMPLES";
  const tipoProduto = tipoOrigem === "VARIACAO" ? "SIMPLES" : tipoOrigem;
  const produtoComComposicao = tipoProduto === "KIT";
  const nomeBase = String(prod.nome || "").trim();

  const composicaoKit = produtoComComposicao
    ? (prod.composicao_kit || []).map((item) => ({
        produto_id: item.produto_id || item.produto_componente_id,
        produto_componente_id: item.produto_componente_id || item.produto_id,
        produto_nome: item.produto_nome || item.nome || "",
        quantidade: item.quantidade || 1,
        ordem: Number.isFinite(Number(item.ordem)) ? Number(item.ordem) : 0,
        opcional: Boolean(item.opcional),
      }))
    : [];

  return {
    codigo: "",
    sku: "",
    nome: nomeBase ? `${nomeBase} (Copia)` : "Produto (Copia)",
    codigo_barras: "",
    categoria_id: prod.categoria_id || "",
    marca_id: prod.marca_id || "",
    departamento_id: prod.departamento_id || "",
    tipo: normalizarTipoComercialProduto(prod.tipo),
    unidade: prod.unidade || "UN",
    descricao: prod.descricao_curta || prod.descricao || "",
    preco_custo: prod.preco_custo || "",
    preco_venda: prod.preco_venda || "",
    preco_promocional: prod.preco_promocional || "",
    data_inicio_promocao: prod.promocao_inicio || prod.data_inicio_promocao || "",
    data_fim_promocao: prod.promocao_fim || prod.data_fim_promocao || "",
    preco_ecommerce: prod.preco_ecommerce ?? "",
    preco_ecommerce_promo: prod.preco_ecommerce_promo ?? "",
    preco_ecommerce_promo_inicio: prod.preco_ecommerce_promo_inicio ?? "",
    preco_ecommerce_promo_fim: prod.preco_ecommerce_promo_fim ?? "",
    preco_app: prod.preco_app ?? "",
    preco_app_promo: prod.preco_app_promo ?? "",
    preco_app_promo_inicio: prod.preco_app_promo_inicio ?? "",
    preco_app_promo_fim: prod.preco_app_promo_fim ?? "",
    anunciar_ecommerce: prod.anunciar_ecommerce ?? true,
    anunciar_app: prod.anunciar_app ?? true,
    ativo: true,
    situacao: true,
    controle_lote: normalizarTipoComercialProduto(prod.tipo) === "servico" ? false : prod.controle_lote ?? true,
    estoque_minimo: prod.estoque_minimo || "",
    estoque_maximo: prod.estoque_maximo || "",
    participa_sugestao_compra:
      normalizarTipoComercialProduto(prod.tipo) === "servico"
        ? false
        : prod.participa_sugestao_compra ?? true,
    tipo_produto: tipoProduto,
    produto_pai_id: null,
    tipo_kit: produtoComComposicao ? prod.tipo_kit || "VIRTUAL" : null,
    e_kit_fisico: produtoComComposicao ? Boolean(prod.e_kit_fisico) : false,
    composicao_kit: composicaoKit,
    produto_predecessor_id: null,
    motivo_descontinuacao: "",
    origem: prod.origem || "0",
    ncm: prod.ncm || "",
    cest: prod.cest || "",
    cfop: prod.cfop || "",
    aliquota_icms: prod.aliquota_icms || "",
    aliquota_pis: prod.aliquota_pis || "",
    aliquota_cofins: prod.aliquota_cofins || "",
    tem_recorrencia: Boolean(prod.tem_recorrencia),
    tipo_recorrencia: prod.tipo_recorrencia || "monthly",
    intervalo_dias: prod.intervalo_dias || "",
    numero_doses: prod.numero_doses || "",
    observacoes_recorrencia: prod.observacoes_recorrencia || "",
    especie_compativel: prod.especie_compativel || "both",
    eh_racao: Boolean(prod.eh_racao),
    e_granel: Boolean(prod.e_granel),
    classificacao_racao:
      prod.classificacao_racao && prod.classificacao_racao !== "sim"
        ? prod.classificacao_racao
        : "",
    peso_embalagem: prod.peso_embalagem || "",
    tabela_nutricional: prod.tabela_nutricional || "",
    tabela_consumo: prod.tabela_consumo || "",
    categoria_racao: prod.categoria_racao || "",
    especies_indicadas: prod.especies_indicadas || "both",
    linha_racao_id: prod.linha_racao_id || "",
    porte_animal_id: prod.porte_animal_id || "",
    fase_publico_id: prod.fase_publico_id || "",
    tipo_tratamento_id: prod.tipo_tratamento_id || "",
    sabor_proteina_id: prod.sabor_proteina_id || "",
    apresentacao_peso_id: prod.apresentacao_peso_id || "",
  };
}

export function montarProdutoComAlteracao(produto, campo) {
  const valorCampo = campo.type === "checkbox" ? campo.checked : campo.value;
  const produtoAtualizado = {
    ...produto,
    [campo.name]: valorCampo,
  };

  if (campo.name !== "preco_custo" && campo.name !== "preco_venda") {
    return produtoAtualizado;
  }

  const margemCalculada = calcularMargemPercentual(
    campo.name === "preco_custo" ? campo.value : produto.preco_custo,
    campo.name === "preco_venda" ? campo.value : produto.preco_venda,
  );

  if (margemCalculada === null) {
    return produtoAtualizado;
  }

  return {
    ...produtoAtualizado,
    margem_lucro: margemCalculada,
  };
}

export function montarEstadoProdutoFormulario(prod = {}) {
  return {
    codigo: prod.codigo || "",
    nome: prod.nome || "",
    descricao: prod.descricao || "",
    categoria_id: prod.categoria_id || "",
    marca_id: prod.marca_id || "",
    departamento_id: prod.departamento_id || "",
    tipo: normalizarTipoComercialProduto(prod.tipo),
    preco_custo: prod.preco_custo || "",
    preco_venda: prod.preco_venda || "",
    margem_lucro: prod.margem_lucro || "",
    estoque_minimo: prod.estoque_minimo || "",
    estoque_maximo: prod.estoque_maximo || "",
    localizacao: prod.localizacao || "",
    observacoes: prod.observacoes || "",
    controle_lote:
      normalizarTipoComercialProduto(prod.tipo) === "servico" ? false : prod.controle_lote || false,
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

  if (produtoControlaEstoque(produto) && produto.controle_lote) {
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
  const tipo = normalizarTipoComercialProduto(produto.tipo);
  const servico = tipo === "servico";

  const payload = {
    ...restoProduto,
    tipo,
    preco_custo: parseFloat(produto.preco_custo) || 0,
    preco_venda: parseFloat(produto.preco_venda) || 0,
    margem_lucro: parseFloat(produto.margem_lucro) || 0,
    controle_lote: servico ? false : Boolean(produto.controle_lote),
    estoque_minimo: servico ? 0 : parseFloat(produto.estoque_minimo) || 0,
    estoque_maximo: servico ? null : parseFloat(produto.estoque_maximo) || 0,
    categoria_id: produto.categoria_id || null,
    marca_id: produto.marca_id || null,
    anunciar_ecommerce: lojaFisicaAtiva ? Boolean(produto.anunciar_ecommerce) : false,
    anunciar_app: lojaFisicaAtiva ? Boolean(produto.anunciar_app) : false,
  };

  if (servico || produto.participa_sugestao_compra !== undefined) {
    payload.participa_sugestao_compra = servico ? false : produto.participa_sugestao_compra;
  }

  return payload;
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
