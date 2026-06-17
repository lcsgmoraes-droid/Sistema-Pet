import {
  formatarDataRelatorio,
  formatarMoedaRelatorio,
  normalizarProdutoPreview,
  obterHistoricoNfAnterior,
} from "./entradaXmlUtils";

export async function montarDadosRelatorioCustosMaiores({
  api,
  obterResumoCustoItem,
  previewProcessamento,
}) {
  const itensAumentaram = (previewProcessamento?.itens || []).filter((item) => {
    const produto = normalizarProdutoPreview(item);
    const variacao = Number(obterResumoCustoItem(item).variacaoCustoPercentual || 0);
    return produto.produto_id && variacao > 0;
  });

  if (itensAumentaram.length === 0) {
    throw new Error("Nenhum produto com aumento de custo nesta NF.");
  }

  const linhas = await Promise.all(
    itensAumentaram.map(async (item) => {
      const produto = normalizarProdutoPreview(item);
      const resumoCusto = obterResumoCustoItem(item);
      let historicos = [];

      try {
        const historicoRes = await api.get(`/produtos/${produto.produto_id}/historico-precos`, {
          params: { limit: 100 },
        });
        historicos = historicoRes.data || [];
      } catch (error) {
        console.warn(`Nao foi possivel buscar historico do produto ${produto.produto_id}`, error);
      }

      const nfAnterior = obterHistoricoNfAnterior(historicos, previewProcessamento?.numero_nota);
      const custoAnteriorNf = Number(
        nfAnterior?.preco_custo_novo ??
          nfAnterior?.preco_custo_anterior ??
          produto.custo_anterior ??
          0,
      );
      const custoAtualNf = Number(
        resumoCusto.custoSistema ??
          produto.custo_novo ??
          item.custo_aquisicao_unitario_nf ??
          item.custo_unitario_efetivo_nf ??
          item.valor_unitario_nf ??
          0,
      );

      return {
        produto_nome: produto.produto_nome || "Produto sem nome",
        sku: produto.produto_codigo || "",
        ean: produto.produto_ean || "",
        fornecedor: previewProcessamento?.fornecedor_nome || "",
        nf_atual_numero: previewProcessamento?.numero_nota || "",
        nf_atual_data: previewProcessamento?.data_emissao || null,
        nf_atual_custo: custoAtualNf,
        nf_atual_quantidade: Number(item.quantidade_efetiva_nf || item.quantidade_nf || 0),
        nf_anterior_numero: nfAnterior?.nota_numero || "",
        nf_anterior_data: nfAnterior?.nota_data_emissao || nfAnterior?.data || null,
        nf_anterior_custo: custoAnteriorNf,
        variacao_percentual: Number(resumoCusto.variacaoCustoPercentual || 0),
        variacao_absoluta: custoAtualNf - custoAnteriorNf,
        composicao_custo: item.composicao_custo || {},
      };
    }),
  );

  return linhas.sort((a, b) => b.variacao_percentual - a.variacao_percentual);
}

export async function exportarRelatorioCustosMaioresCSV({
  api,
  obterResumoCustoItem,
  previewProcessamento,
  setGerandoRelatorioCustos,
  toast,
}) {
  try {
    setGerandoRelatorioCustos(true);
    const linhas = await montarDadosRelatorioCustosMaiores({
      api,
      obterResumoCustoItem,
      previewProcessamento,
    });
    const headers = [
      "Produto",
      "SKU",
      "EAN",
      "Fornecedor",
      "NF Atual",
      "Data NF Atual",
      "Custo Bruto Unit.",
      "Frete Unit.",
      "Seguro Unit.",
      "Outras Despesas Unit.",
      "Desconto Unit.",
      "ICMS ST Unit.",
      "IPI Unit.",
      "ICMS Unit.",
      "PIS Unit.",
      "COFINS Unit.",
      "Custo Aquisicao Unit.",
      "Qtd NF Atual",
      "NF Anterior",
      "Data NF Anterior",
      "Custo NF Anterior",
      "Variacao %",
      "Variacao R$",
    ];

    const escapeCsv = (valor) => `"${String(valor ?? "").replaceAll('"', '""')}"`;
    const corpo = linhas.map((linha) => {
      const comp = linha.composicao_custo?.componentes_unitario || {};

      return [
        linha.produto_nome,
        linha.sku || "Nao informado",
        linha.ean || "Nao informado",
        linha.fornecedor,
        linha.nf_atual_numero,
        formatarDataRelatorio(linha.nf_atual_data),
        formatarMoedaRelatorio(linha.composicao_custo?.custo_bruto_unitario || 0),
        formatarMoedaRelatorio(comp.valor_frete || 0),
        formatarMoedaRelatorio(comp.valor_seguro || 0),
        formatarMoedaRelatorio(comp.valor_outras_despesas || 0),
        formatarMoedaRelatorio(-(comp.valor_desconto || 0)),
        formatarMoedaRelatorio(comp.valor_icms_st || 0),
        formatarMoedaRelatorio(comp.valor_ipi || 0),
        formatarMoedaRelatorio(comp.valor_icms || 0),
        formatarMoedaRelatorio(comp.valor_pis || 0),
        formatarMoedaRelatorio(comp.valor_cofins || 0),
        formatarMoedaRelatorio(linha.nf_atual_custo),
        linha.nf_atual_quantidade,
        linha.nf_anterior_numero || "Nao encontrado",
        formatarDataRelatorio(linha.nf_anterior_data),
        formatarMoedaRelatorio(linha.nf_anterior_custo),
        `${linha.variacao_percentual.toFixed(2).replace(".", ",")}%`,
        formatarMoedaRelatorio(linha.variacao_absoluta),
      ]
        .map(escapeCsv)
        .join(";");
    });

    const csv = `\uFEFF${headers.join(";")}\n${corpo.join("\n")}`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_custos_maiores_nf_${previewProcessamento?.numero_nota || "nfe"}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast.success("CSV gerado com sucesso!");
  } catch (error) {
    toast.error(error.message || "Erro ao gerar CSV");
  } finally {
    setGerandoRelatorioCustos(false);
  }
}

export async function exportarRelatorioCustosMaioresPDF({
  api,
  obterResumoCustoItem,
  previewProcessamento,
  setGerandoRelatorioCustos,
  toast,
}) {
  try {
    setGerandoRelatorioCustos(true);
    const linhas = await montarDadosRelatorioCustosMaiores({
      api,
      obterResumoCustoItem,
      previewProcessamento,
    });
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
    const marginX = 10;
    const pageWidth = doc.internal.pageSize.getWidth();
    const usableWidth = pageWidth - marginX * 2;
    const tableStartY = 30;
    const minRowHeight = 7;
    const lineHeight = 3.4;

    const colunas = [
      { key: "produto_nome", label: "Produto", width: 58 },
      { key: "sku", label: "SKU", width: 17 },
      { key: "nf_atual_numero", label: "NF", width: 14 },
      { key: "custo_bruto_unitario", label: "Bruto", width: 15 },
      { key: "frete_unitario", label: "Frete", width: 14 },
      { key: "seguro_unitario", label: "Seguro", width: 14 },
      { key: "outras_despesas_unitario", label: "Desp.", width: 14 },
      { key: "desconto_unitario", label: "Desc.", width: 14 },
      { key: "icms_st_unitario", label: "ICMS ST", width: 15 },
      { key: "ipi_unitario", label: "IPI", width: 13 },
      { key: "icms_unitario", label: "ICMS", width: 13 },
      { key: "custo_aquisicao", label: "Custo Total", width: 18 },
      { key: "nf_anterior_numero", label: "NF Ant.", width: 15 },
      { key: "nf_anterior_custo", label: "Custo Ant.", width: 18 },
      { key: "variacao_percentual", label: "Var %", width: 14 },
      { key: "variacao_absoluta", label: "Delta R$", width: 17 },
    ];

    const larguraColunas = colunas.reduce((acc, col) => acc + col.width, 0);
    const escala = larguraColunas > usableWidth ? usableWidth / larguraColunas : 1;
    colunas.forEach((col) => {
      col.width = Number((col.width * escala).toFixed(2));
    });

    const quebrarTexto = (texto, larguraMax, maxLinhas = 2) => {
      const valor = String(texto ?? "");
      if (!valor) return [""];
      const linhas = doc.splitTextToSize(valor, Math.max(4, larguraMax));

      if (linhas.length <= maxLinhas) {
        return linhas;
      }

      const visiveis = linhas.slice(0, maxLinhas);
      const ultima = visiveis[maxLinhas - 1] || "";
      let corte = ultima;

      while (corte.length > 1 && doc.getTextWidth(`${corte}...`) > larguraMax) {
        corte = corte.slice(0, -1);
      }

      visiveis[maxLinhas - 1] = `${corte}...`;
      return visiveis;
    };

    const desenharTextoCelula = (texto, x, y, largura, alinhamento = "left", maxLinhas = 2) => {
      const linhas = quebrarTexto(texto, largura - 2, maxLinhas);
      linhas.forEach((linha, index) => {
        const textX = alinhamento === "right" ? x + largura - 1 : x + 1;
        doc.text(linha, textX, y + 4 + index * lineHeight, {
          align: alinhamento,
          maxWidth: largura - 2,
        });
      });
    };

    const renderCabecalhoPagina = () => {
      doc.setTextColor(30, 41, 59);
      doc.setFontSize(12);
      doc.text(
        `Relatorio de custos maiores - NF ${previewProcessamento?.numero_nota || ""}`,
        marginX,
        10,
      );
      doc.setFontSize(9);
      doc.text(
        `Fornecedor: ${previewProcessamento?.fornecedor_nome || "Nao informado"}`,
        marginX,
        16,
      );
      doc.text(
        `Data de emissao NF atual: ${formatarDataRelatorio(previewProcessamento?.data_emissao)}`,
        marginX,
        21,
      );

      doc.setFillColor(226, 232, 240);
      doc.rect(marginX, tableStartY, usableWidth, minRowHeight, "F");
      doc.setDrawColor(203, 213, 225);
      doc.setTextColor(15, 23, 42);
      doc.setFontSize(7);

      let xAtual = marginX;
      colunas.forEach((coluna) => {
        doc.rect(xAtual, tableStartY, coluna.width, minRowHeight);
        desenharTextoCelula(coluna.label, xAtual, tableStartY, coluna.width, "left", 1);
        xAtual += coluna.width;
      });
    };

    renderCabecalhoPagina();

    let y = tableStartY + minRowHeight;
    linhas.forEach((linha) => {
      const comp = linha.composicao_custo?.componentes_unitario || {};
      const rowData = {
        produto_nome: linha.produto_nome || "-",
        sku: linha.sku || "-",
        nf_atual_numero: linha.nf_atual_numero,
        custo_bruto_unitario: formatarMoedaRelatorio(
          linha.composicao_custo?.custo_bruto_unitario || 0,
        ),
        frete_unitario: formatarMoedaRelatorio(comp.valor_frete || 0),
        seguro_unitario: formatarMoedaRelatorio(comp.valor_seguro || 0),
        outras_despesas_unitario: formatarMoedaRelatorio(comp.valor_outras_despesas || 0),
        desconto_unitario: formatarMoedaRelatorio(-(comp.valor_desconto || 0)),
        icms_st_unitario: formatarMoedaRelatorio(comp.valor_icms_st || 0),
        ipi_unitario: formatarMoedaRelatorio(comp.valor_ipi || 0),
        icms_unitario: formatarMoedaRelatorio(comp.valor_icms || 0),
        custo_aquisicao: formatarMoedaRelatorio(linha.nf_atual_custo),
        nf_anterior_numero: linha.nf_anterior_numero || "-",
        nf_anterior_custo: formatarMoedaRelatorio(linha.nf_anterior_custo),
        variacao_percentual: `${Number(linha.variacao_percentual || 0)
          .toFixed(2)
          .replace(".", ",")}%`,
        variacao_absoluta: formatarMoedaRelatorio(linha.variacao_absoluta),
      };

      const maxLinhasProduto = quebrarTexto(rowData.produto_nome, colunas[0].width - 2, 3).length;
      const maxLinhasSku = quebrarTexto(rowData.sku, colunas[1].width - 2, 2).length;
      const rowHeight = Math.max(
        minRowHeight,
        4 + Math.max(maxLinhasProduto, maxLinhasSku, 1) * lineHeight,
      );

      if (y + rowHeight > 195) {
        doc.addPage();
        renderCabecalhoPagina();
        y = tableStartY + minRowHeight;
      }

      let xAtual = marginX;
      doc.setDrawColor(226, 232, 240);
      doc.setTextColor(15, 23, 42);
      doc.setFontSize(6.5);

      colunas.forEach((coluna) => {
        doc.rect(xAtual, y, coluna.width, rowHeight);
        const valor = rowData[coluna.key] || "";
        const alinhamento =
          coluna.key === "produto_nome" || coluna.key === "sku" || coluna.key.includes("numero")
            ? "left"
            : "right";
        const maxLinhas = coluna.key === "produto_nome" ? 3 : coluna.key === "sku" ? 2 : 1;
        desenharTextoCelula(valor, xAtual, y, coluna.width, alinhamento, maxLinhas);
        xAtual += coluna.width;
      });

      y += rowHeight;
    });

    doc.save(`relatorio_custos_maiores_nf_${previewProcessamento?.numero_nota || "nfe"}.pdf`);
    toast.success("PDF gerado com sucesso!");
  } catch (error) {
    toast.error(error.message || "Erro ao gerar PDF");
  } finally {
    setGerandoRelatorioCustos(false);
  }
}
