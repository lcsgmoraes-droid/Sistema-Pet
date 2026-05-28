export const camposIncompletosTexto = (campos = []) =>
  campos.length ? `Falta preencher: ${campos.join(", ")}` : "";

export const normalizarTexto = (valor) =>
  String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

const termosBusca = (valor) =>
  normalizarTexto(valor)
    .split(/\s+/)
    .map((termo) => termo.trim())
    .filter(Boolean);

const aliasesBusca = {
  cao: ["cao", "caes", "canino", "dog", "cachorro"],
  caes: ["caes", "cao", "canino", "dog", "cachorro"],
  cachorro: ["cachorro", "cao", "caes", "canino", "dog"],
  dog: ["dog", "cao", "caes", "canino", "cachorro"],
  especial: ["especial", "special"],
  felino: ["felino", "gato", "cat"],
  gato: ["gato", "felino", "cat"],
  cat: ["cat", "gato", "felino"],
  racao: ["racao", "racoes"],
  racoes: ["racoes", "racao"],
  special: ["special", "especial"],
};

const variacoesTermoBusca = (termo) => aliasesBusca[termo] || [termo];

const temValorPreenchido = (valor) => {
  if (valor === null || valor === undefined) return false;
  if (Array.isArray(valor)) return valor.length > 0;
  if (typeof valor === "object") return Object.keys(valor).length > 0;

  const texto = String(valor).trim();
  return !["", "{}", "[]", "null", "undefined", "none"].includes(
    texto.toLowerCase(),
  );
};

const temJsonPreenchido = (valor) => {
  if (!temValorPreenchido(valor)) return false;
  if (typeof valor === "object") return temValorPreenchido(valor);

  try {
    const parsed = JSON.parse(valor);
    if (Array.isArray(parsed)) return parsed.length > 0;
    if (parsed && typeof parsed === "object") {
      return Object.values(parsed).some((item) => temValorPreenchido(item));
    }
    return temValorPreenchido(parsed);
  } catch {
    return temValorPreenchido(valor);
  }
};

const numeroPositivo = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) && numero > 0;
};

const produtoTemConfigRacao = (produto) => {
  const tipo = normalizarTexto(produto?.tipo);
  const classificacao = normalizarTexto(produto?.classificacao_racao);

  return (
    produto?.eh_racao === true ||
    tipo.startsWith("racao") ||
    tipo.startsWith("ra") ||
    Boolean(produto?.linha_racao_id) ||
    (Boolean(classificacao) && !["nao", "não"].includes(classificacao))
  );
};

export const produtoPareceRacao = (produto) => {
  const textoBusca = normalizarTexto(
    [
      produto?.nome,
      produto?.categoria_nome,
      produto?.categoria?.nome,
      produto?.marca?.nome,
      produto?.classificacao_racao,
      produto?.especies_indicadas,
    ]
      .filter(Boolean)
      .join(" "),
  );

  return (
    produtoTemConfigRacao(produto) ||
    temValorPreenchido(produto?.tabela_consumo) ||
    temValorPreenchido(produto?.tabela_nutricional) ||
    /(racao|racoes|dog|cat|gato|cao|caes|canino|felino|royal|premier|special|especial)/.test(
      textoBusca,
    )
  );
};

export const avaliarAptidaoRacao = (produto) => {
  const faltantes = [];

  if (!produtoTemConfigRacao(produto)) faltantes.push("aba Ração");
  if (!numeroPositivo(produto?.peso_embalagem))
    faltantes.push("peso da embalagem");
  if (!numeroPositivo(produto?.preco_venda)) faltantes.push("preço de venda");
  if (!temValorPreenchido(produto?.linha_racao_id || produto?.classificacao_racao))
    faltantes.push("linha/classificação");
  if (!temValorPreenchido(produto?.porte_animal_id || produto?.porte_animal))
    faltantes.push("porte");
  if (
    !temValorPreenchido(
      produto?.fase_publico_id || produto?.fase_publico || produto?.categoria_racao,
    )
  )
    faltantes.push("fase/público");
  if (!temValorPreenchido(produto?.sabor_proteina_id || produto?.sabor_proteina))
    faltantes.push("sabor/proteína");
  if (!temValorPreenchido(produto?.especies_indicadas))
    faltantes.push("espécie indicada");
  if (!temJsonPreenchido(produto?.tabela_consumo))
    faltantes.push("tabela de consumo");

  return {
    apta: faltantes.length === 0,
    faltantes,
  };
};

export const formatarMoeda = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

export const formatarPeso = (valor) => {
  if (!numeroPositivo(valor)) return "sem peso";
  return `${Number(valor).toLocaleString("pt-BR", {
    maximumFractionDigits: 3,
  })}kg`;
};

export const formatarRacaoLabel = (produto) =>
  `${produto.nome} - ${formatarPeso(produto.peso_embalagem)} - ${formatarMoeda(produto.preco_venda)}`;

export const extrairListaProdutos = (data) => {
  if (typeof data === "string") {
    try {
      return extrairListaProdutos(JSON.parse(data));
    } catch {
      return [];
    }
  }

  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];

  return data.items || data.produtos || data.itens || data.data || [];
};

export const prepararProdutosComAptidao = (lista = []) =>
  lista
    .filter((produto) => produto && produtoPareceRacao(produto))
    .map((produto) => ({
      ...produto,
      aptidao: avaliarAptidaoRacao(produto),
    }));

export const combinarProdutosComAptidao = (...listas) => {
  const mapa = new Map();

  listas.flat().forEach((produto) => {
    if (!produto?.id) return;
    const chave = String(produto.id);
    const anterior = mapa.get(chave) || {};
    mapa.set(chave, {
      ...anterior,
      ...produto,
      aptidao: produto.aptidao || avaliarAptidaoRacao(produto),
    });
  });

  return Array.from(mapa.values());
};

const textoBuscaRacao = (produto) =>
  normalizarTexto(
    [
      produto?.nome,
      produto?.codigo,
      produto?.sku,
      produto?.codigo_barras,
      produto?.categoria_nome,
      produto?.categoria?.nome,
      produto?.marca?.nome,
      produto?.marca_nome,
      produto?.descricao_curta,
      produto?.descricao_completa,
      produto?.classificacao_racao,
      produto?.categoria_racao,
      produto?.especies_indicadas,
      formatarPeso(produto?.peso_embalagem),
      formatarMoeda(produto?.preco_venda),
    ]
      .filter(Boolean)
      .join(" "),
  );

const termoCasaComPalavra = (termo, palavras) =>
  palavras.some((palavra) => {
    if (palavra.includes(termo)) return true;
    return termo.length >= 4 && palavra.length >= 4 && termo.includes(palavra);
  });

const termoEncontradoNoProduto = (termo, texto, palavras) =>
  variacoesTermoBusca(termo).some(
    (alias) => texto.includes(alias) || termoCasaComPalavra(alias, palavras),
  );

export const pontuarBuscaRacao = (produto, valor) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return 1;

  const termos = termosBusca(valor);
  const texto = textoBuscaRacao(produto);
  const nome = normalizarTexto(produto?.nome);
  const palavras = texto.split(/\s+/).filter(Boolean);

  const todosTermosEncontrados = termos.every((termo) =>
    termoEncontradoNoProduto(termo, texto, palavras),
  );

  if (!todosTermosEncontrados) return 0;

  let score = 10;
  if (nome === consulta) score += 120;
  if (nome.startsWith(consulta)) score += 90;
  if (texto.includes(consulta)) score += 70;

  termos.forEach((termo) => {
    if (nome.split(/\s+/).includes(termo)) score += 12;
    else if (nome.includes(termo)) score += 8;
    else score += 4;
  });

  return score;
};

const produtoCasaComTextoSelecionado = (produto, valor) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return false;

  const nome = normalizarTexto(produto?.nome);
  const labelCompleta = normalizarTexto(formatarRacaoLabel(produto));
  const labelSemPreco = normalizarTexto(
    `${produto?.nome || ""} - ${formatarPeso(produto?.peso_embalagem)}`,
  );

  return (
    consulta === nome ||
    consulta === labelCompleta ||
    consulta === labelSemPreco ||
    consulta.includes(nome) ||
    labelCompleta.includes(consulta)
  );
};

export const escolherRacaoAptaPorTexto = (valor, ...listas) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return null;

  const candidatos = combinarProdutosComAptidao(...listas).filter(
    (produto) => produto?.aptidao?.apta,
  );

  const matchDireto = candidatos.find((produto) =>
    produtoCasaComTextoSelecionado(produto, valor),
  );
  if (matchDireto) return matchDireto;

  const pontuados = candidatos
    .map((produto) => ({
      produto,
      score: pontuarBuscaRacao(produto, valor),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => {
      if (a.score !== b.score) return b.score - a.score;
      return a.produto.nome.localeCompare(b.produto.nome, "pt-BR");
    });

  return pontuados.length === 1 ? pontuados[0].produto : null;
};
