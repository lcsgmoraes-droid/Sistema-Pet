export function criarItemOrcamento() {
  return {
    produto_id: null,
    descricao: "",
    quantidade: 1,
    unidade: "un",
    preco_unitario_base: 0,
  };
}

export function preencherItemComProduto(item, produto) {
  const preco =
    produto?.preco_venda_pdv ?? produto?.preco_venda_efetivo ?? produto?.preco_venda ?? 0;
  const precoNumerico = Number(preco);

  return {
    ...item,
    produto_id: produto?.id ?? null,
    descricao: produto?.nome || item?.descricao || "",
    unidade: produto?.unidade || item?.unidade || "un",
    preco_unitario_base: Number.isFinite(precoNumerico) ? precoNumerico : 0,
  };
}

export function calcularTotalBase(itens = []) {
  return itens.reduce(
    (total, item) => total + Number(item.quantidade || 0) * Number(item.preco_unitario_base || 0),
    0,
  );
}

function embaralhar(lista, random) {
  const copia = [...lista];
  for (let index = copia.length - 1; index > 0; index -= 1) {
    const destino = Math.floor(random() * (index + 1));
    [copia[index], copia[destino]] = [copia[destino], copia[index]];
  }
  return copia;
}

export function sortearEmpresas({
  empresas = [],
  selecoes = [],
  quantidade = 2,
  random = Math.random,
}) {
  const ativas = empresas.filter((empresa) => empresa.ativo !== false);
  const ativasPorId = new Map(ativas.map((empresa) => [Number(empresa.id), empresa]));
  const fixadas = selecoes
    .filter((selecao) => selecao.fixada && ativasPorId.has(Number(selecao.empresa_id)))
    .slice(0, quantidade);
  const idsUsados = new Set(fixadas.map((selecao) => Number(selecao.empresa_id)));
  const disponiveis = embaralhar(
    ativas.filter((empresa) => !idsUsados.has(Number(empresa.id))),
    random,
  );
  const resultado = [...fixadas];

  while (resultado.length < quantidade && disponiveis.length > 0) {
    const empresa = disponiveis.shift();
    resultado.push({
      empresa_id: Number(empresa.id),
      fixada: Boolean(empresa.fixada_padrao),
    });
  }
  return resultado;
}

export function nomeArquivoPdf(orcamento, cotacaoId) {
  const numero = orcamento?.numero || `orcamento-${orcamento?.id || "grupo"}`;
  return cotacaoId ? `${numero}-cotacao-${cotacaoId}.pdf` : `${numero}-todos.pdf`;
}
