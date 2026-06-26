import toast from "react-hot-toast";
import { formatarData, getRelatorioValidadeProxima } from "../../api/produtos";
import { montarParametros } from "./produtosValidadeProximaConstants";
import { normalizarValorCsv } from "./produtosValidadeProximaFormatters";

function baixarCsv(nomeArquivo, linhas) {
  const csv = linhas.join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function montarLinhaCsv(item) {
  return [
    item.nome,
    item.codigo || "",
    item.sku || "",
    item.categoria_nome || "",
    item.marca_nome || "",
    item.fornecedor_nome || "",
    item.nome_lote || "",
    formatarData(item.data_validade),
    item.dias_para_vencer,
    item.quantidade_disponivel,
    item.custo_unitario,
    item.preco_venda,
    item.valor_custo_lote,
    item.valor_venda_lote,
    item.status_validade,
    item.faixa_campanha || "",
    item.promocao_ativa ? "Sim" : "Nao",
    item.campanha_validade_ativa ? "Sim" : "Nao",
    item.campanha_validade_excluida ? "Sim" : "Nao",
    Array.isArray(item.campanha_validade_canais) ? item.campanha_validade_canais.join(", ") : "",
    item.percentual_desconto_validade,
    item.preco_promocional_validade_app,
    item.preco_promocional_validade_ecommerce,
    item.quantidade_promocional,
  ]
    .map((valor) => `"${normalizarValorCsv(valor)}"`)
    .join(";");
}

export async function exportarCsvValidade(filtrosAplicados) {
  toast.loading("Montando relatorio CSV...", { id: "csv-validade" });

  let pagina = 1;
  let totalPaginas = 1;
  const itens = [];

  while (pagina <= totalPaginas) {
    const response = await getRelatorioValidadeProxima(
      montarParametros(filtrosAplicados, pagina, 200),
    );
    const payload = response.data || {};
    const linhasPagina = Array.isArray(payload.items) ? payload.items : [];
    itens.push(...linhasPagina);
    totalPaginas = Number(payload.pages || 0) || 1;
    if (!linhasPagina.length) break;
    pagina += 1;
  }

  if (!itens.length) {
    toast.error("Nenhum lote encontrado para exportacao.", { id: "csv-validade" });
    return;
  }

  const cabecalho = [
    "Produto",
    "Codigo",
    "SKU",
    "Categoria",
    "Marca",
    "Fornecedor",
    "Lote",
    "Validade",
    "Dias para vencer",
    "Quantidade",
    "Custo unitario",
    "Preco venda",
    "Valor custo lote",
    "Valor venda lote",
    "Status validade",
    "Faixa campanha",
    "Promocao ativa",
    "Campanha validade ativa",
    "Campanha validade excluida",
    "Canais campanha",
    "Desconto campanha",
    "Preco campanha app",
    "Preco campanha site",
    "Quantidade promocional",
  ]
    .map((coluna) => `"${coluna}"`)
    .join(";");

  const dataArquivo = new Date().toISOString().slice(0, 10);
  baixarCsv(`validade_proxima_${dataArquivo}.csv`, [cabecalho, ...itens.map(montarLinhaCsv)]);
  toast.success(`CSV gerado com ${itens.length} lote(s).`, { id: "csv-validade" });
}
