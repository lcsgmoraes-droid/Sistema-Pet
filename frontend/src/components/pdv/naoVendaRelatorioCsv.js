const formatadorQuantidade = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 4,
});

const formatadorDinheiro = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function formatarQuantidadeNaoVenda(valor) {
  return formatadorQuantidade.format(Number(valor || 0));
}

export function formatarDinheiroNaoVenda(valor) {
  return formatadorDinheiro.format(Number(valor || 0));
}

function escaparCsv(valor) {
  const texto = valor == null ? "" : String(valor);
  return `"${texto.replaceAll('"', '""')}"`;
}

function linhaCsv(valores) {
  return valores.map(escaparCsv).join(";");
}

function formatarData(valor) {
  if (!valor) return "";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "" : data.toLocaleString("pt-BR");
}

export function criarCsvNaoVendas(relatorio) {
  const resumo = relatorio?.resumo || {};
  const motivos = Array.isArray(relatorio?.motivos) ? relatorio.motivos : [];
  const produtos = Array.isArray(relatorio?.produtos) ? relatorio.produtos : [];
  const detalhes = Array.isArray(relatorio?.detalhes) ? relatorio.detalhes : [];
  const linhas = [
    linhaCsv(["RELATÓRIO DE ATENDIMENTOS SEM VENDA"]),
    linhaCsv(["Período", relatorio?.periodo?.data_inicio, relatorio?.periodo?.data_fim]),
    linhaCsv(["Indicador", "Total"]),
    linhaCsv(["Atendimentos sem venda", resumo.total_atendimentos || 0]),
    linhaCsv(["Atendimentos identificados", resumo.atendimentos_identificados || 0]),
    linhaCsv(["Atendimentos anônimos", resumo.atendimentos_anonimos || 0]),
    linhaCsv(["Produtos distintos procurados", resumo.total_produtos_distintos || 0]),
    linhaCsv(["Quantidade procurada", formatarQuantidadeNaoVenda(resumo.quantidade_total)]),
    linhaCsv(["Valor estimado perdido", formatarDinheiroNaoVenda(resumo.valor_estimado_total)]),
    "",
    linhaCsv(["MOTIVOS"]),
    linhaCsv(["Motivo", "Atendimentos", "Percentual", "Valor estimado"]),
  ];

  motivos.forEach((motivo) => {
    linhas.push(
      linhaCsv([
        motivo.motivo,
        motivo.total_atendimentos,
        `${motivo.percentual || 0}%`,
        formatarDinheiroNaoVenda(motivo.valor_estimado_total),
      ]),
    );
  });

  linhas.push(
    "",
    linhaCsv(["PRODUTOS PROCURADOS"]),
    linhaCsv([
      "Fornecedor",
      "Marca",
      "SKU",
      "Produto",
      "Atendimentos",
      "Solicitações",
      "Quantidade",
      "Valor estimado",
    ]),
  );
  produtos.forEach((produto) => {
    linhas.push(
      linhaCsv([
        produto.fornecedor,
        produto.marca,
        produto.sku,
        produto.produto_nome,
        produto.total_atendimentos,
        produto.total_solicitacoes,
        formatarQuantidadeNaoVenda(produto.quantidade_total),
        formatarDinheiroNaoVenda(produto.valor_estimado_total),
      ]),
    );
  });

  linhas.push(
    "",
    linhaCsv(["ATENDIMENTO × PRODUTO"]),
    linhaCsv([
      "Data",
      "Cliente",
      "Telefone",
      "Motivo",
      "Fornecedor",
      "Marca",
      "SKU",
      "Produto",
      "Quantidade",
      "Valor estimado",
      "Lista de espera",
      "Atendente",
      "Observações",
    ]),
  );
  detalhes.forEach((registro) => {
    const itens = registro.itens?.length ? registro.itens : [null];
    itens.forEach((item) => {
      linhas.push(
        linhaCsv([
          formatarData(registro.data_registro),
          registro.cliente_nome,
          registro.cliente_telefone,
          registro.motivo,
          item?.fornecedor,
          item?.marca,
          item?.sku,
          item?.produto_nome || "Sem produto informado",
          item ? formatarQuantidadeNaoVenda(item.quantidade) : "",
          formatarDinheiroNaoVenda(item?.valor_estimado_total || registro.valor_estimado_total),
          item?.adicionado_lista_espera ? "Sim" : "Não",
          registro.usuario_registrou,
          registro.observacoes,
        ]),
      );
    });
  });

  return `\uFEFF${linhas.join("\r\n")}`;
}

export function baixarCsvNaoVendas(relatorio) {
  const blob = new Blob([criarCsvNaoVendas(relatorio)], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const hoje = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = `atendimentos-sem-venda-${hoje}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
