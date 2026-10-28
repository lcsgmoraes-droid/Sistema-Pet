import { formatMoneyBRL } from "../../utils/formatters.js";

const formatarData = (valor) => {
  const data = String(valor || "").slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(data)
    ? `${data.slice(8, 10)}/${data.slice(5, 7)}/${data.slice(0, 4)}`
    : "-";
};

const formatarQuantidade = (valor, produto) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: produto ? 3 : 0,
    maximumFractionDigits: 3,
  });

const textoPdf = (valor) =>
  String(valor ?? "-")
    .replace(/\u00a0/g, " ")
    .replace(/[\u2010-\u2015]/g, "-");

// Usa os mesmos grupos da tela e do Excel; os valores financeiros não são recalculados.
export function prepararDadosVendasPorVendedorPdf({
  grupos = [],
  periodo,
  produto = null,
  vendedor = "",
  geradoEm = new Date(),
}) {
  const quantidadeVendas = grupos.reduce((total, grupo) => total + grupo.quantidade, 0);
  const total = grupos.reduce((soma, grupo) => soma + grupo.total, 0);
  const quantidadeProduto = produto
    ? grupos.reduce((soma, grupo) => soma + grupo.quantidadeProdutos, 0)
    : null;

  return {
    periodo: `${formatarData(periodo.inicio)} a ${formatarData(periodo.fim)}`,
    geradoEm: new Date(geradoEm).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }),
    produto: produto?.label || "Todos os produtos",
    vendedor: vendedor || "Todos os vendedores",
    totalizadores: [
      `${grupos.length} vendedor(es)`,
      `${quantidadeVendas} venda(s)`,
      ...(produto ? [`Quantidade do produto: ${formatarQuantidade(quantidadeProduto, true)}`] : []),
      `${produto ? "Valor bruto do produto" : "Total vendido"}: ${formatMoneyBRL(total)}`,
    ].join("  |  "),
    nota: produto
      ? "Valores brutos do produto, antes de descontos e taxas. As devoluções não são abatidas."
      : "Totais das vendas selecionadas. O vendedor é o indicado na venda, independentemente da comissão.",
    resumo: grupos.map((grupo) => [
      grupo.vendedor,
      String(grupo.quantidade),
      ...(produto ? [formatarQuantidade(grupo.quantidadeProdutos, true)] : []),
      formatMoneyBRL(grupo.total),
    ]),
    detalhes: grupos.flatMap((grupo) =>
      grupo.vendas.map((venda) => [
        grupo.vendedor,
        formatarData(venda.data_venda),
        String(venda.numero_venda || venda.id || "-"),
        venda.cliente_nome || "Sem cliente",
        (venda.itens || [])
          .map(
            (item) =>
              `${item.produto_nome || "Produto removido"} - ${formatarQuantidade(item.quantidade, produto)}`,
          )
          .join("\n") || "Sem itens",
        formatMoneyBRL(produto ? venda.total_relatorio : venda.total_venda),
      ]),
    ),
  };
}

export async function criarPdfVendasPorVendedor(opcoes) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const dados = prepararDadosVendasPorVendedorPdf(opcoes);
  const margem = 14;
  const largura = pdf.internal.pageSize.getWidth() - margem * 2;
  const alturaPagina = pdf.internal.pageSize.getHeight();
  const limite = alturaPagina - 19;
  const inicioConteudo = 37;
  const alturaLinha = 4;
  const padding = 2.5;
  let y = inicioConteudo;

  const fonte = (tamanho = 8.5, negrito = false, cor = [40, 50, 65]) => {
    pdf.setFont("helvetica", negrito ? "bold" : "normal");
    pdf.setFontSize(tamanho);
    pdf.setTextColor(...cor);
  };

  const cabecalhoPagina = () => {
    fonte(11, true, [13, 120, 115]);
    pdf.text("CorePet", margem, 15);
    fonte(18, true, [26, 45, 73]);
    pdf.text("Vendas por vendedor", margem, 25);
    fonte(8);
    pdf.text(`Período: ${dados.periodo}`, margem + largura, 15, { align: "right" });
    pdf.text(`Gerado em: ${dados.geradoEm}`, margem + largura, 22, { align: "right" });
    pdf.setDrawColor(190, 218, 218);
    pdf.line(margem, 30, margem + largura, 30);
  };

  const novaPagina = () => {
    pdf.addPage();
    cabecalhoPagina();
    y = inicioConteudo;
  };

  const paragrafo = (texto, { tamanho = 8.5, negrito = false, espacoDepois = 2 } = {}) => {
    fonte(tamanho, negrito);
    const linhas = pdf.splitTextToSize(textoPdf(texto), largura);
    for (const linha of linhas) {
      if (y + alturaLinha > limite) novaPagina();
      fonte(tamanho, negrito);
      pdf.text(linha, margem, y);
      y += alturaLinha;
    }
    y += espacoDepois;
  };

  const tabela = ({ titulo, colunas, linhas }) => {
    const larguras = colunas.map((coluna) => largura * coluna.proporcao);
    fonte(8, true);
    const titulos = colunas.map((coluna, indice) =>
      pdf.splitTextToSize(coluna.titulo, larguras[indice] - padding * 2),
    );
    const alturaCabecalho = Math.max(...titulos.map((linhasTitulo) => linhasTitulo.length)) * 4 + 5;
    const alturaSecao = 8 + alturaCabecalho;

    const cabecalhoTabela = (continuacao = false) => {
      fonte(11, true, [26, 45, 73]);
      pdf.text(`${titulo}${continuacao ? " (continuação)" : ""}`, margem, y + 4);
      y += 8;
      pdf.setFillColor(230, 242, 241);
      pdf.rect(margem, y, largura, alturaCabecalho, "F");
      fonte(8, true, [26, 70, 73]);
      let x = margem;
      titulos.forEach((linhasTitulo, indice) => {
        const direita = colunas[indice].direita;
        pdf.text(linhasTitulo, direita ? x + larguras[indice] - padding : x + padding, y + 5, {
          align: direita ? "right" : "left",
          lineHeightFactor: (4 * 72) / (25.4 * 8),
        });
        x += larguras[indice];
      });
      y += alturaCabecalho;
    };

    const continuarTabela = () => {
      novaPagina();
      cabecalhoTabela(true);
    };

    if (y + alturaSecao + 10 > limite) novaPagina();
    cabecalhoTabela();

    linhas.forEach((valores, indiceLinha) => {
      fonte(8.5);
      const celulas = valores.map((valor, indiceColuna) =>
        pdf.splitTextToSize(textoPdf(valor), larguras[indiceColuna] - padding * 2),
      );
      const totalLinhas = Math.max(1, ...celulas.map((linhasCelula) => linhasCelula.length));
      const alturaTotal = totalLinhas * alturaLinha + padding * 2;
      const espacoPaginaNova = limite - inicioConteudo - alturaSecao;

      // Linhas normais ficam inteiras. Uma venda com muitos itens é dividida em partes.
      if (y + alturaTotal > limite && alturaTotal <= espacoPaginaNova) continuarTabela();
      let inicioLinha = 0;
      while (inicioLinha < totalLinhas) {
        let capacidade = Math.floor((limite - y - padding * 2) / alturaLinha);
        if (capacidade < 1) {
          continuarTabela();
          capacidade = Math.floor((limite - y - padding * 2) / alturaLinha);
        }
        const quantidade = Math.min(capacidade, totalLinhas - inicioLinha);
        const altura = quantidade * alturaLinha + padding * 2;
        if (indiceLinha % 2 === 0) {
          pdf.setFillColor(247, 249, 251);
          pdf.rect(margem, y, largura, altura, "F");
        }
        fonte(8.5);
        let x = margem;
        celulas.forEach((linhasCelula, indiceColuna) => {
          const parte = linhasCelula.slice(inicioLinha, inicioLinha + quantidade);
          // Repete uma referência curta sem reinserir um nome longo inteiro na continuação.
          const texto = parte.length
            ? parte
            : inicioLinha > 0 && indiceColuna < 3
              ? linhasCelula.slice(0, 1)
              : [];
          if (texto.length) {
            const direita = colunas[indiceColuna].direita;
            pdf.text(texto, direita ? x + larguras[indiceColuna] - padding : x + padding, y + 5.5, {
              align: direita ? "right" : "left",
              lineHeightFactor: (alturaLinha * 72) / (25.4 * 8.5),
            });
          }
          x += larguras[indiceColuna];
        });
        pdf.setDrawColor(224, 230, 236);
        pdf.line(margem, y + altura, margem + largura, y + altura);
        y += altura;
        inicioLinha += quantidade;
        if (inicioLinha < totalLinhas) continuarTabela();
      }
    });
    y += 8;
  };

  cabecalhoPagina();
  paragrafo(`Produto: ${dados.produto}`);
  paragrafo(`Vendedor: ${dados.vendedor}`);
  paragrafo("Canais: Todos os canais");
  paragrafo(dados.totalizadores, { tamanho: 10, negrito: true, espacoDepois: 3 });
  paragrafo(dados.nota, { tamanho: 8, espacoDepois: 5 });

  if (dados.resumo.length) {
    tabela({
      titulo: "Resumo por vendedor",
      colunas: opcoes.produto
        ? [
            { titulo: "Vendedor", proporcao: 0.45 },
            { titulo: "Vendas", proporcao: 0.12, direita: true },
            { titulo: "Quantidade do produto", proporcao: 0.2, direita: true },
            { titulo: "Valor bruto do produto", proporcao: 0.23, direita: true },
          ]
        : [
            { titulo: "Vendedor", proporcao: 0.6 },
            { titulo: "Vendas", proporcao: 0.15, direita: true },
            { titulo: "Total vendido", proporcao: 0.25, direita: true },
          ],
      linhas: dados.resumo,
    });
    tabela({
      titulo: "Detalhes das vendas",
      colunas: [
        { titulo: "Vendedor", proporcao: 0.14 },
        { titulo: "Data", proporcao: 0.08 },
        { titulo: "Venda", proporcao: 0.1 },
        { titulo: "Cliente", proporcao: 0.16 },
        { titulo: "Produtos e quantidades", proporcao: 0.38 },
        {
          titulo: opcoes.produto ? "Valor bruto do produto" : "Total da venda",
          proporcao: 0.14,
          direita: true,
        },
      ],
      linhas: dados.detalhes,
    });
  } else {
    paragrafo("Nenhuma venda encontrada para os filtros selecionados.");
  }

  const totalPaginas = pdf.internal.getNumberOfPages();
  for (let pagina = 1; pagina <= totalPaginas; pagina += 1) {
    pdf.setPage(pagina);
    fonte(8, false, [100, 110, 125]);
    pdf.text("CorePet | Vendas por vendedor", margem, alturaPagina - 9);
    pdf.text(`Página ${pagina} de ${totalPaginas}`, margem + largura, alturaPagina - 9, {
      align: "right",
    });
  }
  return pdf;
}
