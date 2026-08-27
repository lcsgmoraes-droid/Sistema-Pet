const formatadorQuantidade = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 4,
});

export function formatarQuantidadeListaEspera(valor) {
  return formatadorQuantidade.format(Number(valor || 0));
}

function escaparCsv(valor) {
  const texto = valor == null ? "" : String(valor);
  return `"${texto.replaceAll('"', '""')}"`;
}

function linhaCsv(valores) {
  return valores.map(escaparCsv).join(";");
}

function formatarDataCsv(valor) {
  if (!valor) return "";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "" : data.toLocaleDateString("pt-BR");
}

export function criarCsvListaEspera(relatorio) {
  const resumo = relatorio?.resumo || {};
  const produtos = Array.isArray(relatorio?.produtos) ? relatorio.produtos : [];
  const detalhes = Array.isArray(relatorio?.detalhes) ? relatorio.detalhes : [];
  const linhas = [
    linhaCsv(["RELATORIO DA LISTA DE ESPERA ATIVA"]),
    linhaCsv(["Indicador", "Total"]),
    linhaCsv(["Clientes distintos", resumo.total_clientes || 0]),
    linhaCsv(["SKUs distintos", resumo.total_skus || 0]),
    linhaCsv(["Quantidade desejada", formatarQuantidadeListaEspera(resumo.quantidade_total)]),
    linhaCsv(["Registros cliente x produto", resumo.total_registros || 0]),
    "",
    linhaCsv(["TOTALIZADOR POR SKU"]),
    linhaCsv([
      "Fornecedor",
      "Marca",
      "SKU",
      "Produto",
      "Clientes aguardando",
      "Quantidade desejada",
    ]),
  ];

  produtos.forEach((produto) => {
    linhas.push(
      linhaCsv([
        produto.fornecedor,
        produto.marca,
        produto.sku,
        produto.produto_nome,
        produto.total_clientes,
        formatarQuantidadeListaEspera(produto.quantidade_total),
      ]),
    );
  });

  linhas.push(
    "",
    linhaCsv(["CLIENTE X PRODUTO"]),
    linhaCsv([
      "Cliente",
      "Telefone",
      "Fornecedor",
      "Marca",
      "SKU",
      "Produto",
      "Quantidade desejada",
      "Status",
      "Prioridade",
      "Data do registro",
    ]),
  );

  detalhes.forEach((item) => {
    linhas.push(
      linhaCsv([
        item.cliente_nome,
        item.cliente_telefone,
        item.fornecedor,
        item.marca,
        item.sku,
        item.produto_nome,
        formatarQuantidadeListaEspera(item.quantidade_desejada),
        item.status,
        item.prioridade,
        formatarDataCsv(item.data_registro),
      ]),
    );
  });

  return `\uFEFF${linhas.join("\r\n")}`;
}

export function baixarCsvListaEspera(relatorio) {
  const blob = new Blob([criarCsvListaEspera(relatorio)], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const hoje = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = `lista-espera-${hoje}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
