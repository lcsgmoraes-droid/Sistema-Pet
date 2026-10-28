import { formatMoneyBRL, formatPercent } from "../../utils/formatters.js";
import { CANAIS_VENDA } from "./analiseProdutosUtils.js";

const numero = (valor) => (Number.isFinite(Number(valor)) ? Number(valor) : 0);
const quantidade = (valor) => numero(valor).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const textoPdf = (valor) =>
  String(valor ?? "-")
    .replace(/\u00a0/g, " ")
    .replace(/[\u2010-\u2015]/g, "-");
const nomeCadastro = (item) =>
  item?.nome_fantasia || item?.razao_social || item?.nome || item?.name || "";
const dataBr = (valor) => {
  const data = String(valor || "").slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(data)
    ? `${data.slice(8, 10)}/${data.slice(5, 7)}/${data.slice(0, 4)}`
    : "-";
};

// Recebe exclusivamente o resultado já filtrado da tela; não busca outros produtos ou empresas.
export function prepararDadosProdutosPorFornecedorPdf({
  produtos = [],
  filtros = {},
  catalogos = {},
  empresa = null,
  geradoEm = new Date(),
  incluirVendedores = false,
} = {}) {
  const resolverNome = (lista, id, campo) => {
    const cadastro = (Array.isArray(lista) ? lista : []).find(
      (item) => String(item.id) === String(id),
    );
    return (
      nomeCadastro(cadastro) ||
      produtos.find((item) => String(item[`${campo}_id`]) === String(id))?.[`${campo}_nome`] ||
      (campo === "fornecedor" ? "Fornecedor sem nome informado" : `Código ${id}`)
    );
  };
  const fornecedor = filtros.fornecedor_id
    ? resolverNome(catalogos.fornecedores, filtros.fornecedor_id, "fornecedor")
    : "Todos os fornecedores";
  const filtrosDescricao = [];
  for (const [campo, rotulo, lista] of [
    ["categoria", "Categoria", "categorias"],
    ["marca", "Marca", "marcas"],
    ["departamento", "Departamento", "departamentos"],
  ]) {
    if (filtros[`${campo}_id`]) {
      filtrosDescricao.push(
        `${rotulo}: ${resolverNome(catalogos[lista], filtros[`${campo}_id`], campo)}`,
      );
    }
  }
  filtrosDescricao.push(
    `Canal: ${CANAIS_VENDA.find((item) => item.value === (filtros.canal || ""))?.label || filtros.canal}`,
  );
  if (filtros.busca?.trim()) filtrosDescricao.push(`Busca: ${filtros.busca.trim()}`);

  const agrupados = new Map();
  for (const produto of produtos) {
    const id = produto.fornecedor_id ?? "sem-fornecedor";
    const grupo = agrupados.get(id) || {
      id,
      nome: produto.fornecedor_nome || "Sem fornecedor",
      produtos: [],
      quantidade: 0,
      faturamento: 0,
    };
    grupo.produtos.push(produto);
    grupo.quantidade += numero(produto.quantidade);
    grupo.faturamento += numero(produto.faturamento);
    agrupados.set(id, grupo);
  }
  const grupos = [...agrupados.values()]
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
    .map((grupo) => {
      const ordenados = [...grupo.produtos].sort(
        (a, b) =>
          numero(b.faturamento) - numero(a.faturamento) ||
          String(a.produto_nome || "").localeCompare(String(b.produto_nome || ""), "pt-BR"),
      );
      return {
        ...grupo,
        quantidade: Number(grupo.quantidade.toFixed(3)),
        faturamento: Number(grupo.faturamento.toFixed(2)),
        linhas: ordenados.map((produto) => [
          produto.produto_nome || "Produto sem nome",
          produto.codigo || "-",
          quantidade(produto.quantidade),
          formatMoneyBRL(numero(produto.faturamento)),
        ]),
        linhasVendedores: incluirVendedores
          ? ordenados.map((produto) =>
              [...(Array.isArray(produto.vendedores) ? produto.vendedores : [])]
                .sort(
                  (a, b) =>
                    numero(b.faturamento) - numero(a.faturamento) ||
                    String(a.vendedor_nome || "").localeCompare(
                      String(b.vendedor_nome || ""),
                      "pt-BR",
                    ),
                )
                .map((vendedor) => [
                  `Vendedor: ${vendedor.vendedor_nome || "Sem vendedor informado"}`,
                  "",
                  quantidade(vendedor.quantidade),
                  formatMoneyBRL(numero(vendedor.faturamento)),
                  formatPercent(numero(vendedor.participacao_faturamento_pct)),
                ]),
            )
          : [],
      };
    });
  const totalQuantidade = produtos.reduce((soma, item) => soma + numero(item.quantidade), 0);
  const totalFaturamento = produtos.reduce((soma, item) => soma + numero(item.faturamento), 0);

  return {
    empresa: typeof empresa === "string" ? empresa : nomeCadastro(empresa),
    periodo: `${dataBr(filtros.data_inicio)} a ${dataBr(filtros.data_fim)}`,
    geradoEm: new Date(geradoEm).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }),
    fornecedor,
    filtros: filtrosDescricao.join(" | "),
    incluirVendedores,
    grupos,
    totalizadores: `${produtos.length} produto(s) | Quantidade: ${quantidade(totalQuantidade)} | Faturamento: ${formatMoneyBRL(totalFaturamento)}`,
    nota: filtros.fornecedor_id
      ? "Fornecedor conforme o cadastro atual: principal ou vínculo alternativo ativo. Não identifica a origem por lote."
      : "Agrupamento pelo fornecedor principal atual de cada produto. Não identifica a origem por lote.",
  };
}

export async function criarPdfProdutosPorFornecedor(opcoes = {}) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const dados = prepararDadosProdutosPorFornecedorPdf(opcoes);
  const margem = 14;
  const largura = pdf.internal.pageSize.getWidth() - margem * 2;
  const alturaPagina = pdf.internal.pageSize.getHeight();
  const limite = alturaPagina - 19;
  const inicioConteudo = 37;
  const alturaLinha = 4.2;
  const padding = 2.5;
  const colunas = dados.incluirVendedores
    ? [
        { titulo: "Produto / vendedor", proporcao: 0.44 },
        { titulo: "Código / SKU", proporcao: 0.15 },
        { titulo: "Quantidade", proporcao: 0.12, direita: true },
        { titulo: "Faturamento", proporcao: 0.17, direita: true },
        { titulo: "% do produto", proporcao: 0.12, direita: true },
      ]
    : [
        { titulo: "Produto", proporcao: 0.55 },
        { titulo: "Código / SKU", proporcao: 0.16 },
        { titulo: "Quantidade", proporcao: 0.12, direita: true },
        { titulo: "Faturamento", proporcao: 0.17, direita: true },
      ];
  const larguras = colunas.map((coluna) => largura * coluna.proporcao);
  let y = inicioConteudo;

  const fonte = (tamanho = 9, negrito = false, cor = [40, 50, 65]) => {
    pdf.setFont("helvetica", negrito ? "bold" : "normal");
    pdf.setFontSize(tamanho);
    pdf.setTextColor(...cor);
  };
  const escreverLinhas = (linhas, x, yy, tamanho, direita = false) => {
    pdf.text(linhas, x, yy, {
      align: direita ? "right" : "left",
      lineHeightFactor: (alturaLinha * 72) / (25.4 * tamanho),
    });
  };
  const cabecalhoPagina = () => {
    fonte(11, true, [13, 120, 115]);
    pdf.text("CorePet", margem, 15);
    fonte(17, true, [26, 45, 73]);
    pdf.text("Produtos vendidos por fornecedor", margem, 25);
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
  const paragrafo = (texto, { tamanho = 9, negrito = false, espacoDepois = 2 } = {}) => {
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

  const tabelaGrupo = (grupo) => {
    const titulo = `Fornecedor: ${grupo.nome}`;
    fonte(10, true);
    const alturaTituloMaxima =
      pdf.splitTextToSize(textoPdf(`${titulo} (continuação)`), largura).length * alturaLinha + 3;
    const alturaCabecalho = 9;
    const alturaSecao = alturaTituloMaxima + alturaCabecalho;
    const cabecalhoTabela = (continuacao = false) => {
      fonte(10, true, [26, 45, 73]);
      const tituloLinhas = pdf.splitTextToSize(
        textoPdf(`${titulo}${continuacao ? " (continuação)" : ""}`),
        largura,
      );
      escreverLinhas(tituloLinhas, margem, y + 4, 10);
      y += tituloLinhas.length * alturaLinha + 3;
      pdf.setFillColor(230, 242, 241);
      pdf.rect(margem, y, largura, alturaCabecalho, "F");
      fonte(8.5, true, [26, 70, 73]);
      let x = margem;
      colunas.forEach((coluna, indice) => {
        pdf.text(
          coluna.titulo,
          coluna.direita ? x + larguras[indice] - padding : x + padding,
          y + 5.7,
          {
            align: coluna.direita ? "right" : "left",
          },
        );
        x += larguras[indice];
      });
      y += alturaCabecalho;
    };
    const continuar = () => {
      novaPagina();
      cabecalhoTabela(true);
    };

    if (y + alturaSecao + 10 > limite) novaPagina();
    cabecalhoTabela();
    const desenharLinha = (
      valores,
      { vendedor = false, alternada = false, aoContinuar = continuar } = {},
    ) => {
      fonte(8.5, dados.incluirVendedores && !vendedor);
      const celulas = valores.map((valor, indiceColuna) =>
        pdf.splitTextToSize(
          textoPdf(valor),
          larguras[indiceColuna] - padding * 2 - (vendedor && indiceColuna === 0 ? 4 : 0),
        ),
      );
      const totalLinhas = Math.max(1, ...celulas.map((linhas) => linhas.length));
      const alturaTotal = totalLinhas * alturaLinha + padding * 2;
      if (y + alturaTotal > limite && alturaTotal <= limite - inicioConteudo - alturaSecao)
        aoContinuar();

      let inicioLinha = 0;
      while (inicioLinha < totalLinhas) {
        let capacidade = Math.floor((limite - y - padding * 2) / alturaLinha);
        if (capacidade < 1) {
          aoContinuar();
          capacidade = Math.floor((limite - y - padding * 2) / alturaLinha);
        }
        const quantidadeLinhas = Math.min(capacidade, totalLinhas - inicioLinha);
        const altura = quantidadeLinhas * alturaLinha + padding * 2;
        if (vendedor || alternada) {
          pdf.setFillColor(...(vendedor ? [241, 248, 247] : [247, 249, 251]));
          pdf.rect(margem, y, largura, altura, "F");
        }
        fonte(8.5, dados.incluirVendedores && !vendedor, vendedor ? [65, 88, 94] : [40, 50, 65]);
        let x = margem;
        celulas.forEach((linhas, indiceColuna) => {
          const parte = linhas.slice(inicioLinha, inicioLinha + quantidadeLinhas);
          if (parte.length) {
            const direita = colunas[indiceColuna].direita;
            escreverLinhas(
              parte,
              direita
                ? x + larguras[indiceColuna] - padding
                : x + padding + (vendedor && indiceColuna === 0 ? 4 : 0),
              y + 5.5,
              8.5,
              direita,
            );
          }
          x += larguras[indiceColuna];
        });
        pdf.setDrawColor(224, 230, 236);
        pdf.line(margem, y + altura, margem + largura, y + altura);
        y += altura;
        inicioLinha += quantidadeLinhas;
        if (inicioLinha < totalLinhas) aoContinuar();
      }
    };
    grupo.linhas.forEach((valores, indiceLinha) => {
      const vendedores = grupo.linhasVendedores[indiceLinha] || [];
      // Evita deixar um produto sozinho no fim da página quando há vendedores abaixo.
      if (vendedores.length && y + 25 > limite) continuar();
      desenharLinha(valores, { alternada: indiceLinha % 2 === 0 });
      const continuarVendedores = () => {
        continuar();
        fonte(8, true, [26, 70, 73]);
        const contexto = pdf.splitTextToSize(
          textoPdf(`Vendedores de ${valores[0]} (${valores[1]})`),
          largura - padding * 2,
        );
        const rotulo = contexto.length > 2 ? [contexto[0], `${contexto[1]}...`] : contexto;
        escreverLinhas(rotulo, margem + padding, y + 4.5, 8);
        y += rotulo.length * alturaLinha + 4;
      };
      vendedores.forEach((linha) =>
        desenharLinha(linha, { vendedor: true, aoContinuar: continuarVendedores }),
      );
    });
    y += 5;
    paragrafo(
      `Subtotal: ${grupo.produtos.length} produto(s) | Quantidade: ${quantidade(grupo.quantidade)} | Faturamento: ${formatMoneyBRL(grupo.faturamento)}`,
      { negrito: true, espacoDepois: 7 },
    );
  };

  cabecalhoPagina();
  if (dados.empresa) paragrafo(`Empresa: ${dados.empresa}`, { negrito: true });
  paragrafo(`Fornecedor: ${dados.fornecedor}`);
  paragrafo(dados.filtros, { tamanho: 8 });
  paragrafo(dados.totalizadores, { tamanho: 10, negrito: true, espacoDepois: 3 });
  paragrafo(dados.nota, { tamanho: 8, espacoDepois: 5 });
  if (dados.incluirVendedores)
    paragrafo(
      "Vendedores abaixo de cada produto. A participação corresponde ao faturamento do vendedor sobre o total desse produto no filtro aplicado.",
      { tamanho: 8, espacoDepois: 5 },
    );
  if (!dados.grupos.length)
    paragrafo("Nenhuma venda de produto encontrada para os filtros aplicados.");
  for (const grupo of dados.grupos) tabelaGrupo(grupo);
  if (dados.grupos.length)
    paragrafo(`Total geral: ${dados.totalizadores}`, { tamanho: 10, negrito: true });

  const totalPaginas = pdf.internal.getNumberOfPages();
  for (let pagina = 1; pagina <= totalPaginas; pagina += 1) {
    pdf.setPage(pagina);
    fonte(8, false, [100, 110, 125]);
    pdf.text("CorePet | Produtos vendidos por fornecedor", margem, alturaPagina - 9);
    pdf.text(`Página ${pagina} de ${totalPaginas}`, margem + largura, alturaPagina - 9, {
      align: "right",
    });
  }
  return pdf;
}
